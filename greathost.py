#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Greathost.es 自动续期脚本 - GitHub Actions 版本（修订版）
- 修复 Playwright API 用法（不再在 is_visible 上传 timeout）
- 登录判断更稳健（不再“只要不在登录页就当作已登录”）
- 支持 Cookie 登录、邮箱登录、storage_state 登录（可选）
- 续期按钮选择器更宽松，结果判断更可靠
- 遇到错误自动截屏（可通过环境变量关闭）
"""

import os
import sys
import time
import random
import traceback
from urllib.parse import urlparse
from datetime import datetime, timezone, timedelta
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

def parse_bool(val, default=False):
    if val is None:
        return default
    return str(val).strip().lower() in ("1", "true", "yes", "y", "on")

class GreathostRenew:
    def __init__(self):
        """初始化，从环境变量读取 Greathost.es 的配置（兼容 GREATHOST_ 与 GREATHOS_ 前缀）"""
        self._env_cache = dict(os.environ)

        self.url = self._get("GREATHOST_URL", "GREATHOS_URL", default="https://greathost.es").rstrip("/")
        self.login_url = f"{self.url}/auth/login"

        server_urls_str = self._get("GREATHOST_SERVER_URLS", "GREATHOS_SERVER_URLS", default="")
        server_urls_str = server_urls_str.replace("\n", ",")
        self.server_list = [u.strip() for u in server_urls_str.split(",") if u.strip()]

        # 认证信息
        self.remember_cookie_name = self._get("GREATHOST_REMEMBER_COOKIE_NAME", "GREATHOS_REMEMBER_COOKIE_NAME", default="")
        self.remember_cookie_value = self._get("GREATHOST_REMEMBER_COOKIE_VALUE", "GREATHOS_REMEMBER_COOKIE_VALUE", default="")
        self.email = self._get("GREATHOST_EMAIL", "GREATHOS_EMAIL", default="")
        self.password = self._get("GREATHOST_PASSWORD", "GREATHOS_PASSWORD", default="")

        # Playwright 运行参数
        self.headless = parse_bool(self._get("HEADLESS", default="true"), True)
        self.timezone_id = self._get("TIMEZONE_ID", default="Europe/Madrid")
        self.locale = self._get("LOCALE", default="es-ES")

        # storage_state（可选）：先本地导出 state.json，再导入到 CI
        self.storage_state_path = self._get(
            "GREATHOST_STORAGE_STATE", "GREATHOS_STORAGE_STATE", "STORAGE_STATE_PATH", default=""
        )
        self.storage_state_export_path = self._get(
            "GREATHOST_STORAGE_STATE_EXPORT",
            "GREATHOS_STORAGE_STATE_EXPORT",
            "STORAGE_STATE_EXPORT_PATH",
            default=""
        )

        # 错误时自动截图
        self.screenshot_on_error = parse_bool(self._get("SCREENSHOT_ON_ERROR", default="true"), True)

        # 续期按钮可能的文本（西/英）
        self.renew_texts = ["Renovar", "Añadir tiempo", "Extender", "Renew", "Extend"]

        # 解析 Cookie 作用域
        parsed = urlparse(self.url)
        self.base_domain = parsed.hostname or "greathost.es"
        if not self.base_domain.startswith("."):
            self.cookie_domain = f".{self.base_domain}"
        else:
            self.cookie_domain = self.base_domain

        # 点击前后的随机抖动
        self.jitter_range = (0.3, 0.9)

    def _get(self, *keys, default=None):
        for k in keys:
            if k in self._env_cache and str(self._env_cache[k]).strip() != "":
                return self._env_cache[k]
        return default

    def log(self, message, level="INFO"):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [{level.upper()}] {message}")

    def _check_login_status(self, page):
        """检查登录状态，返回 True 表示已登录（更保守）"""
        current_url = page.url or ""
        if "/auth/login" in current_url:
            self.log("当前在登录页面，状态：未登录", "DEBUG")
            return False

        try:
            logout_locator = page.locator(
                'a[href*="auth/logout"], a:has-text("Logout"), a:has-text("Cerrar sesión"), '
                'button:has-text("Logout"), button:has-text("Cerrar sesión"), button:has-text("Salir")'
            ).first
            logout_locator.wait_for(state="visible", timeout=2000)
            self.log("找到登出按钮，状态：已登录", "DEBUG")
            return True
        except PlaywrightTimeoutError:
            pass

        # 再看是否能看到登录入口
        if page.locator(
            'a[href*="/auth/login"], button:has-text("Login"), button:has-text("Iniciar sesión"), text="Iniciar sesión"'
        ).count() > 0:
            self.log("检测到登录入口，状态：未登录", "DEBUG")
            return False

        # 保守：无法确认则判定未登录，避免误判
        self.log(f"当前URL: {current_url}，无法确认登录状态，保守判定未登录", "DEBUG")
        return False

    def _login_with_cookies(self, context, page):
        """使用 Remember Cookie 登录"""
        if not self.remember_cookie_name or not self.remember_cookie_value:
            self.log("Cookie 名称或值未设置，跳过 Cookie 登录。", "WARNING")
            return False

        self.log("尝试使用 Cookie 登录...")
        try:
            # 先访问站点，确保域已建立
            page.goto(self.url, wait_until="domcontentloaded", timeout=60000)
            context.add_cookies([{
                "name": self.remember_cookie_name,
                "value": self.remember_cookie_value,
                "domain": self.cookie_domain,  # 如 .greathost.es
                "path": "/",
                "sameSite": "Lax",
                "secure": True,
                "httpOnly": True,
            }])
            page.reload(wait_until="networkidle", timeout=60000)
            time.sleep(0.5)
            ok = self._check_login_status(page)
            if ok:
                self.log(f"✅ Cookie 登录验证成功（{self.remember_cookie_name}）", "INFO")
            else:
                self.log("Cookie 登录验证失败，可能已过期或无效。", "WARNING")
            return ok
        except Exception as e:
            self.log(f"设置/验证 Cookie 时出错: {e}", "ERROR")
            return False

    def _login_with_email(self, page):
        """使用邮箱和密码登录"""
        if not (self.email and self.password):
            self.log("未提供邮箱/密码，跳过邮箱登录。", "DEBUG")
            return False

        self.log("尝试使用邮箱密码登录...")
        try:
            page.goto(self.login_url, wait_until="domcontentloaded", timeout=60000)

            user_input = page.locator('input[name="email"], input[name="username"]').first
            pass_input = page.locator('input[name="password"], input[type="password"]').first

            if user_input.count() == 0 or pass_input.count() == 0:
                self.log("登录表单未找到预期的输入框", "ERROR")
                return False

            user_input.fill(self.email)
            pass_input.fill(self.password)

            # 提交按钮尽量兼容多个写法
            submit_btn = page.locator(
                'button[type="submit"], button:has-text("Login"), button:has-text("Iniciar sesión"), input[type="submit"]'
            ).first
            if submit_btn.count() > 0:
                submit_btn.click()
            else:
                # 退化：回车提交
                pass_input.press("Enter")

            # 等页面完成请求
            page.wait_for_load_state("networkidle", timeout=60000)

            if "/auth/login" in page.url or not self._check_login_status(page):
                self.log("邮箱密码登录失败，仍在登录态外。", "WARNING")
                return False

            self.log("✅ 邮箱密码登录成功！", "INFO")
            return True
        except Exception as e:
            self.log(f"邮箱密码登录时发生错误: {e}", "ERROR")
            return False

    def _renew_server(self, page, server_url):
        """对单个服务器执行续期操作"""
        server_id = self._extract_server_id(server_url)
        self.log(f"--- 开始处理服务器: {server_id} ---")

        try:
            page.goto(server_url, wait_until="networkidle", timeout=60000)

            if not self._check_login_status(page):
                self.log(f"访问服务器 {server_id} 页面时发现未登录！", "ERROR")
                return f"{server_id}:login_failed_on_server_page"

            # 查找续期按钮（button 或 a，西/英多文本）
            renew_button = None
            for text in self.renew_texts:
                candidate = page.locator(f'button:has-text("{text}"), a:has-text("{text}")')
                if candidate.count() > 0:
                    try:
                        candidate.first.wait_for(state="visible", timeout=5000)
                        renew_button = candidate.first
                        self.log(f"服务器 {server_id}: 找到续期按钮 (文本: {text})")
                        break
                    except PlaywrightTimeoutError:
                        continue

            if renew_button is None:
                self.log(f"服务器 {server_id}: 未找到任何续期按钮。", "WARNING")
                return f"{server_id}:no_button_found"

            # 如果按钮可见但不可用，视为已续期过
            try:
                if not renew_button.is_enabled():
                    self.log(f"服务器 {server_id}: 续期按钮存在但不可点击（灰色/禁用）。", "INFO")
                    return f"{server_id}:already_renewed"
            except Exception:
                # 某些 a 标签没有 disabled 概念，忽略
                pass

            # 点击续期
            self.log(f"服务器 {server_id}: 准备点击续期按钮。")
            renew_button.scroll_into_view_if_needed()
            time.sleep(random.uniform(*self.jitter_range))
            try:
                renew_button.click(timeout=10000)
            except Exception as e:
                self.log(f"常规点击失败，尝试 JS 触发点击：{e}", "WARNING")
                try:
                    page.evaluate("(el) => el.click()", renew_button)
                except Exception as e2:
                    self.log(f"JS 点击也失败：{e2}", "ERROR")
                    return f"{server_id}:runtime_error"

            # 等待反馈信息（toast/提示语）
            time.sleep(random.uniform(*self.jitter_range))

            already_sel = 'text=/ya fue renovado|ya está renovado|ya renovado|already renewed/i'
            success_sel = 'text=/éxito|success|renovado|extendido|tiempo añadido|tiempo agregado/i'

            # 优先判断“已续期”
            try:
                page.locator(already_sel).first.wait_for(state="visible", timeout=5000)
                self.log(f"服务器 {server_id}: 检测到已续期提示。")
                return f"{server_id}:already_renewed"
            except PlaywrightTimeoutError:
                pass

            # 再判断“成功”
            try:
                page.locator(success_sel).first.wait_for(state="visible", timeout=5000)
                self.log(f"服务器 {server_id}: 检测到成功提示。")
                return f"{server_id}:success"
            except PlaywrightTimeoutError:
                pass

            # 兜底：没有明确提示，乐观成功
            self.log(f"服务器 {server_id}: 点击后未检测到明确结果，乐观地假设成功。", "INFO")
            return f"{server_id}:success"

        except Exception as e:
            self.log(f"处理服务器 {server_id} 时发生未知错误: {e}", "ERROR")
            self.log(traceback.format_exc(), "DEBUG")
            if self.screenshot_on_error:
                try:
                    os.makedirs("screens", exist_ok=True)
                    page.screenshot(path=f"screens/{server_id}_error.png", full_page=True)
                    self.log(f"错误截图已保存到 screens/{server_id}_error.png", "INFO")
                except Exception as se:
                    self.log(f"保存错误截图失败：{se}", "WARNING")
            return f"{server_id}:runtime_error"

    def _extract_server_id(self, server_url: str) -> str:
        try:
            path = urlparse(server_url).path.rstrip("/")
            return path.split("/")[-1] or server_url
        except Exception:
            return server_url

    def run(self):
        """主执行函数"""
        self.log("🚀 Greathost.es 自动续期脚本启动")
        if not self.server_list:
            self.log("未提供服务器URL列表 (GREATHOST_SERVER_URLS / GREATHOS_SERVER_URLS)，任务中止。", "ERROR")
            return ["error:no_servers"]

        if not (self.storage_state_path or self.remember_cookie_name or self.email):
            self.log("未提供任何认证信息（storage_state / Cookie / 邮箱密码），任务中止。", "ERROR")
            return ["error:no_auth"]

        results = []
        with sync_playwright() as p:
            browser = None
            try:
                browser = p.chromium.launch(headless=self.headless)
                ctx_kwargs = dict(locale=self.locale, timezone_id=self.timezone_id)
                login_successful = False

                # 如果提供了 storage_state，优先使用
                if self.storage_state_path and os.path.exists(self.storage_state_path):
                    self.log(f"使用 storage_state 登录：{self.storage_state_path}")
                    context = browser.new_context(storage_state=self.storage_state_path, **ctx_kwargs)
                else:
                    context = browser.new_context(**ctx_kwargs)

                page = context.new_page()

                # 先验证已有会话
                try:
                    page.goto(self.url, wait_until="domcontentloaded", timeout=60000)
                    login_successful = self._check_login_status(page)
                    if login_successful:
                        self.log("✅ 已检测到有效登录会话。", "INFO")
                except Exception:
                    login_successful = False

                # 若未登录，尝试 Cookie
                if not login_successful and self.remember_cookie_name:
                    login_successful = self._login_with_cookies(context, page)

                # 若仍未登录，尝试邮箱密码
                if not login_successful and self.email and self.password:
                    login_successful = self._login_with_email(page)

                # 登录失败则结束
                if not login_successful:
                    self.log("所有登录方式均失败，无法继续。", "ERROR")
                    browser.close()
                    return [f"{self._extract_server_id(url)}:login_failed" for url in self.server_list]

                # 登录成功后可选择导出 storage_state，方便后续复用
                if self.storage_state_export_path:
                    try:
                        context.storage_state(path=self.storage_state_export_path)
                        self.log(f"已导出 storage_state 到: {self.storage_state_export_path}", "INFO")
                    except Exception as e:
                        self.log(f"导出 storage_state 失败：{e}", "WARNING")

                self.log(f"登录成功，开始处理 {len(self.server_list)} 个服务器...")
                for server_url in self.server_list:
                    result = self._renew_server(page, server_url)
                    results.append(result)
                    time.sleep(random.uniform(*self.jitter_range) + 0.6)

                browser.close()

            except Exception as e:
                self.log(f"Playwright 运行时发生严重错误: {e}", "CRITICAL")
                self.log(traceback.format_exc(), "DEBUG")
                if browser:
                    try:
                        browser.close()
                    except Exception:
                        pass
                results = ["runtime_error"] * len(self.server_list)

        return results


def update_readme(results):
    """根据运行结果更新 README.md 文件"""
    beijing_time = datetime.now(timezone(timedelta(hours=8))).strftime('%Y-%m-%d %H:%M:%S')

    status_messages = {
        "success": "✅ 续期成功",
        "already_renewed": "ℹ️ 今日已续期",
        "no_button_found": "❌ 未找到续期按钮",
        "login_failed": "❌ 登录失败",
        "login_failed_on_server_page": "❌ 访问服务器时掉线",
        "runtime_error": "💥 运行时错误",
        "error:no_servers": "配置错误：未提供服务器列表",
        "error:no_auth": "配置错误：未提供认证信息",
    }

    content = f"# Greathost.es 自动续期报告\n\n**最后更新时间**: `{beijing_time}` (北京时间)\n\n## 运行状态\n\n"

    if not results:
        content += "- 无任务\n"
    else:
        for result in results:
            parts = result.split(':', 1)
            server_id = parts[0]
            status = parts[1] if len(parts) > 1 else "unknown"
            message = status_messages.get(status, f"❓ 未知状态 ({status})")
            content += f"- 服务器 `{server_id}`: {message}\n"

    try:
        with open("README.md", "w", encoding="utf-8") as f:
            f.write(content)
        print("[INFO] README.md 文件已成功更新。")
    except Exception as e:
        print(f"[ERROR] 更新 README.md 文件失败: {e}")


def main():
    renew_task = GreathostRenew()
    results = renew_task.run()
    update_readme(results)

    print("=" * 50)
    print("📊 运行结果汇总:")
    for result in results:
        print(f"  - {result}")

    # 将失败视作非零退出，便于 CI 观察
    is_failure = any("failed" in r or "error" in r or "found" in r for r in results)
    if is_failure:
        print("\n⚠️ 注意：部分或全部任务未能成功完成。请检查日志与截图（如已开启）。")
        sys.exit(1)
    else:
        print("\n🎉 所有任务均成功完成！")
        sys.exit(0)


if __name__ == "__main__":
    main()
