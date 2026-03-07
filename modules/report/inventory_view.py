import json
from pathlib import Path


DATA = Path.home() / "AIF/data"
INV_FILE = DATA / "inventory/inventory.json"


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.load(open(path))
    except Exception:
        return {}


def build_inventory_overview(title: str = "📦 库存概况") -> str:
    inv = _load_json(INV_FILE)

    raw_dict = inv.get("raw", {}) if isinstance(inv.get("raw"), dict) else {}
    raw_mt = 0.0
    for v in raw_dict.values():
        try:
            raw_mt += float(v or 0)
        except Exception:
            pass

    # WIP：按“托池+窑内”计算，但此处按用户要求仅展示关键环节
    try:
        from modules.utils.wip_calc import compute_wip_units
        wip = compute_wip_units()
        breakdown = wip.get("breakdown", {}) if isinstance(wip.get("breakdown"), dict) else {}
    except Exception:
        wip = {"wip_saw_tray": 0, "pending_2nd_sort": 0, "breakdown": {}}
        breakdown = {}

    def _int(v) -> int:
        try:
            return int(v)
        except Exception:
            return 0

    saw_total = _int(wip.get("wip_saw_tray", 0))
    saw_to_dip = _int(breakdown.get("上锯待药浸", 0))
    dip_to_select = _int(breakdown.get("药浸待分拣", 0))
    select_to_kiln = _int(breakdown.get("分拣待入窑", 0))
    pending_2nd = _int(wip.get("pending_2nd_sort", 0))

    prod = inv.get("product", {}) if isinstance(inv.get("product"), dict) else {}
    prod_count = 0
    prod_m3 = 0.0
    for item in prod.values():
        if not isinstance(item, dict):
            continue
        if item.get("status") != "库存":
            continue
        prod_count += 1
        try:
            prod_m3 += float(item.get("volume", 0) or 0)
        except Exception:
            pass

    lines = [
        title,
        f"原木库存：{raw_mt:.4f} MT",
        "在制详情：",
        f"已锯解：{saw_total} 托（锯解托）",
        f"待药浸：{saw_to_dip} 托（锯解托）",
        f"待分拣：{dip_to_select} 托（锯解托）",
        f"待入窑：{select_to_kiln} 托（入窑托）",
        f"待二分：{pending_2nd} 托（入窑托）",
        "",
        f"成品件数：{prod_count} 件（{prod_m3:.2f} m³）",
    ]
    return "\n".join(lines)
