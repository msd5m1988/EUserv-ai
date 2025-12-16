import os
import time
import json
import random
import imaplib
import email
import re
from email.header import decode_header
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options

# === 配置函数 ===
def get_pin_from_email(gmail_user, gmail_app_pass):
    """连接Gmail IMAP获取最新的EUserv PIN码"""
    try:
        print(f"[*] 正在尝试连接邮箱 {gmail_user} 获取 PIN...")
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(gmail_user, gmail_app_pass)
        mail.select("inbox")

        # 搜索来自 EUserv 的邮件 (Subject usually contains 'PIN' or 'Security check')
        # 根据截图，标题可能是 "PIN for the confirmation..."
        status, messages = mail.search(None, '(FROM "support@euserv.com")')
        
        if status != "OK":
            print("[!] 无法搜索邮件")
            return None

        email_ids = messages[0].split()
        if not email_ids:
            print("[!] 未找到 EUserv 邮件")
            return None

        # 获取最新的一封
        latest_email_id = email_ids[-1]
        status, msg_data = mail.fetch(latest_email_id, "(RFC822)")
        
        for response_part in msg_data:
            if isinstance(response_part, tuple):
                msg = email.message_from_bytes(response_part[1])
                subject, encoding = decode_header(msg["Subject"])[0]
                if isinstance(subject, bytes):
                    subject = subject.decode(encoding if encoding else "utf-8")
                
                print(f"[*] 找到邮件标题: {subject}")
                
                # 获取邮件正文
                body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            body = part.get_payload(decode=True).decode()
                            break
                else:
                    body = msg.get_payload(decode=True).decode()

                # 使用正则提取PIN码 (假设PIN是纯数字或字母数字组合)
                # 根据截图，需要在邮件内容中找 PIN
                # 假设格式: "Your PIN is: 123456" 或类似
                # 这里做一个宽泛的匹配，通常PIN是单独的一行或者跟在特定词后面
                # 简单粗暴提取最近的一个看起来像验证码的字符串
                # 截图里 PIN 输入框很短，猜测 PIN 是 4-8 位
                # 请根据实际邮件内容调整下面的正则
                match = re.search(r'\b[A-Za-z0-9]{4,10}\b', body) 
                # 更好的方式是看邮件里 PIN 具体的上下文，这里假设邮件里有明显数字
                # 如果能提供邮件正文截图，正则可以写得更准。
                # 暂时尝试提取正文中明显的数字:
                match = re.search(r'PIN\s*[:is]*\s*([a-zA-Z0-9]+)', body, re.IGNORECASE)
                
                if match:
                    pin = match.group(1)
                    print(f"[*] 提取到 PIN: {pin}")
                    return pin
                else:
                    print("[!] 未在邮件中匹配到 PIN 格式")
        
        mail.close()
        mail.logout()
    except Exception as e:
        print(f"[!] 邮箱读取错误: {e}")
    return None

