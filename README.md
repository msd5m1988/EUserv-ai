# EUserv-ai
Euserv自动续期
准备工作
为了实现多账户支持和安全性，我们需要将敏感信息存放在 GitHub Secrets 中，而不是代码里。

你需要准备一个 JSON 格式的配置字符串，存入 GitHub Secrets。

1. 设置 GitHub Secrets
在你的 GitHub 仓库中，点击 Settings -> Secrets and variables -> Actions -> New repository secret。

Secret Name: USER_CONFIG

Secret Value: (复制下面的内容，修改为你自己的新密码和应用专用密码)

JSON

[
  {
    "euserv_email": "pinfkle@gmail.com",
    "euserv_password": "YOUR_NEW_EUSERV_PASSWORD",
    "gmail_user": "pinfkle@gmail.com",
    "gmail_app_password": "YOUR_GMAIL_APP_PASSWORD"
  }
]
(如果是多账户，就在 [] 里复制 {...} 加逗号即可)


代码部分
你需要创建两个文件：main.py (主程序) 和 .github/workflows/renew.yml (定时任务)。

1. Python 脚本 (main.py)
这个脚本包含了随机等待、登录、邮件获取验证码、续期的所有逻辑。

2. GitHub Workflow (.github/workflows/renew.yml)
这个文件定义了每个月 12 日和 15 日触发，并安装环境。

重要说明和后续步骤
关于随机时间： GitHub Actions 的 cron 只能定点触发（比如 UTC 4:00）。我在 Python 代码开头加了 time.sleep(random.randint(60, 3600))，这意味着脚本启动后会随机“挂机” 1分钟到60分钟再开始操作，从而实现了你要求的“时间段随机”。

关于 PIN 码提取： 代码中的正则 re.search 是基于通用逻辑写的。由于我看不到邮件的纯文本源码，如果邮件格式复杂，可能提取不到。

建议：第一次手动运行（点击 Actions 里的 Run workflow），观察日志输出。如果提示“提取到 PIN: None”，请查看日志中打印的邮件标题和内容，调整 main.py 里的正则部分。

应用专用密码： 你的 Gmail 必须开启 两步验证 (2FA)，然后在 Google 账户设置里生成一个 App Password (应用专用密码)。不要使用你的 Gmail 登录密码，否则 IMAP 登录会被 Google 拦截。

文件结构： 确保你的 GitHub 仓库结构如下：

Plaintext

YOUR_REPO/
├── .github/
│   └── workflows/
│       └── renew.yml
├── main.py
└── requirements.txt (可选，我直接在yml里install了)
