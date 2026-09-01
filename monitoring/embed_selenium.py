"""gov.uz sahifalarini Selenium (headless Chrome) orqali yuklash."""
from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Iterator

from .embed_proxy import _prepare_html, is_allowed_embed_url, normalize_https_url

logger = logging.getLogger(__name__)

_USER_AGENT = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
    'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
)


@contextmanager
def _chrome_driver() -> Iterator:
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
    except ImportError:
        logger.warning('selenium o\'rnatilmagan — pip install selenium')
        yield None
        return

    options = Options()
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1440,900')
    options.add_argument('--lang=uz-UZ')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument(f'--user-agent={_USER_AGENT}')
    options.page_load_strategy = 'normal'

    driver = None
    try:
        driver = webdriver.Chrome(options=options)
        driver.set_page_load_timeout(45)
        yield driver
    finally:
        if driver is not None:
            try:
                driver.quit()
            except Exception:
                pass


def _wait_ready(driver, wait_sec: int) -> None:
    from selenium.webdriver.support.ui import WebDriverWait
    WebDriverWait(driver, wait_sec).until(
        lambda d: d.execute_script('return document.readyState') == 'complete',
    )
    driver.implicitly_wait(2)


def capture_screenshot(url: str, wait_sec: int = 10) -> bytes | None:
    """Sahifa skrinshoti (PNG) — Next.js proxy xatosiz."""
    normalized = normalize_https_url(url)
    if not normalized or not is_allowed_embed_url(normalized):
        return None

    with _chrome_driver() as driver:
        if driver is None:
            return None
        try:
            driver.get(normalized)
            _wait_ready(driver, wait_sec)
            png = driver.get_screenshot_as_png()
            return png if png and len(png) > 1000 else None
        except Exception as exc:
            logger.warning('Selenium screenshot xato: %s — %s', normalized, exc)
            return None


def fetch_with_selenium(url: str, wait_sec: int = 8) -> tuple[bytes, str] | None:
    normalized = normalize_https_url(url)
    if not normalized or not is_allowed_embed_url(normalized):
        return None

    with _chrome_driver() as driver:
        if driver is None:
            return None
        try:
            driver.get(normalized)
            _wait_ready(driver, wait_sec)
            html = driver.page_source or ''
            if len(html) < 300:
                return None
            return _prepare_html(html.encode('utf-8'), normalized), 'text/html; charset=utf-8'
        except Exception as exc:
            logger.warning('Selenium embed xato: %s — %s', normalized, exc)
            return None
