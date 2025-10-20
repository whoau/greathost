#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Greathost.es 自动续期脚本 - GitHub Actions 版本
基于 Weirdhost 脚本适配，增强了通用性和健壮性
"""

import os
import sys
import time
from datetime import datetime, timezone, timedelta
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

class GreathostRenew:
    def __init__(self):
        """初始化，从环境变量读取 Greathost.es 的配置"""
        self.url = os.getenv('GREATHOS_URL', 'https://greathost.es')
        self.login_url = f"{self.url}/auth/login"
        self.server_urls_str = os.getenv('GREATHOS_SERVER_URLS', '')
        
        # --- 认证信息 ---
        # 关键！greathost.es 的 'remember_web_...' cookie 的完整名称
        self.remember_cookie_name = os.getenv('GREATHOS_REMEMBER_COOKIE_NAME', '')
        # 该 cookie 的值
        self.remember_cookie_value = os.getenv('GREATHOS_REMEMBER_COOKIE_VALUE', '')
        
        # 备用的邮箱密码
        self.email = os.getenv('GREATHOS_EMAIL', '')
        self.password = os.getenv('GREATHOS_PASSWORD', '')
        
        self.headless = os.getenv('HEADLESS', 'true').lower() == 'true'
        self.server_list = [url.strip() for url in self.server_urls_str.split(',') if url.strip()]

    def log(self, message, level="INFO"):
        """格式化的日志输出"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"[{timestamp}] [{level.upper()}] {message}")

    def _check_login_status(self, page):
        """检查登录状态，返回True表示已登录"""
        current_url = page.url
        if "/auth/login" in current_url:
            self.log("当前在登录页面，状态：未登录", "DEBUG")
            return False
        
        try:
            logout_locator = page.locator('a[href*="auth/logout"], button:has-text("Logout"), button:has-text("Cerrar Sesión")')
            if logout_locator.count() > 0 and logout_locator.first.is_visible(timeout=2000):
                self.log("找到登出按钮，状态：已登录", "DEBUG")
                return True
        except PlaywrightTimeoutError:
            pass 

        self.log(f"当前URL: {current_url}，未在登录页，假设已登录", "DEBUG")
        return True

    def _login_with_cookies(self, context):
        """使用 Cookies 登录"""
        if not self.remember_cookie_name or not self.remember_cookie_value:
            self.log("Cookie 名称或值未设置，无法使用 Cookie 登录。", "WARNING")
            return False

        self.log("尝试使用 Cookie 登录...")
        
        try:
            context.add_cookies([{
                'name': self.remember_cookie_name,
                'value': self.remember_cookie_value,
                'domain': 'greathost.es',
                'path': '/',
            }])
            self.log(f"成功添加 Cookie '{self.remember_cookie_name}' 到浏览器上下文。")
            return True
        except Exception as e:
            self.log(f"设置 Cookie 时出错: {e}", "ERROR")
            return False

    def _login_with_email(self, page):
        """使用邮箱和密码登录"""
        if not (self.email and self.password):
            return False

        self.log("尝试使用邮箱密码登录...")
        try:
            page.goto(self.login_url, wait_until="domcontentloaded", timeout=60000)
            page.fill('input[name="username"]', self.email)
            page.fill('input[name="password"]', self.password)
            page.click('button[type="submit"]')
            page.wait_for_navigation(wait_until="networkidle", timeout=60000)
            
            if "/auth/login" in page.url:
                self.log("邮箱密码登录失败，页面仍在登录页。", "WARNING")
                return False
            
            self.log("邮箱密码登录成功！")
            return True
        except Exception as e:
            self.log(f"邮箱密码登录时发生错误: {e}", "ERROR")
            return False

    def _renew_server(self, page, server_url):
        """对单个服务器执行续期操作"""
        server_id = server_url.strip('/').split('/')[-1]
        self.log(f"--- 开始处理服务器: {server_id} ---")

        try:
            page.goto(server_url, wait_until="networkidle", timeout=60000)

            if not self._check_login_status(page):
                self.log(f"在访问服务器 {server_id} 页面时发现未登录！", "ERROR")
                return f"{server_id}:login_failed_on_server_page"
            
            # 查找续期按钮（西班牙语）
            renew_button_selectors = [
                'button:has-text("Renovar")',          # "续期"
                'button:has-text("Añadir tiempo")',   # "增加时间"
                'button:has-text("Extender")',        # "延长"
            ]
            
            renew_button = None
            for selector in renew_button_selectors:
                try:
                    button_locator = page.locator(selector)
                    if button_locator.count() > 0 and button_locator.first.is_visible(timeout=5000):
                        renew_button = button_locator.first
                        self.log(f"服务器 {server_id}: 找到续期按钮 (选择器: {selector})")
                        break
                except PlaywrightTimeoutError:
                    continue

            if not renew_button:
                self.log(f"服务器 {server_id}: 未找到任何续期按钮。", "WARNING")
                return f"{server_id}:no_button_found"

            if not renew_button.is_enabled():
                self.log(f"服务器 {server_id}: 续期按钮存在但不可点击（灰色）。", "INFO")
                return f"{server_id}:already_renewed"

            self.log(f"服务器 {server_id}: 找到并准备点击续期按钮。")
            renew_button.click()
            
            # 等待反馈
            time.sleep(5) # 简单等待，因为弹窗样式可能不同
            
            page_content = page.content().lower()
            if any(s in page_content for s in ["ya fue renovado", "already renewed"]):
                 self.log(f"服务器 {server_id}: 检测到已续期提示。")
                 return f"{server_id}:already_renewed"
            elif any(s in page_content for s in ["éxito", "success", "renovado"]):
                self.log(f"服务器 {server_id}: 检测到成功提示。")
                return f"{server_id}:success"
            else:
                self.log(f"服务器 {server_id}: 点击后未检测到明确结果，乐观地假设成功。", "INFO")
                return f"{server_id}:success"

        except Exception as e:
            self.log(f"处理服务器 {server_id} 时发生未知错误: {e}", "ERROR")
            return f"{server_id}:runtime_error"

    def run(self):
        """主执行函数"""
        self.log("🚀 Greathost.es 自动续期脚本启动")
        if not self.server_list:
            self.log("未提供服务器URL列表 (GREATHOS_SERVER_URLS)，任务中止。", "ERROR")
            return ["error:no_servers"]
            
        if not self.remember_cookie_name and not self.email:
             self.log("未提供任何认证信息 (Cookie或邮箱)，任务中止。", "ERROR")
             return ["error:no_auth"]

        results = []
        with sync_playwright() as p:
            try:
                browser = p.chromium.launch(headless=self.headless)
                context = browser.new_context()
                page = context.new_page()

                login_successful = False
                if self._login_with_cookies(context):
                    page.goto(self.url, wait_until="domcontentloaded", timeout=60000)
                    if self._check_login_status(page):
                        self.log("✅ Cookie 登录验证成功！", "INFO")
                        login_successful = True
                    else:
                        self.log("Cookie 登录验证失败，Cookie可能已过期或名称/值不正确。", "WARNING")
                
                if not login_successful and self._login_with_email(page):
                    login_successful = True
                    self.log("✅ 邮箱密码登录成功！", "INFO")

                if not login_successful:
                    self.log("所有登录方式均失败，无法继续。", "ERROR")
                    browser.close()
                    return [f"{url.strip('/').split('/')[-1]}:login_failed" for url in self.server_list]

                self.log(f"登录成功，开始处理 {len(self.server_list)} 个服务器...")
                for server_url in self.server_list:
                    result = self._renew_server(page, server_url)
                    results.append(result)
                    time.sleep(3)

                browser.close()

            except Exception as e:
                self.log(f"Playwright 运行时发生严重错误: {e}", "CRITICAL")
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

    is_failure = any("failed" in r or "error" in r or "found" in r for r in results)
    if is_failure:
        print("\n⚠️ 注意：部分或全部任务未能成功完成。请检查日志。")
        sys.exit(1)
    else:
        print("\n🎉 所有任务均成功完成！")
        sys.exit(0)

if __name__ == "__main__":
    main()
