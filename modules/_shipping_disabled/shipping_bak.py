from pathlib import Path
from datetime import datetime
from modules.storage.db_doc_store import load_doc, save_doc


PACK_FILE = Path.home() / "AIF/data/packing/pallets.json"
SHIP_FILE = Path.home() / "AIF/data/shipping/shipping.json"
PACK_KEY = "packing_pallets_v1"
SHIP_KEY = "shipping_records_v1"


# =====================================================
# 默认数据
# =====================================================

def default_ship():
    return {"records": []}


# =====================================================
# 工具
# =====================================================

def load_json(p, default):
    key = PACK_KEY if Path(p) == PACK_FILE else SHIP_KEY
    return load_doc(key, default(), legacy_file=p)


def save_json(p, d):
    key = PACK_KEY if Path(p) == PACK_FILE else SHIP_KEY
    save_doc(key, d)


# =====================================================
# 发货
# =====================================================

def ship_pallet(parts):

    try:
        pid = int(parts[1])
        customer = parts[2]
    except:
        return "❌ 格式: 发货 托ID 客户"

    pack = load_json(PACK_FILE, lambda: {"pallets": []})
    ship = load_json(SHIP_FILE, default_ship)

    for p in pack["pallets"]:
        if p["id"] == pid:

            pack["pallets"].remove(p)

            rec = {
                "pallet": pid,
                "customer": customer,
                "volume": p["volume"],
                "time": datetime.now().isoformat(timespec="seconds")
            }

            ship["records"].append(rec)

            save_json(PACK_FILE, pack)
            save_json(SHIP_FILE, ship)

            return (
                f"🚚 托#{pid} 已发货 → {customer}\n"
                f"材积: {p['volume']:.2f} m³"
            )

    return "❌ 未找到托盘"


# =====================================================
# 发货记录
# =====================================================

def ship_list():

    ship = load_json(SHIP_FILE, default_ship)

    if not ship["records"]:
        return "📭 无发货记录"

    lines = ["🚚 发货记录"]

    for r in ship["records"]:
        lines.append(
            f"托#{r['pallet']} → {r['customer']} {r['volume']:.2f}m³"
        )

    return "\n".join(lines)


# =====================================================
# TG入口
# =====================================================

def handle_shipping(text):

    parts = text.split()

    if not parts:
        return None

    if parts[0] == "发货":
        return ship_pallet(parts)

    if text in ("发货记录", "出库记录"):
        return ship_list()

    return None
