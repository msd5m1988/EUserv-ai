import os
import time
import re
import imaplib
import email
from playwright.sync_api import sync_playwright
from playwright_stealth import stealth

# --- 從 GitHub Secrets 獲取環境變量 ---
EUSERV_EMAIL = os.getenv("EUSERV_EMAIL")
EUSERV_PASSWORD = os.getenv("EUSERV_PASSWORD")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")

def get_gmail_pin():
    """
    從 Gmail 獲取 EuServ 發送的 PIN 碼
    """
    print("正在等待 35 秒，確保 EuServ 已發送 PIN 碼郵件...")
    time.sleep(35)
    
    try:
        # 連接 Gmail IMAP 服務器
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(EUSERV_EMAIL, GMAIL_APP_PASSWORD)
        mail.select("inbox")
        
        # 搜索來自 EuServ 的安全檢查郵件
        status, messages = mail.search(None, '(FROM "support-no-reply@euserv.com" SUBJECT "Confirmation of a Security Check")')
        
        if status != "OK" or not messages[0]:
            print("未找到 PIN 碼郵件。")
            return None
            
        latest_msg_id = messages[0].split()[-1]
        res, msg_data = mail.fetch(latest_msg_id, "(RFC822)")
        
        for response_part in msg_data:
            if isinstance(response_part, tuple):
                msg = email.message_from_bytes(response_part[1])
                content = str(msg)
                # 匹配郵件內容中的 PIN 碼
                pin_match = re.search(r'PIN\s*:\s*(\d+)', content)
                if pin_match:
                    return pin_match.group(1)
        return None
    except Exception as e:
        print(f"提取 PIN 碼時發生錯誤: {e}")
        return None

def run():
    with sync_playwright() as p:
        # 啟動瀏覽器並設置真實的瀏覽器特徵
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        # 啟用隱身插件，防止被識別為 Playwright 機器人
        stealth(page)

        try:
            # 步驟 1: 登錄 EuServ
            print("步驟 1: 正在訪問 EuServ 登錄頁面...")
            page.goto("https://support.euserv.com", wait_until="domcontentloaded", timeout=60000)
            
            page.fill('input[name="email"]', EUSERV_EMAIL)
            page.fill('input[name="password"]', EUSERV_PASSWORD)
            
            # 兼容 input 或 button 類型的登錄按鈕
            login_btn = 'input[value="Login"], button:has-text("Login")'
            page.wait_for_selector(login_btn)
            print("找到登錄按鈕，正在點擊...")
            page.click(login_btn)
            
            # 等待登錄後的頁面跳轉
            page.wait_for_load_state("networkidle", timeout=60000)

            # 檢查是否遇到圖形驗證碼
            if page.query_selector('img[src*="captcha"]'):
                 print("❌ 警告：EuServ 彈出了圖形驗證碼！GitHub Actions 無法自動處理。")
                 page.screenshot(path="captcha_blocked.png")
                 return
            
            # 步驟 2: 點擊 vServer 控制面板
            print("步驟 2: 正在進入 vServer 菜單...")
            vserver_selector = 'a:has-text("vServer"), #menu-vserver'
            page.wait_for_selector(vserver_selector, timeout=60000)
            page.click(vserver_selector)

            # 步驟 3: 尋找續期按鈕
            print("步驟 3: 正在檢查是否有續期按鈕 (Extend contract)...")
            extend_btn = 'input[value="Extend contract"], .btn-extend'
            if not page.query_selector(extend_btn):
                print("未發現續期按鈕。可能本月已完成續期，或還未到期。")
                page.screenshot(path="no_extend_button.png")
                return
                
            page.click(extend_btn)

            # 步驟 4: 選擇免費方案並點擊 Extend
            print("步驟 4: 正在確認續期方案...")
            page.wait_for_selector('button:has-text("Extend")', timeout=30000)
            page.click('button:has-text("Extend")')

            # 步驟 5: 處理 PIN 碼輸入
            print("步驟 5: 等待 PIN 碼輸入框彈出...")
            page.wait_for_selector('input[name="pin"]', timeout=30000)
            
            pin = get_gmail_pin()
            if pin:
                print(f"成功獲取 PIN 碼: {pin}，正在提交續期...")
                page.fill('input[name="pin"]', pin)
                page.click('button:has-text("Continue")') # 點擊藍色的 Continue 按鈕
                print("✅ 續期操作已提交！")
            else:
                print("❌ 錯誤：無法從郵箱獲取 PIN 碼。")

        except Exception as e:
            print(f"💥 腳本運行異常: {str(e)}")
        finally:
            # 最後保存一張截圖用於確認結果
            page.screenshot(path="final_result.png")
            print("已保存最後運行結果截圖 final_result.png")
            browser.close()

if __name__ == "__main__":
    run()
