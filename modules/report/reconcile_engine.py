from datetime import datetime

from web.data_store import get_flow_data, get_log_stock_total, get_product_stats
from web.services.daily_report_service import build_daily_report


def _today_second_sort_summary(flow: dict) -> dict:
    recs = flow.get("second_sort_records", []) if isinstance(flow.get("second_sort_records"), list) else []
    today = datetime.now().date()
    trays = 0
    ok_m3 = 0.0
    ab_m3 = 0.0
    bc_m3 = 0.0
    for r in recs:
        if not isinstance(r, dict):
            continue
        text = str(r.get("time", "") or "")
        if not text:
            continue
        try:
            d = datetime.fromisoformat(text).date()
        except Exception:
            continue
        if d != today:
            continue
        trays += int(r.get("trays", 0) or 0)
        ok_m3 += float(r.get("ok_m3", 0) or 0.0)
        ab_m3 += float(r.get("ab_m3", 0) or 0.0)
        bc_m3 += float(r.get("bc_m3", 0) or 0.0)
    return {"trays": trays, "ok_m3": ok_m3, "ab_m3": ab_m3, "bc_m3": bc_m3}


def reconcile_report() -> str:
    flow = get_flow_data()
    raw_mt = float(get_log_stock_total())
    product_count, product_m3 = get_product_stats()
    ss_today = _today_second_sort_summary(flow)

    try:
        from modules.utils.wip_calc import compute_wip_units

        wip = compute_wip_units()
        breakdown = wip.get("breakdown", {}) if isinstance(wip.get("breakdown"), dict) else {}
    except Exception:
        wip = {"wip_saw_tray": 0, "wip_kiln_tray": 0, "pending_2nd_sort": 0}
        breakdown = {}

    day_text = datetime.now().strftime("%Y-%m-%d")
    day_report = build_daily_report(day_text, lang="zh")
    day_summary = day_report.get("summary", {}) if isinstance(day_report.get("summary"), dict) else {}

    lines = [f"🧾 对账 {day_text}", "", "📌 现状（唯一数据库）"]
    lines.append(f"原料: {raw_mt:.4f} MT")
    lines.append(f"在制小计: 锯解托{int(wip.get('wip_saw_tray', 0) or 0)} | 入窑托{int(wip.get('wip_kiln_tray', 0) or 0)}")
    if breakdown:
        lines.append(
            "细分: "
            f"上锯待药浸{int(breakdown.get('上锯待药浸', 0) or 0)} / "
            f"药浸待分拣{int(breakdown.get('药浸待分拣', 0) or 0)} / "
            f"分拣待入窑{int(breakdown.get('分拣待入窑', 0) or 0)} / "
            f"出窑待二拣{int(breakdown.get('出窑待二拣', 0) or 0)}"
        )
    lines.append(f"成品库存: {product_count}件 | {product_m3:.2f} m³")
    lines.append("")
    lines.append("📒 今日台账")
    lines.append(f"入窑: {int(day_summary.get('kiln_load_trays', 0) or 0)} 托")
    lines.append(f"出窑: {int(day_summary.get('kiln_unload_trays', 0) or 0)} 托")
    lines.append(f"二选: {int(day_summary.get('secondary_trays', 0) or 0)} 托")
    lines.append("")
    lines.append("📒 今日二选")
    lines.append(f"二拣入库: {ss_today['trays']}托 | {ss_today['ok_m3']:.2f} m³ (AB {ss_today['ab_m3']:.2f} / BC {ss_today['bc_m3']:.2f})")
    return "\n".join(lines)


def handle_reconcile(text: str):
    if text in ("对账", "核对", "对齐检查", "对账单"):
        return reconcile_report()
    return None
