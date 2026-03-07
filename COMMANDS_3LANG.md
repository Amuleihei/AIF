# AIF Telegram Commands (CN / EN / MM)

This document lists the currently enabled Telegram commands in 3 languages and groups them by permission.

Permission levels (from `modules/auth/auth_engine.py` + `tg_bot/bot.py`):
- Level 1: 操作员 / 财务 (Operator / Finance)
- Level 2: 管理员 / 老板 (Admin / Boss)

Notes:
- “CN command” is always supported.
- EN/MM input is supported for the main commands via the input translator (`modules/i18n/translate_engine.py`). If you find any EN/MM phrase that doesn’t route correctly, tell me the exact text you typed and I’ll add it.
- Multi-line paste: many entry commands support pasting multiple lines (one command per line).

## Level 1 (Operator / Finance)

### Reports / Queries

1) Daily report
- CN: `日报`
- EN: `daily report` / `report` / `daily`
- MM: `နေ့စဉ်အစီရင်ခံစာ`
- Example:
  - CN: `日报`
  - EN: `daily report`
  - MM: `နေ့စဉ်အစီရင်ခံစာ`

2) Reconcile (state vs today ledger)
- CN: `对账`
- EN: `reconcile` / `reconcile report`
- MM: (use CN for now)
- Example:
  - CN: `对账`
  - EN: `reconcile`

3) Stock (full)
- CN: `库存`
- EN: `stock` / `inventory`
- MM: `သိုလှောင်`
- Example:
  - CN: `库存`
  - EN: `inventory`
  - MM: `သိုလှောင်`

4) Stock overview (summary)
- CN: `库存概况`
- EN: `stock overview` / `inventory overview`
- MM: (use CN for now)
- Example:
  - CN: `库存概况`
  - EN: `stock overview`

5) Product stock (detailed)
- CN: `成品库存`
- EN: `product stock` / `finished goods` / `finished stock` / `fg stock`
- MM: (use CN for now)
- Example:
  - CN: `成品库存`
  - EN: `product stock`

6) Production overview
- CN: `生产概况`
- EN: `production overview`
- MM: (use CN for now)
- Example:
  - CN: `生产概况`
  - EN: `production overview`

7) Finance overview (today + balance)
- CN: `财务概况`
- EN: `finance overview`
- MM: (use CN for now)
- Example:
  - CN: `财务概况`
  - EN: `finance overview`

8) Finance details (records)
- CN: `财务明细 [今日|YYYY-MM-DD|条数] [条数]`
- EN: `finance details`
- MM: (use CN for now)
- Example:
  - CN: `财务明细`
  - CN: `财务明细 今日 50`
  - CN: `财务明细 2026-03-04 100`
  - EN: `finance details`

8) Factory status / dashboard
- CN: `工厂状态` / `驾驶舱`
- EN: `factory status` / `dashboard`
- MM: (use CN for now)
- Example:
  - CN: `工厂状态`
  - EN: `factory status`

9) Kiln overview / status
- CN: `窑总览` / `窑状态`
- EN: `kiln overview` / `kiln status`
- MM: `မီးဖိုအခြေအနေ`
- Example:
  - CN: `窑总览`
  - EN: `kiln status`
  - MM: `မီးဖိုအခြေအနေ`

10) Process stock (WIP pools)
- CN: `工序库存` / `流程库存`
- EN: `process stock`
- MM: `အဆင့်သိုလှောင်`
- Example:
  - CN: `工序库存`
  - EN: `process stock`

11) Sorting tray IDs (waiting kiln)
- CN: `分拣编号` / `待入窑编号` / `分拣列表`
- CN (detail export): `待入窑导出 [A|B|C|D] [每行托数] [上限]`
- EN: `export kiln load [A|B|C|D] [per_line] [limit]`
- MM: `မီးဖိုထည့် စာရင်း ထုတ် [A|B|C|D] [တစ်ကြောင်းလျှင်] [အများဆုံး]`
- Example:
  - CN: `分拣编号`
  - CN: `待入窑导出 A 20 200`
  - EN: `export kiln load A 20 200`
  - MM: `မီးဖိုထည့် စာရင်း ထုတ် A 20 200`

12) KPI dashboard
- CN: `KPI` / `运营` / `监控` / `状态总览`
- EN: `kpi`
- MM: (use CN for now)
- Example:
  - CN: `KPI`

### Production Entry (Main Chain)

1) Log stock in
- CN: `原木入库 <MT>`
- EN: `log in <MT>`
- MM: `သစ်ဝင် <MT>`
- Example:
  - CN: `原木入库 5.25`
  - EN: `log in 5.25`
  - MM: `သစ်ဝင် 5.25`

2) Saw (input MT, output saw-trays, optional bark/dust and saw#)
- CN: `上锯 <MT> <托> [树皮托] [木渣袋] [锯号N]`
- EN: `saw <MT> <tray> ...` (numbers only; translator routes to CN)
- MM: `လွှ ...`
- Example:
  - CN: `上锯 10.7522 12 0 0 锯号3`
  - EN: `saw 10.7522 12 0 0 saw#3`

3) Dip (tanks, trays, optional chemical bags)
- CN: `药浸 <罐次> <托> [药剂袋]`
- EN: `dip <tanks> <trays> [bags]`
- MM: `ဆေးစိမ် ...`
- Example:
  - CN: `药浸 4 12 0`
  - EN: `dip 4 12 0`

4) Sort (create trays waiting kiln)
- CN: `分拣 <编号> <规格> <根数> [托数]`
- EN: `select ...` / `sorting ...` (translator routes to CN; use CN if unsure)
- MM: `ရွေး ...`
- Example:
  - CN: `分拣 0305-001 68x21 654 1`

