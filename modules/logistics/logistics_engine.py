import json
from pathlib import Path

DATA_FILE = Path.home() / "AIF/data/logistics/logistics.json"


# =====================================================
# 默认数据
# =====================================================

def default_data():
    return {"shipments": []}


# =====================================================
# 读写
# =====================================================

def load():
    if not DATA_FILE.exists():
        d = default_data()
        save(d)
        return d

    try:
        return json.load(open(DATA_FILE))
    except:
        d = default_data()
        save(d)
        return d


def save(d):
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    json.dump(d, open(DATA_FILE, "w"), indent=2, ensure_ascii=False)


# =====================================================
# TG入口
# =====================================================

def handle_logistics(text):

    data = load()

    # =================================================
    # ERP 发货格式
    # 发货 订单ID 客户 产品 数量
    # 示例：发货 A001 张三 板材 10
    # =================================================

    if text.startswith("发货"):

        parts = text.split()

        if len(parts) != 5:
            return "❌ 格式：发货 订单ID 客户 产品 数量"

        _, oid, client, product, qty = parts

        try:
            qty = float(qty)
        except:
            return "❌ 数量错误"

        record = {
            "id": oid,
            "client": client,
            "product": product,
            "qty": qty,
            "status": "在途"
        }

        data["shipments"].append(record)
        save(data)

        return (
            f"🚚 发货成功\n"
            f"订单: {oid}\n"
            f"客户: {client}\n"
            f"产品: {product} {qty}"
        )

    # =================================================
    # 物流状态
    # =================================================

    if text in ("物流状态", "在途"):

        if not data["shipments"]:
            return "📦 无在途货物"

        lines = ["📦 在途货物"]

        for s in data["shipments"]:
            lines.append(
                f"{s['id']} | {s['client']} | {s['product']} {s['qty']}"
            )

        return "\n".join(lines)

    return None