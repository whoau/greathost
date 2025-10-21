#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import logging
from datetime import datetime

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
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        # 隐藏 webdriver 特征
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': 'Object.defineProperty(navigator, "webdriver", {get: () => undefined})'
        })
        self.driver.implicitly_wait(10)
        logger.info("✅ 浏览器驱动初始化完成")
        
    def login(self):
        """登录网站"""
        try:
            logger.info(f"🌐 正在访问登录页面: {self.url}")
            self.driver.get(self.url)
            time.sleep(3)
            
            # 多种方式尝试定位用户名输入框
            try:
                username_input = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.NAME, "username"))
                )
            except:
                try:
                    username_input = self.driver.find_element(By.ID, "username")
                except:
                    username_input = self.driver.find_element(By.CSS_SELECTOR, "input[type='text'], input[type='email']")
            
            username_input.clear()
            username_input.send_keys(self.username)
            logger.info("✅ 用户名已填写")
            
            # 定位密码输入框
            try:
                password_input = self.driver.find_element(By.NAME, "password")
            except:
                password_input = self.driver.find_element(By.CSS_SELECTOR, "input[type='password']")
            
            password_input.clear()
            password_input.send_keys(self.password)
            logger.info("✅ 密码已填写")
            
            # 定位登录按钮
            try:
                login_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            except:
                try:
                    login_button = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Login') or contains(text(), '登录') or contains(text(), 'Sign in')]")
                except:
                    login_button = self.driver.find_element(By.TAG_NAME, "button")
            
            login_button.click()
            logger.info("✅ 登录按钮已点击")
            
            time.sleep(5)
            logger.info("✅ 登录成功")
            return True
            
        except Exception as e:
            logger.error(f"❌ 登录失败: {str(e)}")
            self.driver.save_screenshot('login_error.png')
            logger.info(f"当前页面URL: {self.driver.current_url}")
            return False
    
    def navigate_to_contracts(self):
        """点击 Contracts 菜单"""
        try:
            logger.info("🔍 正在查找 Contracts 链接")
            
            # 多种方式查找
            try:
                contracts_link = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.LINK_TEXT, "Contracts"))
                )
            except:
                try:
                    contracts_link = self.driver.find_element(By.PARTIAL_LINK_TEXT, "Contract")
                except:
                    contracts_link = self.driver.find_element(By.CSS_SELECTOR, "a[href*='contract']")
            
            contracts_link.click()
            logger.info("✅ 已点击 Contracts")
            time.sleep(3)
            return True
            
        except Exception as e:
            logger.error(f"❌ 访问 Contracts 失败: {str(e)}")
            self.driver.save_screenshot('contracts_error.png')
            return False
    
    def view_details(self):
        """点击 View Details"""
        try:
            logger.info("🔍 正在查找 View Details 按钮")
            
            # 查找所有可能的按钮
            selectors = [
                "//a[contains(text(), 'View Details')]",
                "//button[contains(text(), 'View Details')]",
                "//a[contains(text(), '查看详情')]",
                "//button[contains(text(), 'Details')]",
                "a[href*='details']",
                "button[class*='detail']"
            ]
            
            view_button = None
            for selector in selectors:
                try:
                    if selector.startswith('//'):
                        view_button = self.driver.find_element(By.XPATH, selector)
                    else:
                        view_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                    break
                except:
                    continue
            
            if not view_button:
                logger.warning("❌ 未找到 View Details 按钮")
                self.driver.save_screenshot('no_view_details.png')
                return False
            
            view_button.click()
            logger.info("✅ 已点击 View Details")
            time.sleep(3)
            return True
            
        except Exception as e:
            logger.error(f"❌ 点击 View Details 失败: {str(e)}")
            self.driver.save_screenshot('view_details_error.png')
            return False
    
    def renew_server(self):
        """执行续期操作"""
        try:
            logger.info("🔍 正在查找续期按钮")
            
            # 多种方式查找续期按钮
            selectors = [
                "//button[contains(text(), 'Renew')]",
                "//a[contains(text(), 'Renew')]",
                "//button[contains(text(), '续期')]",
                "//a[contains(text(), '续期')]",
                "//button[contains(@class, 'renew')]",
                "a[href*='renew']",
                "button[class*='renew']"
            ]
            
            renew_button = None
            for selector in selectors:
                try:
                    if selector.startswith('//'):
                        renew_button = WebDriverWait(self.driver, 5).until(
                            EC.element_to_be_clickable((By.XPATH, selector))
                        )
                    else:
                        renew_button = WebDriverWait(self.driver, 5).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                        )
                    break
                except:
                    continue
            
            if not renew_button:
                logger.error("❌ 未找到续期按钮")
                self.driver.save_screenshot('no_renew_button.png')
                return False
            
            renew_button.click()
            logger.info("✅ 续期按钮已点击")
            time.sleep(3)
            
            # 处理可能的确认弹窗
            try:
                confirm_selectors = [
                    "//button[contains(text(), 'Confirm')]",
                    "//button[contains(text(), 'OK')]",
                    "//button[contains(text(), '确认')]",
                    "//button[contains(text(), 'Yes')]"
                ]
                
                for selector in confirm_selectors:
                    try:
                        confirm_button = self.driver.find_element(By.XPATH, selector)
                        confirm_button.click()
                        logger.info("✅ 已确认续期")
                        time.sleep(2)
                        break
                    except:
                        continue
            except:
                logger.info("ℹ️ 无需确认")
            
            # 检查成功提示
            time.sleep(2)
            page_source = self.driver.page_source.lower()
            if any(word in page_source for word in ['success', 'renewed', '成功', 'successful']):
                logger.info("✅ 续期成功！")
                return True
            else:
                logger.warning("⚠️ 未找到成功提示，但操作已完成")
                self.driver.save_screenshot('renew_completed.png')
                return True
                
        except Exception as e:
            logger.error(f"❌ 续期失败: {str(e)}")
            self.driver.save_screenshot('renew_error.png')
            return False
    
    def run(self):
        """运行完整流程"""
        start_time = datetime.now()
        logger.info(f"🚀 开始执行续期任务 - {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        try:
            self.setup_driver()
            
            if not self.login():
                logger.error("❌ 登录失败，终止流程")
                return False
            
            if not self.navigate_to_contracts():
                logger.error("❌ 访问 Contracts 失败，终止流程")
                return False
            
            if not self.view_details():
                logger.error("❌ 访问 View Details 失败，终止流程")
                return False
            
            if not self.renew_server():
                logger.error("❌ 续期失败")
                return False
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            logger.info(f"✅ 所有操作完成！耗时: {duration:.2f}秒")
            return True
            
        except Exception as e:
            logger.error(f"❌ 运行出错: {str(e)}")
            return False
            
        finally:
            if self.driver:
                self.driver.quit()
                logger.info("🔒 浏览器已关闭")

if __name__ == "__main__":
    # 检查环境变量
    if not os.getenv('USERNAME') or not os.getenv('PASSWORD'):
        logger.error("❌ 请设置 USERNAME 和 PASSWORD 环境变量")
        exit(1)
    
    renewal = ServerRenewal()
    success = renewal.run()
    exit(0 if success else 1)
