import os
import re
import threading

from playwright.sync_api import sync_playwright

FLAG = os.environ.get('FLAG', 'L3AK{1f_y0u_c4n_c0un7_y0u_c4n_l34k}')
SITE = os.environ.get('SITE', 'http://127.0.0.1:5000')
TIMEOUT_MS = 30000
VISIT_WAIT_MS = 180000
URL_RE = re.compile(r'^https?://.+')


def _visit(url, admin_password):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-dev-shm-usage'])
        context = browser.new_context()

        try:
            setup = context.new_page()
            setup.goto(f'{SITE}/login', wait_until='networkidle', timeout=TIMEOUT_MS)
            setup.fill('input[name="username"]', 'admin')
            setup.fill('input[name="password"]', admin_password)
            setup.click('button.btn')
            setup.wait_for_load_state('networkidle', timeout=TIMEOUT_MS)

            setup.goto(f'{SITE}/s3cret', wait_until='networkidle', timeout=TIMEOUT_MS)
            setup.fill('#entry-box', FLAG)
            setup.click('#save-btn')
            setup.wait_for_load_state('networkidle', timeout=TIMEOUT_MS)
            setup.close()

            visit = context.new_page()
            visit.goto(url, wait_until='networkidle', timeout=TIMEOUT_MS)
            visit.wait_for_timeout(VISIT_WAIT_MS)
        except Exception as e:
            print(f'admin bot error: {e}')
        finally:
            browser.close()


def visit(url, admin_password):
    if not URL_RE.match(url):
        raise ValueError('invalid url')
    threading.Thread(target=_visit, args=(url, admin_password), daemon=True).start()
