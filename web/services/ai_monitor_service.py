import json
import os
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from modules.ai.ai_engine import ask_ai
from modules.finance.finance_engine import load as load_finance
from modules.hr.hr_engine import get_hr_employees_payload
from modules.storage.db_doc_store import load_doc, save_doc
from web.services.daily_report_service import build_daily_report
from web.services.alert_settings_service import get_ai_monitor_settings, get_ai_capacity_settings
from web.services.alert_center_service import get_alert_center_payload
from web.services.forecast_service import build_forecast_payload
from web.services.ops_upgrade_service import build_equipment_quality_snapshot, build_role_collaboration_plan
from web.services.traceability_service import build_traceability_snapshot
from web.utils import get_stock_data


DOC_KEY = "ai_deep_monitor_v1"
RUN_STATE = {"running": False, "last_started_ts": 0.0}
RUN_LOCK = threading.Lock()
DEEP_MONITOR_MIN_GAP_SECONDS = max(300, int(os.getenv("AIF_AI_DEEP_MONITOR_MIN_GAP_SECONDS", "900") or "900"))
IDLE_MONITOR_SECONDS = max(3600, int(os.getenv("AIF_AI_IDLE_MONITOR_SECONDS", str(3 * 60 * 60)) or str(3 * 60 * 60)))
DB_CHANGE_SETTLE_SECONDS = max(300, int(os.getenv("AIF_AI_DB_CHANGE_SETTLE_SECONDS", str(15 * 60)) or str(15 * 60)))
DEEP_MONITOR_AI_TIMEOUT = max(90, float(os.getenv("AIF_AI_DEEP_MONITOR_TIMEOUT", "150") or "150"))
DEEP_MONITOR_AI_SUMMARY_TIMEOUT = max(15, float(os.getenv("AIF_AI_DEEP_MONITOR_SUMMARY_TIMEOUT", "35") or "35"))


def _now_ts() -> int:
    return int(time.time())


def _today_slot_key(now_dt: datetime | None = None) -> str:
    dt = now_dt or datetime.now()
    return dt.strftime("%Y-%m-%d")


def _safe_float(v: Any, dv: float = 0.0) -> float:
    try:
        return float(v)
    except Exception:
        return dv


def _cached_doc() -> dict[str, Any]:
    data = load_doc(DOC_KEY, default={"by_lang": {}, "meta": {}}, legacy_file=None)
    return data if isinstance(data, dict) else {"by_lang": {}, "meta": {}}


def _save_cached_doc(data: dict[str, Any]) -> None:
    save_doc(DOC_KEY, data if isinstance(data, dict) else {"by_lang": {}, "meta": {}})


def _extract_first_json_object(raw: str) -> str:
    text = str(raw or "")
    start = text.find("{")
    if start < 0:
        raise ValueError("JSON object not found")
    depth = 0
    in_string = False
    escaped = False
    for idx in range(start, len(text)):
        ch = text[idx]
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start : idx + 1]
    raise ValueError("JSON object incomplete")


def _db_path() -> Path:
    return Path(__file__).resolve().parents[2] / "unified.db"


def _get_db_mtime() -> float:
    try:
        return round(_db_path().stat().st_mtime, 6)
    except Exception:
        return 0.0


def _monitor_cfg() -> dict[str, Any]:
    data = get_ai_monitor_settings()
    return {
        "active_start": str(data.get("active_start") or "16:00"),
        "active_end": str(data.get("active_end") or "20:00"),
        "idle_monitor_seconds": max(3600, int(float(data.get("idle_monitor_hours") or 3) * 3600)),
        "db_change_settle_seconds": max(300, int(float(data.get("db_change_settle_minutes") or 15) * 60)),
        "min_gap_seconds": max(300, int(float(data.get("deep_monitor_min_gap_minutes") or 15) * 60)),
    }


def _parse_hhmm_to_min(value: str, default: int = 0) -> int:
    try:
        hour_s, minute_s = str(value or "").strip().split(":", 1)
        hour = max(0, min(23, int(hour_s)))
        minute = max(0, min(59, int(minute_s)))
        return (hour * 60) + minute
    except Exception:
        return default


def _in_monitor_window(now_dt: datetime | None = None) -> bool:
    dt = now_dt or datetime.now()
    cfg = _monitor_cfg()
    start_min = _parse_hhmm_to_min(cfg["active_start"], 16 * 60)
    end_min = _parse_hhmm_to_min(cfg["active_end"], 20 * 60)
    current_min = dt.hour * 60 + dt.minute
    if start_min == end_min:
        return True
    if start_min < end_min:
        return start_min <= current_min < end_min
    return current_min >= start_min or current_min < end_min


