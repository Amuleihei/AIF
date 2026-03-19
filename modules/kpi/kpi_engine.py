from pathlib import Path
from modules.storage.db_doc_store import load_doc


DATA = Path.home() / "AIF/data"


FINANCE_FILE = DATA / "finance/finance.json"
EQUIP_FILE = DATA / "equipment/equipment.json"
HR_FILE = DATA / "hr/hr.json"


# =====================================================
# 工具
# =====================================================

def load(p):
    path = Path(p)
    mapping = {
        str(DATA / "finance/finance.json"): "finance_finance_v1",
        str(DATA / "equipment/equipment.json"): "equipment_v1",
        str(DATA / "hr/hr.json"): "hr_main_v2",
        str(DATA / "inventory/inventory.json"): "inventory_data_v1",
    }
    key = mapping.get(str(path))
    if not key:
        return {}
    return load_doc(key, {}, legacy_file=path)


# =====================================================
# KPI 计算
# =====================================================

def production_kpi():

    # 使用真实数据源（inventory + 台账），避免 production.json 未维护导致 KPI 为 0
    try:
        from modules.inventory.inventory_engine import load as load_inventory
        inv = load_inventory()
    except Exception:
        inv = {}
    raw_total = sum(inv.get("raw", {}).values()) if isinstance(inv.get("raw"), dict) else 0.0

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

    return f"🏭 生产: 原木{raw_total:.1f}MT 成品{prod_count}件({prod_volume:.1f}m³)"


def finance_kpi():

    d = load(FINANCE_FILE)

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

    return f"💰 财务: 收入{income:.0f}KS 支出{expense:.0f}KS"


def equipment_kpi():

    d = load(EQUIP_FILE).get("machines", {})

    total = len(d)
    running = sum(1 for m in d.values() if m["status"] == "运行")

    if total == 0:
        return "⚙️ 设备: 无"

    rate = running / total * 100

    return f"⚙️ 设备运行率: {rate:.0f}%"


def hr_kpi():

    d = load(HR_FILE).get("employees", {})

    total = len(d)
    on = sum(1 for e in d.values() if e["status"] == "在岗")

    if total == 0:
        return "👥 人员: 无"

    rate = on / total * 100

    return f"👥 在岗率: {rate:.0f}%"


# =====================================================
# 综合监控
# =====================================================

def dashboard():

    parts = [
        "📊 AIF 运营监控",
        production_kpi(),
        finance_kpi(),
        equipment_kpi(),
        hr_kpi(),
    ]

    return "\n".join(parts)


# =====================================================
# TG入口
# =====================================================

def handle_kpi(text):

    if text in ("KPI", "运营", "监控", "状态总览"):
        return dashboard()

    return None
