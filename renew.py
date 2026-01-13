import os
import time
import re
import imaplib
import email
from playwright.sync_api import sync_playwright

# --- 配置區 ---
EUSERV_EMAIL = os.getenv("EUSERV_EMAIL")
EUSERV_PASSWORD = os.getenv("EUSERV_PASSWORD")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")

def get_gmail_pin():
    # ... (保持原本的 get_gmail_pin 代碼不變) ...
    print("正在從 Gmail 獲取 PIN...")
    time.sleep(35) # 稍微多等一下郵件
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(EUSERV_EMAIL, GMAIL_APP_PASSWORD)
        mail.select("inbox")
        status, messages = mail.search(None, '(FROM "support-no-reply@euserv.com" SUBJECT "Confirmation of a Security Check")')
        if status != "OK" or not messages[0]: return None
        latest_msg_id = messages[0].split()[-1]
        res, msg_data = mail.fetch(latest_msg_id, "(RFC822)")
        for response_part in msg_data:
            if isinstance(response_part, tuple):
                msg = email.message_from_bytes(response_part[1])
                content = str(msg)
                pin_match = re.search(r'PIN\s*:\s*(\d+)', content)
                if pin_match: return pin_match.group(1)
        return None
    except: return None

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # 模擬更真實的瀏覽器
        context = browser.new_context(viewport={'width': 1280, 'height': 800})
        page = context.new_page()

        try:
            # 1. 訪問首頁
            print("步驟 1: 正在訪問登錄頁面...")
            page.goto("https://support.euserv.com", wait_until="networkidle", timeout=60000)
            
            # 2. 填寫並登錄
            page.fill('input[name="email"]', EUSERV_EMAIL)
            page.fill('input[name="password"]', EUSERV_PASSWORD)
            
            login_btn = 'input[value="Login"], button:has-text("Login")'
            page.wait_for_selector(login_btn)
            print("找到登錄按鈕，正在提交...")
            
            # 點擊後等待跳轉完成
            with page.expect_navigation(wait_until="networkidle", timeout=60000):
                page.click(login_btn)

            # 3. 檢查是否登錄成功
            print("正在檢查登錄狀態...")
            # 如果頁面依然有 password 輸入框，說明登錄失敗了
            if page.query_selector('input[name="password"]'):
                print("❌ 登錄失敗！請檢查 Secrets 中的郵箱和密碼是否正確。")
                page.screenshot(path="login_failed.png")
                return

            # 4. 尋找 vServer 菜單
            print("步驟 2: 尋找 vServer 菜單...")
            # 有時候按鈕在左側菜單，有時候在中間，使用更寬鬆的匹配
            vserver_selector = 'a:has-text("vServer"), #menu-vserver'
            page.wait_for_selector(vserver_selector, timeout=60000)
            page.click(vserver_selector)

            # 5. 尋找續期按鈕
            print("步驟 3: 檢查續期按鈕...")
            page.wait_for_selector('input[value="Extend contract"], .btn-extend', timeout=30000)
            page.click('input[value="Extend contract"]')

            # 6. 確認續期
            print("步驟 4: 點擊確認續期...")
            page.wait_for_selector('button:has-text("Extend")', timeout=30000)
            page.click('button:has-text("Extend")')

            # 7. 處理 PIN 碼
            print("步驟 5: 等待 PIN 碼輸入框...")
            page.wait_for_selector('input[name="pin"]', timeout=30000)
            pin = get_gmail_pin()
            if pin:
                page.fill('input[name="pin"]', pin)
                page.click('button:has-text("Continue")')
                print("✅ 續期成功！")
            else:
                print("❌ 未能獲取 PIN 碼。")

        except Exception as e:
            print(f"💥 發生異常: {str(e)}")
            page.screenshot(path="error_debug.png")
            print("已保存錯誤截圖 error_debug.png。")
        finally:
            browser.close()

if __name__ == "__main__":
    run()
