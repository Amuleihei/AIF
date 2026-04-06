import json
import os
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from modules.ai.ai_engine import ask_ai
from modules.finance.finance_engine import load as load_finance
from modules.hr.hr_engine import get_hr_employees_payload
from modules.storage.db_doc_store import load_doc, save_doc
from web.services.alert_center_service import get_alert_center_payload
from web.utils import get_stock_data


DOC_KEY = "ai_deep_monitor_v1"
RUN_STATE = {"running": False, "last_started_ts": 0.0}
RUN_LOCK = threading.Lock()
DEEP_MONITOR_INTERVAL_MIN = max(5, int(os.getenv("AIF_AI_DEEP_MONITOR_INTERVAL_MIN", "15") or "15"))
DEEP_MONITOR_SLOTS = [s.strip() for s in str(os.getenv("AIF_AI_DEEP_MONITOR_SLOTS", "08:00,12:00,18:00,21:00") or "").split(",") if s.strip()]
IDLE_MONITOR_SECONDS = 2 * 60 * 60


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


def get_cached_deep_monitor(lang: str = "zh") -> dict[str, Any]:
    doc = _cached_doc()
    by_lang = doc.get("by_lang", {}) if isinstance(doc.get("by_lang"), dict) else {}
    out = by_lang.get(lang) or by_lang.get("zh") or {}
    return out if isinstance(out, dict) else {}


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


def _build_monitor_context(lang: str = "zh") -> tuple[dict[str, Any], str]:
    stock = get_stock_data(lang)
    center = get_alert_center_payload(limit_recent=30, lang=lang)
    hr = _build_hr_snapshot()
    finance = _build_finance_snapshot()
    intelligence = center.get("factory_intelligence", {}) if isinstance(center, dict) else {}
    throughput = center.get("throughput", {}) if isinstance(center, dict) else {}
    efficiency = center.get("efficiency", {}) if isinstance(center, dict) else {}
    text = (
        f"语言: {lang}\n"
        f"生产概况: {json.dumps(intelligence, ensure_ascii=False)}\n"
        f"环节产比: {json.dumps((throughput or {}).get('current_day', {}), ensure_ascii=False)}\n"
        f"效率评分: {json.dumps((efficiency or {}).get('current', {}), ensure_ascii=False)}\n"
        f"库存快照: {json.dumps({'log_stock': stock.get('log_stock'), 'saw_stock': stock.get('saw_stock'), 'dip_stock': stock.get('dip_stock'), 'sorting_stock': stock.get('sorting_stock'), 'kiln_done_stock': stock.get('kiln_done_stock'), 'product_count': stock.get('product_count')}, ensure_ascii=False)}\n"
        f"窑状态: {json.dumps(stock.get('kiln_status', {}), ensure_ascii=False)}\n"
        f"HR快照: {json.dumps(hr, ensure_ascii=False)}\n"
        f"财务快照: {json.dumps(finance, ensure_ascii=False)}\n"
    )
    return {
        "stock": stock,
        "center": center,
        "hr": hr,
        "finance": finance,
        "intelligence": intelligence,
    }, text


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
        "lang": lang,
        "trigger": trigger,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "generated_ts": _now_ts(),
    }


def _ask_deep_monitor_ai(lang: str, context_text: str, trigger: str) -> dict[str, Any]:
    prompt = (
        "下面是 AIF 当前全站运行快照，包含生产、HR/考勤、财务。\n"
        "你不是聊天助手，而是系统级监测 AI。\n"
        "请基于事实做跨模块判断，找出最该盯的 3 个提升重点，不要复读所有数据。\n"
        "只输出 JSON，不要加解释文字。\n"
        "{"
        "\"summary\":\"一句总判断\","
        "\"focus\":[\"重点1\",\"重点2\",\"重点3\"],"
        "\"risks\":[\"风险1\",\"风险2\",\"风险3\"],"
        "\"actions\":[\"动作1\",\"动作2\",\"动作3\"],"
        "\"modules\":{"
        "\"production\":\"一句判断\","
        "\"hr\":\"一句判断\","
        "\"finance\":\"一句判断\""
        "}"
        "}\n\n"
        f"触发方式: {trigger}\n"
        f"{context_text}\n"
        "要求：summary 要像老板摘要；focus/risks/actions 都要可执行而且短；优先围绕提升产能、保障连续生产、跨模块协同来写；如果某个模块没明显风险，就写“当前平稳”。"
    )
    system_prompt = (
        "你是 AIF 系统级监测 AI。"
        "你负责跨生产、HR、财务做阶段性深度巡检。"
        "必须基于事实，输出严格 JSON。"
    )
    raw = ask_ai(prompt, system_prompt=system_prompt, max_tokens=420, timeout=95)
    try:
        return json.loads(raw)
    except Exception:
        start = raw.find("{")
        end = raw.rfind("}")
        if start >= 0 and end > start:
            return json.loads(raw[start : end + 1])
        raise


