from datetime import datetime

from web.services.daily_report_service import build_daily_report


def today() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _ordered_pairs(data: dict, labels: dict, order: list[str]) -> list[tuple[str, object]]:
    if not isinstance(data, dict):
        return []
    if not isinstance(labels, dict):
        labels = {}
    if not isinstance(order, list):
        order = list(data.keys())
    out = []
    for key in order:
        if key not in data:
            continue
        out.append((str(labels.get(key, key)), data.get(key)))
    return out


def _section_lines(title: str, rows: list[tuple[str, object]]) -> str:
    if not rows:
        return title + "\n暂无记录"
    body = "\n".join(f"{name}: {value}" for name, value in rows)
    return f"{title}\n{body}"


def daily_report():
    report = build_daily_report(today(), lang="zh")
    labels = report.get("display_labels", {}) if isinstance(report.get("display_labels"), dict) else {}
    order = report.get("display_order", {}) if isinstance(report.get("display_order"), dict) else {}

    summary_rows = _ordered_pairs(
        report.get("summary", {}),
        labels.get("summary", {}),
        order.get("summary", []),
    )
    snapshot_rows = _ordered_pairs(
        report.get("inventory_snapshot", {}),
        labels.get("inventory_snapshot", {}),
        order.get("inventory_snapshot", []),
    )

    breakdown = report.get("breakdown", {}) if isinstance(report.get("breakdown"), dict) else {}
    breakdown_counts = {
        key: len(value) if isinstance(value, list) else 0
        for key, value in breakdown.items()
    }
    breakdown_rows = _ordered_pairs(
        breakdown_counts,
        labels.get("breakdown", {}),
        order.get("breakdown", []),
    )

    summary = report.get("summary", {}) if isinstance(report.get("summary"), dict) else {}
    snapshot = report.get("inventory_snapshot", {}) if isinstance(report.get("inventory_snapshot"), dict) else {}

    log_mt = float(snapshot.get("log_stock_mt", 0.0) or 0.0)
    saw_tray = int(snapshot.get("saw_stock_tray", 0) or 0)
    dip_tray = int(snapshot.get("dip_stock_tray", 0) or 0)
    pending_kiln_tray = int(snapshot.get("sorting_stock_tray", 0) or 0)
    kiln_done_tray = int(snapshot.get("kiln_done_stock_tray", 0) or 0)
    kiln_load_tray = int(summary.get("kiln_load_trays", 0) or 0)
    kiln_unload_tray = int(summary.get("kiln_unload_trays", 0) or 0)

    byproduct_total_ks = float(summary.get("byproduct_bark_ks", 0.0) or 0.0)

    parts = [
        f"📊 {report.get('date', today())} 生产日报",
        f"范围: {report.get('range', {}).get('start', '')} ~ {report.get('range', {}).get('end', '')}",
        _section_lines("📈 汇总", summary_rows),
        "📦 库存明细\n"
        f"原木库存：{log_mt:.4f} MT\n"
        "在制详情：\n"
        f"已锯解：{saw_tray} 托（锯解托）\n"
        f"待分拣：{dip_tray} 托（锯解托）\n"
        f"待入窑：{pending_kiln_tray} 托（入窑托）\n"
        f"待二拣：{kiln_done_tray} 托（入窑托）",
        "📒 今日台账\n"
        f"入窑: {kiln_load_tray} 托\n"
        f"出窑: {kiln_unload_tray} 托",
        _section_lines("📦 库存快照", snapshot_rows),
        _section_lines("🧾 明细计数", breakdown_rows),
        f"💰 财务汇总\n总额: {byproduct_total_ks:.2f} KS",
        f"ℹ️ {report.get('meta', {}).get('note', '')}",
    ]
    return "\n\n".join(parts)


def handle_daily_report(text):
    if text in ("日报", "今日报告", "生产日报", "工厂日报"):
        return daily_report()
    return None
