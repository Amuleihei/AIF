from __future__ import annotations

import json
from datetime import datetime, date, timedelta

from web.models import (
    Session,
    TgSetting,
    LogEntry,
    SawRecord,
    DipRecord,
    SortRecord,
    TrayBatch,
    ProductBatch,
    ByproductRecord,
    FlowSecondSortRecord,
)
from web.data_store import get_log_stock_total, get_product_stats, get_flow_data

WEEKLY_REPORTS_KEY = "period_reports_weekly_v1"
MONTHLY_REPORTS_KEY = "period_reports_monthly_v1"


def _to_int(v, default=0) -> int:
    try:
        if v in (None, ""):
            return int(default)
        return int(float(v))
    except Exception:
        return int(default)


def _to_float(v, default=0.0) -> float:
    try:
        if v in (None, ""):
            return float(default)
        return float(v)
    except Exception:
        return float(default)


def _load_json(session, key: str, default):
    row = session.query(TgSetting).filter_by(key=key).first()
    if not row or not str(row.value or "").strip():
        return default
    try:
        return json.loads(str(row.value))
    except Exception:
        return default


def _save_json(session, key: str, value) -> None:
    text = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    row = session.query(TgSetting).filter_by(key=key).first()
    if not row:
        row = TgSetting(key=key, value=text)
        session.add(row)
    else:
        row.value = text


def _between(session, model, start_iso: str, end_iso: str, time_field: str = "created_at"):
    col = getattr(model, time_field)
    return session.query(model).filter(col >= start_iso, col <= end_iso).all()


def _snapshot_now() -> dict:
    flow = get_flow_data()
    product_count, product_m3 = get_product_stats()
    return {
        "log_stock_mt": round(float(get_log_stock_total()), 4),
        "saw_stock_tray": _to_int(flow.get("saw_tray_pool"), 0),
        "dip_stock_tray": _to_int(flow.get("dip_tray_pool"), 0),
        "sorting_stock_tray": _to_int(flow.get("selected_tray_pool"), 0),
        "kiln_done_stock_tray": _to_int(flow.get("kiln_done_tray_pool"), 0),
        "finished_product_count": _to_int(product_count, 0),
        "finished_product_m3": round(_to_float(product_m3), 3),
    }


def _build_range_report(start_day: date, end_day: date, period_type: str, period_key: str) -> dict:
    start_iso = f"{start_day.strftime('%Y-%m-%d')}T00:00:00"
    end_iso = f"{end_day.strftime('%Y-%m-%d')}T23:59:59"

    session = Session()
    try:
        log_rows = _between(session, LogEntry, start_iso, end_iso)
        saw_rows = _between(session, SawRecord, start_iso, end_iso)
        dip_rows = _between(session, DipRecord, start_iso, end_iso)
        sort_rows = _between(session, SortRecord, start_iso, end_iso)
        tray_rows = _between(session, TrayBatch, start_iso, end_iso)
        product_rows = _between(session, ProductBatch, start_iso, end_iso)
        byproduct_rows = _between(session, ByproductRecord, start_iso, end_iso)
        second_rows = _between(session, FlowSecondSortRecord, start_iso, end_iso, time_field="time")
    finally:
        session.close()

    report = {
        "type": str(period_type or "weekly"),
        "key": str(period_key or ""),
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "range": {
            "start": start_iso,
            "end": end_iso,
        },
        "summary": {
            "log_in_mt": round(sum(_to_float(r.log_amount) for r in log_rows), 4),
            "saw_log_consumed_mt": round(sum(_to_float(r.saw_mt) for r in saw_rows), 4),
            "saw_output_trays": sum(_to_int(r.saw_trays) for r in saw_rows),
            "dip_cans": sum(_to_int(r.dip_cans) for r in dip_rows),
            "dip_trays": sum(_to_int(r.dip_trays) for r in dip_rows),
            "sort_trays": sum(_to_int(r.sort_trays) for r in sort_rows),
            "kiln_load_trays": sum(_to_int(r.tray_count) for r in tray_rows),
            "secondary_trays": sum(_to_int(r.trays) for r in second_rows),
            "finished_pcs": sum(_to_int(r.product_count) for r in product_rows),
            "finished_m3": round(sum(_to_float(r.total_volume) for r in product_rows), 3),
            "bark_sale_ks": round(sum(_to_float(r.bark_sale_amount) for r in byproduct_rows), 2),
        },
        "counts": {
            "log_entries": len(log_rows),
            "saw_records": len(saw_rows),
            "dip_records": len(dip_rows),
            "sort_records": len(sort_rows),
            "tray_batches": len(tray_rows),
            "product_batches": len(product_rows),
            "byproduct_records": len(byproduct_rows),
            "second_sort_records": len(second_rows),
        },
        "inventory_snapshot": _snapshot_now(),
    }
    return report


