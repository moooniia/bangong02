#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
网站访问量 / 工具调用量 汇总脚本（服务器端每日 cron 运行）

数据来源：nginx access.log（含已压缩的历史 gz）
设计要点：
  1. 只统计「真人」：
     - 巡检脚本 monitor_check.py 直连 127.0.0.1:5000，不经过 nginx，
       所以 nginx 日志里本来就没有巡检流量，天然排除。
     - 外部扫描（打 /wp-admin、/xmlrpc.php、/api/.env 等探测路径）用路径黑名单排除。
     - 明显的爬虫/扫描 UA（bot、python-requests、zgrab 等）排除。
  2. 访问量(PV) = 真实页面（*.html 或首页）的 GET 次数；
     独立访客(UV) = 按客户端 IP 去重。
  3. 工具调用量 = 走 nginx 的真实 /api/ 接口调用（同样排除探测路径）。
  4. 长期累计：每次运行解析「当前日志 + 仍在保留期内的 gz」，
     用解析结果覆盖对应日期，但保留已超出日志保留期、不再出现的旧日期，
     从而实现数月趋势累积。
"""
import os
import re
import gzip
import json
import glob
import argparse
from collections import defaultdict
from datetime import datetime

# ---- 路径（可用环境变量覆盖，方便本地用样例日志测试） ----
NGINX_LOG_DIR = os.environ.get("NGINX_LOG_DIR", "/var/log/nginx")
HISTORY_PATH = os.environ.get(
    "STATS_HISTORY",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "stats_history.json"),
)

# 扫描 / 探测路径黑名单（命中即不算真人）
SCAN_RE = re.compile(
    r"(/wp-admin|/wp-login|/xmlrpc\.php|/phpmyadmin|/\.env|/admin|/config|"
    r"/api/\.env|/api/graphql|/api/v1/|/api/settings|/api/config|/boaform|"
    r"/shell|/vendor/|/\.git|/php$|/cgi-bin|/actuator|/console|/setup\.php|"
    r"/jndi|/solr|/manager/html|/api/users|/api/login|/api/auth|/ecp/|"
    r"/.well-known/|/api/_|/api/test)",
    re.I,
)

# 明显爬虫 / 扫描 UA
BOT_UA_RE = re.compile(
    r"(bot|spider|crawl|semrush|ahrefs|mj12|dotbot|python-requests|curl|wget|"
    r"zgrab|nmap|scanner|masscan|netsystems|bytespider|bingpreview|go-http|"
    r"java/|okhttp|headless|phantom)",
    re.I,
)

# 工具接口（/api/...）扫描 / 探测过滤：路径穿越、注入、空接口、超长 fuzzing 段
API_SCAN_RE = re.compile(
    r"(\.\./|/etc/passwd|/proc/self|union\s+select|select\s+.+\s+from|"
    r"/api/?$|/api/[A-Za-z0-9]{80,})",
    re.I,
)

PAGE_RE = re.compile(r"^/(?:index\.html)?$|^/[^/?#]+\.html$")
API_RE = re.compile(r"^/api/")

LINE_RE = re.compile(
    r'^(?P<ip>\S+)\s+\S+\s+\S+\s+\[(?P<time>[^\]]+)\]\s+'
    r'"(?P<method>[A-Z]+)\s+(?P<path>\S+)[^"]*"\s+(?P<status>\d+)\s+'
    r'\S+\s+"[^"]*"\s+"(?P<ua>[^"]*)"'
)


def _parse_line(line):
    m = LINE_RE.search(line)
    if not m:
        return None
    try:
        dt = datetime.strptime(m.group("time"), "%d/%b/%Y:%H:%M:%S %z")
    except Exception:
        return None
    return (
        m.group("ip"),
        dt,
        m.group("method"),
        m.group("path"),
        m.group("status"),
        m.group("ua"),
    )


def _iter_log_lines(log_dir):
    for path in sorted(glob.glob(os.path.join(log_dir, "access.log*"))):
        if path.endswith(".gz"):
            try:
                with gzip.open(path, "rt", errors="ignore") as f:
                    for line in f:
                        yield line
            except Exception:
                continue
        else:
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        yield line
            except Exception:
                continue


def aggregate(log_dir):
    """返回 {date: {'pv':int,'uv':int,'pages':{path:cnt},'tools':{api:cnt}}}"""
    days = defaultdict(lambda: {"pv": 0, "uv": set(), "pages": defaultdict(int), "tools": defaultdict(int)})
    for line in _iter_log_lines(log_dir):
        parsed = _parse_line(line)
        if not parsed:
            continue
        ip, dt, method, path, status, ua = parsed
        date_key = dt.date().isoformat()

        # 扫描路径 => 跳过
        if SCAN_RE.search(path):
            continue
        # 扫描/爬虫 UA => 跳过
        if BOT_UA_RE.search(ua or ""):
            continue

        d = days[date_key]
        # 真实页面访问（PV / UV）
        if method == "GET" and (PAGE_RE.match(path) or path == "/"):
            d["pv"] += 1
            d["uv"].add(ip)
            # 归一化首页
            norm = "/" if path in ("/", "/index.html") else path
            d["pages"][norm] += 1
        # 真实工具接口调用（先过滤 /api/ 探测）
        elif API_RE.match(path):
            if API_SCAN_RE.search(path):
                continue
            d["tools"][path] += 1
    return days


def to_serializable(days):
    out = {}
    for date_key, d in days.items():
        out[date_key] = {
            "pv": d["pv"],
            "uv": len(d["uv"]),
            "pages": dict(d["pages"]),
            "tools": dict(d["tools"]),
        }
    return out


def run(log_dir=None, history_path=None, verbose=False):
    log_dir = log_dir or NGINX_LOG_DIR
    history_path = history_path or HISTORY_PATH

    # 旧历史（保留已超出日志保留期、不再出现的旧日期）
    old = {}
    if os.path.exists(history_path):
        try:
            with open(history_path, encoding="utf-8") as f:
                old = json.load(f)
        except Exception:
            old = {}

    parsed = aggregate(log_dir)
    merged = dict(old)  # 先复制旧的全部
    for date_key, d in to_serializable(parsed).items():
        merged[date_key] = d  # 用本轮解析结果覆盖（本轮数据更全）

    merged = dict(sorted(merged.items()))
    with open(history_path, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)

    if verbose:
        print(f"日志目录: {log_dir}")
        print(f"历史文件: {history_path}")
        print(f"本轮解析日期数: {len(parsed)}，历史总日期数: {len(merged)}")
        for k in sorted(parsed.keys())[-5:]:
            v = merged[k]
            tool_sum = sum(v["tools"].values())
            print(f"  {k}: PV={v['pv']} UV={v['uv']} 工具调用={tool_sum}")
    return merged


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--log-dir", default=None, help="nginx 日志目录（默认 /var/log/nginx）")
    ap.add_argument("--history", default=None, help="输出 json 路径")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()
    run(args.log_dir, args.history, args.verbose)
