import os
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException

def setup_driver():
    """设置Chrome浏览器驱动"""
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    driver = webdriver.Chrome(options=chrome_options)
    return driver

def login(driver, username, password):
    """登录到GreatHost"""
    try:
        print("正在访问登录页面...")
        driver.get("https://greathost.es/login")
        time.sleep(3)
        
        # 查找并填写用户名
        print("输入用户名...")
        username_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.NAME, "username"))
        )
        username_field.clear()
        username_field.send_keys(username)
        
        # 查找并填写密码
        print("输入密码...")
        password_field = driver.find_element(By.NAME, "password")
        password_field.clear()
        password_field.send_keys(password)
        
        # 点击登录按钮
        print("点击登录按钮...")
        login_button = driver.find_element(By.XPATH, "//button[@type='submit']")
        login_button.click()
        
        # 等待登录成功
        time.sleep(5)
        print("登录成功!")
        return True
        
    except Exception as e:
        print(f"登录失败: {str(e)}")
        return False

def navigate_to_contracts(driver):
    """导航到Contracts页面"""
    try:
        print("正在导航到Contracts页面...")
        
        # 查找并点击Contracts链接
        contracts_link = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'Contracts')]"))
        )
        contracts_link.click()
        
        time.sleep(3)
        print("已进入Contracts页面")
        return True
        
    except Exception as e:
        print(f"导航到Contracts失败: {str(e)}")
        return False

def click_view_details(driver):
    """点击View Details按钮"""
    try:
        print("正在查找View Details按钮...")
        
        # 查找View Details按钮
        view_details_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'View Details')] | //a[contains(text(), 'View Details')]"))
        )
        view_details_button.click()
        
        time.sleep(3)
        print("已点击View Details")
        return True
        
    except Exception as e:
        print(f"点击View Details失败: {str(e)}")
        return False

def renew_contract(driver):
    """点击续期按钮"""
    try:
        print("正在查找续期按钮...")
        
        # 查找并点击renew+12hour按钮
        renew_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'renew+12hour')] | //a[contains(text(), 'renew+12hour')]"))
        )
        
        print("找到续期按钮，正在点击...")
        renew_button.click()
        
        time.sleep(3)
        
        # 检查是否有确认对话框
        try:
            confirm_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Confirm')] | //button[contains(text(), '确认')]")
            if confirm_button:
                print("发现确认按钮，点击确认...")
                confirm_button.click()
                time.sleep(2)
        except NoSuchElementException:
            pass
        
        print("续期操作完成!")
        return True
        
    except TimeoutException:
        print("未找到续期按钮，可能已经续期或页面结构已变化")
        return False
    except Exception as e:
        print(f"续期失败: {str(e)}")
        return False

def main():
    """主函数"""
    # 从环境变量获取登录凭据
    username = os.environ.get('GREATHOST_USERNAME')
    password = os.environ.get('GREATHOST_PASSWORD')
    
    if not username or not password:
        print("错误: 请设置GREATHOST_USERNAME和GREATHOST_PASSWORD环境变量")
        return False
    
    driver = None
    try:
        # 初始化浏览器
        driver = setup_driver()
        
        # 执行登录
        if not login(driver, username, password):
            return False
        
        # 导航到Contracts
        if not navigate_to_contracts(driver):
            return False
        
        # 点击View Details
        if not click_view_details(driver):
            return False
        
        # 执行续期
        if not renew_contract(driver):
            return False
        
        print("✅ 所有操作成功完成!")
        return True
        
    except Exception as e:
        print(f"发生错误: {str(e)}")
        return False
    
    finally:
        if driver:
            driver.quit()
            print("浏览器已关闭")

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