def _next_window_start(now_dt: datetime | None = None) -> datetime:
    dt = now_dt or datetime.now()
    cfg = _monitor_cfg()
    start_min = _parse_hhmm_to_min(cfg["active_start"], 16 * 60)
    end_min = _parse_hhmm_to_min(cfg["active_end"], 20 * 60)
    current_min = dt.hour * 60 + dt.minute
    start_dt = dt.replace(hour=start_min // 60, minute=start_min % 60, second=0, microsecond=0)

    if start_min == end_min:
        return dt
    if start_min < end_min:
        if current_min < start_min:
            return start_dt
        if current_min >= end_min:
            return start_dt + timedelta(days=1)
        return dt
    if current_min >= start_min or current_min < end_min:
        return dt
    return start_dt


def _fit_to_monitor_window(target_dt: datetime) -> datetime:
    if _in_monitor_window(target_dt):
        return target_dt
    return _next_window_start(target_dt)


def get_ai_monitor_runtime_status() -> dict[str, Any]:
    doc = _cached_doc()
    meta = doc.get("meta", {}) if isinstance(doc.get("meta"), dict) else {}
    cfg = _monitor_cfg()
    now_dt = datetime.now()
    now_ts = int(now_dt.timestamp())
    last_generated_ts = int(meta.get("last_generated_ts") or 0)
    last_success_ts = int(meta.get("last_success_ts") or 0)
    last_started_ts = int(float(RUN_STATE.get("last_started_ts") or 0.0))
    pending_deadline_ts = int(meta.get("pending_db_deadline_ts") or 0)
    pending_db_mtime = float(meta.get("pending_db_mtime") or 0.0)
    last_trigger = str(meta.get("last_trigger") or "").strip()

    last_generated_at = ""
    if last_generated_ts > 0:
        try:
            last_generated_at = datetime.fromtimestamp(last_generated_ts).strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            last_generated_at = ""

    base_ts = last_success_ts if last_success_ts > 0 else last_generated_ts
    periodic_due_dt = _fit_to_monitor_window(
        datetime.fromtimestamp(max(base_ts, now_ts) if base_ts <= 0 else base_ts + int(cfg["idle_monitor_seconds"]))
    )

    pending_due_dt = None
    if pending_deadline_ts > 0 and pending_db_mtime > 0:
        pending_base_ts = max(now_ts, pending_deadline_ts)
        pending_due_dt = _fit_to_monitor_window(datetime.fromtimestamp(pending_base_ts))

    next_run_dt = periodic_due_dt
    next_reason = "periodic"
    if pending_due_dt is not None:
        if periodic_due_dt <= pending_due_dt:
            next_run_dt = periodic_due_dt
            next_reason = "periodic"
        else:
            next_run_dt = pending_due_dt
            next_reason = "db_change"

    if RUN_STATE["running"]:
        next_reason = "running"

    return {
        "is_running": bool(RUN_STATE["running"]),
        "in_window": bool(_in_monitor_window(now_dt)),
        "window_start": str(cfg["active_start"]),
        "window_end": str(cfg["active_end"]),
        "last_generated_at": last_generated_at,
        "last_success_at": datetime.fromtimestamp(last_success_ts).strftime("%Y-%m-%d %H:%M:%S") if last_success_ts > 0 else "",
        "last_trigger": last_trigger,
        "last_started_at": datetime.fromtimestamp(last_started_ts).strftime("%Y-%m-%d %H:%M:%S") if last_started_ts > 0 else "",
        "pending_db_change": bool(pending_due_dt is not None),
        "pending_due_at": pending_due_dt.strftime("%Y-%m-%d %H:%M:%S") if pending_due_dt is not None else "",
        "next_run_at": next_run_dt.strftime("%Y-%m-%d %H:%M:%S"),
        "next_reason": next_reason,
    }


def get_cached_deep_monitor(lang: str = "zh") -> dict[str, Any]:
    doc = _cached_doc()
    by_lang = doc.get("by_lang", {}) if isinstance(doc.get("by_lang"), dict) else {}
    success_by_lang = doc.get("success_by_lang", {}) if isinstance(doc.get("success_by_lang"), dict) else {}
    out = by_lang.get(lang) or by_lang.get("zh") or {}
    if isinstance(out, dict) and str(out.get("error") or "").strip():
        fallback = success_by_lang.get(lang) or success_by_lang.get("zh")
        if isinstance(fallback, dict) and fallback:
            out = dict(fallback)
    if not isinstance(out, dict):
        return {}
    result = dict(out)
    result["template_version"] = str(result.get("template_version") or "deep_monitor_v2")
    return result


def _build_hr_snapshot() -> dict[str, Any]:
    payload = get_hr_employees_payload()
    rows = payload.get("rows", []) if isinstance(payload.get("rows"), list) else []
    by_status: dict[str, int] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        status = str(row.get("today_attendance_status_text", "") or row.get("today_attendance_status", "") or "").strip() or "未知"
        by_status[status] = by_status.get(status, 0) + 1
    return {
        "employee_total": int(payload.get("employee_total", 0) or 0),
        "employee_active": int(payload.get("employee_active", 0) or 0),
        "absent_today_count": int(payload.get("absent_today_count", 0) or 0),
        "by_status": by_status,
        "team_live_stats": payload.get("team_live_stats", {}) if isinstance(payload.get("team_live_stats"), dict) else {},
        "saw_operation_stats": payload.get("saw_operation_stats", {}) if isinstance(payload.get("saw_operation_stats"), dict) else {},
    }


def _build_finance_snapshot() -> dict[str, Any]:
    data = load_finance()
    accounts = data.get("accounts", {}) if isinstance(data.get("accounts"), dict) else {}
    records = data.get("records", []) if isinstance(data.get("records"), list) else []
    today = datetime.now().date()
    income_today = 0.0
    expense_today = 0.0
    for row in records:
        if not isinstance(row, dict):
            continue
        try:
            dt = datetime.fromisoformat(str(row.get("time") or ""))
        except Exception:
            continue
        if dt.date() != today:
            continue
        typ = str(row.get("type") or "").strip()
        amt = _safe_float(row.get("amount"), 0.0)
        if typ == "income":
            income_today += amt
        elif typ == "expense":
            expense_today += amt
    return {
        "cash": round(_safe_float(accounts.get("cash"), 0.0), 2),
        "bank": round(_safe_float(accounts.get("bank"), 0.0), 2),
        "income_today": round(income_today, 2),
        "expense_today": round(expense_today, 2),
        "net_today": round(income_today - expense_today, 2),
        "records_today": sum(1 for row in records if isinstance(row, dict) and str(row.get("time") or "").startswith(today.isoformat())),
    }


def _build_production_monitor_template(stock: dict[str, Any], center: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    intelligence = center.get("factory_intelligence", {}) if isinstance(center, dict) else {}
    throughput = center.get("throughput", {}) if isinstance(center, dict) else {}
    efficiency = center.get("efficiency", {}) if isinstance(center, dict) else {}

    stage_scores = []
    for row in (intelligence.get("stage_scores") or [])[:3] if isinstance(intelligence, dict) else []:
        if not isinstance(row, dict):
            continue
        stage_scores.append(
            {
                "name": str(row.get("name") or ""),
                "score": _safe_float(row.get("score"), 0.0),
                "day_score": _safe_float(row.get("day_score"), 0.0),
            }
        )

    priority_stage = {
        "name": str((((intelligence.get("priority_stage") or {}) if isinstance(intelligence, dict) else {}).get("name")) or ""),
        "reason": str((((intelligence.get("priority_stage") or {}) if isinstance(intelligence, dict) else {}).get("reason")) or ""),
    }
    pressure_stage = {
        "name": str((((intelligence.get("pressure_stage") or {}) if isinstance(intelligence, dict) else {}).get("name")) or ""),
        "reason": str((((intelligence.get("pressure_stage") or {}) if isinstance(intelligence, dict) else {}).get("reason")) or ""),
    }
    kiln_summary = dict((intelligence.get("kiln_summary") or {}) if isinstance(intelligence, dict) else {})
    kiln_status = {}
    raw_kiln_status = stock.get("kiln_status", {})
    if isinstance(raw_kiln_status, dict):
        for key in ("empty", "drying", "ready", "unloading", "unknown"):
            if key in raw_kiln_status:
                kiln_status[key] = raw_kiln_status.get(key)

    production_template = {
        "brief": str((intelligence.get("brief") if isinstance(intelligence, dict) else "") or ""),
        "stage_scores": stage_scores,
        "throughput_current_day": dict(((throughput or {}).get("current_day") or {})),
        "efficiency_current": dict(((efficiency or {}).get("current") or {})),
        "inventory_snapshot": {
            "log_stock": stock.get("log_stock"),
            "saw_stock": stock.get("saw_stock"),
            "dip_stock": stock.get("dip_stock"),
            "sorting_stock": stock.get("sorting_stock"),
            "kiln_done_stock": stock.get("kiln_done_stock"),
            "product_count": stock.get("product_count"),
        },
        "kiln_status": kiln_status,
        "kiln_summary": kiln_summary,
    }
    return production_template, priority_stage, pressure_stage


def _build_hr_monitor_template(hr: dict[str, Any], stock: dict[str, Any]) -> dict[str, Any]:
    by_status = hr.get("by_status", {}) if isinstance(hr.get("by_status"), dict) else {}
    team_live_stats = hr.get("team_live_stats", {}) if isinstance(hr.get("team_live_stats"), dict) else {}
    saw_operation_stats = hr.get("saw_operation_stats", {}) if isinstance(hr.get("saw_operation_stats"), dict) else {}
    sorting_team = team_live_stats.get("sorting", {}) if isinstance(team_live_stats.get("sorting"), dict) else {}
    dip_kiln_team = team_live_stats.get("dip_kiln", {}) if isinstance(team_live_stats.get("dip_kiln"), dict) else {}
    hints: list[dict[str, Any]] = []
    running_machine_count = int(saw_operation_stats.get("running_machine_count", 0) or 0)
    configured_machine_count = int(saw_operation_stats.get("configured_machine_count", 0) or 0)
    likely_reason = str(saw_operation_stats.get("likely_reason", "") or "").strip()
    log_stock = _safe_float(stock.get("log_stock"), 0.0)
    sorting_stock = int(stock.get("sorting_stock", 0) or 0)
    kiln_done_stock = int(stock.get("kiln_done_stock", 0) or 0)
    if configured_machine_count > 0 and running_machine_count < configured_machine_count:
        if likely_reason in ("staff_shortage", "attendance_gap"):
            reason = "saw_staff_shortage"
        elif log_stock <= 20:
            reason = "raw_material_shortage"
        else:
            reason = "dispatch_or_material_mix"
        hints.append(
            {
                "signal": "saw_operation_gap",
                "running": running_machine_count,
                "configured": configured_machine_count,
                "reason": reason,
                "idle_machines": saw_operation_stats.get("idle_machines", []),
            }
        )
    if sorting_stock <= 4:
        hints.append(
            {
                "signal": "kiln_feed_risk",
                "sorting_stock": sorting_stock,
                "dip_kiln_on_duty": int(dip_kiln_team.get("on_duty", 0) or 0),
                "reason": "upstream_feed_shortage",
            }
        )
    if kiln_done_stock >= 8:
        hints.append(
            {
                "signal": "secondary_sort_pressure",
                "kiln_done_stock": kiln_done_stock,
                "sorting_team_on_duty": int(sorting_team.get("on_duty", 0) or 0),
                "sorting_team_unavailable": int(sorting_team.get("unavailable", 0) or 0),
                "reason": "sorting_capacity_or_staffing",
            }
        )
    return {
        "employee_total": int(hr.get("employee_total", 0) or 0),
        "employee_active": int(hr.get("employee_active", 0) or 0),
        "absent_today_count": int(hr.get("absent_today_count", 0) or 0),
        "on_duty_count": int(sum(int(by_status.get(key, 0) or 0) for key in ("出勤中", "午餐休息", "加班中", "present", "lunch", "overtime"))),
        "leave_related_count": int(sum(int(by_status.get(key, 0) or 0) for key in ("休假", "病假", "休息", "leave", "sick", "rest", "absent"))),
        "by_status": by_status,
        "team_live_stats": team_live_stats,
        "saw_operation_stats": saw_operation_stats,
        "workforce_pressure_hints": hints,
    }


def _build_finance_monitor_template(finance: dict[str, Any]) -> dict[str, Any]:
    return {
        "cash": round(_safe_float(finance.get("cash"), 0.0), 2),
        "bank": round(_safe_float(finance.get("bank"), 0.0), 2),
        "income_today": round(_safe_float(finance.get("income_today"), 0.0), 2),
        "expense_today": round(_safe_float(finance.get("expense_today"), 0.0), 2),
        "net_today": round(_safe_float(finance.get("net_today"), 0.0), 2),
        "records_today": int(finance.get("records_today", 0) or 0),
        "funding_state": "tight" if (_safe_float(finance.get("cash"), 0.0) + _safe_float(finance.get("bank"), 0.0)) <= 0 else "available",
    }


def _build_capacity_targets_template() -> dict[str, Any]:
    cfg = get_ai_capacity_settings()
    band_saw_machine_count = int(cfg.get("band_saw_machine_count", 6) or 6)
    secondary_saw_machine_count = int(cfg.get("secondary_saw_machine_count", 3) or 3)
    return {
        "band_saw": {
            "machine_count": band_saw_machine_count,
            "primary_staff_target": int(cfg.get("band_saw_primary_target", 6) or 0),
            "assistant_staff_target": int(cfg.get("band_saw_assistant_target", 6) or 0),
            "qc_staff_target": int(cfg.get("band_saw_qc_target", 6) or 0),
            "daily_target_trays_per_machine": int(cfg.get("band_saw_daily_target_trays_per_machine", 4) or 0),
            "daily_target_trays_total": band_saw_machine_count * int(cfg.get("band_saw_daily_target_trays_per_machine", 4) or 0),
        },
        "secondary_saw": {
            "machine_count": secondary_saw_machine_count,
            "operator_target": int(cfg.get("secondary_saw_operator_target", 3) or 0),
            "daily_finish_target_pcs": int(cfg.get("secondary_daily_finish_target_pcs", 15) or 0),
        },
    }


def _recent_capacity_days(days: int = 3) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    total = max(1, min(3, int(days or 3)))
    for back in range(total):
        day_obj = datetime.now() - timedelta(days=back)
        day_text = day_obj.strftime("%Y-%m-%d")
        try:
            report = build_daily_report(day_text, lang="zh")
        except Exception:
            continue
        summary = report.get("summary", {}) if isinstance(report.get("summary"), dict) else {}
        out.append(
            {
                "date": day_text,
                "saw_output_trays": int(summary.get("saw_output_trays", 0) or 0),
                "finished_pcs": int(summary.get("finished_pcs", 0) or 0),
            }
        )
    return out


def _under_target_streak(days: list[dict[str, Any]], key: str, target: int) -> dict[str, Any]:
    streak = 0
    sampled: list[dict[str, Any]] = []
    for row in days:
        actual = int((row or {}).get(key, 0) or 0)
        under = actual < target
        sampled.append({"date": str((row or {}).get("date") or ""), "actual": actual, "under_target": under})
        if under:
            streak += 1
        else:
            break
    return {
        "target": target,
        "streak_days": streak,
        "recent_days": sampled[:7],
    }


def _build_capacity_gap_template(
    capacity_targets: dict[str, Any],
    production_template: dict[str, Any],
    hr_template: dict[str, Any],
) -> dict[str, Any]:
    band = capacity_targets.get("band_saw", {}) if isinstance(capacity_targets.get("band_saw"), dict) else {}
    secondary = capacity_targets.get("secondary_saw", {}) if isinstance(capacity_targets.get("secondary_saw"), dict) else {}
    throughput_day = production_template.get("throughput_current_day", {}) if isinstance(production_template.get("throughput_current_day"), dict) else {}
    saw_stats = hr_template.get("saw_operation_stats", {}) if isinstance(hr_template.get("saw_operation_stats"), dict) else {}
    sorting_team = (hr_template.get("team_live_stats", {}) or {}).get("sorting", {}) if isinstance(hr_template.get("team_live_stats"), dict) else {}

    saw_target_total = int(band.get("daily_target_trays_total", 0) or 0)
    saw_actual = int(throughput_day.get("saw_output_trays", 0) or 0)
    saw_running = int(saw_stats.get("running_machine_count", 0) or 0)
    saw_machine_target = int(band.get("machine_count", 0) or 0)
    finished_target = int(secondary.get("daily_finish_target_pcs", 0) or 0)
    finished_actual = int(throughput_day.get("product_count", throughput_day.get("finished_pcs", 0)) or 0)
    secondary_target_operators = int(secondary.get("operator_target", 0) or 0)
    secondary_on_duty = int(sorting_team.get("on_duty", 0) or 0)
    recent_days = _recent_capacity_days(3)
    saw_streak = _under_target_streak(recent_days, "saw_output_trays", saw_target_total)
    finished_streak = _under_target_streak(recent_days, "finished_pcs", finished_target)

    saw_gap_reason = "on_track"
    if saw_actual < saw_target_total:
        if saw_running < saw_machine_target:
            if str(saw_stats.get("likely_reason", "") or "").strip() in ("staff_shortage", "attendance_gap"):
                saw_gap_reason = "saw_staff_gap"
            else:
                saw_gap_reason = "saw_machine_or_material_gap"
        else:
            saw_gap_reason = "saw_efficiency_gap"

    secondary_gap_reason = "on_track"
    if finished_actual < finished_target:
        if secondary_on_duty < secondary_target_operators:
            secondary_gap_reason = "secondary_staff_gap"
        elif int(secondary.get("machine_count", 0) or 0) <= 3:
            secondary_gap_reason = "secondary_capacity_gap"
        else:
            secondary_gap_reason = "secondary_flow_gap"

    return {
        "band_saw": {
            "target_daily_trays": saw_target_total,
            "actual_daily_trays": saw_actual,
            "gap_trays": saw_actual - saw_target_total,
            "target_machine_count": saw_machine_target,
            "actual_running_machines": saw_running,
            "gap_reason": saw_gap_reason,
            "under_target_streak_days": int(saw_streak.get("streak_days", 0) or 0),
            "recent_days": saw_streak.get("recent_days", []),
        },
        "secondary_finish": {
            "target_daily_finished_pcs": finished_target,
            "actual_daily_finished_pcs": finished_actual,
            "gap_pcs": finished_actual - finished_target,
            "target_operator_count": secondary_target_operators,
            "actual_on_duty_count": secondary_on_duty,
            "machine_count": int(secondary.get("machine_count", 0) or 0),
            "gap_reason": secondary_gap_reason,
            "under_target_streak_days": int(finished_streak.get("streak_days", 0) or 0),
            "recent_days": finished_streak.get("recent_days", []),
        },
    }


def _build_monitor_context(lang: str = "zh") -> tuple[dict[str, Any], str]:
    stock = get_stock_data(lang)
    center = get_alert_center_payload(limit_recent=30, lang=lang)
    hr = _build_hr_snapshot()
    finance = _build_finance_snapshot()
    intelligence = center.get("factory_intelligence", {}) if isinstance(center, dict) else {}
    production_template, priority_stage, pressure_stage = _build_production_monitor_template(stock, center)
    capacity_targets = _build_capacity_targets_template()
    hr_template = _build_hr_monitor_template(hr, stock)
    hr_template["capacity_targets"] = capacity_targets
    production_template["capacity_targets"] = capacity_targets
    capacity_gap = _build_capacity_gap_template(capacity_targets, production_template, hr_template)
    hr_template["capacity_gap"] = capacity_gap
    production_template["capacity_gap"] = capacity_gap
    finance_template = _build_finance_monitor_template(finance)
    traceability = build_traceability_snapshot(lang=lang, limit=8)
    forecast = build_forecast_payload(lang=lang, stock=stock, intelligence=intelligence)
    equipment_quality = build_equipment_quality_snapshot(
        lang=lang,
        stock=stock,
        factory_intelligence=intelligence,
        throughput_day=((center.get("throughput") or {}) if isinstance(center, dict) else {}).get("current_day", {}),
    )
    role_collaboration = build_role_collaboration_plan(
        lang=lang,
        factory_intelligence=intelligence,
        equipment_quality=equipment_quality,
        forecast=forecast,
    )
    structured_payload = {
        "language": lang,
        "template_version": "deep_monitor_v2",
        "monitor_frame": {
            "goal": "围绕提升产能、保障连续生产、跨模块协同做深巡检",
            "note": "以下是系统整理后的关键事实，不代表结论，结论需要由AI自行判断",
            "trigger": "",
        },
        "production_core_signals": production_template,
        "hr_core_signals": hr_template,
        "finance_core_signals": finance_template,
        "forecast_core_signals": forecast,
        "traceability_core_signals": traceability,
        "equipment_quality_signals": equipment_quality,
        "role_collaboration_signals": role_collaboration,
        "capacity_targets": capacity_targets,
        "capacity_gap": capacity_gap,
        "current_priority_stage": priority_stage,
        "current_pressure_stage": pressure_stage,
    }
    text = json.dumps(structured_payload, ensure_ascii=False, separators=(",", ":"))
    return {
        "stock": stock,
        "center": center,
        "hr": hr,
        "finance": finance,
        "intelligence": intelligence,
        "traceability": traceability,
        "forecast": forecast,
        "equipment_quality": equipment_quality,
        "role_collaboration": role_collaboration,
        "template_payload": structured_payload,
    }, text


def _system_lang_pack(lang: str) -> dict[str, str]:
    lc = str(lang or "zh").strip().lower()
    if lc == "en":
        return {
            "summary": "The plant should still focus first on {priority}, while current pressure is showing mainly around {pressure}.",
            "summary_streak": "The plant should still focus first on {priority}, while current pressure is showing mainly around {pressure}. This is no longer a one-day fluctuation.",
            "production_ok": "Production is broadly steady.",
            "production_gap": "Production pressure is concentrated around {pressure}; priority improvement still points to {priority}.",
            "hr_ok": "HR is broadly steady.",
            "hr_absent": "HR needs to watch staffing coverage. Today absent/unavailable: {count}.",
            "finance_ok": "Finance is broadly steady.",
            "finance_tight": "Finance should protect production-critical cash usage first. Net today: {net:.2f} KS.",
            "risk_streak_saw": "Band-saw output has been below target for {days} consecutive days.",
            "risk_streak_secondary": "Secondary finished output has been below target for {days} consecutive days.",
            "risk_forecast": "Tomorrow's main forecast risk is {risk}.",
            "risk_equipment": "{risk}",
            "focus_priority": "Keep lifting {priority} instead of only reacting to surface symptoms.",
            "focus_pressure": "Current most visible pressure is at {pressure}.",
            "focus_streak": "Treat the repeated under-target pattern as a sustained issue, not a one-off fluctuation.",
            "action_role": "{role}: {action}",
            "action_forecast": "Prepare around tomorrow's risk: {risk}.",
            "action_default": "Use the next shift to stabilize handoff, staffing, and capacity around the priority stage.",
            "stale_notice": "This result is primarily system-derived because the local AI summary did not complete in time.",
        }
    if lc == "my":
        return {
            "summary": "စက်ရုံတစ်ခုလုံးအနေနဲ့ {priority} ကို အရင်တိုးမြှင့်သင့်ပြီး လက်ရှိဖိအားက {pressure} မှာ ပိုပြနေပါတယ်။",
            "summary_streak": "စက်ရုံတစ်ခုလုံးအနေနဲ့ {priority} ကို အရင်တိုးမြှင့်သင့်ပြီး လက်ရှိဖိအားက {pressure} မှာ ပိုပြနေပါတယ်။ ဒီအခြေအနေက တစ်ရက်တည်းကိစ္စမဟုတ်တော့ပါ။",
            "production_ok": "ထုတ်လုပ်ရေးအခြေအနေ အများအားဖြင့် တည်ငြိမ်ပါသည်။",
            "production_gap": "ထုတ်လုပ်ရေးဖိအားက {pressure} မှာ စုပြီးပြနေပြီး ဦးစားပေးတိုးမြှင့်ရမည့်အပိုင်းကတော့ {priority} ဖြစ်နေဆဲပါ။",
            "hr_ok": "HR အခြေအနေ အများအားဖြင့် တည်ငြိမ်ပါသည်။",
            "hr_absent": "HR က လူအင်အားဖုံးလွှမ်းမှုကို စောင့်ကြည့်ရပါမည်။ ယနေ့ မလာ/မရရှိသူ {count} ဦး။",
            "finance_ok": "ငွေကြေးအခြေအနေ အများအားဖြင့် တည်ငြိမ်ပါသည်။",
            "finance_tight": "ငွေကြေးဘက်က ထုတ်လုပ်မှုအရေးကြီးအသုံးစရိတ်ကို အရင်ကာကွယ်သင့်ပါသည်။ ယနေ့ net {net:.2f} KS။",
            "risk_streak_saw": "Band-saw ထွက်အားဟာ {days} ရက်ဆက်တိုက် ပစ်မှတ်မမီခဲ့ပါ။",
            "risk_streak_secondary": "ဒုတိယရွေးကုန်ချောထွက်အားဟာ {days} ရက်ဆက်တိုက် ပစ်မှတ်မမီခဲ့ပါ။",
            "risk_forecast": "မနက်ဖြန် အဓိကအန္တရာယ်က {risk} ဖြစ်နိုင်ပါတယ်။",
            "risk_equipment": "{risk}",
            "focus_priority": "{priority} ကို အရင်ဆွဲတင်ပြီး ပေါ်ပင်လက္ခဏာကိုသာ မလိုက်ပါနဲ့။",
            "focus_pressure": "လက်ရှိအထင်ရှားဆုံး ဖိအားက {pressure} မှာပါ။",
            "focus_streak": "ပစ်မှတ်မမီမှုကို တစ်ကြိမ်တည်းပြဿနာမဟုတ်ဘဲ ဆက်တိုက်ပြဿနာအဖြစ် ကိုင်တွယ်ပါ။",
            "action_role": "{role}: {action}",
            "action_forecast": "မနက်ဖြန် အန္တရာယ် {risk} ကို ကြိုတင်ပြင်ဆင်ပါ။",
            "action_default": "နောက် shift မှာ priority stage ပတ်ဝန်းကျင်က handoff၊ staffing နဲ့ capacity ကို တည်ငြိမ်အောင် လုပ်ပါ။",
            "stale_notice": "ဒီရလဒ်က local AI summary အချိန်မီမပြီးလို့ system analysis ကို အခြေခံထားပါတယ်။",
        }
    return {
        "summary": "当前还是应该先把「{priority}」提起来，现场压力主要出现在「{pressure}」。",
        "summary_streak": "当前还是应该先把「{priority}」提起来，现场压力主要出现在「{pressure}」。这已经不是单日波动了。",
        "production_ok": "生产侧整体还算平稳。",
        "production_gap": "生产侧压力集中在「{pressure}」，而优先提升环节仍然指向「{priority}」。",
        "hr_ok": "HR 侧当前整体平稳。",
        "hr_absent": "HR 侧要继续盯人手覆盖，今日未到岗/不可用 {count} 人。",
        "finance_ok": "财务侧当前整体平稳。",
        "finance_tight": "财务侧要先保生产关键支出，今日净额 {net:.2f} KS。",
        "risk_streak_saw": "带锯产出已连续 {days} 天未达目标。",
        "risk_streak_secondary": "二选成品产出已连续 {days} 天未达目标。",
        "risk_forecast": "明日主风险更像在「{risk}」。",
        "risk_equipment": "{risk}",
        "focus_priority": "先把「{priority}」拉起来，不要只跟着表面症状跑。",
        "focus_pressure": "当前最明显的压力点在「{pressure}」。",
        "focus_streak": "把“连续未达标”当成持续性问题来处理，不要按单日波动看。",
        "action_role": "{role}：{action}",
        "action_forecast": "围绕明日风险「{risk}」提前做准备。",
        "action_default": "下一班次先稳住优先提升环节周边的人手、衔接和设备节拍。",
        "stale_notice": "本轮本地 AI 总结未及时完成，当前结果以系统深分析为主。",
    }


def _safe_str(value: Any, default: str = "") -> str:
    text = str(value or "").strip()
    return text or default


def _build_system_deep_monitor_answer(context: dict[str, Any], lang: str, trigger: str) -> dict[str, Any]:
    lp = _system_lang_pack(lang)
    intelligence = context.get("intelligence", {}) if isinstance(context.get("intelligence"), dict) else {}
    hr = context.get("hr", {}) if isinstance(context.get("hr"), dict) else {}
    finance = context.get("finance", {}) if isinstance(context.get("finance"), dict) else {}
    forecast = context.get("forecast", {}) if isinstance(context.get("forecast"), dict) else {}
    equipment_quality = context.get("equipment_quality", {}) if isinstance(context.get("equipment_quality"), dict) else {}
    role_collaboration = context.get("role_collaboration", {}) if isinstance(context.get("role_collaboration"), dict) else {}
    template_payload = context.get("template_payload", {}) if isinstance(context.get("template_payload"), dict) else {}
    capacity_gap = template_payload.get("capacity_gap", {}) if isinstance(template_payload.get("capacity_gap"), dict) else {}
    band_gap = capacity_gap.get("band_saw", {}) if isinstance(capacity_gap.get("band_saw"), dict) else {}
    secondary_gap = capacity_gap.get("secondary_finish", {}) if isinstance(capacity_gap.get("secondary_finish"), dict) else {}

    priority = _safe_str(((intelligence.get("priority_stage") or {}) if isinstance(intelligence.get("priority_stage"), dict) else {}).get("name"), "未明确")
    pressure = _safe_str(((intelligence.get("pressure_stage") or {}) if isinstance(intelligence.get("pressure_stage"), dict) else {}).get("name"), priority)

    saw_streak = int(band_gap.get("under_target_streak_days", 0) or 0)
    secondary_streak = int(secondary_gap.get("under_target_streak_days", 0) or 0)
    repeated_issue = saw_streak >= 2 or secondary_streak >= 2

    summary = lp["summary_streak" if repeated_issue else "summary"].format(priority=priority, pressure=pressure)

    focus = [
        lp["focus_priority"].format(priority=priority),
        lp["focus_pressure"].format(pressure=pressure),
    ]
    if repeated_issue:
        focus.append(lp["focus_streak"])

    risks: list[str] = []
    if saw_streak >= 2:
        risks.append(lp["risk_streak_saw"].format(days=saw_streak))
    if secondary_streak >= 2:
        risks.append(lp["risk_streak_secondary"].format(days=secondary_streak))
    top_risk = _safe_str(forecast.get("top_risk"))
    if top_risk:
        risks.append(lp["risk_forecast"].format(risk=top_risk))
    for item in (equipment_quality.get("risks") or [])[:3]:
        risk_text = _safe_str(item)
        if risk_text:
            risks.append(lp["risk_equipment"].format(risk=risk_text))
    seen_risks = []
    risks = [r for r in risks if not (r in seen_risks or seen_risks.append(r))]
    risks = risks[:3]

    actions: list[str] = []
    for row in (role_collaboration.get("rows") or [])[:4]:
        if not isinstance(row, dict):
            continue
        role_name = _safe_str(row.get("role"))
        action = _safe_str(row.get("action"))
        if role_name and action:
            actions.append(lp["action_role"].format(role=role_name, action=action))
    if top_risk:
        actions.append(lp["action_forecast"].format(risk=top_risk))
    if not actions:
        actions.append(lp["action_default"])
    actions = actions[:3]

    absent_count = int(hr.get("absent_today_count", 0) or 0)
    net_today = float(finance.get("net_today", 0.0) or 0.0)
    modules = {
        "production": lp["production_gap"].format(priority=priority, pressure=pressure) if repeated_issue or risks else lp["production_ok"],
        "hr": lp["hr_absent"].format(count=absent_count) if absent_count > 0 else lp["hr_ok"],
        "finance": lp["finance_tight"].format(net=net_today) if net_today < 0 else lp["finance_ok"],
    }

    return {
        "summary": summary,
        "focus": focus[:3],
        "risks": risks[:3],
        "actions": actions[:3],
        "modules": modules,
        "template_version": "deep_monitor_v3",
        "analysis_mode": "system_deep_analysis",
        "source": "system",
        "lang": lang,
        "trigger": trigger,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "generated_ts": _now_ts(),
    }


def _build_ai_summary_prompt(system_answer: dict[str, Any], context: dict[str, Any], trigger: str, lang: str) -> tuple[str, str]:
    payload = {
        "trigger": trigger,
        "system_answer": {
            "summary": system_answer.get("summary"),
            "focus": system_answer.get("focus"),
            "risks": system_answer.get("risks"),
            "actions": system_answer.get("actions"),
            "modules": system_answer.get("modules"),
        },
        "forecast": {
            "summary": ((context.get("forecast") or {}) if isinstance(context.get("forecast"), dict) else {}).get("summary"),
            "top_risk": ((context.get("forecast") or {}) if isinstance(context.get("forecast"), dict) else {}).get("top_risk"),
        },
        "equipment_quality": {
            "summary": ((context.get("equipment_quality") or {}) if isinstance(context.get("equipment_quality"), dict) else {}).get("summary"),
        },
    }
    prompt = (
        "下面是 AIF 系统先算好的深分析结果。"
        "请你只做最后一层综合表达，不要推翻系统结论，不要新增无根据数字。"
        "你可以压缩句子、调整顺序，让它更像老板摘要。"
        "只输出 JSON，不要加解释文字。"
        "{"
        "\"summary\":\"一句更顺的总判断\","
        "\"focus\":[\"重点1\",\"重点2\"],"
        "\"risks\":[\"风险1\",\"风险2\"],"
        "\"actions\":[\"动作1\",\"动作2\"],"
        "\"modules\":{\"production\":\"一句判断\",\"hr\":\"一句判断\",\"finance\":\"一句判断\"}"
        "}"
        f"\n输入数据: {json.dumps(payload, ensure_ascii=False, separators=(',', ':'))}"
    )
    system_prompt = (
        "你是 AIF 的管理摘要 AI。"
        "系统已经先完成深分析，你只负责把结论整理得更自然、更短、更可执行。"
        "必须输出严格 JSON。"
    )
    return prompt, system_prompt


def build_ai_monitor_template_payload(lang: str = "zh", trigger: str = "") -> dict[str, Any]:
    context, _ = _build_monitor_context(lang)
    payload = dict(context.get("template_payload") or {})
    frame = payload.get("monitor_frame", {}) if isinstance(payload.get("monitor_frame"), dict) else {}
    frame["trigger"] = str(trigger or "")
    payload["monitor_frame"] = frame
    return payload


def build_ai_monitor_template_text(lang: str = "zh", trigger: str = "") -> str:
    payload = build_ai_monitor_template_payload(lang=lang, trigger=trigger)
    production = payload.get("production_core_signals", {}) if isinstance(payload.get("production_core_signals"), dict) else {}
    hr = payload.get("hr_core_signals", {}) if isinstance(payload.get("hr_core_signals"), dict) else {}
    finance = payload.get("finance_core_signals", {}) if isinstance(payload.get("finance_core_signals"), dict) else {}
    forecast = payload.get("forecast_core_signals", {}) if isinstance(payload.get("forecast_core_signals"), dict) else {}
    traceability = payload.get("traceability_core_signals", {}) if isinstance(payload.get("traceability_core_signals"), dict) else {}
    equipment_quality = payload.get("equipment_quality_signals", {}) if isinstance(payload.get("equipment_quality_signals"), dict) else {}
    role_collaboration = payload.get("role_collaboration_signals", {}) if isinstance(payload.get("role_collaboration_signals"), dict) else {}
    band_gap = (payload.get("capacity_gap", {}) or {}).get("band_saw", {}) if isinstance(payload.get("capacity_gap"), dict) else {}
    secondary_gap = (payload.get("capacity_gap", {}) or {}).get("secondary_finish", {}) if isinstance(payload.get("capacity_gap"), dict) else {}
    compact_payload = {
        "language": payload.get("language"),
        "template_version": payload.get("template_version"),
        "monitor_frame": {
            "goal": ((payload.get("monitor_frame") or {}) if isinstance(payload.get("monitor_frame"), dict) else {}).get("goal"),
            "trigger": trigger,
        },
        "production_core_signals": {
            "brief": production.get("brief"),
            "stage_scores": (production.get("stage_scores") or [])[:3],
            "efficiency_current": {
                "raw_security": ((production.get("efficiency_current") or {}) if isinstance(production.get("efficiency_current"), dict) else {}).get("raw_security"),
                "front_balance": ((production.get("efficiency_current") or {}) if isinstance(production.get("efficiency_current"), dict) else {}).get("front_balance"),
                "middle_flow": ((production.get("efficiency_current") or {}) if isinstance(production.get("efficiency_current"), dict) else {}).get("middle_flow"),
                "backlog_health": ((production.get("efficiency_current") or {}) if isinstance(production.get("efficiency_current"), dict) else {}).get("backlog_health"),
                "product_health": ((production.get("efficiency_current") or {}) if isinstance(production.get("efficiency_current"), dict) else {}).get("product_health"),
                "kiln_health": ((production.get("efficiency_current") or {}) if isinstance(production.get("efficiency_current"), dict) else {}).get("kiln_health"),
            },
            "throughput_current_day": {
                "saw_trays": ((production.get("throughput_current_day") or {}) if isinstance(production.get("throughput_current_day"), dict) else {}).get("saw_trays"),
                "sort_trays": ((production.get("throughput_current_day") or {}) if isinstance(production.get("throughput_current_day"), dict) else {}).get("sort_trays"),
                "secondary_trays": ((production.get("throughput_current_day") or {}) if isinstance(production.get("throughput_current_day"), dict) else {}).get("secondary_trays"),
                "product_m3": ((production.get("throughput_current_day") or {}) if isinstance(production.get("throughput_current_day"), dict) else {}).get("product_m3"),
                "ratio_sort_vs_dip": ((production.get("throughput_current_day") or {}) if isinstance(production.get("throughput_current_day"), dict) else {}).get("ratio_sort_vs_dip"),
                "ratio_secondary_vs_sort": ((production.get("throughput_current_day") or {}) if isinstance(production.get("throughput_current_day"), dict) else {}).get("ratio_secondary_vs_sort"),
                "ratio_product_vs_secondary": ((production.get("throughput_current_day") or {}) if isinstance(production.get("throughput_current_day"), dict) else {}).get("ratio_product_vs_secondary"),
            },
            "inventory_snapshot": production.get("inventory_snapshot"),
            "kiln_summary": production.get("kiln_summary"),
        },
        "hr_core_signals": {
            "employee_total": hr.get("employee_total"),
            "employee_active": hr.get("employee_active"),
            "absent_today_count": hr.get("absent_today_count"),
            "on_duty_count": hr.get("on_duty_count"),
            "leave_related_count": hr.get("leave_related_count"),
            "saw_operation_stats": {
                "configured_machine_count": ((hr.get("saw_operation_stats") or {}) if isinstance(hr.get("saw_operation_stats"), dict) else {}).get("configured_machine_count"),
                "running_machine_count": ((hr.get("saw_operation_stats") or {}) if isinstance(hr.get("saw_operation_stats"), dict) else {}).get("running_machine_count"),
                "likely_reason": ((hr.get("saw_operation_stats") or {}) if isinstance(hr.get("saw_operation_stats"), dict) else {}).get("likely_reason"),
            },
            "workforce_pressure_hints": (hr.get("workforce_pressure_hints") or [])[:3],
        },
        "finance_core_signals": finance,
        "forecast_core_signals": {
            "summary": forecast.get("summary"),
            "top_risk": forecast.get("top_risk"),
            "risk_drivers": (forecast.get("risk_drivers") or [])[:4],
            "predictions": forecast.get("predictions"),
            "calibration": forecast.get("calibration"),
        },
        "traceability_core_signals": {
            "summary": (traceability.get("summary") or {}),
            "events": [
                {
                    "time": item.get("created_at"),
                    "stage": item.get("stage_label"),
                    "action": item.get("action"),
                    "target": item.get("target"),
                }
                for item in (traceability.get("events") or [])[:5]
                if isinstance(item, dict)
            ],
        },
        "equipment_quality_signals": {
            "summary": equipment_quality.get("summary"),
            "metrics": equipment_quality.get("metrics"),
            "risks": (equipment_quality.get("risks") or [])[:4],
        },
        "role_collaboration_signals": {
            "summary": role_collaboration.get("summary"),
            "rows": [
                {
                    "role": item.get("role"),
                    "summary": item.get("summary"),
                    "action": item.get("action"),
                }
                for item in (role_collaboration.get("rows") or [])[:5]
                if isinstance(item, dict)
            ],
        },
        "capacity_gap": {
            "band_saw": {
                "target_daily_trays": band_gap.get("target_daily_trays"),
                "actual_daily_trays": band_gap.get("actual_daily_trays"),
                "gap_trays": band_gap.get("gap_trays"),
                "gap_reason": band_gap.get("gap_reason"),
                "under_target_streak_days": band_gap.get("under_target_streak_days"),
            },
            "secondary_finish": {
                "target_daily_finished_pcs": secondary_gap.get("target_daily_finished_pcs"),
                "actual_daily_finished_pcs": secondary_gap.get("actual_daily_finished_pcs"),
                "gap_pcs": secondary_gap.get("gap_pcs"),
                "gap_reason": secondary_gap.get("gap_reason"),
                "under_target_streak_days": secondary_gap.get("under_target_streak_days"),
            },
        },
        "current_priority_stage": payload.get("current_priority_stage"),
        "current_pressure_stage": payload.get("current_pressure_stage"),
    }
    return json.dumps(compact_payload, ensure_ascii=False, separators=(",", ":"))


def _compose_deep_monitor_answer(parsed: dict, lang: str, trigger: str) -> dict[str, Any]:
    data = parsed if isinstance(parsed, dict) else {}
    summary = str(data.get("summary") or "").strip()
    focus = [str(x or "").strip() for x in (data.get("focus") or []) if str(x or "").strip()]
    risks = [str(x or "").strip() for x in (data.get("risks") or []) if str(x or "").strip()]
    actions = [str(x or "").strip() for x in (data.get("actions") or []) if str(x or "").strip()]
    modules = data.get("modules", {}) if isinstance(data.get("modules"), dict) else {}
    return {
        "summary": summary,
        "focus": focus[:3],
        "risks": risks[:3],
        "actions": actions[:3],
        "modules": modules,
        "template_version": "deep_monitor_v2",
        "lang": lang,
        "trigger": trigger,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "generated_ts": _now_ts(),
    }


def _ask_deep_monitor_ai(lang: str, context_text: str, trigger: str) -> dict[str, Any]:
    prompt = (
        "下面是 AIF 的深巡检固定输入模板。\n"
        "模板版本是 deep_monitor_v2，包含 production_core_signals、hr_core_signals、finance_core_signals 三个独立模块。\n"
        "这只是结构化事实，不代表结论。\n"
        "你不是聊天助手，而是系统级监测 AI。\n"
        "你必须基于这些事实自己判断，不要把 current_priority_stage 或 current_pressure_stage 直接原样复读成答案，除非证据确实支持。\n"
        "请做跨生产、HR、财务的综合判断，找出最该盯的 2 到 3 个提升重点。\n"
        "输出务必短、直接、可执行，不要写长解释。\n"
        "只输出 JSON，不要加解释文字。\n"
        "{"
        "\"summary\":\"一句总判断\","
        "\"focus\":[\"重点1\",\"重点2\"],"
        "\"risks\":[\"风险1\",\"风险2\"],"
        "\"actions\":[\"动作1\",\"动作2\"],"
        "\"modules\":{"
        "\"production\":\"一句判断\","
        "\"hr\":\"一句判断\","
        "\"finance\":\"一句判断\""
        "}"
        "}\n\n"
        f"触发方式: {trigger}\n"
        f"输入模板: {context_text}\n"
        "要求："
        "summary 要像老板摘要；"
        "focus/risks/actions 都要可执行而且短；"
        "优先围绕提升产能、保障连续生产、跨模块协同来写；"
        "如果某个模块没明显风险，就写“当前平稳”；"
        "如果 current_priority_stage 与 current_pressure_stage 不一致，要结合 production_core_signals 自己判断是症状和原因不同，还是事实已经变化。"
    )
    system_prompt = (
        "你是 AIF 系统级监测 AI。"
        "你负责跨生产、HR、财务做阶段性深度巡检。"
        "必须基于事实，输出严格 JSON。"
    )
    raw = ask_ai(prompt, system_prompt=system_prompt, max_tokens=260, timeout=DEEP_MONITOR_AI_TIMEOUT)
    try:
        return json.loads(raw)
    except Exception:
        try:
            return json.loads(_extract_first_json_object(raw))
        except Exception:
            pass
        raise


def run_deep_monitor_once(trigger: str = "manual", lang: str = "zh") -> dict[str, Any]:
    context, context_text = _build_monitor_context(lang)
    current_db_mtime = _get_db_mtime()
    answer = _build_system_deep_monitor_answer(context, lang=lang, trigger=trigger)
    ai_error = ""
    try:
        prompt, system_prompt = _build_ai_summary_prompt(answer, context, trigger=trigger, lang=lang)
        raw = ask_ai(prompt, system_prompt=system_prompt, max_tokens=220, timeout=DEEP_MONITOR_AI_SUMMARY_TIMEOUT)
        try:
            parsed = json.loads(raw)
        except Exception:
            parsed = json.loads(_extract_first_json_object(raw))
        ai_answer = _compose_deep_monitor_answer(parsed, lang=lang, trigger=trigger)
        if str(ai_answer.get("summary") or "").strip():
            answer["summary"] = ai_answer["summary"]
        if isinstance(ai_answer.get("focus"), list) and ai_answer["focus"]:
            answer["focus"] = ai_answer["focus"][:3]
        if isinstance(ai_answer.get("risks"), list) and ai_answer["risks"]:
            answer["risks"] = ai_answer["risks"][:3]
        if isinstance(ai_answer.get("actions"), list) and ai_answer["actions"]:
            answer["actions"] = ai_answer["actions"][:3]
        if isinstance(ai_answer.get("modules"), dict) and ai_answer["modules"]:
            answer["modules"] = ai_answer["modules"]
        answer["source"] = "system+ai"
        answer["analysis_mode"] = "system_deep_analysis_ai_summary"
    except Exception as exc:
        ai_error = str(exc)
        answer["source"] = "system"
        answer["analysis_mode"] = "system_deep_analysis"
        answer["ai_note"] = _system_lang_pack(lang)["stale_notice"]
        answer["ai_error"] = ai_error
    answer["context_overview"] = {
        "production": (context.get("intelligence") or {}).get("brief", ""),
        "hr_absent_today": (context.get("hr") or {}).get("absent_today_count", 0),
        "finance_net_today": (context.get("finance") or {}).get("net_today", 0.0),
        "forecast_summary": (context.get("forecast") or {}).get("summary", ""),
        "equipment_quality_summary": (context.get("equipment_quality") or {}).get("summary", ""),
        "role_collaboration_summary": (context.get("role_collaboration") or {}).get("summary", ""),
    }

    doc = _cached_doc()
    by_lang = doc.get("by_lang", {}) if isinstance(doc.get("by_lang"), dict) else {}
    by_lang[lang] = answer
    doc["by_lang"] = by_lang
    if not str(answer.get("error") or "").strip():
        success_by_lang = doc.get("success_by_lang", {}) if isinstance(doc.get("success_by_lang"), dict) else {}
        success_by_lang[lang] = dict(answer)
        doc["success_by_lang"] = success_by_lang
    meta = doc.get("meta", {}) if isinstance(doc.get("meta"), dict) else {}
    meta["last_trigger"] = trigger
    meta["last_lang"] = lang
    meta["last_generated_ts"] = answer["generated_ts"]
    meta["last_result_ok"] = 1
    meta["last_success_ts"] = answer["generated_ts"]
    meta["last_error"] = ""
    meta["last_error_trigger"] = ""
    if ai_error:
        meta["last_ai_error"] = ai_error
        meta["last_ai_error_ts"] = answer["generated_ts"]
    else:
        meta["last_ai_error"] = ""
        meta["last_ai_error_ts"] = 0
    if current_db_mtime:
        meta["last_monitor_db_mtime"] = current_db_mtime
    _clear_deferred_db_trigger(meta)
    doc["meta"] = meta
    _save_cached_doc(doc)
    return answer


def queue_deep_monitor(trigger: str = "manual", lang: str = "zh", force: bool = False) -> bool:
    now_ts = time.time()
    cfg = _monitor_cfg()
    with RUN_LOCK:
        if RUN_STATE["running"]:
            return False
        if not force and (now_ts - float(RUN_STATE.get("last_started_ts") or 0.0)) < int(cfg["min_gap_seconds"]):
            return False
        RUN_STATE["running"] = True
        RUN_STATE["last_started_ts"] = now_ts

    def _runner():
        try:
            run_deep_monitor_once(trigger=trigger, lang=lang)
        finally:
            with RUN_LOCK:
                RUN_STATE["running"] = False

    thread = threading.Thread(target=_runner, daemon=True, name=f"aif-deep-monitor-{lang}")
    thread.start()
    return True


def _reserve_deferred_db_trigger(meta: dict[str, Any], current_mtime: float, now_ts: int) -> bool:
    pending_mtime = float(meta.get("pending_db_mtime") or 0.0)
    pending_deadline_ts = int(meta.get("pending_db_deadline_ts") or 0)
    last_monitor_db_mtime = float(meta.get("last_monitor_db_mtime") or 0.0)
    if not current_mtime or current_mtime == last_monitor_db_mtime:
        return False
    if current_mtime != pending_mtime:
        meta["pending_db_mtime"] = current_mtime
        meta["pending_db_deadline_ts"] = now_ts + DB_CHANGE_SETTLE_SECONDS
        return True
    if not pending_deadline_ts:
        meta["pending_db_deadline_ts"] = now_ts + DB_CHANGE_SETTLE_SECONDS
        return True
    return False


def _clear_deferred_db_trigger(meta: dict[str, Any]) -> None:
    meta.pop("pending_db_mtime", None)
    meta.pop("pending_db_deadline_ts", None)


def maybe_schedule_deep_monitor(now_dt: datetime | None = None, lang: str = "zh") -> bool:
    dt = now_dt or datetime.now()
    now_ts = int(dt.timestamp())
    cfg = _monitor_cfg()
    if not _in_monitor_window(dt):
        return False
    doc = _cached_doc()
    meta = doc.get("meta", {}) if isinstance(doc.get("meta"), dict) else {}
    last_generated_ts = int(meta.get("last_success_ts") or meta.get("last_generated_ts") or 0)

    if (now_ts - last_generated_ts) < int(cfg["idle_monitor_seconds"]):
        return False

    queued = queue_deep_monitor(trigger="idle-3h", lang=lang, force=True)
    if queued:
        _clear_deferred_db_trigger(meta)
        doc["meta"] = meta
        _save_cached_doc(doc)
    return queued


def maybe_trigger_deep_monitor_by_db(lang: str = "zh") -> bool:
    now_ts = _now_ts()
    now_dt = datetime.now()
    cfg = _monitor_cfg()
    current_mtime = _get_db_mtime()
    if not current_mtime:
        return False

    doc = _cached_doc()
    meta = doc.get("meta", {}) if isinstance(doc.get("meta"), dict) else {}
    last_generated_ts = int(meta.get("last_success_ts") or meta.get("last_generated_ts") or 0)
    last_monitor_db_mtime = float(meta.get("last_monitor_db_mtime") or 0.0)
    pending_mtime = float(meta.get("pending_db_mtime") or 0.0)
    pending_deadline_ts = int(meta.get("pending_db_deadline_ts") or 0)
    in_window = _in_monitor_window(now_dt)

    # 仅在设定时间段内执行深巡检。
    if in_window and (now_ts - last_generated_ts) >= int(cfg["idle_monitor_seconds"]):
        queued = queue_deep_monitor(trigger="idle-3h", lang=lang, force=True)
        if queued:
            _clear_deferred_db_trigger(meta)
            doc["meta"] = meta
            _save_cached_doc(doc)
        return queued

    changed = current_mtime != last_monitor_db_mtime
    mutated = _reserve_deferred_db_trigger(meta, current_mtime, now_ts)
    if mutated:
        doc["meta"] = meta
        _save_cached_doc(doc)

    # 非巡检时间段只记录变化，不执行深巡检。
    if not in_window:
        return False

    # 没有待重试/待触发窗口时，先不巡检。
    if not pending_mtime or not pending_deadline_ts:
        return False

    # 等待窗口未到，持续合并后续更新。
    if now_ts < pending_deadline_ts:
        return False

    # 数据库在等待期内再次变化，重新顺延一轮。
    if current_mtime != pending_mtime:
        if _reserve_deferred_db_trigger(meta, current_mtime, now_ts):
            doc["meta"] = meta
            _save_cached_doc(doc)
        return False

    queued = queue_deep_monitor(trigger="db-change-settled", lang=lang, force=False)
    if queued:
        _clear_deferred_db_trigger(meta)
        doc["meta"] = meta
        _save_cached_doc(doc)
    return queued
