#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import logging
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException

# --- 配置日志 ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ServerRenewal:
    def __init__(self):
        """初始化配置"""
        self.url = os.getenv('LOGIN_URL', 'https://example.com/login')
        self.username = os.getenv('USERNAME')
        self.password = os.getenv('PASSWORD')
        self.cookie_file = 'cookies.json'
        self.driver = None

    def setup_driver(self):
        """配置并初始化 Chrome 驱动"""
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        # 隐藏 webdriver 特征，增强反检测能力
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': 'Object.defineProperty(navigator, "webdriver", {get: () => undefined})'
        })
        
        # 移除隐式等待，完全依赖显式等待，避免混合使用导致不可预测的行为
        # self.driver.implicitly_wait(10)
        
        logger.info("✅ 浏览器驱动初始化完成")

    def save_cookies(self):
        """登录成功后保存cookies到文件"""
        try:
            cookies = self.driver.get_cookies()
            with open(self.cookie_file, 'w') as f:
                json.dump(cookies, f)
            logger.info(f"✅ Cookies 已成功保存到 {self.cookie_file}")
        except Exception as e:
            logger.error(f"❌ 保存 Cookies 失败: {e}")

    def login_with_cookies(self):
        """尝试使用 Cookie 登录"""
        if not os.path.exists(self.cookie_file):
            logger.info("ℹ️ Cookie 文件不存在，将进行常规登录。")
            return False

        try:
            # 必须先访问域名才能设置 Cookie
            base_url = "/".join(self.url.split("/")[:3])
            self.driver.get(base_url)

            with open(self.cookie_file, 'r') as f:
                cookies = json.load(f)
            
            for cookie in cookies:
                # 'expiry' 键有时会导致问题，如果存在则移除
                if 'expiry' in cookie:
                    del cookie['expiry']
                self.driver.add_cookie(cookie)

            logger.info("✅ Cookies 已加载，正在刷新页面验证登录状态...")
            self.driver.refresh()

            # 通过等待登录后才能看到的元素来验证 Cookie 是否有效
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.LINK_TEXT, "Contracts"))
            )
            logger.info("✅ 使用 Cookie 登录成功！")
            return True
        except (TimeoutException, Exception) as e:
            logger.warning(f"⚠️ 使用 Cookie 登录失败，可能是 Cookie 已过期。错误: {e}")
            # 清理无效的Cookie文件
            if os.path.exists(self.cookie_file):
                os.remove(self.cookie_file)
                logger.info(f"🗑️ 已删除失效的 Cookie 文件: {self.cookie_file}")
            return False

    def login_with_credentials(self):
        """使用用户名和密码登录"""
        try:
            logger.info(f"🌐 正在访问登录页面: {self.url}")
            self.driver.get(self.url)
            
            # 使用显式等待代替 time.sleep
            username_input = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.NAME, "username"))
            )
            username_input.clear()
            username_input.send_keys(self.username)
            logger.info("✅ 用户名已填写")
            
            password_input = self.driver.find_element(By.NAME, "password")
            password_input.clear()
            password_input.send_keys(self.password)
            logger.info("✅ 密码已填写")
            
            login_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            login_button.click()
            logger.info("✅ 登录按钮已点击")
            
            # 等待登录成功后的页面元素出现，以此确认登录成功
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.LINK_TEXT, "Contracts"))
            )
            logger.info("✅ 用户名密码登录成功")
            self.save_cookies()  # 登录成功后保存/更新 Cookie
            return True
        except TimeoutException:
            logger.error("❌ 登录失败：超时或用户名/密码错误。")
            self.driver.save_screenshot('login_error.png')
            logger.info(f"当前页面URL: {self.driver.current_url}")
            return False
        except Exception as e:
            logger.error(f"❌ 登录过程中发生未知错误: {e}")
            self.driver.save_screenshot('login_unexpected_error.png')
            return False

    def navigate_to_contracts(self):
        """点击 Contracts 菜单并等待下一页加载"""
        try:
            logger.info("🔍 正在查找并点击 Contracts 链接")
            contracts_link = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.PARTIAL_LINK_TEXT, "Contract"))
            )
            contracts_link.click()
            
            # 等待下一页的标志性元素“View Details”出现
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.PARTIAL_LINK_TEXT, "Details"))
            )
            logger.info("✅ 已进入 Contracts 页面")
            return True
        except TimeoutException as e:
            logger.error(f"❌ 访问 Contracts 失败: {e}")
            self.driver.save_screenshot('contracts_error.png')
            return False

    def view_details(self):
        """点击 View Details 并等待下一页加载"""
        try:
            logger.info("🔍 正在查找并点击 View Details 按钮")
            view_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.PARTIAL_LINK_TEXT, "Details"))
            )
            view_button.click()

            # 等待详情页的标志性元素“Renew”按钮出现
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.PARTIAL_LINK_TEXT, "Renew"))
            )
            logger.info("✅ 已进入详情页面")
            return True
        except TimeoutException as e:
            logger.error(f"❌ 点击 View Details 失败: {e}")
            self.driver.save_screenshot('view_details_error.png')
            return False

    def renew_server(self):
        """执行续期操作"""
        try:
            logger.info("🔍 正在查找并点击续期按钮")
            renew_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.PARTIAL_LINK_TEXT, "Renew"))
            )
            renew_button.click()
            logger.info("✅ 续期按钮已点击")

            # 处理可能的确认弹窗
            try:
                confirm_button = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Confirm') or contains(text(), 'OK') or contains(text(), '确认')]"))
                )
                confirm_button.click()
                logger.info("✅ 已确认续期")
            except TimeoutException:
                logger.info("ℹ️ 无需点击确认弹窗")

            # 更精确地检查成功提示元素
            try:
                success_message = WebDriverWait(self.driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div.alert-success, div[class*='message-success'], *[class*='success']"))
                )
                logger.info(f"✅ 续期成功！提示信息: {success_message.text.strip()}")
                return True
            except TimeoutException:
                logger.warning("⚠️ 未找到明确的成功提示。操作可能已完成，但无法自动验证。")
                self.driver.save_screenshot('renew_completed_no_prompt.png')
                return True # 保持乐观判断
        except Exception as e:
            logger.error(f"❌ 续期操作失败: {e}")
            self.driver.save_screenshot('renew_error.png')
            return False

    def run(self):
        """运行完整续期流程"""
        start_time = datetime.now()
        logger.info(f"🚀 开始执行续期任务 - {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        try:
            self.setup_driver()
            
            # 步骤 1: 尝试使用 Cookie 登录
            logged_in = self.login_with_cookies()
            
            # 如果 Cookie 登录失败，则回退到用户名密码登录
            if not logged_in:
                logged_in = self.login_with_credentials()

            # 如果两种登录方式都失败，则终止
            if not logged_in:
                logger.error("❌ 登录失败，终止所有操作。")
                return False
            
            # 步骤 2: 导航到合同页
            if not self.navigate_to_contracts():
                return False
            
            # 步骤 3: 查看详情
            if not self.view_details():
                return False
            
            # 步骤 4: 执行续期
            if not self.renew_server():
                return False
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            logger.info(f"🎉 任务成功完成！总耗时: {duration:.2f}秒")
            return True
            
        except Exception as e:
            logger.error(f"❌ 脚本运行期间发生意外错误: {e}")
            if self.driver:
                self.driver.save_screenshot('fatal_error.png')
            return False
        finally:
            if self.driver:
                self.driver.quit()
                logger.info("🔒 浏览器已关闭，资源已释放。")

if __name__ == "__main__":
    # 检查环境变量
    if not os.getenv('USERNAME') or not os.getenv('PASSWORD'):
        logger.error("❌ 关键环境变量缺失！请设置 USERNAME 和 PASSWORD。")
        exit(1)
    
    renewal_task = ServerRenewal()
    is_success = renewal_task.run()
    
    # 根据任务结果返回退出码，便于自动化流程判断
    exit(0 if is_success else 1)
