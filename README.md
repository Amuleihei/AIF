# AIF - 木材厂智能管理系统 / Smart Management for Wood Factories / သစ်စက်ရုံ စမတ်စီမံခန့်ခွဲမှုစနစ်

![AIF Logo](static/AIF_logo.png)

中文 | English | မြန်မာ

## 中文

### 定位
AIF 是专为东南亚橡胶木木材加工厂打造的一体化智能管理系统。  
从原木入库到最终发货，全流程数字化管理，支持 Telegram Bot + Web 后台协同操作。

### 适用场景
- 东南亚木材加工厂
- 原木采购、入库、锯解、分拣、烘干、成品打包、发货物流等完整流程
- 多岗位协作工厂（老板、办公室、仓库、车间、财务、HR）

### 完整流程覆盖
1. 原木入库与库存台账
2. 锯解生产与产能记录
3. 分拣与在制品跟踪
4. 烘干窑进出窑管理
5. 成品库存与打包管理
6. 发货与物流追踪
7. 财务核算与经营报表
8. HR、考勤、薪资（支持按小时与加班挂钩）

### 核心价值
- 一部手机即可管理整个工厂
- 指令化录入，办公室操作更便捷
- 数据实时汇总，减少人工统计与对账压力
- 降低重复岗位投入，节省大量人员成本
- 支持多语言（中文/英文/缅文），适配跨语言团队

### 系统能力
- Telegram Bot 快速录入与查询
- Flask Web 管理后台
- 多模块：HR、薪资、库存、设备、财务、报表、物流
- 多语言与简写命令识别

### 快速启动
1. 安装依赖
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```
2. 配置环境变量（严禁提交真实 token）
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

> 发布前请把占位地址替换为你的真实收款地址。

---

## English

### Positioning
AIF is an all-in-one intelligent management system built for Southeast Asian rubberwood processing factories.  
It digitalizes the full production chain from log intake to final shipment, with Telegram Bot + Web console collaboration.

### Best For
- Southeast Asian timber/wood processing factories
- End-to-end operations: log receiving, sawing, sorting, kiln drying, packing, shipping, logistics
- Multi-role factory teams: owner, office, warehouse, workshop, finance, HR

### Full Workflow Coverage
1. Log receiving and inventory ledger
2. Sawing production and capacity tracking
3. Sorting and WIP tracking
4. Kiln drying in/out control
5. Finished goods inventory and packing
6. Shipment and logistics tracking
7. Financial accounting and management reports
8. HR, attendance, payroll (hourly and overtime-linked)

### Core Value
- Manage the whole factory from one phone
- Faster office operations via command-driven input
- Real-time data aggregation with less manual reconciliation
- Lower staffing overhead and significant labor-cost savings
- Trilingual support (Chinese/English/Burmese) for cross-language teams

### System Features
- Fast input/query through Telegram Bot
- Flask-based web admin
- Multi-module coverage: HR, payroll, inventory, equipment, finance, reports, logistics
- Multilingual + shortcut command normalization

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

### Documents
- Trilingual command reference: `COMMANDS_3LANG.md`
- Web deployment guide: `WEB_DEPLOYMENT_README.md`

### Donation
If this project helps you, you can support development here:
- USDT (TRC20): `YOUR_USDT_TRC20_ADDRESS`
- BTC: `YOUR_BTC_ADDRESS`
- ETH (ERC20): `YOUR_ETH_ADDRESS`
- Buy Me a Coffee: `https://buymeacoffee.com/YOUR_ID`
- Ko-fi: `https://ko-fi.com/YOUR_ID`

---

## မြန်မာ

### စနစ်定位
AIF သည် အရှေ့တောင်အာရှ ရော်ဘာသစ် wood processing စက်ရုံများအတွက် ဖန်တီးထားသော all-in-one စမတ်စီမံခန့်ခွဲမှုစနစ်ဖြစ်သည်။  
Raw log ဝင်ရောက်ချိန်မှ နောက်ဆုံး shipment အထိ လုပ်ငန်းစဉ်အပြည့်ကို Telegram Bot + Web Console ဖြင့် စီမံနိုင်သည်။

### အသုံးချရန်သင့်တော်သောနေရာ
- အရှေ့တောင်အာရှ သစ်/wood processing စက်ရုံများ
- Log receiving, sawing, sorting, kiln drying, packing, shipping, logistics အပြည့်အစုံ
- Owner, office, warehouse, workshop, finance, HR အဖွဲ့ပေါင်းစုံ

### လုပ်ငန်းစဉ်အပြည့် လွှမ်းခြုံမှု
1. Raw log ဝင်ကုန်နှင့် stock ledger
2. Sawing production နှင့် capacity မှတ်တမ်း
3. Sorting နှင့် WIP tracking
4. Kiln drying အဝင်/အထွက် စီမံခန့်ခွဲမှု
5. Finished goods stock နှင့် packing
6. Shipment နှင့် logistics tracking
7. Finance accounting နှင့် management report
8. HR, attendance, payroll (hourly + overtime ချိတ်ဆက်)

### အဓိကတန်ဖိုး
- ဖုန်းတစ်လုံးနဲ့ စက်ရုံတစ်ခုလုံးကို စီမံနိုင်သည်
- Command workflow ကြောင့် office အလုပ်များ ပိုမြန်စေသည်
- Real-time data ကြောင့် manual reconcile အလုပ်လျော့နည်းစေသည်
- လုပ်သားစရိတ်နှင့် staffing cost ကို အတော်လျော့ချပေးနိုင်သည်
- Chinese / English / Burmese သုံးဘာသာကို ထောက်ပံ့သည်

### စနစ်စွမ်းရည်
- Telegram Bot ဖြင့် မြန်ဆန်သော data input/query
- Flask အခြေပြု Web Admin
- HR, payroll, inventory, equipment, finance, report, logistics module များ
- Multilingual + shortcut command ပြောင်းလဲမှု

### အမြန်စတင်ခြင်း
1. Dependencies ထည့်သွင်းရန်
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```
2. Environment ဖိုင် ပြင်ရန် (secret မတင်ပါနှင့်)
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

### စာရွက်စာတမ်း
- Command သုံးဘာသာ: `COMMANDS_3LANG.md`
- Web deployment: `WEB_DEPLOYMENT_README.md`

### လှူဒါန်းရန်
- USDT (TRC20): `YOUR_USDT_TRC20_ADDRESS`
- BTC: `YOUR_BTC_ADDRESS`
- ETH (ERC20): `YOUR_ETH_ADDRESS`
- Buy Me a Coffee: `https://buymeacoffee.com/YOUR_ID`
- Ko-fi: `https://ko-fi.com/YOUR_ID`
