import json
from pathlib import Path
from datetime import datetime


DATA = Path.home() / "AIF/data"
INV_FILE = DATA / "inventory/inventory.json"
FLOW_FILE = DATA / "process_flow/flow.json"
LEDGER_FILE = DATA / "ledger/production_ledger.json"


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.load(open(path))
    except Exception:
        return {}


def _today() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _product_stock_summary(inv: dict) -> dict:
    prod = inv.get("product", {}) if isinstance(inv.get("product"), dict) else {}
    count = 0
    vol = 0.0
    ab = 0.0
    bc = 0.0
    for item in prod.values():
        if not isinstance(item, dict):
            continue
        if item.get("status") != "库存":
            continue
        count += 1
        v = float(item.get("volume", 0) or 0)
        vol += v
        g = (item.get("grade") or "").strip().upper()
        if g == "AB":
            ab += v
        elif g == "BC":
            bc += v
    return {"count": count, "vol": vol, "ab": ab, "bc": bc}


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
        t = r.get("time")
        if not t:
            continue
        try:
            d = datetime.fromisoformat(t).date()
        except Exception:
            continue
        if d != today:
            continue
        trays += int(r.get("trays", 0) or 0)
        ok_m3 += float(r.get("ok_m3", 0) or 0)
        ab_m3 += float(r.get("ab_m3", 0) or 0)
        bc_m3 += float(r.get("bc_m3", 0) or 0)
    return {"trays": trays, "ok_m3": ok_m3, "ab_m3": ab_m3, "bc_m3": bc_m3}


def reconcile_report() -> str:
    day = _today()
    inv = _load_json(INV_FILE)
    flow = _load_json(FLOW_FILE)
    ledger = _load_json(LEDGER_FILE)
    r = ledger.get(day, {}) if isinstance(ledger, dict) else {}

    raw = inv.get("raw", {}) if isinstance(inv.get("raw"), dict) else {}
    raw_mt = sum(float(v or 0) for v in raw.values())

    try:
        from modules.utils.wip_calc import compute_wip_units
        wip = compute_wip_units()
        wip_break = wip.get("breakdown", {}) or {}
    except Exception:
        wip = {"wip_saw_tray": 0, "wip_kiln_tray": 0, "pending_2nd_sort": 0, "breakdown": {}}
        wip_break = {}

    prod_sum = _product_stock_summary(inv)
    ss_today = _today_second_sort_summary(flow)

    # today ledger key fields (may be missing)
    saw_mt = float(r.get("saw_mt", 0) or 0)
    saw_tray = int(r.get("saw_tray", 0) or 0)
    dip_tank = int(r.get("dip_tank", 0) or 0)
    dip_tray = int(r.get("dip_tray", 0) or 0)
    kiln_in = int(r.get("kiln_tray", 0) or 0)
    kiln_out = int(r.get("kiln_out_tray", 0) or 0)
    pack_pkg = int(r.get("pack_pkg", 0) or 0)
    pack_m3 = float(r.get("pack_m3", 0) or 0)
    ab_m3 = float(r.get("ab_m3", 0) or 0)
    bc_m3 = float(r.get("bc_m3", 0) or 0)

    lines = [f"🧾 对账 {day}"]
    lines.append("")
    lines.append("📌 现状（状态/存量）")
    lines.append(f"原料: {raw_mt:.4f} MT")
    if isinstance(wip_break, dict) and wip_break:
        lines.append(
            "在制(锯解托): "
            f"上锯待药浸{int(wip_break.get('上锯待药浸',0) or 0)} + "
            f"药浸待分拣{int(wip_break.get('药浸待分拣',0) or 0)}"
        )
        lines.append(
            "在制(入窑托): "
            f"分拣待入窑{int(wip_break.get('分拣待入窑',0) or 0)} + "
            f"窑内{int(wip_break.get('窑内',0) or 0)}"
        )
        lines.append(f"待二拣(入窑托): {int(wip_break.get('出窑待二拣', 0) or 0)}托")
    lines.append(f"在制小计: 锯解托{int(wip.get('wip_saw_tray',0) or 0)} | 入窑托{int(wip.get('wip_kiln_tray',0) or 0)}")
    lines.append(f"成品库存: {prod_sum['count']}件 | {prod_sum['vol']:.2f} m³ (AB {prod_sum['ab']:.2f} / BC {prod_sum['bc']:.2f})")
    loose = 0
    try:
        loose = int(flow.get("selected_loose_pcs", 0) or 0)
    except Exception:
        loose = 0
    if loose > 0:
        lines.append(f"分拣未满托余料: {loose}根")

    lines.append("")
    lines.append("📒 今日台账（流水/累计）")
    lines.append(f"上锯投入: {saw_mt:.4f} MT")
    lines.append(f"上锯产出: {saw_tray}托")
    if dip_tank or dip_tray:
        lines.append(f"药浸: {dip_tank}罐 {dip_tray}托")
    lines.append(f"入窑: {kiln_in}托")
    lines.append(f"出窑: {kiln_out}托")
    lines.append(f"成品: {pack_pkg}件 | {pack_m3:.2f} m³ (AB {ab_m3:.2f} / BC {bc_m3:.2f})")

    lines.append("")
    lines.append("🔎 今日二拣记录（可用于核对台账）")
    lines.append(f"二拣入库: {ss_today['trays']}托 | {ss_today['ok_m3']:.2f} m³ (AB {ss_today['ab_m3']:.2f} / BC {ss_today['bc_m3']:.2f})")

    # checks + suggestions
    warnings: list[str] = []
    if pack_pkg and ss_today["trays"] and pack_pkg != ss_today["trays"]:
        warnings.append(f"成品件数(台账){pack_pkg} != 今日二拣托数{ss_today['trays']}（可能还有成品入库pi，或台账被强制修正过）")
    if (pack_m3 > 0) and (ss_today["ok_m3"] > 0) and abs(pack_m3 - ss_today["ok_m3"]) > 1e-6:
        warnings.append(f"成品m³(台账){pack_m3:.2f} != 今日二拣m³{ss_today['ok_m3']:.2f}（可能还有pi入库，或更正导致差异）")

    if warnings:
        lines.append("")
        lines.append("⚠️ 差异提示")
        lines.extend([f"- {w}" for w in warnings])

    lines.append("")
    lines.append("✅ 建议")
    lines.append("1) 先把“状态”补齐（强制托池/窑状态/成品库存），再看日报。")
    lines.append("2) 如果仅报表数字不对，用：强制 今日台账 ... 做最后修正。")

    return "\n".join(lines)


def handle_reconcile(text: str):
    if text in ("对账", "核对", "对齐检查", "对账单"):
        return reconcile_report()
    return None