def run_renewal(account):
    print(f"--- 开始处理账户: {account['euserv_email']} ---")
    
    # 设置 Chrome 无头模式
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # GitHub Actions 必须无头
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    wait = WebDriverWait(driver, 20)

    try:
        # 1. 登录
        driver.get("https://support.euserv.com/index.iphp")
        print("[*] 打开登录页面")
        
        email_field = wait.until(EC.visibility_of_element_located((By.NAME, "email")))
        pass_field = driver.find_element(By.NAME, "password")
        
        email_field.send_keys(account['euserv_email'])
        pass_field.send_keys(account['euserv_password'])
        
        # 点击登录按钮 (根据截图是蓝色按钮 Login)
        login_btn = driver.find_element(By.XPATH, "//input[@value='Login'] | //button[contains(text(),'Login')]")
        login_btn.click()
        print("[*] 提交登录")

        # 2. 检测是否登录成功并跳转到合同列表
        # 假设登录后 URL 变了或者有特定元素，这里简单等待
        time.sleep(5) 
        
        # 导航到合同页面 (如果登录后不是直接在合同页)
        # 通常需要点击左侧的 "Contracts"
        try:
            contract_link = driver.find_element(By.XPATH, "//a[contains(text(), 'Contracts')]")
            contract_link.click()
            print("[*] 进入合同列表")
        except:
            print("[*] 假设已在首页或直接显示了列表")

        # 3. 查找续期按钮 (Extend contract)
        # 根据截图，是在表格右侧的 "Details" 或者操作栏
        # 这里寻找页面上所有的 "Extend contract" 链接/按钮
        # 注意：截图显示如果不需续期，可能没有那个按钮，或者按钮是灰的
        
        # 查找包含 'Extend contract' 的元素
        extend_buttons = driver.find_elements(By.XPATH, "//span[contains(text(), 'Extend contract')] | //a[contains(text(), 'Extend contract')]")
        
        if not extend_buttons:
            print("[✓] 未发现需要续期的合同。")
            return

        print(f"[*] 发现 {len(extend_buttons)} 个待续期合同，开始处理...")

        # 这里的逻辑是处理第一个，如果需要处理多个，需要循环刷新页面
        # 简单起见，处理第一个
        extend_buttons[0].click()
        print("[*] 点击了 Extend contract")

        # 4. 选择 Keep existing contract (Free)
        # 截图显示这是一个 Radio button "Keep existing contract"
        # 或者是一个包含 "Free" 字样的选项
        time.sleep(3)
        
        # 尝试选中 "Keep existing contract" (根据截图是第一个选项)
        try:
            # 这里可能需要根据具体的 HTML 结构来定位，尝试定位 value 包含 free 的 radio
            # 或者直接找 "Extend" 蓝色按钮上面的 Radio
            keep_radio = driver.find_element(By.XPATH, "//input[@type='radio' and contains(@onclick, '0.00 EUR')] | //div[contains(text(), 'Keep existing contract')]//preceding-sibling::input")
            keep_radio.click()
            print("[*] 选择了 Keep existing contract")
        except:
            print("[!] 未找到 Keep existing 选项，尝试直接点击 Extend")

        # 5. 点击弹窗里的 Extend 按钮
        # 截图中有个蓝色的 Extend 按钮
        confirm_extend_btn = driver.find_element(By.XPATH, "//input[@value='Extend'] | //button[contains(text(), 'Extend')]")
        confirm_extend_btn.click()
        print("[*] 点击确认续期")

        # 6. 处理 PIN 码 (Security check)
        # 等待 PIN 输入框出现
        try:
            wait.until(EC.visibility_of_element_located((By.XPATH, "//input[contains(@name, 'pin') or @placeholder='Enter PIN']")))
            print("[*] 弹出 PIN 码验证，正在去邮箱获取...")
            
            # 等待几十秒让邮件发送
            time.sleep(30)
            
            pin_code = get_pin_from_email(account['gmail_user'], account['gmail_app_password'])
            
            if pin_code:
                pin_input = driver.find_element(By.XPATH, "//input[contains(@name, 'pin') or @placeholder='Enter PIN']")
                pin_input.send_keys(pin_code)
                print("[*] 填入 PIN 码")
                
                # 点击 Continue
                continue_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Continue')] | //input[@value='Continue']")
                continue_btn.click()
                print("[✓] 已提交 PIN 码，续期流程完成 (请检查日志确认最终结果)")
            else:
                print("[X] 获取 PIN 码失败，无法继续")
                
        except Exception as e:
            print(f"[?] 未检测到 PIN 输入框或出错: {e}，可能不需要 PIN 或已经成功")

    except Exception as e:
        print(f"[X] 发生错误: {e}")
        # 保存截图以便调试 (在 GitHub Actions Artifacts 中查看)
        driver.save_screenshot("error_screenshot.png")
    
    finally:
        driver.quit()

if __name__ == "__main__":
    # 0. 随机等待 (模拟随机时间段)
    # GitHub Action 是准点触发，我们在代码里 sleep
    # 需求：随机时间段。这里设置 0 到 3600秒 (1小时) 之间的随机等待
    delay = random.randint(60, 3600)
    print(f"[*] 为防风控，随机等待 {delay} 秒...")
    time.sleep(delay)

    # 從環境變量讀取配置
    config_str = os.environ.get("USER_CONFIG")
    if not config_str:
        print("[X] 致命錯誤: 未找到 USER_CONFIG 環境變量")
        exit(1)

    # === 新增：清理字符串，防止 JSON 解析錯誤 ===
    # 去除前後空白，並去除字符串內部的換行符
    config_str = config_str.strip().replace('\n', '').replace('\r', '')
    
    try:
        accounts = json.loads(config_str)
    except json.JSONDecodeError as e:
        print(f"[X] JSON 格式解析錯誤，請檢查 Secret 格式是否為標準 JSON: {e}")
        exit(1)
    
    for account in accounts:
        run_renewal(account)
