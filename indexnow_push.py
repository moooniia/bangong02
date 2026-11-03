#!/usr/bin/env python3
# IndexNow 推送 - Bing / Yandex / Seznam / Naver 秒级收录通道
# 说明：Google 官方不支持 IndexNow，Google 需要走 Search Console 提交 sitemap。
import json, time, uuid
import xml.etree.ElementTree as ET
from urllib.request import urlopen, Request

SITEMAP = 'https://www.bangong02.com/sitemap.xml'
HOST = 'www.bangong02.com'
KEY = '5834ea35bd294de2832bf28a9934444fab77fb5e4f2a45ba'
KEY_LOCATION = 'https://%s/%s.txt' % (HOST, KEY)
ENDPOINT = 'https://api.indexnow.org/indexnow'


def get_urls():
    r = urlopen(SITEMAP, timeout=30)
    root = ET.fromstring(r.read())
    ns = '{http://www.sitemaps.org/schemas/sitemap/0.9}'
    return [u.find(ns + 'loc').text.strip()
            for u in root.findall(ns + 'url')
            if u.find(ns + 'loc') is not None and u.find(ns + 'loc').text]


def submit(urls):
    payload = {
        'host': HOST,
        'key': KEY,
        'keyLocation': KEY_LOCATION,
        'urlList': urls,
    }
    data = json.dumps(payload).encode('utf-8')
    req = Request(ENDPOINT, data=data, headers={
        'Content-Type': 'application/json; charset=utf-8',
        'User-Agent': 'Mozilla/5.0 (compatible; bangong02-indexnow/1.0)',
    }, method='POST')
    try:
        with urlopen(req, timeout=60) as resp:
            return resp.status, resp.read().decode('utf-8', 'ignore') or '(空响应)'
    except Exception as e:
        detail = ''
        if hasattr(e, 'read'):
            try:
                detail = e.read().decode('utf-8', 'ignore')
            except Exception:
                pass
        return getattr(e, 'code', 'ERR'), detail or str(e)


if __name__ == '__main__':
    print('[%s] indexnow push start' % time.strftime('%Y-%m-%d %H:%M:%S'))
    urls = get_urls()
    print('[INFO] got %d urls from sitemap' % len(urls))
    if not urls:
        print('[SKIP] no urls')
        raise SystemExit(0)
    # IndexNow 单次上限 10000 条，全站 39 条一次推完
    code, body = submit(urls)
    print('[RESULT] http=%s body=%s' % (code, body[:300]))
    if code in (200, 202):
        print('[OK] 已提交给 IndexNow，Bing 通常几分钟到几天内抓取')
    elif code == 429:
        print('[WARN] 提交过于频繁，被限流，稍后再试')
    else:
        print('[FAIL] 提交失败，请检查 key 文件是否可访问: %s' % KEY_LOCATION)
    print('[DONE] submitted=%d' % len(urls))
