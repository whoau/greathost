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
        wait = WebDriverWait(driver, 30)

        # 1. 访问您指定的登录网址
        print("1. 正在访问您指定的登录网址 https://greathost.es/login ...")
        driver.get("https://greathost.es/login")
        
        # 2. 处理Cookie弹窗（保留此逻辑作为安全措施）
        try:
            print("2. 正在检查并处理Cookie同意弹窗...")
            cookie_accept_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, "btnAccept"))
            )
            cookie_accept_button.click()
            print("✓ 已点击Cookie同意按钮。")
        except TimeoutException:
            print("✓ 未找到Cookie弹窗，或已处理，继续执行。")
        
        # --- 【致命错误修复：切换到 iframe 内部】 ---
        # 这是之前所有失败的根源。登录表单在ID为 "login-iframe" 的iframe里。
        print("3. 正在切换到登录表单的 iframe 中...")
        wait.until(EC.frame_to_be_available_and_switch_to_it((By.ID, "login-iframe")))
        print("✓ 已成功切换到 iframe。")
        # --- 【修复结束】 ---

        # 4. 在 iframe 内部，输入用户名和密码并登录
        print("4. 正在输入用户名和密码...")
        
        # 现在因为已经在iframe里了，下面的代码可以正常工作
        email_input = wait.until(EC.element_to_be_clickable((By.ID, "inputEmail")))
        email_input.send_keys(GREATHOS_USERNAME)
        
        password_input = driver.find_element(By.ID, "inputPassword")
        password_input.send_keys(GREATHOS_PASSWORD)
        
        login_button = driver.find_element(By.ID, "login")
        login_button.click()

        # 登录成功后，页面会跳转，driver会自动从iframe跳回到主页面
        print("   - 等待登录成功并跳转到Dashboard...")
        
        # 5. 等待登录成功后的 Dashboard 页面
        # 此时需要切换回默认内容，因为Dashboard不在iframe里
        driver.switch_to.default_content()
        wait.until(EC.presence_of_element_located((By.XPATH, "//h1[contains(text(), 'Dashboard')]")))
        print("✓ 登录成功！")

        # 后续所有操作都在主页面，无需再动
        print("6. 正在导航到 'Contracts'...")
        contracts_link = wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(@href, 'contracts')]//span[contains(text(), 'Contracts')]")))
        contracts_link.click()
        wait.until(EC.presence_of_element_located((By.XPATH, "//h1[contains(text(), 'My Contracts')]")))
        print("✓ 已进入 'Contracts' 页面。")

        print(f"7. 正在查找合同 '{CONTRACT_IDENTIFIER}'...")
        view_details_xpath = f"//tr[contains(., '{CONTRACT_IDENTIFIER}')]//a[contains(text(), 'View Details')]"
        view_details_button = wait.until(EC.element_to_be_clickable((By.XPATH, view_details_xpath)))
        driver.execute_script("arguments[0].click();", view_details_button)
        print("✓ 已点击 'View Details'。")

        print("8. 正在查找并点击 'Renew' 按钮...")
        renew_button_xpath = "//button[contains(., 'Renew')]"
        renew_button = wait.until(EC.element_to_be_clickable((By.XPATH, renew_button_xpath)))
        driver.execute_script("arguments[0].click();", renew_button)
        print("✓ 已点击 'Renew'。")

        print("9. 正在验证续订流程...")
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
