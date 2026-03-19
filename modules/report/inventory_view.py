from web.data_store import get_inventory_data, get_log_stock_total, get_product_stats


def build_inventory_overview(title: str = "📦 库存概况") -> str:
    inv = get_inventory_data()

    raw_mt = float(get_log_stock_total())

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

    prod_count, prod_m3 = get_product_stats()

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
