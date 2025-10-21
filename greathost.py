#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ServerRenewal:
    def __init__(self):
        self.url = os.getenv('LOGIN_URL', 'https://example.com/login')
        self.username = os.getenv('USERNAME')
        self.password = os.getenv('PASSWORD')
        self.driver = None
        
    def setup_driver(self):
        """配置 Chrome 驱动"""
        chrome_options = Options()
        chrome_options.add_argument('--headless')  # 无头模式
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.implicitly_wait(10)
        logger.info("浏览器驱动初始化完成")
        
    def login(self):
        """登录网站"""
        try:
            logger.info(f"正在访问登录页面: {self.url}")
            self.driver.get(self.url)
            time.sleep(2)
            
            # 等待并填写用户名（根据实际网站调整选择器）
            username_input = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.NAME, "username"))
                # 或使用其他定位方式：
                # EC.presence_of_element_located((By.ID, "username"))
                # EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='username']"))
            )
            username_input.clear()
            username_input.send_keys(self.username)
            logger.info("用户名已填写")
            
            # 填写密码
            password_input = self.driver.find_element(By.NAME, "password")
            password_input.clear()
            password_input.send_keys(self.password)
            logger.info("密码已填写")
            
            # 点击登录按钮
            login_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            # 或使用：By.XPATH, "//button[contains(text(), 'Login')]"
            login_button.click()
            logger.info("登录按钮已点击")
            
            # 等待登录成功
            time.sleep(3)
            logger.info("登录成功")
            return True
            
        except TimeoutException:
            logger.error("登录超时")
            self.driver.save_screenshot('login_error.png')
            return False
        except Exception as e:
            logger.error(f"登录失败: {str(e)}")
            self.driver.save_screenshot('login_error.png')
            return False
    
    def navigate_to_contracts(self):
        """点击 Contracts 菜单"""
        try:
            logger.info("正在查找 Contracts 链接")
            
            # 方式1: 通过文本查找
            contracts_link = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.LINK_TEXT, "Contracts"))
                # 或部分文本匹配：
                # EC.element_to_be_clickable((By.PARTIAL_LINK_TEXT, "Contract"))
            )
            
            # 方式2: 通过 CSS 选择器
            # contracts_link = self.driver.find_element(By.CSS_SELECTOR, "a[href*='contracts']")
            
            # 方式3: 通过 XPath
            # contracts_link = self.driver.find_element(By.XPATH, "//a[contains(text(), 'Contracts')]")
            
            contracts_link.click()
            logger.info("已点击 Contracts")
            time.sleep(2)
            return True
            
        except Exception as e:
            logger.error(f"访问 Contracts 失败: {str(e)}")
            self.driver.save_screenshot('contracts_error.png')
            return False
    
    def view_details(self):
        """点击 View Details"""
        try:
            logger.info("正在查找 View Details 按钮")
            
            # 如果有多个服务器，处理所有的续期按钮
            view_buttons = self.driver.find_elements(By.XPATH, "//a[contains(text(), 'View Details')] | //button[contains(text(), 'View Details')]")
            
            if not view_buttons:
                logger.warning("未找到 View Details 按钮")
                return False
            
            logger.info(f"找到 {len(view_buttons)} 个 View Details 按钮")
            
            # 点击第一个（或遍历所有）
            view_buttons[0].click()
            logger.info("已点击 View Details")
            time.sleep(2)
            return True
            
        except Exception as e:
            logger.error(f"点击 View Details 失败: {str(e)}")
            self.driver.save_screenshot('view_details_error.png')
            return False
    
    def renew_server(self):
        """执行续期操作"""
        try:
            logger.info("正在查找续期按钮")
            
            # 查找续期按钮（根据实际情况调整）
            renew_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, 
                    "//button[contains(text(), 'Renew')] | //a[contains(text(), 'Renew')] | //button[contains(text(), '续期')]"))
            )
            
            renew_button.click()
            logger.info("续期按钮已点击")
            time.sleep(2)
            
            # 如果有确认弹窗，处理确认
            try:
                confirm_button = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Confirm')] | //button[contains(text(), '确认')]")
                confirm_button.click()
                logger.info("已确认续期")
                time.sleep(2)
            except NoSuchElementException:
                logger.info("无需确认，续期完成")
            
            # 验证续期成功
            try:
                success_message = self.driver.find_element(By.XPATH, 
                    "//*[contains(text(), 'success') or contains(text(), '成功')]")
                logger.info(f"续期成功: {success_message.text}")
                return True
            except NoSuchElementException:
                logger.warning("未找到成功提示，但操作已完成")
                return True
                
        except Exception as e:
            logger.error(f"续期失败: {str(e)}")
            self.driver.save_screenshot('renew_error.png')
            return False
    
    def run(self):
        """运行完整流程"""
        try:
            self.setup_driver()
            
            if not self.login():
                logger.error("登录失败，终止流程")
                return False
            
            if not self.navigate_to_contracts():
                logger.error("访问 Contracts 失败，终止流程")
                return False
            
            if not self.view_details():
                logger.error("访问 View Details 失败，终止流程")
                return False
            
            if not self.renew_server():
                logger.error("续期失败")
                return False
            
            logger.info("✅ 所有操作完成")
            return True
            
        except Exception as e:
            logger.error(f"运行出错: {str(e)}")
            return False
            
        finally:
            if self.driver:
                self.driver.quit()
                logger.info("浏览器已关闭")

if __name__ == "__main__":
    # 检查必需的环境变量
    if not os.getenv('USERNAME') or not os.getenv('PASSWORD'):
        logger.error("请设置 USERNAME 和 PASSWORD 环境变量")
        exit(1)
    
    renewal = ServerRenewal()
    success = renewal.run()
    exit(0 if success else 1)
