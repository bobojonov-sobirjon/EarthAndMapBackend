"""gov.uz sahifalarini ichki iframe uchun proxy (X-Frame-Options olib tashlanadi)."""
from __future__ import annotations

import re
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse, urlunparse
from urllib.request import Request, urlopen

_USER_AGENT = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
    'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
)

_CSP_META_RE = re.compile(
    r'<meta[^>]+http-equiv=["\']Content-Security-Policy["\'][^>]*>',
    re.IGNORECASE,
)
_HEAD_RE = re.compile(r'(<head[^>]*>)', re.IGNORECASE)


def normalize_https_url(url: str) -> str:
    raw = (url or '').strip()
    if not raw:
        return ''
    if not raw.lower().startswith(('http://', 'https://')):
        raw = f'https://{raw}'
    parsed = urlparse(raw)
    if parsed.scheme != 'https':
        return ''
    return urlunparse(parsed)


def is_allowed_embed_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        host = (parsed.hostname or '').lower()
        if not host:
            return False
        if host == 'gov.uz' or host.endswith('.gov.uz'):
            return True
        return False
    except ValueError:
        return False


def _html_base_url(page_url: str) -> str:
    parsed = urlparse(page_url)
    path = parsed.path or '/'
    if not path.endswith('/'):
        path = path.rsplit('/', 1)[0] + '/'
    return urlunparse((parsed.scheme, parsed.netloc, path, '', '', ''))


def _prepare_html(html: bytes, page_url: str) -> bytes:
    text = html.decode('utf-8', errors='replace')
    text = _CSP_META_RE.sub('', text)
    base_href = _html_base_url(page_url)
    base_tag = f'<base href="{base_href}">'
    if _HEAD_RE.search(text):
        text = _HEAD_RE.sub(r'\1' + base_tag, text, count=1)
    else:
        text = base_tag + text
    return text.encode('utf-8')


def fetch_embed_content(url: str) -> tuple[bytes, str]:
    """(content, content_type)"""
    req = Request(url, headers={'User-Agent': _USER_AGENT, 'Accept-Language': 'uz,ru,en'})
    with urlopen(req, timeout=25) as resp:
        raw = resp.read()
        ctype = resp.headers.get('Content-Type', 'text/html; charset=utf-8')
        if 'text/html' in ctype.lower():
            return _prepare_html(raw, url), 'text/html; charset=utf-8'
        return raw, ctype.split(';')[0]


def fetch_embed_safe(url: str, use_selenium: bool = True) -> tuple[bytes, str] | None:
    normalized = normalize_https_url(url)
    if not normalized or not is_allowed_embed_url(normalized):
        return None

    if use_selenium:
        try:
            from django.conf import settings
            if getattr(settings, 'EMBED_USE_SELENIUM', True):
                from .embed_selenium import fetch_with_selenium
                wait = int(getattr(settings, 'EMBED_SELENIUM_WAIT_SEC', 8))
                selenium_result = fetch_with_selenium(normalized, wait_sec=wait)
                if selenium_result:
                    return selenium_result
        except Exception:
            pass

    try:
        return fetch_embed_content(normalized)
    except (HTTPError, URLError, TimeoutError, ValueError):
        return None
