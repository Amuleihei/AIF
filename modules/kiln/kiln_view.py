from web.utils import get_stock_data


def build_kiln_overview(
    title: str = "🔥 窑总览",
    include_footer: bool = True,
    footer_style: str = "two_lines",
) -> str:
    """
    统一口径：直接复用 Web 端的 kiln_status 计算结果，避免 TG 与 Web 状态分叉。
    """
    try:
        stock = get_stock_data("zh")
    except Exception:
        return f"{title}\n无数据"

    kiln_status = stock.get("kiln_status", {}) if isinstance(stock, dict) else {}
    if not isinstance(kiln_status, dict):
        kiln_status = {}

    lines: list[str] = [title]
    running = 0
    trays_total = 0

    for kid in ("A", "B", "C", "D"):
        info = kiln_status.get(kid, {}) if isinstance(kiln_status.get(kid), dict) else {}
        status_raw = str(info.get("status", "empty") or "empty")
        status_display = str(info.get("status_display", "空") or "空")
        progress = str(info.get("progress", "") or "")

        if status_raw in ("loading", "drying", "unloading"):
            running += 1

        total_trays = int(info.get("total_trays", 0) or 0)
        trays_total += max(0, total_trays)

        line = f"{kid}窑：{status_display}"
        if progress:
            line += f" - {progress}"
        lines.append(line)

    if include_footer:
        lines.append("")
        if footer_style == "inline":
            lines.append(f"运行: {running}窑 | 总托: {trays_total}托")
        else:
            lines.append(f"运行: {running}窑")
            lines.append(f"总托: {trays_total}托")

    bark_stock_m3 = float(stock.get("bark_stock_m3", 0.0) or 0.0)
    dust_bag_pool = int(stock.get("dust_bag_stock", 0) or 0)
    lines.append("")
    lines.append("💰 副产品")
    lines.append(f"树皮库存: {bark_stock_m3:.2f} 立方")
    lines.append(f"木渣库存: {dust_bag_pool} 袋")

    return "\n".join(lines)
