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
    pass

def run():
    with sync_playwright() as p:
        # 增加偽裝，避免被識別為自動化工具
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        try:
            # 步驟 1: 登錄
            print("步驟 1: 正在登錄 EuServ...")
            page.goto("https://support.euserv.com", wait_until="networkidle")
            
            # 檢查是否進入了頁面
            print(f"當前頁面標題: {page.title()}")

            # 填寫郵箱和密碼
            page.fill('input[name="email"]', EUSERV_EMAIL)
            page.fill('input[name="password"]', EUSERV_PASSWORD)

            # 更換更強大的選擇器來點擊 Login 按鈕
            # 這裡嘗試匹配任何包含 "Login" 文字的按鈕或輸入框
            login_selector = 'input[value="Login"], button:has-text("Login"), .login-button'
            page.wait_for_selector(login_selector, timeout=60000)
            
            print("找到登錄按鈕，正在點擊...")
            page.click(login_selector)

            # 步驟 2: 點擊 vServer
            print("步驟 2: 等待進入控制面板並尋找 vServer 按鈕...")
            # 增加等待時間，因為登錄後跳轉可能較慢
            page.wait_for_selector('a:has-text("vServer")', timeout=60000)
            page.click('a:has-text("vServer")')

            # --- 後續步驟保持不變 ---
            # ... (步驟 3, 4, 5 的代碼) ...
            
            print("流程完成。")

        except Exception as e:
            print(f"發生錯誤: {e}")
            # 發生錯誤時截圖，這對 debug 非常重要
            page.screenshot(path="error_debug.png")
            print("已保存錯誤截圖 error_debug.png，請在 GitHub Artifacts 中查看。")
        finally:
            browser.close()

if __name__ == "__main__":
    run()
