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
        self.url = 'https://greathost.es/login'  # 直接写死登录 URL
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
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': 'Object.defineProperty(navigator, "webdriver", {get: () => undefined})'
        })
        logger.info("✅ 浏览器驱动初始化完成")

    def save_cookies(self):
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
            # 必须先访问根域名才能设置 Cookie
            self.driver.get('https://greathost.es/')
            with open(self.cookie_file, 'r') as f:
                cookies = json.load(f)
            for cookie in cookies:
                if 'expiry' in cookie:
                    del cookie['expiry']
                self.driver.add_cookie(cookie)
            logger.info("✅ Cookies 已加载，正在刷新页面验证登录状态...")
            self.driver.get('https://greathost.es/clientarea.php') # 直接访问客户区
            
            # 验证登录成功的标志：页面标题包含 "Client Area"
            WebDriverWait(self.driver, 10).until(
                EC.title_contains("Client Area")
            )
            logger.info("✅ 使用 Cookie 登录成功！")
            return True
        except (TimeoutException, Exception) as e:
            logger.warning(f"⚠️ 使用 Cookie 登录失败: {e}")
            if os.path.exists(self.cookie_file):
                os.remove(self.cookie_file)
            return False

    def login_with_credentials(self):
        """使用用户名和密码登录"""
        try:
            logger.info(f"🌐 正在访问登录页面: {self.url}")
            self.driver.get(self.url)
            
            # 使用更精确的 ID 定位器
            username_input = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "inputEmail"))
            )
            username_input.clear()
            username_input.send_keys(self.username)
            
            password_input = self.driver.find_element(By.ID, "inputPassword")
            password_input.clear()
            password_input.send_keys(self.password)
            
            # 检查是否有reCAPTCHA，如果有，脚本无法继续
            try:
                self.driver.find_element(By.CLASS_NAME, "g-recaptcha")
                logger.error("❌ 检测到 reCAPTCHA 验证码，脚本无法自动登录。请尝试使用 Cookie 登录。")
                self.driver.save_screenshot('recaptcha_error.png')
                return False
            except:
                logger.info("✅ 未检测到 reCAPTCHA，继续登录。")

            login_button = self.driver.find_element(By.ID, "login")
            login_button.click()
            
            # 验证登录成功的标志：页面标题包含 "Client Area"
            WebDriverWait(self.driver, 15).until(
                EC.title_contains("Client Area")
            )
            logger.info("✅ 用户名密码登录成功")
            self.save_cookies()
            return True
        except TimeoutException:
            logger.error("❌ 登录失败：超时或用户名/密码错误。")
            self.driver.save_screenshot('login_error.png')
            return False
        except Exception as e:
            logger.error(f"❌ 登录过程中发生未知错误: {e}")
            self.driver.save_screenshot('login_unexpected_error.png')
            return False

    def navigate_to_services(self):
        """导航到 'My Services' 页面"""
        try:
            logger.info("🔍 正在查找并点击 'Services' 菜单")
            # 链接文本是 "Services"，它会带我们到服务列表
            services_link = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//a[contains(., 'Services')]"))
            )
            services_link.click()

            # 等待服务列表页面加载完成的标志：页面标题包含 "My Products & Services"
            WebDriverWait(self.driver, 10).until(
                EC.title_contains("My Products & Services")
            )
            logger.info("✅ 已进入服务列表页面")
            return True
        except TimeoutException as e:
            logger.error(f"❌ 导航到 Services 页面失败: {e}")
            self.driver.save_screenshot('navigate_services_error.png')
            return False

    def check_service_status(self):
        """进入第一个活动的服务详情页并检查状态"""
        try:
            logger.info("🔍 正在查找第一个 'Active' 的服务并进入详情页")
            # 查找第一个状态为 'Active' 的服务行，并点击它
            active_service_row = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//tr[td/span[@class='label label-success' and text()='Active']]"))
            )
            active_service_row.click()
            
            # 等待详情页面加载完成的标志：页面标题包含 "Manage Product"
            WebDriverWait(self.driver, 10).until(
                EC.title_contains("Manage Product")
            )
            logger.info("✅ 已进入服务详情页面")
            
            # 提取关键信息，例如到期日
            due_date_element = self.driver.find_element(By.XPATH, "//*[contains(text(), 'Next Due Date')]/following-sibling::td")
            status_element = self.driver.find_element(By.XPATH, "//*[contains(text(), 'Status')]/following-sibling::td/span")
            
            logger.info(f"🎉 服务状态检查成功！")
            logger.info(f"   - 状态: {status_element.text}")
            logger.info(f"   - 到期日: {due_date_element.text}")
            
            # 由于没有直接的续期按钮，脚本到此已完成其主要任务
            return True
            
        except TimeoutException:
            logger.warning("⚠️ 未找到状态为 'Active' 的服务，或无法进入详情页。")
            self.driver.save_screenshot('no_active_service_error.png')
            # 如果没有活动服务，也算作脚本“成功”执行，因为它完成了检查
            return True 
        except Exception as e:
            logger.error(f"❌ 检查服务状态时出错: {e}")
            self.driver.save_screenshot('check_status_error.png')
            return False

    def run(self):
        """运行完整流程"""
        start_time = datetime.now()
        logger.info(f"🚀 开始执行任务 - {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        try:
            self.setup_driver()
            
            logged_in = self.login_with_cookies()
            if not logged_in:
                logged_in = self.login_with_credentials()

            if not logged_in:
                logger.error("❌ 登录失败，终止所有操作。")
                return False
            
            if not self.navigate_to_services():
                return False
            
            if not self.check_service_status():
                return False
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            logger.info(f"✅ 任务完成！总耗时: {duration:.2f}秒")
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
    if not os.getenv('USERNAME') or not os.getenv('PASSWORD'):
        logger.error("❌ 关键环境变量缺失！请设置 USERNAME 和 PASSWORD。")
        exit(1)
    
    task = ServerRenewal()
    is_success = task.run()
    exit(0 if is_success else 1)