5) Kiln load / fire / unload
- CN:
  - `A窑入窑 <84x21> <10托>` (by spec)
  - `A窑入窑 <批次编号> <84x21x10>`（旧格式：规格x数量）
  - `A窑入窑 <批次编号> <95x71x10+95x46x5>`（混合规格：用 `+`；数量相加=托数）
  - `A窑入窑 <分拣编号列表>` (by IDs)
  - `A窑点火`
  - `A窑出窑`
  - `A窑出窑 <N托>`（兼容旧格式：分批出窑）
  - `A窑出窑 <95x71+95x46> <N托>`（兼容旧格式：按规格分批出窑；中间如有根数等数字会被忽略）
  - `A窑出窑 <托编号1> <托编号2> ...`（按托编号出窑，如 `A001 A002`）
  - `A窑出窑详情` / `A窑出窑明细`
- EN:
  - `kiln A load 84x21 10 tray`
  - `kiln A load batch001 95x71x10+95x46x5`
  - `kiln A fire`
  - `kiln A unload`
  - `kiln A unload 10 tray`
  - `kiln A unload 95x71+95x46 1 tray`
  - `kiln A unload A001 A002`
  - `kiln A unload details`
- MM: (supported when text contains kiln letter + action words)
- Example:
  - CN: `B窑入窑 84x21 10托`
  - CN: `A窑入窑 批次0305 95x71x10+95x46x5`
  - EN: `kiln B load 84x21 10 tray`
  - EN: `kiln B fire`
  - EN: `kiln A unload`
  - CN: `A窑出窑 14托`
  - CN: `A窑出窑 95x84 297 8托`
  - CN: `A窑出窑 A001 A002 A003`
  - CN: `A窑出窑详情`

> 批量录入：TG 输入框支持“一行一条”，可一次粘贴多条 `A窑入窑 ...`。

6) Second sort (ss)
- CN:
  - Daily reference (no change): `二次拣选` / `ss`（输出“待二拣”入窑规格汇总）
  - Backfill (deduct only): `二次拣选 <X托>` / `ss <X托>`（仅扣减待二拣托池，并记录规格参考）
- EN: `second sort ...` (translator routes to CN if numbers are present)
- MM: `ဒုတိယရွေး ...`
- Example:
  - CN: `ss`
  - CN: `ss 10托`

### Product / Shipping

1) Product in (supports multi-line paste)
- CN: `成品入库 <编号> <规格> <等级AB/BC> <根数> <体积> [托数]`
- EN: (use CN for now)
- MM: (use CN for now)
- Example:
  - CN: `成品入库 0305-001 68x21 AB 654 0.887 1`

2) Undo last product in (fix mistaken entry)
- CN:
  - Undo last: `成品入库 -`
  - Undo by code (must be the last one): `成品入库 - 0305-001`
- EN/MM: (use CN for now)
- Example:
  - CN: `成品入库 - 0305-001`

3) Ship products
- CN: `成品发货 <编号/区间/逗号分隔>`
- EN: (use CN for now)
- MM: (use CN for now)
- Example:
  - CN: `成品发货 0304-051、0304-052`

4) Query product
- CN: `成品查询 <编号> [等级AB/BC]` / `成品查看 <编号> [等级AB/BC]`（当同一编号存在 AB/BC 两条时需带等级）
- Example:
  - CN: `成品查询 0304-051`
  - CN: `成品查询 0213-005 AB`

### Finance Entry

1) Income / Expense / Transfer
- CN:
  - `收入 <金额> <备注>`
  - `支出 <金额> <备注>`
  - `转账 <金额> <源账户> <目标账户>` (default accounts: `cash`, `bank`)
- EN:
  - `income <amount> <note>`
  - `expense <amount> <note>`
  - `transfer <amount> <src> <dst>`
  - `balance`
  - `today finance`
- MM: (use CN for now)
- Example:
  - CN: `收入 50000 现金收款`
  - EN: `income 50000 cash`
  - CN: `支出 12000 买耗材`
  - EN: `expense 12000 supplies`
  - CN: `转账 100000 cash bank`
  - EN: `transfer 100000 cash bank`

## Level 2 (Admin / Boss)

### Force (Admin-only)

Entry point:
- CN: `强制 ...`
- EN: (use CN for now)
- MM: (use CN for now)

Force stage pools:
- `强制 上锯待药浸 <N>托`
- `强制 药浸待分拣 <N>托`
- `强制 分拣待入窑 <N>托`
- `强制 出窑待二拣 <N>托` (or shorthand: `强制 待二拣 <N>托`)
- `强制 分拣未满托 <N>根`
- `强制 分拣入库 <编号> <规格> <根数> <托数>` (force add “待入窑” trays)
- `强制 原木库存 <MT>` (absolute set)

Force kilns:
- `强制 B窑烘干中 共计55托 已运行78小时`
- `强制 A窑出窑 15托 剩余30托`
- `强制 C窑空`

Rebuild ledger (from traceable sources):
- `强制 重算台账` (today)
- `强制 重算台账 2026-03-04`
- `强制 累计台账更正` (all days)

### System / Restricted Operations (Admin-only)

- `清空 ...`
- `开始挖矿`
- `停止挖矿`
- `系统重启`
- `全厂停产`
- `全厂加班`

## CN-only Commands (Enabled, but not fully translated for input)

These commands are enabled in code but currently best entered in Chinese:
- `订单` / `订单列表`
- `采购` / `采购列表`
- `生产预测` / `订单预测` / `预测订单列表` / `新增预测订单 ...`
- `设备` / `设备状态`
- `排产` / `计划` / `生成计划` / `生产计划`
- `发货 ...` / `在途` / `物流状态`
- `事件日志` / `系统日志` / `流程日志`
