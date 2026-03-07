import json
from pathlib import Path


DATA_FILE = Path.home() / "AIF/data/orders/orders.json"


def default_data():
    return {"orders": []}


def load():

    if not DATA_FILE.exists():
        data = default_data()
        save(data)
        return data

    try:
        return json.load(open(DATA_FILE))
    except Exception:
        data = default_data()
        save(data)
        return data


def save(d):

    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)

    with open(DATA_FILE, "w") as f:
        json.dump(d, f, indent=2, ensure_ascii=False)


# =====================================================

def handle_orders(text):

    data = load()

    if text.startswith("新增预测订单"):

        name = text.replace("新增预测订单", "").strip()
        data["orders"].append(name)
        save(data)

        return f"📦 已录入预测订单: {name}"

    if text == "预测订单列表":

        if not data["orders"]:
            return "📄 无预测订单"

        return "\n".join(data["orders"])

    return None
