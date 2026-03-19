from pathlib import Path
from modules.storage.db_doc_store import load_doc, save_doc


DATA_FILE = Path.home() / "AIF/data/orders/orders.json"
DOC_KEY = "forecast_orders_v1"


def default_data():
    return {"orders": []}


def load():
    return load_doc(DOC_KEY, default_data(), legacy_file=DATA_FILE)


def save(d):
    save_doc(DOC_KEY, d)


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