def run_deep_monitor_once(trigger: str = "manual", lang: str = "zh") -> dict[str, Any]:
    context, context_text = _build_monitor_context(lang)
    try:
        parsed = _ask_deep_monitor_ai(lang, context_text, trigger=trigger)
        answer = _compose_deep_monitor_answer(parsed, lang=lang, trigger=trigger)
    except Exception as exc:
        existing = get_cached_deep_monitor(lang)
        base_summary = str(((context.get("intelligence") or {}).get("brief")) or "当前系统已完成一轮基础判断。").strip()
        hr_absent = int((context.get("hr") or {}).get("absent_today_count", 0) or 0)
        finance_net = float((context.get("finance") or {}).get("net_today", 0.0) or 0.0)
        fallback_focus = [
            base_summary,
            f"HR 今日未出勤 {hr_absent} 人，需要确认是否影响班组排产。",
            f"财务今日净额 {finance_net:.2f} KS，建议结合收支记录看是否足够支撑当前提升重点。",
        ]
        fallback_risks = [
            f"生产侧：{base_summary}",
            f"HR 侧：今日未出勤 {hr_absent} 人。",
            f"财务侧：今日净额 {finance_net:.2f} KS。",
        ]
        fallback_actions = [
            "先按当前优先提升环节安排现场调度。",
            "再核对 HR 出勤与当班排产是否匹配。",
            "最后查看今日财务收支是否存在异常记录。",
        ]
        answer = existing if isinstance(existing, dict) and existing else {}
        answer = {
            **answer,
            "summary": str(answer.get("summary") or f"AI 深度监测本轮超时，先沿用系统快照判断。{base_summary}"),
            "focus": list(answer.get("focus") or fallback_focus),
            "risks": list(answer.get("risks") or fallback_risks),
            "actions": list(answer.get("actions") or fallback_actions),
            "modules": dict(answer.get("modules") or {}),
            "lang": lang,
            "trigger": f"{trigger}:timeout",
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "generated_ts": _now_ts(),
            "error": str(exc),
        }
    answer["context_overview"] = {
        "production": (context.get("intelligence") or {}).get("brief", ""),
        "hr_absent_today": (context.get("hr") or {}).get("absent_today_count", 0),
        "finance_net_today": (context.get("finance") or {}).get("net_today", 0.0),
    }

    doc = _cached_doc()
    by_lang = doc.get("by_lang", {}) if isinstance(doc.get("by_lang"), dict) else {}
    by_lang[lang] = answer
    doc["by_lang"] = by_lang
    meta = doc.get("meta", {}) if isinstance(doc.get("meta"), dict) else {}
    meta["last_trigger"] = trigger
    meta["last_lang"] = lang
    meta["last_generated_ts"] = answer["generated_ts"]
    db_path = Path(__file__).resolve().parents[2] / "unified.db"
    try:
        meta["last_monitor_db_mtime"] = round(db_path.stat().st_mtime, 6)
    except Exception:
        pass
    doc["meta"] = meta
    _save_cached_doc(doc)
    return answer


def queue_deep_monitor(trigger: str = "manual", lang: str = "zh", force: bool = False) -> bool:
    now_ts = time.time()
    with RUN_LOCK:
        if RUN_STATE["running"]:
            return False
        if not force and (now_ts - float(RUN_STATE.get("last_started_ts") or 0.0)) < (DEEP_MONITOR_INTERVAL_MIN * 60):
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


def maybe_schedule_deep_monitor(now_dt: datetime | None = None, lang: str = "zh") -> bool:
    dt = now_dt or datetime.now()
    slot = dt.strftime("%H:%M")
    if slot not in DEEP_MONITOR_SLOTS:
        return False
    doc = _cached_doc()
    meta = doc.get("meta", {}) if isinstance(doc.get("meta"), dict) else {}
    slot_marks = meta.get("slot_marks", {}) if isinstance(meta.get("slot_marks"), dict) else {}
    slot_key = f"{_today_slot_key(dt)} {slot}"
    if slot_marks.get(slot_key):
        return False
    queued = queue_deep_monitor(trigger=f"schedule:{slot}", lang=lang, force=True)
    if queued:
        slot_marks[slot_key] = 1
        meta["slot_marks"] = slot_marks
        doc["meta"] = meta
        _save_cached_doc(doc)
    return queued


def maybe_trigger_deep_monitor_by_db(lang: str = "zh") -> bool:
    db_path = Path(__file__).resolve().parents[2] / "unified.db"
    try:
        current_mtime = round(db_path.stat().st_mtime, 6)
    except Exception:
        return False

    doc = _cached_doc()
    meta = doc.get("meta", {}) if isinstance(doc.get("meta"), dict) else {}
    last_generated_ts = int(meta.get("last_generated_ts") or 0)
    last_seen_business_db_mtime = float(meta.get("last_seen_business_db_mtime") or 0.0)
    last_monitor_db_mtime = float(meta.get("last_monitor_db_mtime") or 0.0)

    if current_mtime and current_mtime != last_monitor_db_mtime and current_mtime != last_seen_business_db_mtime:
        queued = queue_deep_monitor(trigger="db-change", lang=lang, force=True)
        if queued:
            meta["last_seen_business_db_mtime"] = current_mtime
            doc["meta"] = meta
            _save_cached_doc(doc)
        return queued

    now_ts = _now_ts()
    if (now_ts - last_generated_ts) >= IDLE_MONITOR_SECONDS:
        return queue_deep_monitor(trigger="idle-2h", lang=lang, force=True)

    return False
