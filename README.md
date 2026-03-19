# AIF - 三语版 / Trilingual / သုံးဘာသာ

## 中文

### 项目简介
AIF 是一个面向工厂场景的智能管理系统，支持 Telegram Bot 指令交互与 Web 后台协同管理。  
系统覆盖 HR、薪资、库存、设备、财务、报表等模块，并支持中/英/缅语输入。

### 主要能力
- 多模块业务处理（HR、薪资、库存、财务、产能、报表等）
- Telegram Bot 快速录入与查询
- Web 管理后台（Flask）
- 多语言与简写命令转换
- 支持按小时与加班场景扩展薪资计算

### 快速启动
1. 安装依赖
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```
2. 配置环境变量（不要提交真实 token）
```bash
cp .env.example .env
```
3. 启动 Bot
```bash
python run_bot.py
```
4. 启动 Web
```bash
python web_app.py
```

### 文档
- 三语命令参考：`COMMANDS_3LANG.md`
- Web 部署文档：`WEB_DEPLOYMENT_README.md`

### 打赏通道
如果这个项目对你有帮助，欢迎支持开发：
- USDT (TRC20): `YOUR_USDT_TRC20_ADDRESS`
- BTC: `YOUR_BTC_ADDRESS`
- ETH (ERC20): `YOUR_ETH_ADDRESS`
- Buy Me a Coffee: `https://buymeacoffee.com/YOUR_ID`
- Ko-fi: `https://ko-fi.com/YOUR_ID`

> 请将以上地址替换为你自己的收款地址后再公开。

---

## English

### Overview
AIF is a factory-oriented intelligent management system with both Telegram Bot workflows and a Flask-based web console.  
It includes HR, payroll, inventory, equipment, finance, and reporting modules, with multilingual input support.

### Highlights
- Multi-module operations (HR, payroll, inventory, finance, production, reports)
- Fast command workflow via Telegram Bot
- Web admin console (Flask)
- Multilingual + shortcut command normalization
- Ready for hourly and overtime-linked payroll extensions

### Quick Start
1. Install dependencies
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```
2. Configure environment variables (never commit real secrets)
```bash
cp .env.example .env
```
3. Start bot
```bash
python run_bot.py
```
4. Start web app
```bash
python web_app.py
```

### Docs
- Trilingual command reference: `COMMANDS_3LANG.md`
- Web deployment guide: `WEB_DEPLOYMENT_README.md`

### Donation
If this project helps you, you can support development here:
- USDT (TRC20): `YOUR_USDT_TRC20_ADDRESS`
- BTC: `YOUR_BTC_ADDRESS`
- ETH (ERC20): `YOUR_ETH_ADDRESS`
- Buy Me a Coffee: `https://buymeacoffee.com/YOUR_ID`
- Ko-fi: `https://ko-fi.com/YOUR_ID`

> Replace all placeholder addresses/links with your own before publishing.

---

## မြန်မာ

### စနစ်အကျဉ်းချုပ်
AIF သည် စက်ရုံလုပ်ငန်းအတွက် တည်ဆောက်ထားသော စမတ်စီမံခန့်ခွဲမှုစနစ်ဖြစ်ပြီး Telegram Bot နှင့် Web Console ကို ပေါင်းစည်းအသုံးပြုနိုင်ပါသည်။  
HR၊ လစာ၊ ကုန်လှောင်/လက်ကျန်၊ စက်ပစ္စည်း၊ ဘဏ္ဍာရေး၊ အစီရင်ခံစာ မော်ဂျူးများ ပါဝင်ပြီး ဘာသာစကားစုံ အသုံးပြုနိုင်ပါသည်။

### အဓိကလုပ်ဆောင်ချက်များ
- မော်ဂျူးစုံ စီမံခန့်ခွဲမှု (HR/Payroll/Inventory/Finance/Report)
- Telegram Bot မှ မြန်ဆန်သော command workflow
- Flask အခြေပြု Web Admin
- ဘာသာစကားစုံ + shortcut command ပြောင်းလဲခြင်း
- နာရီလိုက်နှင့် OT (overtime) ဆက်စပ် လစာတွက်ချက်မှုချဲ့ထွင်နိုင်ခြင်း

### အမြန်စတင်ခြင်း
1. Dependencies ထည့်သွင်းရန်
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```
2. Environment ဖိုင် ပြင်ဆင်ရန် (secret မတင်ပါနှင့်)
```bash
cp .env.example .env
```
3. Bot စတင်ရန်
```bash
python run_bot.py
```
4. Web စတင်ရန်
```bash
python web_app.py
```

### စာရွက်စာတမ်းများ
- Command သုံးဘာသာ: `COMMANDS_3LANG.md`
- Web Deployment: `WEB_DEPLOYMENT_README.md`

### လှူဒါန်းရန်
ဒီ project က အကျိုးရှိခဲ့ရင် development ကိုပံ့ပိုးနိုင်ပါတယ်။
- USDT (TRC20): `YOUR_USDT_TRC20_ADDRESS`
- BTC: `YOUR_BTC_ADDRESS`
- ETH (ERC20): `YOUR_ETH_ADDRESS`
- Buy Me a Coffee: `https://buymeacoffee.com/YOUR_ID`
- Ko-fi: `https://ko-fi.com/YOUR_ID`

> Public မတင်ခင် placeholder တွေကို သင့် address/link များဖြင့် အစားထိုးပါ။

