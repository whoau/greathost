import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# --- 配置信息 ---
# 警告：请勿将真实的用户名和密码直接硬编码在此处并上传到公共仓库。
# 推荐使用环境变量或更安全的密钥管理方式。
GREATHOS_USERNAME = "your_email@example.com"  # 替换为您的登录邮箱
GREATHOS_PASSWORD = "your_password"          # 替换为您的登录密码

# 您要续订的合同标识符（例如，与合同关联的域名或服务名称）
# 脚本会用这个标识符在合同列表中找到正确的合同
CONTRACT_IDENTIFIER = "your_domain.com" # 例如 "myservice.com" 或 "Web Hosting"

# -----------------

# 设置WebDriver（以Chrome为例）
# 如果chromedriver不在脚本同级目录或系统PATH中，需要指定路径
# driver = webdriver.Chrome(executable_path='/path/to/your/chromedriver')
options = webdriver.ChromeOptions()
# 如果你想在后台运行，不打开浏览器窗口，请取消下一行的注释
# options.add_argument("--headless") 
options.add_argument("--start-maximized") # 最大化窗口，避免元素被遮挡
driver = webdriver.Chrome(options=options)

# 设置一个全局的显式等待，最长等待时间为20秒
wait = WebDriverWait(driver, 20)

def login():
    """登录到GreatHost.es"""
    try:
        print("1. 正在打开登录页面...")
        driver.get("https://greathost.es/clients/login")

        print("2. 正在输入用户名和密码...")
        # 等待用户名输入框加载完成
        username_input = wait.until(EC.presence_of_element_located((By.ID, "username")))
        password_input = driver.find_element(By.ID, "password")

        username_input.send_keys(GREATHOS_USERNAME)
        password_input.send_keys(GREATHOS_PASSWORD)

        print("3. 正在点击登录按钮...")
        login_button = driver.find_element(By.ID, "login")
        login_button.click()

        # 等待登录成功并跳转到Dashboard，判断标志是 "Dashboard" 标题的出现
        wait.until(EC.presence_of_element_located((By.XPATH, "//h1[contains(text(), 'Dashboard')]")))
        print("✓ 登录成功！已进入Dashboard。")
        return True
    except TimeoutException:
        print("✗ 登录失败：页面加载超时或找不到登录元素。请检查您的网络和网站状态。")
        return False
    except Exception as e:
        print(f"✗ 登录过程中发生未知错误: {e}")
        return False

def navigate_to_contracts():
    """从Dashboard导航到Contracts页面"""
    try:
        print("4. 正在导航到 'Contracts' 页面...")
        # 网站导航栏中的"Contracts"链接
        contracts_link = wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(@href, 'contracts')]//span[contains(text(), 'Contracts')]")))
        contracts_link.click()

        # 等待Contracts页面加载完成
        wait.until(EC.presence_of_element_located((By.XPATH, "//h1[contains(text(), 'My Contracts')]")))
        print("✓ 已成功进入 'Contracts' 页面。")
        return True
    except TimeoutException:
        print("✗ 导航失败：找不到 'Contracts' 链接或页面加载超时。")
        return False
    except Exception as e:
        print(f"✗ 导航到 'Contracts' 页面时发生错误: {e}")
        return False

def renew_contract():
    """在合同列表中找到指定合同并点击续订"""
    try:
        print(f"5. 正在合同列表中查找 '{CONTRACT_IDENTIFIER}'...")
        
        # 这个XPath非常关键：
        # 它查找一个表格行(tr)，这个行中必须包含你指定的CONTRACT_IDENTIFIER文本
        # 然后在这一行内，查找包含 "View Details" 文本的链接(a)
        # 这种定位方式比绝对路径更稳定
        view_details_xpath = f"//tr[contains(., '{CONTRACT_IDENTIFIER}')]//a[contains(text(), 'View Details')]"
        
        view_details_button = wait.until(EC.element_to_be_clickable((By.XPATH, view_details_xpath)))
        
        print(f"✓ 找到合同 '{CONTRACT_IDENTIFIER}'，正在点击 'View Details'...")
        # 使用JavaScript点击，可以避免一些遮挡或不可点击的问题
        driver.execute_script("arguments[0].click();", view_details_button)

        print("6. 正在 'View Details' 页面查找并点击 'Renew' 按钮...")
        # 等待Renew按钮加载完成
        renew_button_xpath = "//button[contains(., 'Renew')]"  # 假设它是一个包含'Renew'文本的按钮
        renew_button = wait.until(EC.element_to_be_clickable((By.XPATH, renew_button_xpath)))
        
        print("✓ 找到 'Renew' 按钮，正在点击...")
        renew_button.click()
        
        # 续订操作通常会跳转到购物车或支付页面
        # 等待页面跳转后的某个标志性元素，例如 "Checkout"
        wait.until(EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'Checkout') or contains(text(), 'Shopping Cart')]")))
        print("✓ 已成功点击 'Renew' 并进入续订流程页面！")
        print("脚本任务完成。后续支付流程需要您手动操作。")
        return True
        
    except TimeoutException:
        print(f"✗ 操作失败：找不到合同 '{CONTRACT_IDENTIFIER}' 或其 'View Details'/'Renew' 按钮。")
        print("请检查：")
        print(f"  - '{CONTRACT_IDENTIFIER}' 是否拼写正确且在合同列表中可见。")
        print("  - 网站的HTML结构是否已改变。")
        return False
    except NoSuchElementException:
        print("✗ 操作失败：元素未找到。可能是页面结构发生了变化。")
        return False
    except Exception as e:
        print(f"✗ 续订过程中发生未知错误: {e}")
        return False


if __name__ == "__main__":
    if not all([GREATHOS_USERNAME != "your_email@example.com", GREATHOS_PASSWORD != "your_password", CONTRACT_IDENTIFIER != "your_domain.com"]):
        print("!!! 警告：请先修改脚本中的配置信息（用户名、密码、合同标识符）再运行。")
    else:
        try:
            if login():
                if navigate_to_contracts():
                    renew_contract()
        finally:
            # 脚本执行完毕后，暂停10秒，方便您查看最后的结果，然后自动关闭浏览器
            print("\n脚本执行完毕，浏览器将在10秒后关闭...")
            time.sleep(10)
            driver.quit()
            print("浏览器已关闭。")
