import json
from pathlib import Path


# =====================================================
# 数据路径（统一 AIF/data）
# =====================================================

DATA = Path.home() / "AIF/data"

FINANCE_FILE = DATA / "finance/finance.json"
INVENTORY_FILE = DATA / "inventory/inventory.json"
KILN_FILE = DATA / "kiln/kilns.json"


# =====================================================
# 工具
# =====================================================

def load_json(p):

    if not p.exists():
        return {}

    try:
        return json.load(open(p))
    except Exception:
        return {}


def finance_totals(d: dict):
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
    return float(income), float(expense)


# =====================================================
# 💰 财务概况
# =====================================================

def finance_report():
    return "💰 财务概况\n⛔ 财务功能已暂时关闭（系统维护中）"


# =====================================================
# 🏭 生产概况
# =====================================================

def production_report():

    # 生产概况口径改为“真实数据源”，避免 production.json 未维护导致长期为 0
    inv = load_json(INVENTORY_FILE)
    raw_total = sum(inv.get("raw", {}).values()) if isinstance(inv.get("raw"), dict) else 0.0

    # “累计产出”按当前成品库存（件数 + m³）展示，便于与库存对齐
    prod_count = 0
    prod_volume = 0.0
    prod = inv.get("product", {}) if isinstance(inv.get("product"), dict) else {}
    for item in prod.values():
        if not isinstance(item, dict):
            continue
        if item.get("status") != "库存":
            continue
        prod_count += 1
        try:
            prod_volume += float(item.get("volume", 0) or 0)
        except Exception:
            pass

    return (
        "🏭 生产概况\n"
        f"原木库存: {raw_total:.4f} MT\n"
        f"累计产出: {prod_count}件 ({prod_volume:.2f} m³)"
    )


# =====================================================
# 📦 库存概况（ERP三层）
# =====================================================

def inventory_report():
    try:
        from modules.report.inventory_view import build_inventory_overview
        return build_inventory_overview("📦 库存概况")
    except Exception:
        return "📦 库存概况\n❌ 生成失败"


# =====================================================
# 🔥 窑状态
# =====================================================

def kiln_report():

    d = load_json(KILN_FILE)

    if not d:
        return "🔥 无窑数据"

    lines = ["🔥 窑状态"]

    running = 0

    for k, v in d.items():

        trays = v.get("trays", [])

        if not trays:
            lines.append(f"{k}窑: 空")
            continue

        status = v.get("status", "loading")

        if status == "drying":
            running += 1
            lines.append(f"{k}窑: 烘干中 ({len(trays)}托)")
        else:
            lines.append(f"{k}窑: 入窑中 ({len(trays)}托)")

    lines.append(f"\n运行中: {running} 个")

    return "\n".join(lines)


# =====================================================
# 📊 工厂总览（管理层）
# =====================================================

def factory_report():

    parts = [
        "📊 AIF 工厂总览",
        finance_report(),
        inventory_report(),
        production_report(),
        kiln_report(),
    ]

    return "\n\n".join(parts)


# =====================================================
# 🧠 ⭐ 工厂驾驶舱（老板用）
# =====================================================

def dashboard():

    inv = load_json(INVENTORY_FILE)

    raw_total = sum(inv.get("raw", {}).values()) if isinstance(inv.get("raw"), dict) else 0
    try:
        from modules.utils.wip_calc import compute_wip_units
        w = compute_wip_units()
        wip_saw = int(w.get("wip_saw_tray", 0) or 0)
        wip_kiln = int(w.get("wip_kiln_tray", 0) or 0)
    except Exception:
        wip_saw = 0
        wip_kiln = 0

    prod_count = 0
    prod_volume = 0

    for item in inv.get("product", {}).values():

        if not isinstance(item, dict):
            continue

        if item.get("status") != "库存":
            continue

        prod_count += 1
        prod_volume += item.get("volume", 0)

    finance = load_json(FINANCE_FILE)

    income, expense = finance_totals(finance)
    balance = income - expense

    kiln = load_json(KILN_FILE)

    running_kilns = 0

    for v in kiln.values():
        if v.get("status") == "drying":
            running_kilns += 1

    lines = [
        "🏭 工厂状态",
        "",
        "💰 财务",
        f"净额: {balance:.2f} KS",
        "",
        "📦 库存",
        f"原料: {raw_total}",
        f"在制(锯解托): {wip_saw}托",
        f"在制(入窑托): {wip_kiln}托",
        f"成品件数: {prod_count}",
        f"成品体积: {prod_volume:.2f} m³",
        "",
        "🔥 烘房",
        f"运行中: {running_kilns} 个",
    ]

    return "\n".join(lines)


# =====================================================
# TG入口
# =====================================================

def handle_report(text):

    # -------- 老板驾驶舱 --------

    if text in ("工厂状态", "今日汇总", "驾驶舱"):
        return dashboard()

    # -------- 管理报表 --------

    if text in ("总览", "工厂总览", "系统总览"):
        return factory_report()

    if text in ("财务概况", "财务报告"):
        return finance_report()

    if text in ("生产概况", "生产报告"):
        return production_report()

    if text in ("库存概况", "库存报告"):
        return inventory_report()

    if text in ("窑概况", "窑报告"):
        return kiln_report()

    return None
