#!/usr/bin/env python3
import os
import re
import sys
import time
import datetime
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

# ---------------- 工具 ----------------
def log(msg):
    print(f"[renew] {msg}", flush=True)

def mask_email(email: str) -> str:
    try:
        name, domain = email.split("@", 1)
        if len(name) <= 2:
            masked = name[0] + "*" * max(0, len(name)-1)
        else:
            masked = name[:2] + "*" * (len(name)-2)
        return f"{masked}@{domain}"
    except Exception:
        return email[:2] + "***"

def now_utc_str():
    return datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

def now_bjt_str():
    # 北京时间 UTC+8（不依赖系统时区）
    return (datetime.datetime.utcnow() + datetime.timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S (UTC+8)")

# ---------------- Playwright 便捷函数 ----------------
def fill_first_visible(page, selectors, value, timeout=8000):
    for s in selectors:
        try:
            loc = page.locator(s).first
            loc.wait_for(state="visible", timeout=timeout)
            try:
                loc.click(timeout=2000)
            except Exception:
                pass
            loc.fill(value, timeout=timeout)
            return True
        except Exception:
            continue
    return False

def click_any(page, selectors, timeout=8000):
    for s in selectors:
        try:
            loc = page.locator(s).first
            loc.wait_for(state="visible", timeout=timeout)
            loc.scroll_into_view_if_needed(timeout=2000)
            loc.click(timeout=timeout)
            return True
        except Exception:
            continue
    return False

def click_by_text_candidates(page, patterns, timeout=8000):
    for pat in patterns:
        regex = re.compile(pat, re.I)
        candidates = [
            page.get_by_role("button", name=regex).first,
            page.get_by_role("link", name=regex).first,
            page.get_by_text(regex).first,
        ]
        for loc in candidates:
            try:
                loc.wait_for(state="visible", timeout=timeout)
                loc.scroll_into_view_if_needed(timeout=2000)
                loc.click(timeout=timeout)
                return True
            except Exception:
                continue
    return False

def wait_for_any(page, selectors, state="visible", timeout=10000):
    deadline = time.time() + timeout/1000.0
    last_err = None
    for s in selectors:
        try:
            page.locator(s).first.wait_for(state=state, timeout=timeout)
            return True
        except Exception as e:
            last_err = e
            if time.time() > deadline:
                break
    if last_err:
        log(f"wait_for_any last error: {last_err}")
    return False

# ---------------- 页面流程 ----------------
def login(page, base_url, email, password):
    login_url = f"{base_url.rstrip('/')}/login"
    log(f"访问登录页: {login_url}")
    page.goto(login_url, wait_until="domcontentloaded")
    page.wait_for_load_state("networkidle", timeout=20000)

    email_selectors = [
        'input[name="email"]',
        'input[type="email"]',
        'input#email',
        'input[placeholder*="Email" i]',
        'input[placeholder*="Correo" i]',
        'input[name*="user" i]',
        'input[name*="correo" i]',
    ]
    pwd_selectors = [
        'input[name="password"]',
        'input[type="password"]',
        'input#password',
        'input[placeholder*="Password" i]',
        'input[placeholder*="Contraseña" i]',
    ]

    ok_email = fill_first_visible(page, email_selectors, email)
    ok_pwd = fill_first_visible(page, pwd_selectors, password)
    if not (ok_email and ok_pwd):
        log("未找到邮箱/密码输入框，可能需要更新选择器。")
        return False

    login_clicked = click_any(page, [
        'button[type="submit"]',
        'input[type="submit"]',
        'button:has-text("Login")',
        'button:has-text("Log in")',
        'button:has-text("Sign in")',
        'button:has-text("Acceder")',
        'button:has-text("Iniciar")',
        'button:has-text("Entrar")',
        'text=Login',
        'text=Sign in',
        'text=Acceder',
        'text=Iniciar sesión',
    ], timeout=8000)

    if not login_clicked:
        try:
            page.locator(pwd_selectors[0]).first.press("Enter", timeout=2000)
        except Exception:
            pass

    try:
        page.wait_for_load_state("networkidle", timeout=20000)
    except PWTimeout:
        pass

    # 登录成功：URL 离开 /login 或出现 Contracts 导航
    login_ok = False
    try:
        if "/login" not in page.url:
            login_ok = True
    except Exception:
        pass

    if not login_ok:
        login_ok = wait_for_any(page, [
            'a:has-text("Contracts")',
            'text=Contracts',
            'a:has-text("Contratos")',
            'text=Contratos',
        ], timeout=8000)

    log(f"登录状态: {'成功' if login_ok else '失败'}")
    return login_ok

def goto_contracts(page):
    log("进入 Contracts 页面")
    ok = click_by_text_candidates(page, [
        r'\bContracts?\b',
        r'\bContratos?\b',
        r'合同|合约',
    ], timeout=8000)

    if not ok:
        ok = click_any(page, [
            'a[href*="contract"]',
            'a[href*="contrato"]',
            'a[href*="/contracts"]',
        ], timeout=6000)

    if not ok:
        log("未找到 Contracts 入口")
        return False

    try:
        page.wait_for_load_state("networkidle", timeout=15000)
    except PWTimeout:
        pass
    return True

def open_any_contract_details(page):
    log("打开某个合约的 View Details")
    ok = click_by_text_candidates(page, [
        r'\bView details?\b',
        r'\bDetails?\b',
        r'\bVer detalles?\b',
        r'\bVer\b',
        r'查看详情|详情',
    ], timeout=8000)

    if not ok:
        ok = click_any(page, [
            'a:has-text("View")',
            'a:has-text("Details")',
            'button:has-text("View")',
            'button:has-text("Details")',
            'a[href*="details"]',
        ], timeout=8000)

    if not ok:
        log("未找到 View Details")
        return False

    try:
        page.wait_for_load_state("networkidle", timeout=15000)
    except PWTimeout:
        pass
    return True

def renew_plus_12h(page):
    log("尝试点击 Renew +12h")
    def on_dialog(dialog):
        log(f"弹窗: {dialog.message}")
        try:
            dialog.accept()
        except Exception:
            pass
    page.on("dialog", on_dialog)

    patterns = [
        r'renew\s*\+?\s*12\s*h',
        r'renew\s*\+?\s*12\s*hour',
        r'renovar.*\+?\s*12',
        r'extend.*\+?\s*12',
        r'extender.*\+?\s*12',
        r'续.*12',
        r'延长.*12',
        r'\+?\s*12\s*(hours?|h)\b',
    ]

    ok = click_by_text_candidates(page, patterns, timeout=8000)
    if not ok:
        ok = click_any(page, [
            'button:has-text("+12")',
            'a:has-text("+12")',
            'button:has-text("Renew")',
            'a:has-text("Renew")',
            'button:has-text("Renovar")',
            'a:has-text("Renovar")',
        ], timeout=8000)

    if ok:
        try:
            page.wait_for_load_state("networkidle", timeout=15000)
        except PWTimeout:
            pass
    return ok

def detect_renew_success(page) -> bool:
    # 根据页面出现的成功提示/状态变化做简单判定
    patterns = [
        r'\brenew(ed|al).*(success|complete|done)\b',
        r'\bsuccess(fully)?\b.*\b(renew|extend)',
        r'\b(renewed|extended)\b',
        r'renovad[oa]',  # 西语
        r'续期成功|已续期|延长成功|已延长',
    ]
    try:
        body_text = page.text_content("body") or ""
        for pat in patterns:
            if re.search(pat, body_text, re.I):
                return True
    except Exception:
        pass
    return False

# ---------------- README 写入（仅成功时） ----------------
def update_readme_on_success(readme_path: str, base_url: str, account_mask: str):
    success_line = f"✅ Greathost 续期成功 | 账号: {account_mask} | 时间: {now_utc_str()} / {now_bjt_str()} | 站点: {base_url}"
    section_title = "## Greathost 续期状态"
    start_marker = "<!-- GREATHOST-RENEW-STATUS:START -->"
    end_marker = "<!-- GREATHOST-RENEW-STATUS:END -->"

    block = (
        f"{section_title}\n\n"
        f"{start_marker}\n"
        f"{success_line}\n"
        f"{end_marker}\n"
    )

    if not os.path.exists(readme_path):
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write(f"# README\n\n{block}\n")
        log(f"README 不存在，已创建并写入成功状态。")
        return

    with open(readme_path, "r", encoding="utf-8") as f:
        content = f.read()

    if start_marker in content and end_marker in content:
        # 替换标记之间的内容
        pattern = re.compile(rf"{re.escape(start_marker)}.*?{re.escape(end_marker)}", re.S)
        new_content = pattern.sub(f"{start_marker}\n{success_line}\n{end_marker}", content)
    else:
        # 追加一个状态段落到文末
        new_content = content.rstrip() + "\n\n" + block + "\n"

    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(new_content)

    log("已将续期成功通知写入 README.md")

# ---------------- 主流程（单账号） ----------------
def main():
    base_url = os.getenv("BASE_URL", "https://greathost.es").rstrip("/")
    headless = os.getenv("HEADLESS", "1") != "0"
    readme_path = os.getenv("README_PATH", "README.md")
    email = os.getenv("GREATHOST_EMAIL", "").strip()
    password = os.getenv("GREATHOST_PASSWORD", "")

    if not email or not password:
        log("请设置 GREATHOST_EMAIL / GREATHOST_PASSWORD")
        sys.exit(1)

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=headless,
            args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"],
        )
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118 Safari/537.36",
            locale="en-US",
            timezone_id="UTC",
        )
        page = context.new_page()
        page.set_default_timeout(30000)

        try:
            if not login(page, base_url, email, password):
                log("登录失败")
                sys.exit(2)

            if not goto_contracts(page):
                log("进入 Contracts 失败")
                sys.exit(3)

            if not open_any_contract_details(page):
                log("未找到合约详情")
                sys.exit(4)

            clicked = renew_plus_12h(page)
            if not clicked:
                log("未找到可点击的 +12h（可能冷却中或按钮文案变化）")
                sys.exit(5)

            success = detect_renew_success(page)
            if success:
                update_readme_on_success(readme_path, base_url, mask_email(email))
                sys.exit(0)
            else:
                log("已点击 +12h，但未检测到明确的成功提示，README 不更新。")
                sys.exit(6)

        finally:
            try:
                context.close()
            except Exception:
                pass
            try:
                browser.close()
            except Exception:
                pass

if __name__ == "__main__":
    main()
