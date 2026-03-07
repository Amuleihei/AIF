from modules.production.capacity_engine import load as load_capacity
from modules.inventory.inventory_engine import load as load_inventory
from modules.finance.finance_engine import load as load_finance
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


def summary():

    cap = load_capacity()
    inv = load_inventory()
    fin = load_finance()
    orders = load_orders()

    daily = cap["daily_capacity"]
    stock = inventory_stock(inv)
    cash = fin.get("accounts", {}).get("cash", 0.0)
    order_count = len(orders["orders"])

    return daily, stock, cash, order_count


def ceo_advice():

    daily, stock, cash, order_count = summary()

    if order_count > 0 and stock < daily * 2:
        return "⚠️ 库存偏低，应加快生产"

    if stock > daily * 15:
        return "📦 库存过高，建议降低生产"

    if cash < 0:
        return "💸 现金流紧张，建议控制支出"

    return "✅ 运营健康"


# TG入口
def handle_ceo(text):

    if text == "公司状况":

        daily, stock, cash, orders = summary()

        return (
            "👑 CEO报告\n"
            f"日产能: {daily} m³\n"
            f"库存: {stock}\n"
            f"现金: {cash:.2f} KS\n"
            f"订单: {orders}\n\n"
            + ceo_advice()
        )

    return None
