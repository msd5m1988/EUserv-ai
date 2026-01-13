import os
import time
import re
import imaplib
import email
from playwright.sync_api import sync_playwright
# 修改這裏：使用正確的導入方式
from playwright_stealth import stealth

# --- 從 GitHub Secrets 獲取變量 ---
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
                # 匹配郵件中的 PIN
                pin_match = re.search(r'PIN\s*:\s*(\d+)', content)
                if pin_match: return pin_match.group(1)
        return None
    except Exception as e:
        print(f"提取 PIN 碼錯誤: {e}")
        return None

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={'width': 1280, 'height': 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        # 修正後的隱身插件調用方式
        stealth(page)

        try:
            # 1. 登錄頁面
            print("步驟 1: 正在訪問登錄頁面...")
            page.goto("https://support.euserv.com", wait_until="domcontentloaded", timeout=60000)
            page.fill('input[name="email"]', EUSERV_EMAIL)
            page.fill('input[name="password"]', EUSERV_PASSWORD)
            
            login_btn = 'input[value="Login"], button:has-text("Login")'
            page.wait_for_selector(login_btn)
            page.click(login_btn)
            page.wait_for_load_state("networkidle", timeout=60000)

            # 檢查是否有驗證碼圖片
            if page.query_selector('img[src*="captcha"]'):
                print("❌ 遇到圖形驗證碼，GitHub Actions 無法處理。")
                page.screenshot(path="captcha_blocked.png")
                return

            # 2. 進入 vServer 菜單
            print("步驟 2: 尋找 vServer 菜單...")
            vserver_selector = 'a:has-text("vServer"), #menu-vserver'
            page.wait_for_selector(vserver_selector, timeout=30000)
            page.click(vserver_selector)

            # 3. 檢查續期按鈕
            print("步驟 3: 檢查續期按鈕...")
            extend_btn = 'input[value="Extend contract"], .btn-extend'
            if not page.query_selector(extend_btn):
                print("本月可能已續期或按鈕尚未出現。")
                page.screenshot(path="no_button.png")
                return
            page.click(extend_btn)

            # 4. 點擊 Extend
            page.wait_for_selector('button:has-text("Extend")', timeout=30000)
            page.click('button:has-text("Extend")')

            # 5. PIN 碼處理
            page.wait_for_selector('input[name="pin"]', timeout=30000)
            pin = get_gmail_pin()
            if pin:
                page.fill('input[name="pin"]', pin)
                page.click('button:has-text("Continue")') # 點擊 Continue 按鈕
                print("✅ 續期成功提交！")
            else:
                print("❌ 未能獲取 PIN。")

        except Exception as e:
            print(f"💥 發生異常: {str(e)}")
        finally:
            # 確保無論如何都保存一張截圖，解決 Artifacts 找不到文件的報錯
            page.screenshot(path="final_result.png")
            print("已保存最後截圖。")
            browser.close()

if __name__ == "__main__":
    run()
