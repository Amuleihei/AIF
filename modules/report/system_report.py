import json
from pathlib import Path
from datetime import datetime


DATA = Path.home() / "AIF/data"

FINANCE_FILE = DATA / "finance/finance.json"
INVENTORY_FILE = DATA / "inventory/inventory.json"
KILN_FILE = DATA / "kiln/kilns.json"
LEDGER_FILE = DATA / "ledger/production_ledger.json"


# =====================================================
# 工具
# =====================================================

def load_json(p):
    if not p.exists():
        return {}
    try:
        return json.load(open(p))
    except:
        return {}


def today():
    return datetime.now().strftime("%Y-%m-%d")


# =====================================================
# 今日生产数据
# =====================================================

def production_today():

    d = load_json(LEDGER_FILE)

    r = d.get(today())

    if not r:
        return None

    return (
        "⚙️ 今日生产\n"
        f"上锯: {r['saw_mt']} MT ({r['saw_m3']} m³)\n"
        f"入窑: {r['kiln_in_m3']} m³\n"
        f"出窑: {r['kiln_out_m3']} m³\n"
        f"成品: {r['product_m3']} m³"
    )


# =====================================================
# 库存摘要
# =====================================================

def inventory_summary():

    d = load_json(INVENTORY_FILE)

    raw = sum(d.get("raw", {}).values())
    wip = sum(d.get("wip", {}).values())

    prod = d.get("product", {})
    prod_count = len(prod)
    prod_vol = sum(
        item.get("volume", 0)
        for item in prod.values()
        if isinstance(item, dict)
        and item.get("status") == "库存"
    )

    return raw, wip, prod_count, prod_vol


# =====================================================
# 窑摘要
# =====================================================

def kiln_summary():

    d = load_json(KILN_FILE)

    running = 0
    trays = 0

    for v in d.values():
        if v.get("status") in ("drying", "loading"):
            running += 1
            trays += len(v.get("trays", []))

    return running, trays


# =====================================================
# 财务摘要
# =====================================================

def finance_summary():

    d = load_json(FINANCE_FILE)

    income = d.get("income")
    expense = d.get("expense")
    if income is None or expense is None:
        income = 0.0
        expense = 0.0
        for rec in d.get("records", []):
            if rec.get("type") == "income":
                income += float(rec.get("amount", 0))
            elif rec.get("type") == "expense":
                expense += float(rec.get("amount", 0))

    return income, expense, income - expense


# =====================================================
# 预警系统
# =====================================================

def alerts(raw, prod_vol, running):

    msg = []

    if raw == 0:
        msg.append("⚠️ 原料库存为 0")

    if prod_vol == 0:
        msg.append("⚠️ 无成品库存")

    if running == 0:
        msg.append("⚠️ 无窑运行")

    return "\n".join(msg) if msg else None


# =====================================================
# 工厂日报（增强版）
# =====================================================

def factory_daily():

    raw, wip, pc, pv = inventory_summary()
    running, trays = kiln_summary()
    income, expense, balance = finance_summary()

    parts = [
        f"📊 AIF 工厂日报 {today()}",
        "",
        "📦 库存",
        f"原料: {raw:.2f}",
        f"在制: {wip:.2f}",
        f"成品: {pv:.2f} m³ ({pc}件)",
        "",
        "🔥 窑",
        f"运行: {running} 个",
        f"托数: {trays}",
        "",
        "💰 财务",
        f"收入: {income:.2f} KS",
        f"支出: {expense:.2f} KS",
        f"净额: {balance:.2f} KS",
    ]

    # ⭐ 今日生产
    p = production_today()
    if p:
        parts.insert(2, p)
    else:
        parts.insert(2, "⚠️ 今日无生产记录")

    # ⭐ 预警
    a = alerts(raw, pv, running)
    if a:
        parts.append("\n🚨 预警\n" + a)

    return "\n".join(parts)


# =====================================================
# TG入口
# =====================================================

def handle_system_report(text):

    if text in ("日报", "今日日报", "工厂日报"):
        return factory_daily()

    return None
