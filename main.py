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

        # 搜索来自 EUserv 的邮件
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
                            try:
                                body = part.get_payload(decode=True).decode('utf-8')
                            except UnicodeDecodeError:
                                body = part.get_payload(decode=True).decode(part.get_content_charset() or 'iso-8859-1')
                            break
                else:
                    body = msg.get_payload(decode=True).decode()

                # --- 优化后的 PIN 码正则提取 ---
                match = re.search(r'(?:PIN\s*[:is]*\s*|Ihr\s+PIN\s+ist\s*)\b([A-Z0-9]{4,10})\b', body, re.IGNORECASE)
                
                if not match:
                    # 尝试匹配一个独立的 6-8 位数字串
                    match = re.search(r'\b([0-9]{6,8})\b', body) 
                
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
    chrome_options.add_argument("--headless")
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
        
        login_btn = driver.find_element(By.XPATH, "//input[@value='Login'] | //button[contains(text(),'Login')]")
        login_btn.click()
        print("[*] 提交登录")

        # 2. 导航到合同页面 (保持不变)
        time.sleep(5) 
        try:
            contract_link = wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(@href, 'contracts.iphp')] | //a[contains(text(), 'Contracts')]")))
            contract_link.click()
            print("[*] 进入合同列表")
            time.sleep(3) 
        except:
            print("[*] 假设已在首页或直接显示了列表")

       # 3. *** 查找并点击 Extend contract 链接 (关键修正点) ***
        print("[*] 正在尝试查找并点击 'Extend contract' 链接...")
        
        try:
            # 根据截图，'Extend contract' 是位于合同列表行 (通常在 Actions/Options 列) 中的一个链接
            # 查找包含 'vServer' 文本的表格行中，文本为 'Extend contract' 的链接
            extend_link_xpath = "//td[contains(text(), 'vServer')]/ancestor::tr[1]//a[contains(text(), 'Extend contract')]"
            
            extend_link = wait.until(EC.element_to_be_clickable((By.XPATH, extend_link_xpath)))
            extend_link.click()
            print("[*] 成功点击了 'vServer' 合同旁的 'Extend contract' 链接。")

        except Exception as e:
            if "no such element" in str(e).lower():
                 print("[✓] 经检查，未找到需要续期的合同 (vServer 旁的 Extend contract 链接)。")
            else:
                 print(f"[!] 查找 Extend contract 链接出错: {e}")
            return # 找不到续期目标，退出当前账户流程

        # 4. 选择 Keep existing contract (Free)
        time.sleep(3)
        
        try:
            # 尝试选中 "Keep existing contract" (0.00 EUR 选项)
            keep_radio_xpath = ("//input[@type='radio' and contains(@value, '0.00')] | "
                                "//div[contains(text(), 'Keep existing contract')]/input[@type='radio']")
                                
            keep_radio = wait.until(EC.element_to_be_clickable((By.XPATH, keep_radio_xpath)))
            
            driver.execute_script("arguments[0].scrollIntoView(true);", keep_radio)
            keep_radio.click()
            print("[*] 选择了 Keep existing contract (0.00 EUR 选项)")
            
        except Exception as e:
            print(f"[!] 未找到 Keep existing/0.00 EUR 选项，继续尝试下一步 Extend 确认: {e}")

        # 5. 点击弹窗里的 Extend 按钮
        confirm_extend_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//input[@value='Extend'] | //button[contains(text(), 'Extend')]")))
        confirm_extend_btn.click()
        print("[*] 点击确认续期")

        # 6. 处理 PIN 码 (Security check)
        try:
            pin_input_xpath = "//input[contains(@name, 'pin') or @placeholder='Enter PIN']"
            wait.until(EC.visibility_of_element_located((By.XPATH, pin_input_xpath)))
            print("[*] 弹出 PIN 码验证，等待 30 秒让邮件发送并获取...")
            
            time.sleep(30)
            
            pin_code = get_pin_from_email(account['gmail_user'], account['gmail_app_password'])
            
            if pin_code:
                pin_input = driver.find_element(By.XPATH, pin_input_xpath)
                pin_input.send_keys(pin_code)
                print("[*] 填入 PIN 码")
                
                continue_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Continue')] | //input[@value='Continue']")
                continue_btn.click()
                print("[✓] 已提交 PIN 码，续期流程完成 (请检查日志确认最终结果)")
            else:
                print("[X] 获取 PIN 码失败，无法继续提交。")
                
        except Exception as e:
            print(f"[?] 未检测到 PIN 输入框或出错: {e}，可能不需要 PIN 或已经成功完成续期")

    except Exception as e:
        print(f"[X] 发生致命错误: {e}")
        driver.save_screenshot(f"{account['euserv_email']}_error_screenshot.png")
    
    finally:
        driver.quit()

if __name__ == "__main__":
    # 0. 随机等待 (模拟随机时间段)
    delay = random.randint(60, 3600)
    print(f"[*] 为防风控，随机等待 {delay} 秒...")
    time.sleep(delay)

    # 從環境變量讀取配置
    config_str = os.environ.get("USER_CONFIG")
    if not config_str:
        print("[X] 致命錯誤: 未找到 USER_CONFIG 環境變量")
        exit(1)

    # === 清理字符串，防止 JSON 解析錯誤 ===
    config_str = config_str.strip().replace('\n', '').replace('\r', '')
    
    try:
        accounts = json.loads(config_str)
    except json.JSONDecodeError as e:
        print(f"[X] JSON 格式解析錯誤，請檢查 Secret 格式是否為標準 JSON: {e}")
        exit(1)
    
    for account in accounts:
        run_renewal(account)
