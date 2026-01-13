import os
import time
import re
import imaplib
import email
# 1. 導入 stealth
from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_sync

# --- 配置區 ---
EUSERV_EMAIL = os.getenv("EUSERV_EMAIL")
EUSERV_PASSWORD = os.getenv("EUSERV_PASSWORD")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")

def get_gmail_pin():
    # ... (保持原本的 get_gmail_pin 代碼不變，為了節省篇幅這裡省略)
    print("正在從 Gmail 獲取 PIN...")
    time.sleep(35)
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
        # 啟動瀏覽器
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        # 2. 應用隱身模式，抹除機器人特徵
        stealth_sync(page)

        try:
            print("步驟 1: 正在訪問登錄頁面 (隱身模式)...")
            page.goto("https://support.euserv.com", wait_until="domcontentloaded", timeout=60000)
            
            page.fill('input[name="email"]', EUSERV_EMAIL)
            page.fill('input[name="password"]', EUSERV_PASSWORD)
            
            login_btn = 'input[value="Login"], button:has-text("Login")'
            page.wait_for_selector(login_btn)
            print("找到登錄按鈕，正在提交...")
            
            # 點擊登錄，等待頁面加載完成
            page.click(login_btn)
            page.wait_for_load_state("networkidle", timeout=60000)

            # --- 關鍵修改：檢查是否遇到驗證碼 ---
            print("正在檢查登錄結果...")
            # 檢查頁面上是否有驗證碼圖片特徵
            if page.query_selector('img[src*="captcha"]'):
                 print("❌ 嚴重錯誤：EuServ 彈出了圖形驗證碼！")
                 print("原因：GitHub Actions 的 IP 被網站風控，隱身模式未能繞過。")
                 print("此類驗證碼無法通過免費腳本自動解決。")
                 page.screenshot(path="captcha_blocked.png")
                 return
            
            # 檢查是否還在登錄頁（密碼錯誤）
            if page.query_selector('input[name="password"]'):
                print("❌ 登錄失敗，可能是帳號密碼錯誤。")
                page.screenshot(path="login_failed.png")
                return

            # 如果沒有驗證碼，也沒有留在登錄頁，嘗試尋找後台元素
            print("步驟 2: 尋找 vServer 菜單...")
            vserver_selector = 'a:has-text("vServer"), #menu-vserver'
            # 這裡稍微縮短超時時間，因為如果成功登錄應該很快能看到
            page.wait_for_selector(vserver_selector, state="attached", timeout=30000)
            page.click(vserver_selector)

            # ... (後續續期步驟與之前相同)
            print("步驟 3: 檢查續期按鈕...")
            page.wait_for_selector('input[value="Extend contract"], .btn-extend', timeout=30000)
            page.click('input[value="Extend contract"]')
            
            print("步驟 4: 點擊確認續期...")
            page.wait_for_selector('button:has-text("Extend")', timeout=30000)
            page.click('button:has-text("Extend")')

            print("步驟 5: 等待 PIN 碼輸入框...")
            page.wait_for_selector('input[name="pin"]', timeout=30000)
            pin = get_gmail_pin()
            if pin:
                page.fill('input[name="pin"]', pin)
                page.click('button:has-text("Continue")')
                print("✅ 續期流程完成！請檢查最後截圖確認結果。")
            else:
                print("❌ 未能獲取 PIN 碼。")

        except Exception as e:
            # 捕獲超時等其他錯誤
            print(f"💥 執行過程中發生錯誤: {str(e)}")
            # 如果是因為找不到元素超時，通常也是因為被攔截在了某個頁面
            if "Timeout" in str(e):
                 print("提示：超時通常意味著被驗證碼攔截或網路不通。")
        finally:
            # 不管成功失敗，最後都截圖一張看看停在了哪裡
            page.screenshot(path="final_result.png")
            browser.close()

if __name__ == "__main__":
    run()
