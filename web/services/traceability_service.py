from __future__ import annotations

import re
from collections import Counter
from datetime import datetime

from web.models import AdminAuditLog, Session


_ACTION_STAGE = {
    "submit_log_entry": "raw_log",
    "submit_saw": "saw",
    "submit_dip": "dip",
    "submit_sort": "sort",
    "kiln_action": "kiln",
    "adjust_kiln": "kiln",
    "submit_secondary_sort": "secondary_sort",
    "submit_secondary_products": "finished",
    "create_shipping_order": "shipping",
    "create_shipping_order_manual": "shipping",
    "update_shipping_status": "shipping",
    "finance_action": "finance",
    "payroll_post_to_finance": "finance",
    "add_hr_employee": "hr",
    "update_hr_employee": "hr",
    "update_hr_employee_status": "hr",
    "add_hr_attendance_batch": "hr",
}


_I18N = {
    "zh": {
        "title": "事件追溯",
        "subtitle": "把原木、生产、物流、财务、人事放到同一条事件链里。",
        "all_stages": "全部环节",
        "all_actions": "全部动作",
        "summary": "追溯摘要",
        "recent_events": "最近事件",
        "trace_result": "追溯结果",
        "query": "追溯关键词",
        "query_hint": "车牌 / 批次号 / 产品号 / 窑号 / 物流单 / 人名",
        "event_total": "事件总数",
        "stage_total": "覆盖环节",
        "top_stage": "最活跃环节",
        "latest_time": "最近时间",
        "time": "时间",
        "stage": "环节",
        "action": "动作",
        "target": "目标",
        "detail": "详情",
        "refs": "追溯锚点",
        "empty": "暂无可追溯事件",
        "lookup_empty": "没有找到相关追溯结果",
        "stage_raw_log": "原木",
        "stage_saw": "锯解",
        "stage_dip": "药浸",
        "stage_sort": "拣选",
        "stage_kiln": "窑",
        "stage_secondary_sort": "二选",
        "stage_finished": "成品",
        "stage_shipping": "物流",
        "stage_finance": "财务",
        "stage_hr": "人事",
        "stage_other": "其他",
    },
    "en": {
        "title": "Traceability",
        "subtitle": "Link logs, production, shipping, finance, and HR into one event chain.",
        "all_stages": "All Stages",
        "all_actions": "All Actions",
        "summary": "Trace Summary",
        "recent_events": "Recent Events",
        "trace_result": "Trace Result",
        "query": "Trace Query",
        "query_hint": "truck / batch / product / kiln / shipment / name",
        "event_total": "Events",
        "stage_total": "Stages",
        "top_stage": "Top Stage",
        "latest_time": "Latest Time",
        "time": "Time",
        "stage": "Stage",
        "action": "Action",
        "target": "Target",
        "detail": "Detail",
        "refs": "Anchors",
        "empty": "No trace events yet",
        "lookup_empty": "No matching trace result",
        "stage_raw_log": "Raw Log",
        "stage_saw": "Sawing",
        "stage_dip": "Dipping",
        "stage_sort": "Sorting",
        "stage_kiln": "Kiln",
        "stage_secondary_sort": "Secondary",
        "stage_finished": "Finished",
        "stage_shipping": "Shipping",
        "stage_finance": "Finance",
        "stage_hr": "HR",
        "stage_other": "Other",
    },
    "my": {
        "title": "ဖြစ်စဉ်နောက်ကြောင်း",
        "subtitle": "ထင်းဝင်၊ ထုတ်လုပ်မှု၊ ပို့ဆောင်ရေး၊ ငွေကြေး၊ လူမှုရေးကို အဖြစ်အပျက်တစ်ကြောင်းတည်းနဲ့ ချိတ်ဆက်ပြသပါသည်။",
        "all_stages": "အဆင့်အားလုံး",
        "all_actions": "လုပ်ဆောင်ချက်အားလုံး",
        "summary": "နောက်ကြောင်းအကျဉ်း",
        "recent_events": "နောက်ဆုံးဖြစ်စဉ်များ",
        "trace_result": "နောက်ကြောင်းရလဒ်",
        "query": "ရှာဖွေရန်စကားလုံး",
        "query_hint": "ကားနံပါတ် / batch / product / kiln / shipment / အမည်",
        "event_total": "ဖြစ်စဉ်စုစုပေါင်း",
        "stage_total": "အဆင့်အရေအတွက်",
        "top_stage": "အများဆုံးအဆင့်",
        "latest_time": "နောက်ဆုံးအချိန်",
        "time": "အချိန်",
        "stage": "အဆင့်",
        "action": "လုပ်ဆောင်ချက်",
        "target": "ဦးတည်ချက်",
        "detail": "အသေးစိတ်",
        "refs": "ဆက်စပ်အမှတ်များ",
        "empty": "နောက်ကြောင်းဖြစ်စဉ် မရှိသေးပါ",
        "lookup_empty": "ကိုက်ညီသော နောက်ကြောင်း မတွေ့ပါ",
        "stage_raw_log": "ထင်းဝင်",
        "stage_saw": "လွှဖြတ်",
        "stage_dip": "ဆေးစိမ်",
        "stage_sort": "ရွေးချယ်",
        "stage_kiln": "မီးဖို",
        "stage_secondary_sort": "ဒုတိယရွေး",
        "stage_finished": "ကုန်ချော",
        "stage_shipping": "ပို့ဆောင်ရေး",
        "stage_finance": "ငွေကြေး",
        "stage_hr": "ဝန်ထမ်း",
        "stage_other": "အခြား",
    },
}


