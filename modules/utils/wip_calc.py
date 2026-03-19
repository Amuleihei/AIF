from web.data_store import get_flow_data, get_kilns_data


def compute_wip_trays() -> tuple[int, dict]:
    """
    WIP definition (trays) across stages before product packing:
    - process_flow pools: saw_tray_pool, dip_tray_pool, selected_tray_pool, kiln_done_tray_pool
    - kiln trays currently inside kilns (A-D)
    Returns (total_trays, breakdown_dict).

    默认 total_trays 不包含“出窑待二拣”，因为通常会单独展示该字段。
    """
    flow = get_flow_data()
    kiln = get_kilns_data()

    def _int(v) -> int:
        try:
            return int(v)
        except Exception:
            return 0

    saw = _int(flow.get("saw_tray_pool", 0))
    dip = _int(flow.get("dip_tray_pool", 0))
    selected = _int(flow.get("selected_tray_pool", 0))
    kiln_done = _int(flow.get("kiln_done_tray_pool", 0))

    kiln_in = 0
    if isinstance(kiln, dict):
        for kid in ("A", "B", "C", "D"):
            k = kiln.get(kid) or {}
            trays = k.get("trays") or []
            if isinstance(trays, list):
                kiln_in += len(trays)

    breakdown = {
        "上锯待药浸": saw,
        "药浸待分拣": dip,
        "分拣待入窑": selected,
        "窑内": kiln_in,
        "出窑待二拣": kiln_done,
    }
    # NOTE: "出窑待二拣" 往往会在报表里单独展示（避免和“在制”口径混淆），
    # 所以默认不计入 total；需要包含时可显式传参 include_kiln_done=True。
    total = saw + dip + selected + kiln_in
    return total, breakdown


def compute_wip_trays_include_kiln_done() -> tuple[int, dict]:
    total, breakdown = compute_wip_trays()
    try:
        total += int(breakdown.get("出窑待二拣", 0) or 0)
    except Exception:
        pass
    return total, breakdown


def compute_wip_units() -> dict:
    """
    Some stages use different tray/pallet standards (容量不同). Even though both are called “托”,
    they should not be summed blindly.

    Returns:
      {
        'wip_saw_tray': int,        # 锯解托口径（上锯待药浸 + 药浸待分拣）
        'wip_kiln_tray': int,       # 入窑托口径（分拣待入窑 + 窑内）
        'pending_2nd_sort': int,    # 入窑托口径（出窑待二拣）
        'breakdown': dict,
      }
    """
    total, breakdown = compute_wip_trays()
    saw_tray = int(breakdown.get("上锯待药浸", 0) or 0) + int(breakdown.get("药浸待分拣", 0) or 0)
    kiln_tray = int(breakdown.get("分拣待入窑", 0) or 0) + int(breakdown.get("窑内", 0) or 0)
    pending = int(breakdown.get("出窑待二拣", 0) or 0)
    return {
        "wip_saw_tray": saw_tray,
        "wip_kiln_tray": kiln_tray,
        "pending_2nd_sort": pending,
        "breakdown": breakdown,
    }
