#!/usr/bin/env python3
import os
import re
import sys
import time
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

# 简单日志
def log(msg):
    print(f"[renew] {msg}", flush=True)

def fill_first_visible(page, selectors, value, timeout=8000):
    for s in selectors:
        try:
            loc = page.locator(s).first
            loc.wait_for(state="visible", timeout=timeout)
            # 点击聚焦后填，避免某些脚本验证不触发
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
    # 多策略：button/link 文本、任意文本节点
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

    # 登录按钮尝试（多语言）
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
        # 兜底：在密码框按回车
        try:
            page.locator(pwd_selectors[0]).first.press("Enter", timeout=2000)
        except Exception:
            pass

    # 等待跳转或出现 dashboard/Contracts
    try:
        page.wait_for_load_state("networkidle", timeout=20000)
    except PWTimeout:
        pass

    # 登录成功判断：出现 Contracts/Contratos 链接或 URL 离开 /login
    login_ok = False
    try:
        if not page.url.endswith("/login") and "/login" not in page.url:
            login_ok = True
    except Exception:
        pass

    if not login_ok:
        # 再尝试找 Contracts/Contratos
        login_ok = wait_for_any(page, [
            'a:has-text("Contracts")',
            'text=Contracts',
            'a:has-text("Contratos")',
            'text=Contratos',
        ], timeout=8000)

    log(f"登录状态: {'成功' if login_ok else '失败'}")
    return login_ok

def goto_contracts(page):
    log("尝试进入 Contracts 页面")
    ok = click_by_text_candidates(page, [
        r'\bContracts?\b',
        r'\bContratos?\b',
        r'合同|合约',
    ], timeout=8000)

    if not ok:
        # 尝试常见菜单图标/导航按钮
        ok = click_any(page, [
            'a[href*="contract"]',
            'a[href*="contrato"]',
            'a[href*="/contracts"]',
        ], timeout=6000)

    if not ok:
        log("未找到 Contracts 入口，可能界面有变动。")
        return False

    try:
        page.wait_for_load_state("networkidle", timeout=15000)
    except PWTimeout:
        pass
    return True

def open_any_contract_details(page):
    log("在 Contracts 中寻找 View Details")
    ok = click_by_text_candidates(page, [
        r'\bView details?\b',
        r'\bDetails?\b',
        r'\bVer detalles?\b',
        r'\bVer\b',
        r'查看详情|详情',
    ], timeout=8000)

    if not ok:
        # 直接点常见选择器
        ok = click_any(page, [
            'a:has-text("View")',
            'a:has-text("Details")',
            'button:has-text("View")',
            'button:has-text("Details")',
            'a[href*="details"]',
        ], timeout=8000)

    if not ok:
        log("未找到 View Details 按钮/链接。")
        return False

    try:
        page.wait_for_load_state("networkidle", timeout=15000)
    except PWTimeout:
        pass
    return True

def renew_plus_12h(page):
    log("尝试点击 Renew +12h")
    # 接受可能的确认弹窗
    def on_dialog(dialog):
        log(f"检测到弹窗: {dialog.message}")
        try:
            dialog.accept()
        except Exception:
            pass
    page.on("dialog", on_dialog)

    patterns = [
        r'renew\s*\+?\s*12\s*h',            # renew +12h / renew 12h
        r'renew\s*\+?\s*12\s*hour',         # renew +12 hour(s)
        r'renovar.*\+?\s*12',               # 西语 renovar +12
        r'extend.*\+?\s*12',                # extend +12
        r'extender.*\+?\s*12',              # 西语 extender +12
        r'续.*12',                           # 中文 续期/续订 12
        r'延长.*12',                         # 中文 延长 12
        r'\+?\s*12\s*(hours?|h)\b',
    ]

    ok = click_by_text_candidates(page, patterns, timeout=8000)
    if not ok:
        # 常见选择器兜底
        ok = click_any(page, [
            'button:has-text("+12")',
            'a:has-text("+12")',
            'button:has-text("Renew")',
            'a:has-text("Renew")',
            'button:has-text("Renovar")',
            'a:has-text("Renovar")',
        ], timeout=8000)

    if ok:
        # 等待操作完成（按钮可能变灰或出现提示）
        try:
            page.wait_for_load_state("networkidle", timeout=15000)
        except PWTimeout:
            pass
    return ok

def main():
    email = os.getenv("GREATHOST_EMAIL")
    password = os.getenv("GREATHOST_PASSWORD")
    base_url = os.getenv("BASE_URL", "https://greathost.es").rstrip("/")
    headless = os.getenv("HEADLESS", "1") != "0"

    if not email or not password:
        log("请设置环境变量 GREATHOST_EMAIL / GREATHOST_PASSWORD（在 GitHub Secrets 配置）")
        sys.exit(1)

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=headless,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
            ],
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
                log("登录失败，退出")
                sys.exit(2)

            if not goto_contracts(page):
                log("进入 Contracts 失败，退出")
                sys.exit(3)

            if not open_any_contract_details(page):
                log("打开某条合约详情失败，退出")
                sys.exit(4)

            if renew_plus_12h(page):
                log("续期 +12 小时：已点击成功（若有配额/限制请以页面实际为准）")
                sys.exit(0)
            else:
                log("未找到可点击的续期 +12h 按钮，可能是冷却中或页面变动。")
                sys.exit(5)
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
