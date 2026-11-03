"""
MiniMax API 翻译备选。
mymemory 失败（限流/超时/错误）时降级用。

配置（写入 /home/toolbox/toolbox.env）:
    MiniMax_API_KEY=sk-ant-xxx
    MiniMax_MODEL=MiniMax-M3
    MiniMax_BASE_URL=https://api.minimaxi.com/anthropic

API 协议: Anthropic Messages（baseUrl 末尾为 /anthropic 时去掉前缀，
         用相对路径 /v1/messages）。
"""

import json
import os
import time
import urllib.error
import urllib.request

ENV_PATH = os.environ.get("TOOLBOX_ENV", "/home/toolbox/toolbox.env")

# 语言代码转人类可读名称，写进 prompt 让 LLM 翻译
_LANG_NAME = {
    'auto': 'auto-detect',
    'zh-CN': 'Simplified Chinese',
    'zh': 'Simplified Chinese',
    'en': 'English',
    'ja': 'Japanese',
    'ko': 'Korean',
    'fr': 'French',
    'de': 'German',
    'es': 'Spanish',
}

# 简单内存缓存（重启失效）。命中就不调后端，省配额。
_CACHE = {}
_CACHE_MAX = 512


def _load_env():
    if not os.path.isfile(ENV_PATH):
        return
    try:
        with open(ENV_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, val = line.split("=", 1)
                key = key.strip()
                val = val.strip().strip('"').strip("'")
                if key and key not in os.environ:
                    os.environ[key] = val
    except Exception:
        pass


def is_configured():
    _load_env()
    return bool(os.environ.get("MiniMax_API_KEY", "").strip())


def _cache_key(text, src, tgt):
    import hashlib
    h = hashlib.sha1((text + '|' + src + '|' + tgt).encode('utf-8')).hexdigest()
    return h


def translate_with_minimax(text, source_lang, target_lang, _retry=0):
    """用 MiniMax API 翻译单段文本。

    返回译文字符串。失败抛 ValueError，调用方应捕获后透传给用户或再降级。
    """
    _load_env()
    api_key = os.environ.get("MiniMax_API_KEY", "").strip()
    if not api_key:
        raise ValueError("MiniMax API key 未配置")

    # 缓存命中：直接返回，省 token
    key = _cache_key(text, source_lang or 'auto', target_lang)
    if key in _CACHE:
        return _CACHE[key]

    model = os.environ.get("MiniMax_MODEL", "MiniMax-M3").strip()
    base_url = os.environ.get("MiniMax_BASE_URL", "https://api.minimaxi.com/anthropic").strip()
    url = base_url.rstrip("/") + "/v1/messages"

    src_name = _LANG_NAME.get(source_lang, source_lang or 'auto-detect')
    tgt_name = _LANG_NAME.get(target_lang, target_lang)
    if source_lang == 'auto':
        system_prompt = (
            "You are a professional translator. Detect the source language and "
            f"translate the user text into {tgt_name}. Output ONLY the translation, "
            "no explanation, no quotation marks."
        )
        user_prompt = text
    else:
        system_prompt = (
            f"You are a professional translator. Translate the user text from "
            f"{src_name} into {tgt_name}. Output ONLY the translation, no explanation, "
            "no quotation marks."
        )
        user_prompt = text

    payload = {
        "model": model,
        "max_tokens": min(len(text) * 4 + 256, 4096),
        "system": system_prompt,
        "messages": [{"role": "user", "content": user_prompt}],
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        # 529/429/5xx 重试一次
        if e.code in (429, 500, 502, 503, 504, 529) and _retry < 1:
            time.sleep(1.5)
            return translate_with_minimax(text, source_lang, target_lang, _retry=_retry + 1)
        try:
            err_body = e.read().decode("utf-8", errors="replace")[:200]
        except Exception:
            err_body = ""
        raise ValueError(f"MiniMax HTTP {e.code}: {err_body}") from e
    except Exception as e:
        raise ValueError(f"MiniMax 请求失败：{e}") from e

    # 解析 Anthropic Messages 响应
    try:
        content = body.get("content", [])
        parts = []
        for c in content:
            if c.get("type") == "text":
                parts.append(c.get("text", ""))
        result = "".join(parts).strip()
    except Exception as e:
        raise ValueError(f"MiniMax 响应解析失败：{e}") from e

    if not result:
        raise ValueError("MiniMax 返回空结果")

    # LRU 简化版：超过上限清一半
    if len(_CACHE) >= _CACHE_MAX:
        for _ in range(_CACHE_MAX // 2):
            _CACHE.pop(next(iter(_CACHE)), None)
    _CACHE[key] = result
    return result