def _lp(lang: str) -> dict:
    return _I18N.get(lang, _I18N["zh"])


def _safe_int(raw, default=0) -> int:
    try:
        if raw in (None, ""):
            return int(default)
        return int(float(raw))
    except Exception:
        return int(default)


def _parse_detail(detail: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for part in [p.strip() for p in str(detail or "").split(",") if p.strip()]:
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        out[str(key or "").strip()] = str(value or "").strip()
    return out


def _stage_key(action: str) -> str:
    return _ACTION_STAGE.get(str(action or "").strip(), "other")


def _stage_label(stage_key: str, lang: str) -> str:
    return _lp(lang).get(f"stage_{stage_key}", _lp(lang)["stage_other"])


def _collect_refs(action: str, target: str, detail: str) -> list[str]:
    refs: list[str] = []
    action = str(action or "").strip()
    target = str(target or "").strip()
    detail_map = _parse_detail(detail)

    candidates = [target]
    for key in ("driver", "customer", "vehicle", "status", "kiln_id", "truck_number", "batch_number", "shipment_no"):
        value = str(detail_map.get(key, "") or "").strip()
        if value:
            candidates.append(value)
    if target.startswith("log_entry:"):
        candidates.append(target.split(":", 1)[-1].strip())
    if target.startswith("kiln_"):
        candidates.append(target.replace("kiln_", "").strip())
    if re.fullmatch(r"[A-Z]{2}\d{11}", target):
        candidates.append(target)
    if re.fullmatch(r"CP\d+", target, re.I):
        candidates.append(target)
    for item in candidates:
        item = str(item or "").strip()
        if not item or item in refs:
            continue
        refs.append(item)
    return refs[:5]


def _event_to_dict(row, lang: str) -> dict:
    action = str(getattr(row, "action", "") or "").strip()
    target = str(getattr(row, "target", "") or "").strip()
    detail = str(getattr(row, "detail", "") or "").strip()
    stage_key = _stage_key(action)
    return {
        "id": _safe_int(getattr(row, "id", 0), 0),
        "created_at": str(getattr(row, "created_at", "") or "").replace("T", " ")[:19],
        "operator": str(getattr(row, "operator", "") or "").strip(),
        "action": action,
        "target": target,
        "detail": detail,
        "stage_key": stage_key,
        "stage_label": _stage_label(stage_key, lang),
        "refs": _collect_refs(action, target, detail),
    }


def _query_rows(keyword: str = "", action: str = "", day: str = "", limit: int = 80):
    session = Session()
    try:
        q = session.query(AdminAuditLog)
        if action:
            q = q.filter(AdminAuditLog.action == action)
        if day:
            q = q.filter(AdminAuditLog.created_at.like(f"{day}%"))
        if keyword:
            q = q.filter(
                (AdminAuditLog.target.like(f"%{keyword}%"))
                | (AdminAuditLog.detail.like(f"%{keyword}%"))
                | (AdminAuditLog.operator.like(f"%{keyword}%"))
            )
        rows = q.order_by(AdminAuditLog.id.desc()).limit(max(1, min(limit, 300))).all()
        return rows
    finally:
        session.close()


def _build_summary(events: list[dict], lang: str) -> dict:
    stage_counter = Counter(e.get("stage_key", "other") for e in events)
    top_stage_key = stage_counter.most_common(1)[0][0] if stage_counter else "other"
    return {
        "event_total": len(events),
        "stage_total": len([k for k, v in stage_counter.items() if v > 0]),
        "top_stage": _stage_label(top_stage_key, lang) if events else "-",
        "latest_time": events[0]["created_at"] if events else "-",
    }


def build_traceability_snapshot(lang: str = "zh", day_text: str | None = None, limit: int = 12) -> dict:
    day = str(day_text or datetime.now().strftime("%Y-%m-%d")).strip()
    rows = _query_rows(day=day, limit=limit)
    events = [_event_to_dict(row, lang) for row in rows]
    return {
        "day": day,
        "summary": _build_summary(events, lang),
        "events": events[:8],
        "template": "traceability_v1",
    }


def build_traceability_lookup(keyword: str = "", lang: str = "zh", action: str = "", day: str = "", limit: int = 120) -> dict:
    rows = _query_rows(keyword=keyword, action=action, day=day, limit=limit)
    events = [_event_to_dict(row, lang) for row in rows]
    ref_counter = Counter()
    for event in events:
        for ref in event.get("refs", []):
            ref_counter[str(ref)] += 1
    return {
        "keyword": str(keyword or "").strip(),
        "action": str(action or "").strip(),
        "day": str(day or "").strip(),
        "summary": _build_summary(events, lang),
        "events": events,
        "hot_refs": [{"value": key, "count": count} for key, count in ref_counter.most_common(12)],
        "actions": sorted({str(e.get("action", "") or "").strip() for e in events if str(e.get("action", "") or "").strip()}),
        "template": "traceability_v1",
    }

