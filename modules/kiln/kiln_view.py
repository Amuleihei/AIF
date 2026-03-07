import json
from pathlib import Path
from datetime import datetime, timedelta


DATA_FILE = Path.home() / "AIF/data/kiln/kilns.json"


def _load() -> dict:
    if not DATA_FILE.exists():
        return {}
    try:
        return json.load(open(DATA_FILE))
    except Exception:
        return {}


def _format_one_kiln(kid: str, k: dict, now: datetime, day: str, inferred_kiln_out_tray: int | None) -> tuple[str, int, bool]:
    trays = k.get("trays", []) or []
    remain_trays = len(trays) if isinstance(trays, list) else 0
    status = k.get("status")

    # default
    running = False
    total_trays_for_sum = remain_trays

    if status == "drying" and k.get("start"):
        running = True
        try:
            start = datetime.fromisoformat(k["start"])
        except Exception:
            start = now
        remain = start + timedelta(hours=120) - now
        h = max(0, int(remain.total_seconds() / 3600))
        if h > 0:
            return f"{kid}窑：烘干中 剩{h}h ({remain_trays}托)", total_trays_for_sum, running
        return f"{kid}窑：烘干完成待出 ({remain_trays}托)", total_trays_for_sum, False

    if status == "loading":
        running = True
        return f"{kid}窑：入窑中 ({remain_trays}托)", total_trays_for_sum, running

    if status == "ready_unload":
        return f"{kid}窑：烘干完成待出 ({remain_trays}托)", total_trays_for_sum, False

    if status == "unloading":
        running = True
        total = k.get("unloading_total_trays")
        if total is not None:
            try:
                total_i = int(total)
            except Exception:
                total_i = None
            if total_i is not None and total_i >= remain_trays:
                return f"{kid}窑：出窑中 ({total_i}托, 剩{remain_trays}托)", total_trays_for_sum, running
        return f"{kid}窑：出窑中 ({remain_trays}托)", total_trays_for_sum, running

    if status == "completed":
        # 现场口径：完成即视为空窑（不显示完成时间，避免刷屏）
        return f"{kid}窑：空 (0托)", 0, False

    if not trays:
        return f"{kid}窑：空 (0托)", 0, False

    # fallback
    return f"{kid}窑：{status or '空'} ({remain_trays}托)", total_trays_for_sum, False


def build_kiln_overview(
    title: str = "🔥 窑总览",
    include_footer: bool = True,
    footer_style: str = "two_lines",
) -> str:
    """
    Shared kiln view used by:
    - 菜单里的“窑概况/窑总览”
    - 日报里的“窑状态/窑总览”
    """
    d = _load()
    if not d:
        return f"{title}\n无数据"

    now = datetime.now()
    day = now.strftime("%Y-%m-%d")

    inferred_kiln_out_tray: int | None = None
    try:
        from modules.ledger.production_ledger_engine import load as ledger_load
        ledger = ledger_load()
        if isinstance(ledger, dict) and isinstance(ledger.get(day), dict):
            inferred_kiln_out_tray = int(ledger[day].get("kiln_out_tray", 0) or 0) or None
    except Exception:
        inferred_kiln_out_tray = None

    lines: list[str] = [title]
    running = 0
    trays_total = 0

    for kid in ["A", "B", "C", "D"]:
        k = d.get(kid, {}) or {}
        line, trays_for_sum, is_running = _format_one_kiln(kid, k, now, day, inferred_kiln_out_tray)
        lines.append(line)
        trays_total += int(trays_for_sum or 0)
        if is_running and trays_for_sum > 0:
            running += 1

    if include_footer:
        if footer_style == "inline":
            lines.append("")
            lines.append(f"运行: {running}窑 | 总托: {trays_total}托")
        else:
            lines.append("")
            lines.append(f"运行: {running}窑")
            lines.append(f"总托: {trays_total}托")

    return "\n".join(lines)
