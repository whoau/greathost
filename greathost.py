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
        # 增加全局等待时间，以应对网络波动
        wait = WebDriverWait(driver, 30)

        # 1. 访问您指定的登录网址
        print("1. 正在访问您指定的登录网址 https://greathost.es/login ...")
        driver.get("https://greathost.es/login")
        
        # --- 【全新增加：处理Cookie弹窗，这是问题的根源】 ---
        try:
            print("2. 正在检查并处理Cookie同意弹窗...")
            # 等待“Aceptar”(接受)按钮出现，最多等10秒
            cookie_accept_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, "btnAccept"))
            )
            cookie_accept_button.click()
            print("✓ 已点击Cookie同意按钮。")
            # 点击后，最好加一个短暂的等待，让页面元素稳定下来
            time.sleep(2)
        except TimeoutException:
            # 如果10秒内没找到这个按钮，说明弹窗可能不存在，直接继续执行，不要报错
            print("✓ 未找到Cookie弹窗，或已处理，继续执行。")
        # --- 【增加步骤结束】 ---

        # 3. 在登录页面输入用户名和密码并登录
        print("3. 正在输入用户名和密码...")
        wait.until(EC.presence_of_element_located((By.ID, "inputEmail"))).send_keys(GREATHOS_USERNAME)
        driver.find_element(By.ID, "inputPassword").send_keys(GREATHOS_PASSWORD)
        driver.find_element(By.ID, "login").click()
        wait.until(EC.presence_of_element_located((By.XPATH, "//h1[contains(text(), 'Dashboard')]")))
        print("✓ 登录成功！")

        # 4. 导航到 Contracts
        print("4. 正在导航到 'Contracts'...")
        contracts_link = wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(@href, 'contracts')]//span[contains(text(), 'Contracts')]")))
        contracts_link.click()
        wait.until(EC.presence_of_element_located((By.XPATH, "//h1[contains(text(), 'My Contracts')]")))
        print("✓ 已进入 'Contracts' 页面。")

        # 5. 查找合同并点击 View Details
        print(f"5. 正在查找合同 '{CONTRACT_IDENTIFIER}'...")
        view_details_xpath = f"//tr[contains(., '{CONTRACT_IDENTIFIER}')]//a[contains(text(), 'View Details')]"
        view_details_button = wait.until(EC.element_to_be_clickable((By.XPATH, view_details_xpath)))
        driver.execute_script("arguments[0].click();", view_details_button)
        print("✓ 已点击 'View Details'。")

        # 6. 点击 Renew
        print("6. 正在查找并点击 'Renew' 按钮...")
        renew_button_xpath = "//button[contains(., 'Renew')]"
        renew_button = wait.until(EC.element_to_be_clickable((By.XPATH, renew_button_xpath)))
        renew_button.click()
        print("✓ 已点击 'Renew'。")

        # 7. 验证结果
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