def _period_key_week(day: date) -> str:
    y, w, _ = day.isocalendar()
    return f"{int(y)}-W{int(w):02d}"


def _period_key_month(day: date) -> str:
    return day.strftime("%Y-%m")


def _upsert_report(key_name: str, report: dict) -> None:
    session = Session()
    try:
        arr = _load_json(session, key_name, [])
        if not isinstance(arr, list):
            arr = []
        key = str(report.get("key") or "")
        replaced = False
        for i, row in enumerate(arr):
            if str((row or {}).get("key") or "") == key:
                arr[i] = report
                replaced = True
                break
        if not replaced:
            arr.append(report)
        arr = sorted(arr, key=lambda x: str((x or {}).get("key") or ""), reverse=True)[:24]
        _save_json(session, key_name, arr)
        session.commit()
    finally:
        session.close()


def _latest_report(key_name: str) -> dict | None:
    session = Session()
    try:
        arr = _load_json(session, key_name, [])
        if not isinstance(arr, list) or not arr:
            return None
        arr = sorted(arr, key=lambda x: str((x or {}).get("key") or ""), reverse=True)
        return arr[0]
    finally:
        session.close()


def get_report(period: str, key: str | None = None) -> dict | None:
    key_name = WEEKLY_REPORTS_KEY if str(period) == "weekly" else MONTHLY_REPORTS_KEY
    session = Session()
    try:
        arr = _load_json(session, key_name, [])
        if not isinstance(arr, list) or not arr:
            return None
        if key:
            for row in arr:
                if str((row or {}).get("key") or "") == str(key):
                    return row
            return None
        arr = sorted(arr, key=lambda x: str((x or {}).get("key") or ""), reverse=True)
        return arr[0]
    finally:
        session.close()


def ensure_period_reports_generated(now: datetime | None = None) -> dict:
    cur = now or datetime.now()
    today = cur.date()
    hour = int(cur.hour)

    # weekly: every Saturday 20:00 generate current ISO week report
    monday = today - timedelta(days=today.weekday())
    saturday = monday + timedelta(days=5)
    if today > saturday or (today == saturday and hour >= 20):
        wk_key = _period_key_week(saturday)
        exists = get_report("weekly", wk_key)
        if not exists:
            rep = _build_range_report(monday, saturday, "weekly", wk_key)
            _upsert_report(WEEKLY_REPORTS_KEY, rep)

    # catch-up previous week (for downtime / restart)
    prev_saturday = saturday - timedelta(days=7)
    prev_monday = monday - timedelta(days=7)
    prev_wk_key = _period_key_week(prev_saturday)
    if not get_report("weekly", prev_wk_key):
        rep = _build_range_report(prev_monday, prev_saturday, "weekly", prev_wk_key)
        _upsert_report(WEEKLY_REPORTS_KEY, rep)

    # monthly: last day of month 20:00 generate this month report
    first_next = (today.replace(day=1) + timedelta(days=32)).replace(day=1)
    month_last = first_next - timedelta(days=1)
    if today > month_last or (today == month_last and hour >= 20):
        mon_key = _period_key_month(month_last)
        exists = get_report("monthly", mon_key)
        if not exists:
            start = month_last.replace(day=1)
            rep = _build_range_report(start, month_last, "monthly", mon_key)
            _upsert_report(MONTHLY_REPORTS_KEY, rep)

    # catch-up for previous month if missed
    prev_month_last = today.replace(day=1) - timedelta(days=1)
    prev_mon_key = _period_key_month(prev_month_last)
    if not get_report("monthly", prev_mon_key):
        prev_start = prev_month_last.replace(day=1)
        rep = _build_range_report(prev_start, prev_month_last, "monthly", prev_mon_key)
        _upsert_report(MONTHLY_REPORTS_KEY, rep)

    w = _latest_report(WEEKLY_REPORTS_KEY)
    m = _latest_report(MONTHLY_REPORTS_KEY)
    return {
        "weekly": w,
        "monthly": m,
    }


def get_period_report_links() -> dict:
    w = _latest_report(WEEKLY_REPORTS_KEY)
    m = _latest_report(MONTHLY_REPORTS_KEY)
    return {
        "weekly": {
            "generated": bool(w),
            "key": str((w or {}).get("key") or ""),
            "generated_at": str((w or {}).get("generated_at") or ""),
            "url": f"/report/weekly?key={str((w or {}).get('key') or '')}" if w else "",
        },
        "monthly": {
            "generated": bool(m),
            "key": str((m or {}).get("key") or ""),
            "generated_at": str((m or {}).get("generated_at") or ""),
            "url": f"/report/monthly?key={str((m or {}).get('key') or '')}" if m else "",
        },
    }
