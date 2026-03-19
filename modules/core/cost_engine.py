from pathlib import Path
from modules.storage.db_doc_store import load_doc, save_doc


DATA_FILE = Path.home() / "AIF/data/cost/cost.json"
DOC_KEY = "core_cost_v1"


# =====================================================
# 默认数据
# =====================================================

def default_data():
    return {
        "products": {},   # 产品成本
        "sales": []       # 销售记录
    }


# =====================================================
# 读写
# =====================================================

def load():
    return load_doc(DOC_KEY, default_data(), legacy_file=DATA_FILE)


def save(d):
    save_doc(DOC_KEY, d)


# =====================================================
# 设置产品成本
# =====================================================

def set_cost(d, parts):

    try:
        name = parts[1]
        cost = float(parts[2])
    except:
        return "❌ 格式: 成本 产品 单位成本"

    d["products"][name] = cost
    save(d)

    return f"💸 {name} 成本 = {cost:.2f} KS"


# =====================================================
# 销售记录
# =====================================================

def record_sale(d, parts):

    try:
        product = parts[1]
        qty = float(parts[2])
        price = float(parts[3])
    except:
        return "❌ 格式: 销售 产品 数量 单价"

    if product not in d["products"]:
        return "❌ 未设置成本"

    cost = d["products"][product] * qty
    revenue = price * qty
    profit = revenue - cost

    d["sales"].append({
        "product": product,
        "qty": qty,
        "price": price,
        "revenue": revenue,
        "cost": cost,
        "profit": profit
    })

    save(d)

    return (
        f"🧾 销售记录\n"
        f"收入: {revenue:.2f} KS\n"
        f"成本: {cost:.2f} KS\n"
        f"利润: {profit:.2f} KS"
    )


# =====================================================
# 利润统计
# =====================================================

def profit_report(d):

    if not d["sales"]:
        return "📉 无销售记录"

    revenue = sum(s["revenue"] for s in d["sales"])
    cost = sum(s["cost"] for s in d["sales"])
    profit = revenue - cost

    return (
        "📊 利润统计\n"
        f"收入: {revenue:.2f} KS\n"
        f"成本: {cost:.2f} KS\n"
        f"利润: {profit:.2f} KS"
    )


# =====================================================
# TG入口
# =====================================================

def handle_cost(text):

    d = load()

    parts = text.split()

    if not parts:
        return None

    cmd = parts[0]

    if cmd == "成本":
        return set_cost(d, parts)

    if cmd == "销售":
        return record_sale(d, parts)

    if text in ("利润", "利润统计"):
        return profit_report(d)

    return None
