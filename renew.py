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
    """從 Gmail 獲取最新的 EuServ PIN 碼"""
    print("正在檢查 Gmail 獲取 PIN 碼...")
    # 等待郵件發送（約 30 秒）
    time.sleep(30)
    
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(EUSERV_EMAIL, GMAIL_APP_PASSWORD)
        mail.select("inbox")
        
        # 搜索來自 EuServ 的郵件
        status, messages = mail.search(None, '(FROM "support-no-reply@euserv.com" SUBJECT "Confirmation of a Security Check")')
        if status != "OK" or not messages[0]:
            return None
            
        latest_msg_id = messages[0].split()[-1]
        res, msg_data = mail.fetch(latest_msg_id, "(RFC822)")
        
        for response_part in msg_data:
            if isinstance(response_part, tuple):
                msg = email.message_from_bytes(response_part[1])
                content = str(msg)
                # 正則匹配 PIN: 181941 這種格式
                pin_match = re.search(r'PIN\s*:\s*(\d+)', content)
                if pin_match:
                    return pin_match.group(1)
        return None
    except Exception as e:
        print(f"提取 PIN 碼失敗: {e}")
        return None

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True) # GitHub 環境必須 True
        context = browser.new_context()
        page = context.new_page()

        # 步驟 1: 登錄
        print("步驟 1: 正在登錄 EuServ...")
        page.goto("https://support.euserv.com")
        page.fill('input[name="email"]', EUSERV_EMAIL)
        page.fill('input[name="password"]', EUSERV_PASSWORD)
        page.click('button:has-text("Login")')
        
        # 步驟 2: 點擊 vServer
        print("步驟 2: 進入 vServer 控制面板...")
        page.wait_for_selector('a:has-text("vServer")')
        page.click('a:has-text("vServer")')

        # 步驟 3: 檢查是否有續期按鈕
        # 如果這個月已經續期成功，按鈕通常不會是 "Extend contract" 或者狀態已更新
        extend_btn = page.query_selector('input[value="Extend contract"]')
        if not extend_btn:
            print("未發現續期按鈕，可能本月已完成續期或尚未到期。")
            browser.close()
            return

        print("步驟 3: 點擊 Extend contract 藍色按鈕...")
        extend_btn.click()

        # 步驟 4: 選擇免費方案並點擊 Extend
        print("步驟 4: 確認續期方案...")
        page.wait_for_selector('button:has-text("Extend")')
        page.click('button:has-text("Extend")')

        # 步驟 5: 處理 PIN 碼
        print("步驟 5: 等待 PIN 碼輸入框...")
        page.wait_for_selector('input[name="pin"]')
        
        pin = get_gmail_pin()
        if pin:
            print(f"獲取到 PIN 碼: {pin}，正在提交...")
            page.fill('input[name="pin"]', pin)
            page.click('button:has-text("Continue")')
            print("續期流程執行完畢！")
        else:
            print("錯誤：無法獲取 PIN 碼。")

        # 截圖留存（可在 GitHub Artifacts 查看）
        page.screenshot(path="result.png")
        browser.close()

if __name__ == "__main__":
    run()
