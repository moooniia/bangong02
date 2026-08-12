#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
本地预览用开发服务器（仅本地，不上传服务器）。
- 在 8000 端口 serve frontend 静态文件
- /api/stats 返回由真实 nginx 日志生成的统计（_real_stats_history.json）
这样统计页在本地就能看到真实数据，部署到服务器后由 app.py 的 /api/stats 接管。
"""
import os
import json
import http.server
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
FRONTEND = os.path.join(HERE, "frontend")
HISTORY = os.path.join(HERE, "backend", "_real_stats_history.json")


def build_stats():
    with open(HISTORY, encoding="utf-8") as f:
        history = json.load(f)
    dates = sorted(history.keys())
    pv = [history[d]["pv"] for d in dates]
    uv = [history[d]["uv"] for d in dates]
    tools_daily = [sum(history[d].get("tools", {}).values()) for d in dates]
    pages_total, tools_total = {}, {}
    for d in history.values():
        for k, v in d.get("pages", {}).items():
            pages_total[k] = pages_total.get(k, 0) + v
        for k, v in d.get("tools", {}).items():
            tools_total[k] = tools_total.get(k, 0) + v
    pages = sorted(pages_total.items(), key=lambda x: -x[1])[:10]
    top_tools = sorted(tools_total.items(), key=lambda x: -x[1])[:10]
    latest = dates[-1]
    ld = history[latest]
    today_tools = sorted(ld.get("tools", {}).items(), key=lambda x: -x[1])[:10]
    today = {"pv": ld["pv"], "uv": ld["uv"], "tools": sum(ld.get("tools", {}).values())}
    return {
        "days": dates,
        "pv": pv,
        "uv": uv,
        "tools": tools_daily,
        "pages": [{"name": k, "count": v} for k, v in pages],
        "topTools": [{"name": k, "count": v} for k, v in top_tools],
        "todayTools": [{"name": k, "count": v} for k, v in today_tools],
        "today": today,
    }


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=FRONTEND, **kw)

    def do_GET(self):
        if self.path.startswith("/api/toolbox-stats"):
            body = json.dumps(build_stats(), ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        return super().do_GET()

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    srv = ThreadingHTTPServer(("0.0.0.0", 8000), Handler)
    print("本地预览服务器已启动: http://localhost:8000  (真实数据模式)")
    srv.serve_forever()
