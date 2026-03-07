from modules.production.capacity_engine import load as load_capacity
from modules.inventory.inventory_engine import load as load_inventory
from modules.forecast.order_engine import load as load_orders


def inventory_stock(inv):
    if not inv:
        return 0.0

    raw = sum(inv.get("raw", {}).values()) if isinstance(inv.get("raw"), dict) else 0.0
    wip = sum(inv.get("wip", {}).values()) if isinstance(inv.get("wip"), dict) else 0.0

    product = 0.0
    for item in inv.get("product", {}).values():
        if isinstance(item, dict) and item.get("status") == "库存":
            product += float(item.get("volume", 0))

    return raw + wip + product


def analyze():

    cap = load_capacity()
    inv = load_inventory()
    orders = load_orders()

    daily = cap["daily_capacity"]
    stock = inventory_stock(inv)
    order_count = len(orders["orders"])

    return daily, stock, order_count


def decision():

    daily, stock, order_count = analyze()

    if order_count > 0 and stock < daily * 3:
        return "⚠️ 建议提高生产"

    if stock > daily * 10:
        return "📦 库存偏高，建议控制生产"

    return "✅ 生产平衡"


# TG入口
def handle_brain(text):

    if text == "工厂建议":
        return "🧠 " + decision()

    return None
