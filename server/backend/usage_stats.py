"""付费API调用次数计数器，按天记录到一个json文件，不用数据库。"""
import json
import os
import threading
from datetime import date

_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'api_usage.json')
_LOCK = threading.Lock()


def bump(metric):
    """给某个付费接口的今日计数 +1，出错也不影响主流程。"""
    try:
        today = date.today().isoformat()
        with _LOCK:
            data = {}
            if os.path.exists(_PATH):
                try:
                    with open(_PATH, encoding='utf-8') as f:
                        data = json.load(f)
                except Exception:
                    data = {}
            day = data.setdefault(today, {})
            day[metric] = day.get(metric, 0) + 1
            with open(_PATH, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def report(days=30):
    """返回最近 N 天的计数，外加总计，用于打印/巡检。"""
    if not os.path.exists(_PATH):
        return {}, {}
    with open(_PATH, encoding='utf-8') as f:
        data = json.load(f)
    recent_dates = sorted(data.keys())[-days:]
    recent = {d: data[d] for d in recent_dates}
    totals = {}
    for day in recent.values():
        for metric, count in day.items():
            totals[metric] = totals.get(metric, 0) + count
    return recent, totals
