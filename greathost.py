import os
import sys
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

# --- 从环境变量读取配置信息 ---
GREATHOS_USERNAME = os.getenv("GREATHOS_USERNAME")
GREATHOS_PASSWORD = os.getenv("GREATHOS_PASSWORD")
CONTRACT_IDENTIFIER = os.getenv("CONTRACT_IDENTIFIER")

def main():
    """主执行函数"""
    if not all([GREATHOS_USERNAME, GREATHOS_PASSWORD, CONTRACT_IDENTIFIER]):
        print("错误：环境变量 GREATHOS_USERNAME, GREATHOS_PASSWORD, 或 CONTRACT_IDENTIFIER 未设置。")
        sys.exit(1)

    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    
    driver = None
    try:
        print("正在启动 WebDriver...")
        driver = webdriver.Chrome(options=options)
        wait = WebDriverWait(driver, 20)

        # 1. 【最终版，严格遵守】使用您指定的网址 https://greathost.es/login
        print("1. 正在访问您指定的登录网址 https://greathost.es/login ...")
        driver.get("https://greathost.es/login")
        
        # 2. 在登录页面输入用户名和密码并登录
        print("2. 正在输入用户名和密码...")
        # Selenium会自动处理从 /login 到 /clients/login 的跳转，所以后续元素定位依然有效
        wait.until(EC.presence_of_element_located((By.ID, "username"))).send_keys(GREATHOS_USERNAME)
        driver.find_element(By.ID, "password").send_keys(GREATHOS_PASSWORD)
        driver.find_element(By.ID, "login").click()
        wait.until(EC.presence_of_element_located((By.XPATH, "//h1[contains(text(), 'Dashboard')]")))
        print("✓ 登录成功！")

        # 3. 导航到 Contracts
        print("3. 正在导航到 'Contracts'...")
        contracts_link = wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(@href, 'contracts')]//span[contains(text(), 'Contracts')]")))
        contracts_link.click()
        wait.until(EC.presence_of_element_located((By.XPATH, "//h1[contains(text(), 'My Contracts')]")))
        print("✓ 已进入 'Contracts' 页面。")

        # 4. 查找合同并点击 View Details
        print(f"4. 正在查找合同 '{CONTRACT_IDENTIFIER}'...")
        view_details_xpath = f"//tr[contains(., '{CONTRACT_IDENTIFIER}')]//a[contains(text(), 'View Details')]"
        view_details_button = wait.until(EC.element_to_be_clickable((By.XPATH, view_details_xpath)))
        driver.execute_script("arguments[0].click();", view_details_button)
        print("✓ 已点击 'View Details'。")

        # 5. 点击 Renew
        print("5. 正在查找并点击 'Renew' 按钮...")
        renew_button_xpath = "//button[contains(., 'Renew')]"
        renew_button = wait.until(EC.element_to_be_clickable((By.XPATH, renew_button_xpath)))
        renew_button.click()
        print("✓ 已点击 'Renew'。")

        # 6. 验证结果
        wait.until(EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'Checkout') or contains(text(), 'Shopping Cart')]")))
        print("🎉 任务成功！已将续订项目加入购物车。")
        
    except Exception as e:
        print(f"✗ 脚本执行失败: {e}")
        if driver:
            screenshot_path = "error_screenshot.png"
            driver.save_screenshot(screenshot_path)
            print(f"已保存错误截图 '{screenshot_path}'。")
        sys.exit(1)
    finally:
        if driver:
            driver.quit()
            print("WebDriver 已关闭。")

if __name__ == "__main__":
    main()
