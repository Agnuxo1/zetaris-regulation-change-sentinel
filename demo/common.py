"""Shared settings for the browser recording. Credentials come from ZETARIS_ENV_FILE and are never printed."""
import glob, os, pathlib
ENV = pathlib.Path(os.environ.get("ZETARIS_ENV_FILE", ".env"))
CHROME = os.environ.get("CHROME_PATH") or (glob.glob(os.path.expanduser("~/AppData/Local/ms-playwright/chromium-*/chrome-win*/chrome.exe")) or [None])[0]
UI = os.environ.get("ZETARIS_UI_URL", "http://127.0.0.1:3000")


def creds():
    cfg = dict(l.split("=", 1) for l in ENV.read_text().splitlines() if "=" in l and not l.startswith("#"))
    user = cfg.get("ZETARIS_USERNAME") or cfg.get("ZETARIS_ADMIN_EMAIL")
    password = cfg.get("ZETARIS_PASSWORD") or cfg.get("ZETARIS_ADMIN_PASSWORD")
    return user.strip(), password.strip()


def login(browser, state="state.json"):
    """Sign in in an unrecorded context and save the session for the recorded one."""
    ctx = browser.new_context(viewport={"width": 1600, "height": 900}); pg = ctx.new_page()
    pg.goto(UI, wait_until="networkidle")
    u, p = creds()
    pg.fill("input[type=text]", u); pg.fill("input[type=password]", p); pg.click("button[type=submit]")
    pg.wait_for_load_state("networkidle"); pg.wait_for_timeout(2500)
    ctx.storage_state(path=state); url = pg.url; ctx.close(); return url
