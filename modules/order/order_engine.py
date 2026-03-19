from pathlib import Path
from datetime import datetime
from modules.storage.db_doc_store import load_doc, save_doc


DATA_FILE = Path.home() / "AIF/data/order/orders.json"
DOC_KEY = "order_orders_v1"


# =====================================================
# 默认数据
# =====================================================

def default_data():
    return {
        "orders": [],
        "next_id": 1
    }


# =====================================================
# 读写
# =====================================================

def load():
    return load_doc(DOC_KEY, default_data(), legacy_file=DATA_FILE)


def save(d):
    save_doc(DOC_KEY, d)


# =====================================================
# 创建订单
# =====================================================

def create_order(d, parts):

    try:
        customer = parts[1]
        product = parts[2]
        qty = float(parts[3])
    except:
        return "❌ 格式: 新订单 客户 产品 数量"

    oid = d["next_id"]

    order = {
        "id": oid,
        "customer": customer,
        "product": product,
        "qty": qty,
        "status": "待生产",
        "time": datetime.now().isoformat(timespec="seconds")
    }

    d["orders"].append(order)
    d["next_id"] += 1

    save(d)

    return f"🧾 订单 #{oid} 已创建 ({customer} {product} {qty})"


# =====================================================
# 修改状态
# =====================================================

def update_status(d, parts):

    try:
        oid = int(parts[1])
        status = parts[2]
    except:
        return "❌ 格式: 订单状态 ID 状态"

    for o in d["orders"]:
        if o["id"] == oid:
            o["status"] = status
            save(d)
            return f"🔄 订单 #{oid} 状态 → {status}"

    return "❌ 未找到订单"


# =====================================================
# 订单列表
# =====================================================

def list_orders(d):

    if not d["orders"]:
        return "📭 无订单"

    lines = ["🧾 订单列表"]

    for o in d["orders"]:
        lines.append(
            f"#{o['id']} {o['customer']} {o['product']} {o['qty']} [{o['status']}]"
        )

    return "\n".join(lines)


# =====================================================
# 客户订单
# =====================================================

def customer_orders(d, parts):

    try:
        name = parts[1]
    except:
        return "❌ 格式: 客户订单 客户名"

    result = [o for o in d["orders"] if o["customer"] == name]

    if not result:
        return "📭 无记录"

    lines = [f"📦 {name} 的订单"]

    for o in result:
        lines.append(
            f"#{o['id']} {o['product']} {o['qty']} [{o['status']}]"
        )

    return "\n".join(lines)


# =====================================================
# TG入口
# =====================================================

def handle_order(text):

    d = load()

    parts = text.split()

    if not parts:
        return None

    cmd = parts[0]

    if cmd == "新订单":
        return create_order(d, parts)

    if cmd == "订单状态":
        return update_status(d, parts)

    if text in ("订单", "订单列表"):
        return list_orders(d)

    if cmd == "客户订单":
        return customer_orders(d, parts)

    return None
