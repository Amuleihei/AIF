import json
import os
import time
import secrets
import hashlib
from bisect import bisect_right
from datetime import datetime, timedelta
from urllib import request as urllib_request

from modules.ai.ai_engine import ask_ai
from tg_bot.config import get_bot_token
from web.i18n import LANGUAGES
from web.data_store import get_flow_data, get_kilns_data, get_log_stock_total, get_product_stats, get_shipping_data
from web.models import (
    Session,
    TgSetting,
    TgUserRole,
    SawRecord,
    DipRecord,
    SortRecord,
    ProductBatch,
    FlowSecondSortRecord,
    FlowSelectedTray,
    FlowSelectedTrayDetail,
)
from web.services.factory_intelligence_service import build_factory_intelligence
from web.services.traceability_service import build_traceability_snapshot


ALERT_EVENTS_KEY = "alert_engine_events_v1"
ALERT_HISTORY_KEY = "alert_engine_stock_history_v1"
ALERT_STATE_KEY = "alert_engine_state_v1"
ALERT_ENGINE_CFG_KEY = "alert_engine_config_v1"
ALERT_THRESHOLD_VERSIONS_KEY = "alert_threshold_versions_v1"
ALERT_AI_THROUGHPUT_CACHE_KEY = "alert_engine_ai_throughput_v1"
_EFFICIENCY_MEMORY_CACHE = {"signature": "", "payload": None, "generated_ts": 0}
ALERT_AI_CALIBRATION_ENABLED = str(os.getenv("AIF_ALERT_AI_CALIBRATION_ENABLED", "0") or "0").strip().lower() in ("1", "true", "yes", "on")


def _period_ts_range(kind: str, now: datetime | None = None) -> tuple[int, int]:
    dt = now or datetime.now()
    if kind == "day":
        start = dt.replace(hour=0, minute=0, second=0, microsecond=0)
        end = dt
        return int(start.timestamp()), int(end.timestamp())
    if kind == "week":
        start = (dt - timedelta(days=dt.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
        end = dt
        return int(start.timestamp()), int(end.timestamp())
    if kind == "week_prev":
        cur_start = (dt - timedelta(days=dt.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
        prev_start = cur_start - timedelta(days=7)
        prev_end = prev_start + (dt - cur_start)
        return int(prev_start.timestamp()), int(prev_end.timestamp())
    if kind == "month":
        start = dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end = dt
        return int(start.timestamp()), int(end.timestamp())
    if kind == "month_prev":
        cur_start = dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        prev_end_anchor = cur_start - timedelta(seconds=1)
        prev_start = prev_end_anchor.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        elapsed = dt - cur_start
        prev_end = min(prev_start + elapsed, prev_end_anchor.replace(hour=23, minute=59, second=59, microsecond=0))
        return int(prev_start.timestamp()), int(prev_end.timestamp())
    if kind == "year_ago_day":
        end = dt - timedelta(days=365)
        start = end.replace(hour=0, minute=0, second=0, microsecond=0)
        return int(start.timestamp()), int(end.timestamp())
    if kind == "year_ago_week":
        cur_start = (dt - timedelta(days=dt.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
        start = cur_start - timedelta(days=364)
        end = start + (dt - cur_start)
        return int(start.timestamp()), int(end.timestamp())
    if kind == "year_ago_month":
        cur_start = dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        start = cur_start - timedelta(days=365)
        end = start + (dt - cur_start)
        return int(start.timestamp()), int(end.timestamp())
    raise ValueError(f"unsupported period kind: {kind}")


def _build_traceability_links(lang: str, intelligence: dict, traceability: dict) -> list[dict]:
    links: list[dict] = []
    pressure = ((intelligence.get("pressure_stage") or {}) if isinstance(intelligence, dict) else {}) or {}
    priority = ((intelligence.get("priority_stage") or {}) if isinstance(intelligence, dict) else {}) or {}
    recent_events = traceability.get("events", []) if isinstance(traceability.get("events"), list) else []

    pressure_name = str(pressure.get("name") or "").strip()
    priority_name = str(priority.get("name") or "").strip()
    if pressure_name:
        links.append({"label": f"反查压力环节：{pressure_name}", "q": "", "action": ""})
    if priority_name and priority_name != pressure_name:
        links.append({"label": f"反查优先提升环节：{priority_name}", "q": "", "action": ""})
    for item in recent_events[:3]:
        if not isinstance(item, dict):
            continue
        target = str(item.get("target") or "").strip()
        if not target:
            continue
        links.append({"label": f"追最近事件：{target}", "q": target, "action": str(item.get("action") or "").strip()})
    dedup: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for item in links:
        key = (str(item.get("q") or ""), str(item.get("action") or ""))
        if key in seen:
            continue
        seen.add(key)
        dedup.append(item)
    return dedup[:5]


def _to_float(v, default=0.0):
    try:
        if v in (None, ""):
            return float(default)
        return float(v)
    except Exception:
        return float(default)


def _to_int(v, default=0):
    try:
        if v in (None, ""):
            return int(default)
        return int(float(v))
    except Exception:
        return int(default)


def _load_json(session, key: str, default):
    row = session.query(TgSetting).filter_by(key=key).first()
    if not row or not str(row.value or "").strip():
        return default
    try:
        val = json.loads(str(row.value))
        return val
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


def get_alert_engine_config() -> dict:
    session = Session()
    try:
        cfg = _load_json(session, ALERT_ENGINE_CFG_KEY, {})
    finally:
        session.close()

    out = {
        "dedup_seconds": max(60, _to_int(cfg.get("dedup_seconds"), 900)),
        "silence_seconds": max(0, _to_int(cfg.get("silence_seconds"), 0)),
        "trend_window_hours": max(1, _to_int(cfg.get("trend_window_hours"), 6)),
        "trend_sort_drop_trays": max(1, _to_int(cfg.get("trend_sort_drop_trays"), 15)),
        "trend_log_drop_mt": max(1.0, _to_float(cfg.get("trend_log_drop_mt"), 8.0)),
        "history_days": max(7, _to_int(cfg.get("history_days"), 14)),
        "product_ready_threshold": max(1, _to_int(cfg.get("product_ready_threshold"), 26)),
        "product_full_threshold": max(1, _to_int(cfg.get("product_full_threshold"), 76)),
        "product_burst_threshold": max(1, _to_int(cfg.get("product_burst_threshold"), 100)),
        "enable_bottleneck_mode": 1 if _to_int(cfg.get("enable_bottleneck_mode"), 1) == 1 else 0,
        "bottleneck_kiln_done_threshold": max(1, _to_int(cfg.get("bottleneck_kiln_done_threshold"), 40)),
        "bottleneck_relax_weight_pct": max(0, min(100, _to_int(cfg.get("bottleneck_relax_weight_pct"), 35))),
        "improve_bonus_2day": max(0.0, min(30.0, _to_float(cfg.get("improve_bonus_2day"), 10.0))),
        "improve_bonus_3day": max(0.0, min(30.0, _to_float(cfg.get("improve_bonus_3day"), 5.0))),
        "smooth_day_window_points": max(1, _to_int(cfg.get("smooth_day_window_points"), 3)),
        "smooth_week_window_points": max(1, _to_int(cfg.get("smooth_week_window_points"), 3)),
        "weight_raw_security": max(1, min(60, _to_int(cfg.get("weight_raw_security"), 20))),
        "weight_front_balance": max(1, min(60, _to_int(cfg.get("weight_front_balance"), 20))),
        "weight_middle_flow": max(1, min(60, _to_int(cfg.get("weight_middle_flow"), 20))),
        "weight_backlog_health": max(1, min(60, _to_int(cfg.get("weight_backlog_health"), 20))),
        "weight_product_health": max(1, min(60, _to_int(cfg.get("weight_product_health"), 20))),
        # 0 表示自动推演；>0 表示手工覆盖“药浸/拣选/二选”每托立方
        "throughput_spec_tray_m3_override": max(0.0, min(5.0, _to_float(cfg.get("throughput_spec_tray_m3_override"), 0.0))),
        # 原木MT折算m³系数（用于损耗按m³估算）
        "raw_mt_to_m3_factor": max(0.1, min(3.0, _to_float(cfg.get("raw_mt_to_m3_factor"), 1.0))),
        # 橡胶木鲜木->干木体积缩水比例（绿材到干材）
        "kiln_green_to_dry_shrinkage_pct": max(0.0, min(30.0, _to_float(cfg.get("kiln_green_to_dry_shrinkage_pct"), 7.5))),
        "kiln_status_warn_hours": max(12, _to_int(cfg.get("kiln_status_warn_hours"), 24)),
        "kiln_status_critical_hours": max(24, _to_int(cfg.get("kiln_status_critical_hours"), 36)),
    }
    return out


def save_alert_engine_config(values: dict) -> dict:
    current = get_alert_engine_config()
    merged = dict(current)
    merged.update(values or {})
    normalized = {
        "dedup_seconds": max(60, _to_int(merged.get("dedup_seconds"), current["dedup_seconds"])),
        "silence_seconds": max(0, _to_int(merged.get("silence_seconds"), current["silence_seconds"])),
        "trend_window_hours": max(1, _to_int(merged.get("trend_window_hours"), current["trend_window_hours"])),
        "trend_sort_drop_trays": max(1, _to_int(merged.get("trend_sort_drop_trays"), current["trend_sort_drop_trays"])),
        "trend_log_drop_mt": max(1.0, _to_float(merged.get("trend_log_drop_mt"), current["trend_log_drop_mt"])),
        "history_days": max(7, _to_int(merged.get("history_days"), current["history_days"])),
        "product_ready_threshold": max(1, _to_int(merged.get("product_ready_threshold"), current["product_ready_threshold"])),
        "product_full_threshold": max(1, _to_int(merged.get("product_full_threshold"), current["product_full_threshold"])),
        "product_burst_threshold": max(1, _to_int(merged.get("product_burst_threshold"), current["product_burst_threshold"])),
        "enable_bottleneck_mode": 1 if _to_int(merged.get("enable_bottleneck_mode"), current["enable_bottleneck_mode"]) == 1 else 0,
        "bottleneck_kiln_done_threshold": max(1, _to_int(merged.get("bottleneck_kiln_done_threshold"), current["bottleneck_kiln_done_threshold"])),
        "bottleneck_relax_weight_pct": max(0, min(100, _to_int(merged.get("bottleneck_relax_weight_pct"), current["bottleneck_relax_weight_pct"]))),
        "improve_bonus_2day": max(0.0, min(30.0, _to_float(merged.get("improve_bonus_2day"), current["improve_bonus_2day"]))),
        "improve_bonus_3day": max(0.0, min(30.0, _to_float(merged.get("improve_bonus_3day"), current["improve_bonus_3day"]))),
        "smooth_day_window_points": max(1, _to_int(merged.get("smooth_day_window_points"), current["smooth_day_window_points"])),
        "smooth_week_window_points": max(1, _to_int(merged.get("smooth_week_window_points"), current["smooth_week_window_points"])),
        "weight_raw_security": max(1, min(60, _to_int(merged.get("weight_raw_security"), current["weight_raw_security"]))),
        "weight_front_balance": max(1, min(60, _to_int(merged.get("weight_front_balance"), current["weight_front_balance"]))),
        "weight_middle_flow": max(1, min(60, _to_int(merged.get("weight_middle_flow"), current["weight_middle_flow"]))),
        "weight_backlog_health": max(1, min(60, _to_int(merged.get("weight_backlog_health"), current["weight_backlog_health"]))),
        "weight_product_health": max(1, min(60, _to_int(merged.get("weight_product_health"), current["weight_product_health"]))),
        "throughput_spec_tray_m3_override": max(0.0, min(5.0, _to_float(merged.get("throughput_spec_tray_m3_override"), current["throughput_spec_tray_m3_override"]))),
        "raw_mt_to_m3_factor": max(0.1, min(3.0, _to_float(merged.get("raw_mt_to_m3_factor"), current["raw_mt_to_m3_factor"]))),
        "kiln_green_to_dry_shrinkage_pct": max(0.0, min(30.0, _to_float(merged.get("kiln_green_to_dry_shrinkage_pct"), current["kiln_green_to_dry_shrinkage_pct"]))),
        "kiln_status_warn_hours": max(12, _to_int(merged.get("kiln_status_warn_hours"), current["kiln_status_warn_hours"])),
        "kiln_status_critical_hours": max(24, _to_int(merged.get("kiln_status_critical_hours"), current["kiln_status_critical_hours"])),
    }

    session = Session()
    try:
        _save_json(session, ALERT_ENGINE_CFG_KEY, normalized)
        session.commit()
    finally:
        session.close()
    return normalized


def append_threshold_version(settings: dict, operator: str) -> None:
    now_ts = int(time.time())
    item = {
        "id": f"AV{now_ts}{secrets.randbelow(10000):04d}",
        "ts": now_ts,
        "operator": str(operator or ""),
        "settings": {
            "log_stock_mt_min": _to_float(settings.get("log_stock_mt_min"), 0.0),
            "sorting_stock_tray_min": _to_int(settings.get("sorting_stock_tray_min"), 0),
            "kiln_done_stock_tray_max": _to_int(settings.get("kiln_done_stock_tray_max"), 0),
            "product_shippable_tray_min": _to_int(settings.get("product_shippable_tray_min"), 0),
        },
    }
    session = Session()
    try:
        arr = _load_json(session, ALERT_THRESHOLD_VERSIONS_KEY, [])
        if not isinstance(arr, list):
            arr = []
        arr.append(item)
        arr = arr[-120:]
        _save_json(session, ALERT_THRESHOLD_VERSIONS_KEY, arr)
        session.commit()
    finally:
        session.close()


def _format_ts(ts: int) -> str:
    try:
        return datetime.fromtimestamp(int(ts)).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return "-"


def _severity_rank(level: str) -> int:
    return {"L3": 3, "L2": 2, "L1": 1}.get(str(level or "").upper(), 1)


def _css_level(level: str) -> str:
    return {"L3": "high", "L2": "medium", "L1": "low"}.get(str(level or "").upper(), "low")


def _norm_lang(lang: str) -> str:
    lc = str(lang or "zh").strip().lower()
    return lc if lc in ("zh", "en", "my") else "zh"


def _i18n_value(i18n_obj, lang: str, fallback: str = "") -> str:
    lc = _norm_lang(lang)
    if isinstance(i18n_obj, dict):
        v = str(i18n_obj.get(lc) or i18n_obj.get("zh") or fallback or "").strip()
        return v
    return str(fallback or "")


def _t(lang: str, key: str, default: str = "") -> str:
    lc = _norm_lang(lang)
    base = LANGUAGES.get("zh", {})
    pack = LANGUAGES.get(lc, base)
    return str(pack.get(key, base.get(key, default or key)) or default or key)


def _fmt_t(lang: str, key: str, default: str = "", **params) -> str:
    tpl = _t(lang, key, default=default)
    if not params:
        return tpl
    try:
        return tpl.format(**params)
    except Exception:
        return tpl


def _parse_iso_ts(text: str) -> int:
    s = str(text or "").strip()
    if not s:
        return 0
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        return int(dt.timestamp())
    except Exception:
        pass
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return int(datetime.strptime(s, fmt).timestamp())
        except Exception:
            continue
    return 0


def _pack_i18n_text(key: str, default: str = "", **params) -> dict:
    return {
        "zh": _fmt_t("zh", key, default=default, **params),
        "en": _fmt_t("en", key, default=default, **params),
        "my": _fmt_t("my", key, default=default, **params),
    }


def _build_stock_snapshot_for_intelligence(lang: str) -> dict:
    lc = _norm_lang(lang)
    log_stock = float(get_log_stock_total())
    product_count, product_m3 = get_product_stats()
    flow = get_flow_data()
    shipping = get_shipping_data()
    shipping_summary = {'去仰光途中': 0, '仰光仓已到': 0, '已从仰光出港': 0, '异常': 0}
    for item in shipping.get('shipments', []) if isinstance(shipping.get('shipments'), list) else []:
        if not isinstance(item, dict):
            continue
        status = str(item.get('status', '待发货') or '待发货')
        if status == '待发车':
            shipping_summary['去仰光途中'] = shipping_summary.get('去仰光途中', 0) + 1
        elif status in shipping_summary:
            shipping_summary[status] = shipping_summary.get(status, 0) + 1

    kiln_status = {}
    kilns = get_kilns_data()
    now_ts = int(time.time())
    for kiln_id in ['A', 'B', 'C', 'D']:
        kiln_data = kilns.get(kiln_id, {}) if isinstance(kilns, dict) else {}
        status = str(kiln_data.get('status', 'empty') or 'empty')
        if status == 'ready_unload':
            status = 'ready'
        status_display = {
            'empty': LANGUAGES[lc]['empty'],
            'loading': LANGUAGES[lc]['loading'],
            'drying': LANGUAGES[lc]['drying'],
            'unloading': LANGUAGES[lc]['unloading'],
            'ready': LANGUAGES[lc]['ready'],
            'completed': LANGUAGES[lc]['completed'],
        }.get(status, status)
        trays_list = kiln_data.get('trays', [])
        trays_in_kiln = sum(int(tray.get('count', 0) or 0) for tray in trays_list) if isinstance(trays_list, list) else 0
        stored_total_trays = int(kiln_data.get('unloading_total_trays', 0) or 0)
        unloaded_trays = int(kiln_data.get('unloaded_count', 0) or 0)
        total_trays = stored_total_trays if status in {'ready', 'unloading', 'completed'} and stored_total_trays > 0 else trays_in_kiln
        remaining_trays = max(0, total_trays - unloaded_trays)
        progress = ""
        elapsed_hours = 0
        remaining_hours = 0
        if status == 'drying' and (kiln_data.get('dry_start') or kiln_data.get('start')):
            base = kiln_data.get('dry_start') or kiln_data.get('start')
            try:
                if isinstance(base, str):
                    start_ts = int(datetime.fromisoformat(base.replace('Z', '+00:00')).timestamp())
                else:
                    start_ts = int(base)
            except Exception:
                start_ts = now_ts
            elapsed = max(0, now_ts - start_ts)
            remaining = max(0, 120 * 3600 - elapsed)
            elapsed_hours = elapsed // 3600
            remaining_hours = remaining // 3600
            progress = LANGUAGES[lc]['drying_progress'].format(elapsed=elapsed_hours, remaining=remaining_hours)
        elif total_trays > 0:
            progress = f"{LANGUAGES[lc]['total_trays']}{total_trays} {LANGUAGES[lc]['remaining_trays']}{remaining_trays}{LANGUAGES[lc]['trays']}"

        changed_raw = kiln_data.get('status_changed_at')
        changed_ts = int(changed_raw) if isinstance(changed_raw, (int, float)) else 0
        if changed_ts <= 0 and isinstance(changed_raw, str) and changed_raw.strip():
            try:
                changed_ts = int(datetime.fromisoformat(changed_raw.replace('Z', '+00:00')).timestamp())
            except Exception:
                changed_ts = 0
        if changed_ts <= 0:
            changed_ts = now_ts
        status_duration_hours = max(0.0, (now_ts - changed_ts) / 3600.0)
        kiln_status[kiln_id] = {
            'status': status,
            'status_display': status_display,
            'progress': progress,
            'elapsed_hours': elapsed_hours,
            'remaining_hours': remaining_hours,
            'total_trays': total_trays,
            'remaining_trays': remaining_trays,
            'in_kiln_trays': trays_in_kiln,
            'remaining_kiln_trays': remaining_trays,
            'status_duration_hours': round(status_duration_hours, 2),
        }

    return {
        "log_stock": log_stock,
        "saw_stock": flow.get("saw_tray_pool", 0),
        "dip_stock": flow.get("dip_tray_pool", 0),
        "sorting_stock": flow.get("selected_tray_pool", 0),
        "kiln_done_stock": flow.get("kiln_done_tray_pool", 0),
        "product_count": product_count,
        "product_m3": product_m3,
        "shipping_summary": shipping_summary,
        "kiln_status": kiln_status,
    }


def _collect_admin_chat_ids(session) -> list[str]:
    ids = {
        str(r.user_id).strip()
        for r in session.query(TgUserRole).all()
        if str(getattr(r, "role", "") or "") in ("管理员", "老板", "admin", "boss") and str(getattr(r, "user_id", "") or "").strip()
    }
    fallback = str(os.getenv("BOT_CHAT_ID", "") or "").strip()
    if fallback:
        ids.add(fallback)
    return sorted(ids)


def _notify_l2_l3(level: str, title: str, text: str) -> None:
    if _severity_rank(level) < 2:
        return
    try:
        token = get_bot_token()
    except Exception:
        return
    if not token:
        return

    session = Session()
    try:
        chat_ids = _collect_admin_chat_ids(session)
    finally:
        session.close()
    if not chat_ids:
        return

    msg = (
        "AIF 预警通知\n"
        f"等级: {level}\n"
        f"标题: {title}\n"
        f"内容: {text}\n"
        f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    headers = {"Content-Type": "application/json"}
    for cid in chat_ids:
        try:
            payload = json.dumps({"chat_id": str(cid), "text": msg, "disable_web_page_preview": True}).encode("utf-8")
            req = urllib_request.Request(url, data=payload, headers=headers, method="POST")
            urllib_request.urlopen(req, timeout=5)
        except Exception:
            continue


def _estimate_daily_log_consumption(history: list) -> float:
    if not history:
        return 0.0
    now_ts = int(time.time())
    cutoff = now_ts - 3 * 86400
    pts = [p for p in history if _to_int(p.get("ts"), 0) >= cutoff]
    if len(pts) < 2:
        return 0.0
    pts.sort(key=lambda x: _to_int(x.get("ts"), 0))
    first = pts[0]
    last = pts[-1]
    delta_mt = max(0.0, _to_float(first.get("log_stock"), 0.0) - _to_float(last.get("log_stock"), 0.0))
    delta_days = max(1.0 / 24.0, (_to_int(last.get("ts"), 0) - _to_int(first.get("ts"), 0)) / 86400.0)
    return max(0.0, delta_mt / delta_days)


def _infer_spec_tray_m3(session) -> float:
    # 由规格自动推演单托立方：优先解析规格字符串，其次尺寸*件数，最后回退。
    vals = []
    try:
        rows0 = session.query(FlowSelectedTrayDetail).limit(1000).all()
        for r in rows0:
            text = str(getattr(r, "spec", "") or "")
            import re
            m = re.search(r"(\d{2,4})x(\d{2,3})x(\d{1,3})x(\d{1,5})", text)
            if not m:
                continue
            l = _to_int(m.group(1), 0)
            w = _to_int(m.group(2), 0)
            t = _to_int(m.group(3), 0)
            pcs = _to_int(m.group(4), 0)
            if l < 100:
                l *= 10
            v = (float(l) * float(w) * float(t) * float(pcs)) / 1_000_000_000.0
            if 0.05 <= v <= 2.0:
                vals.append(v)
    except Exception:
        vals = []
    if vals:
        return round(sum(vals) / float(len(vals)), 4)

    try:
        rows = session.query(FlowSelectedTray).limit(600).all()
        for r in rows:
            l = _to_float(getattr(r, "length_mm", 0), 0.0)
            w = _to_float(getattr(r, "width_mm", 0), 0.0)
            t = _to_float(getattr(r, "thick_mm", 0), 0.0)
            pcs = _to_float(getattr(r, "pcs", 0), 0.0)
            if l > 0 and w > 0 and t > 0 and pcs > 0:
                vals.append((l * w * t * pcs) / 1_000_000_000.0)
    except Exception:
        vals = []
    sane = [v for v in vals if 0.05 <= v <= 2.0]
    if sane:
        return round(sum(sane) / float(len(sane)), 4)
    return 0.53


def _sum_stage_range(
    session,
    begin_ts: int,
    end_ts: int,
    tray_m3_other: float,
    raw_mt_to_m3_factor: float,
    kiln_green_to_dry_shrinkage_pct: float,
) -> dict:
    saw_trays = 0
    saw_mt = 0.0
    dip_trays = 0
    sort_trays = 0
    secondary_trays = 0
    secondary_real_m3 = 0.0
    product_m3 = 0.0

    try:
        for r in session.query(SawRecord).all():
            ts = _parse_iso_ts(getattr(r, "created_at", ""))
            if begin_ts <= ts <= end_ts:
                saw_trays += _to_int(getattr(r, "saw_trays", 0), 0)
                saw_mt += _to_float(getattr(r, "saw_mt", 0.0), 0.0)
    except Exception:
        pass
    try:
        for r in session.query(DipRecord).all():
            ts = _parse_iso_ts(getattr(r, "created_at", ""))
            if begin_ts <= ts <= end_ts:
                dip_trays += _to_int(getattr(r, "dip_trays", 0), 0)
    except Exception:
        pass
    try:
        for r in session.query(SortRecord).all():
            ts = _parse_iso_ts(getattr(r, "created_at", ""))
            if begin_ts <= ts <= end_ts:
                sort_trays += _to_int(getattr(r, "sort_trays", 0), 0)
    except Exception:
        pass
    try:
        for r in session.query(FlowSecondSortRecord).all():
            ts = _parse_iso_ts(getattr(r, "time", ""))
            if begin_ts <= ts <= end_ts:
                secondary_trays += _to_int(getattr(r, "trays", 0), 0)
                secondary_real_m3 += (
                    _to_float(getattr(r, "ok_m3", 0.0), 0.0)
                    + _to_float(getattr(r, "ab_m3", 0.0), 0.0)
                    + _to_float(getattr(r, "bc_m3", 0.0), 0.0)
                    + _to_float(getattr(r, "loss_m3", 0.0), 0.0)
                )
    except Exception:
        pass
    try:
        for r in session.query(ProductBatch).all():
            ts = _parse_iso_ts(getattr(r, "created_at", ""))
            if begin_ts <= ts <= end_ts:
                product_m3 += _to_float(getattr(r, "total_volume", 0.0), 0.0)
    except Exception:
        pass

    # 锯解按固定 0.53 m³/托；其余环节按规格推演系数。
    saw_m3 = float(saw_trays) * 0.53
    dip_m3 = float(dip_trays) * float(tray_m3_other)
    sort_m3 = float(sort_trays) * float(tray_m3_other)
    secondary_m3_by_tray = float(secondary_trays) * float(tray_m3_other)
    shrink_ratio = max(0.0, min(0.3, float(kiln_green_to_dry_shrinkage_pct) / 100.0))
    kiln_out_m3 = float(secondary_real_m3) if secondary_real_m3 > 0 else (float(sort_m3) * (1.0 - shrink_ratio))
    secondary_m3 = kiln_out_m3 if kiln_out_m3 > 0 else secondary_m3_by_tray
    raw_input_m3_est = float(saw_mt) * float(raw_mt_to_m3_factor)

    # 三段损耗（按m³）
    loss_raw_to_saw_m3 = max(0.0, raw_input_m3_est - saw_m3)
    loss_kiln_in_to_out_m3 = max(0.0, sort_m3 - kiln_out_m3)
    loss_out_to_product_m3 = max(0.0, kiln_out_m3 - product_m3)

    def _loss_rate(loss: float, base: float) -> float:
        b = max(0.0001, float(base))
        return round((float(loss) / b) * 100.0, 2)

    def _ratio(cur: float, prev: float) -> float:
        p = max(0.0001, float(prev))
        return round((float(cur) / p) * 100.0, 1)

    return {
        "saw_trays": int(saw_trays),
        "dip_trays": int(dip_trays),
        "sort_trays": int(sort_trays),
        "secondary_trays": int(secondary_trays),
        "saw_mt": round(float(saw_mt), 4),
        "raw_input_m3_est": round(raw_input_m3_est, 4),
        "saw_m3": round(saw_m3, 4),
        "dip_m3": round(dip_m3, 4),
        "sort_m3": round(sort_m3, 4),
        "secondary_m3": round(secondary_m3, 4),
        "kiln_out_m3": round(kiln_out_m3, 4),
        "product_m3": round(max(0.0, product_m3), 4),
        "loss_raw_to_saw_m3": round(loss_raw_to_saw_m3, 4),
        "loss_raw_to_saw_rate_pct": _loss_rate(loss_raw_to_saw_m3, raw_input_m3_est),
        "loss_kiln_in_to_out_m3": round(loss_kiln_in_to_out_m3, 4),
        "loss_kiln_in_to_out_rate_pct": _loss_rate(loss_kiln_in_to_out_m3, sort_m3),
        "loss_out_to_product_m3": round(loss_out_to_product_m3, 4),
        "loss_out_to_product_rate_pct": _loss_rate(loss_out_to_product_m3, secondary_m3),
        "product_m3_per_raw_mt": round((product_m3 / max(0.0001, saw_mt)), 4),
        "raw_mt_for_10_product_m3": round((10.0 / max(0.0001, (product_m3 / max(0.0001, saw_mt)))), 4),
        "ratio_dip_vs_saw": _ratio(dip_m3, saw_m3),
        "ratio_sort_vs_dip": _ratio(sort_m3, dip_m3),
        "ratio_secondary_vs_sort": _ratio(secondary_m3, sort_m3),
        "ratio_product_vs_secondary": _ratio(product_m3, secondary_m3),
    }


def _pct_change(cur: float, base: float):
    b = float(base)
    if abs(b) < 1e-6:
        return None
    return round(((float(cur) - b) / b) * 100.0, 1)


def _build_stage_throughput_payload(lang: str = "zh", cfg: dict | None = None) -> dict:
    lc = _norm_lang(lang)
    now = datetime.now()

    session = Session()
    try:
        auto_tray_m3 = _infer_spec_tray_m3(session)
        override_tray_m3 = _to_float((cfg or {}).get("throughput_spec_tray_m3_override"), 0.0)
        tray_m3_other = override_tray_m3 if override_tray_m3 > 0 else auto_tray_m3
        raw_mt_to_m3_factor = _to_float((cfg or {}).get("raw_mt_to_m3_factor"), 1.0)
        kiln_green_to_dry_shrinkage_pct = _to_float((cfg or {}).get("kiln_green_to_dry_shrinkage_pct"), 7.5)
        day_start, day_end = _period_ts_range("day", now)
        week_start, week_end = _period_ts_range("week", now)
        month_start, month_end = _period_ts_range("month", now)
        day_prev_start, day_prev_end = day_start - 86400, day_start
        week_prev_start, week_prev_end = _period_ts_range("week_prev", now)
        month_prev_start, month_prev_end = _period_ts_range("month_prev", now)
        day_yoy_start, day_yoy_end = _period_ts_range("year_ago_day", now)
        week_yoy_start, week_yoy_end = _period_ts_range("year_ago_week", now)
        month_yoy_start, month_yoy_end = _period_ts_range("year_ago_month", now)

        day_cur = _sum_stage_range(session, day_start, day_end, tray_m3_other, raw_mt_to_m3_factor, kiln_green_to_dry_shrinkage_pct)
        week_cur = _sum_stage_range(session, week_start, week_end, tray_m3_other, raw_mt_to_m3_factor, kiln_green_to_dry_shrinkage_pct)
        month_cur = _sum_stage_range(session, month_start, month_end, tray_m3_other, raw_mt_to_m3_factor, kiln_green_to_dry_shrinkage_pct)

        day_prev = _sum_stage_range(session, day_prev_start, day_prev_end, tray_m3_other, raw_mt_to_m3_factor, kiln_green_to_dry_shrinkage_pct)
        week_prev = _sum_stage_range(session, week_prev_start, week_prev_end, tray_m3_other, raw_mt_to_m3_factor, kiln_green_to_dry_shrinkage_pct)
        month_prev = _sum_stage_range(session, month_prev_start, month_prev_end, tray_m3_other, raw_mt_to_m3_factor, kiln_green_to_dry_shrinkage_pct)

        day_yoy = _sum_stage_range(session, day_yoy_start, day_yoy_end, tray_m3_other, raw_mt_to_m3_factor, kiln_green_to_dry_shrinkage_pct)
        week_yoy = _sum_stage_range(session, week_yoy_start, week_yoy_end, tray_m3_other, raw_mt_to_m3_factor, kiln_green_to_dry_shrinkage_pct)
        month_yoy = _sum_stage_range(session, month_yoy_start, month_yoy_end, tray_m3_other, raw_mt_to_m3_factor, kiln_green_to_dry_shrinkage_pct)

        labels = []
        saw_arr = []
        dip_arr = []
        sort_arr = []
        sec_arr = []
        prod_arr = []
        for d in range(13, -1, -1):
            end_dt = now - timedelta(days=d)
            begin_ts = int((end_dt - timedelta(days=1)).timestamp())
            end_ts = int(end_dt.timestamp())
            item = _sum_stage_range(session, begin_ts, end_ts, tray_m3_other, raw_mt_to_m3_factor, kiln_green_to_dry_shrinkage_pct)
            labels.append(end_dt.strftime("%m-%d"))
            saw_arr.append(item["saw_m3"])
            dip_arr.append(item["dip_m3"])
            sort_arr.append(item["sort_m3"])
            sec_arr.append(item["secondary_m3"])
            prod_arr.append(item["product_m3"])
    finally:
        session.close()

    def _cmp(cur: dict, prev: dict, yoy: dict) -> dict:
        cur_val = _to_float(cur.get("product_m3"), 0.0)
        prev_val = _to_float(prev.get("product_m3"), 0.0)
        yoy_val = _to_float(yoy.get("product_m3"), 0.0)
        return {
            "product_m3": round(cur_val, 4),
            "mom_pct": _pct_change(cur_val, prev_val),
            "yoy_pct": _pct_change(cur_val, yoy_val),
        }

    stage_labels = [
        _t(lc, "throughput_stage_saw", "锯解"),
        _t(lc, "throughput_stage_dip", "药浸"),
        _t(lc, "throughput_stage_sort", "拣选"),
        _t(lc, "throughput_stage_secondary", "二选"),
        _t(lc, "throughput_stage_product", "成品"),
    ]
    return {
        "tray_coefficients": {
            "saw_fixed_m3_per_tray": 0.53,
            "spec_inferred_m3_per_tray": round(tray_m3_other, 4),
            "spec_auto_inferred_m3_per_tray": round(auto_tray_m3, 4),
            "spec_override_m3_per_tray": round(override_tray_m3, 4),
            "raw_mt_to_m3_factor": round(raw_mt_to_m3_factor, 4),
            "kiln_green_to_dry_shrinkage_pct": round(kiln_green_to_dry_shrinkage_pct, 3),
        },
        "current_day": day_cur,
        "current_week": week_cur,
        "current_month": month_cur,
        "comparison": {
            "day": _cmp(day_cur, day_prev, day_yoy),
            "week": _cmp(week_cur, week_prev, week_yoy),
            "month": _cmp(month_cur, month_prev, month_yoy),
        },
        "trend_daily": {
            "labels": labels,
            "saw_m3": saw_arr,
            "dip_m3": dip_arr,
            "sort_m3": sort_arr,
            "secondary_m3": sec_arr,
            "product_m3": prod_arr,
        },
        "stage_labels": stage_labels,
    }


def _build_rules(stock: dict, cfg: dict, threshold_cfg: dict, history: list, lang: str = "zh") -> list[dict]:
    log_min = _to_float(threshold_cfg.get("log_stock_mt_min"), 80.0)
    product_full = _to_int(cfg.get("product_full_threshold"), 76)
    product_burst = _to_int(cfg.get("product_burst_threshold"), 100)

    log_stock = _to_float(stock.get("log_stock"), 0.0)
    product_count = _to_int(stock.get("product_count"), 0)

    daily_use = _estimate_daily_log_consumption(history)
    days_left = (log_stock / daily_use) if daily_use > 0 else 999.0
    shared_days_i18n = _pack_i18n_text(
        "alert_text_log_stock_days_left",
        default="原木库存 {log_stock:.4f} MT，按近3天消耗估算可用约 {days_left:.1f} 天",
        log_stock=log_stock,
        days_left=days_left,
    )
    return [
        {
            "key": "log_stock_need_buy",
            "level": "L1",
            "title": _t("zh", "alert_title_log_stock_need_buy", "原木需采购"),
            "title_i18n": _pack_i18n_text("alert_title_log_stock_need_buy", default="原木需采购"),
            "active": log_stock < log_min and days_left <= 3.0,
            "text": shared_days_i18n["zh"],
            "text_i18n": shared_days_i18n,
        },
        {
            "key": "log_stock_urgent_buy",
            "level": "L2",
            "title": _t("zh", "alert_title_log_stock_urgent_buy", "原木急需采购"),
            "title_i18n": _pack_i18n_text("alert_title_log_stock_urgent_buy", default="原木急需采购"),
            "active": log_stock < log_min and days_left <= 2.0,
            "text": shared_days_i18n["zh"],
            "text_i18n": shared_days_i18n,
        },
        {
            "key": "log_stock_tomorrow_risk",
            "level": "L3",
            "title": _t("zh", "alert_title_log_stock_tomorrow_risk", "原木明天断料风险"),
            "title_i18n": _pack_i18n_text("alert_title_log_stock_tomorrow_risk", default="原木明天断料风险"),
            "active": log_stock < log_min and days_left <= 1.0,
            "text": shared_days_i18n["zh"],
            "text_i18n": shared_days_i18n,
        },
        {
            "key": "product_stock_full",
            "level": "L2",
            "title": _t("zh", "alert_title_product_stock_full", "成品库存满仓"),
            "title_i18n": _pack_i18n_text("alert_title_product_stock_full", default="成品库存满仓"),
            "active": product_count > product_full,
            "text": _fmt_t("zh", "alert_text_product_stock_full", "成品库存 {product_count} 件，超过满仓阈值 {product_full} 件", product_count=product_count, product_full=product_full),
            "text_i18n": _pack_i18n_text(
                "alert_text_product_stock_full",
                default="成品库存 {product_count} 件，超过满仓阈值 {product_full} 件",
                product_count=product_count,
                product_full=product_full,
            ),
        },
        {
            "key": "product_stock_burst",
            "level": "L3",
            "title": _t("zh", "alert_title_product_stock_burst", "成品库存爆满"),
            "title_i18n": _pack_i18n_text("alert_title_product_stock_burst", default="成品库存爆满"),
            "active": product_count > product_burst,
            "text": _fmt_t("zh", "alert_text_product_stock_burst", "成品库存 {product_count} 件，超过爆满阈值 {product_burst} 件", product_count=product_count, product_burst=product_burst),
            "text_i18n": _pack_i18n_text(
                "alert_text_product_stock_burst",
                default="成品库存 {product_count} 件，超过爆满阈值 {product_burst} 件",
                product_count=product_count,
                product_burst=product_burst,
            ),
        },
    ]


def _build_kiln_status_rules(stock: dict, cfg: dict, lang: str = "zh") -> list[dict]:
    kiln_status = stock.get("kiln_status", {}) if isinstance(stock, dict) else {}
    if not isinstance(kiln_status, dict):
        return []
    warn_h = _to_int(cfg.get("kiln_status_warn_hours"), 24)
    crit_h = _to_int(cfg.get("kiln_status_critical_hours"), 36)
    saw_stock = _to_int(stock.get("saw_stock"), 0)
    dip_stock = _to_int(stock.get("dip_stock"), 0)
    sorting_stock = _to_int(stock.get("sorting_stock"), 0)
    kiln_done_stock = _to_int(stock.get("kiln_done_stock"), 0)
    product_count = _to_int(stock.get("product_count"), 0)
    rules = []

    for kiln_id, info in kiln_status.items():
        if not isinstance(info, dict):
            continue
        status = str(info.get("status") or "").strip().lower()
        status_i18n = {
            "zh": _t("zh", status, "未知状态"),
            "en": _t("en", status, "Unknown"),
            "my": _t("my", status, "မသိသောအခြေအနေ"),
        }
        hours = _to_float(info.get("status_duration_hours"), 0.0)
        # 烘干工艺默认 120 小时，120 小时内不触发预警。
        if status == "drying" and hours < 120.0:
            continue
        if hours < float(warn_h):
            continue
        level = "L3" if hours >= float(crit_h) else "L2"
        key = f"kiln_{str(kiln_id).upper()}_{status}_overdue"
        title_i18n = _pack_i18n_text("alert_title_kiln_status_overdue", default="窑{kiln_id} 状态超时", kiln_id=str(kiln_id).upper())
        text_i18n = {
            "zh": _fmt_t("zh", "alert_text_kiln_status_overtime", "窑{kiln_id} 在“{status_label}”状态已持续 {hours:.1f} 小时。", kiln_id=str(kiln_id).upper(), status_label=status_i18n["zh"], hours=hours),
            "en": _fmt_t("en", "alert_text_kiln_status_overtime", "Kiln {kiln_id} has stayed in '{status_label}' for {hours:.1f} hours.", kiln_id=str(kiln_id).upper(), status_label=status_i18n["en"], hours=hours),
            "my": _fmt_t("my", "alert_text_kiln_status_overtime", "မီးဖို {kiln_id} သည် '{status_label}' အခြေအနေတွင် {hours:.1f} နာရီကြာနေသည်။", kiln_id=str(kiln_id).upper(), status_label=status_i18n["my"], hours=hours),
        }
        advice_i18n = {"zh": "", "en": "", "my": ""}

        if status == "empty":
            if dip_stock <= 2 and saw_stock > 3:
                advice_i18n = _pack_i18n_text("alert_advice_kiln_empty_dip_handoff", default="判断：药浸到拣选交接可能不顺。建议：检查药浸出料节拍与交接人员安排。")
            elif saw_stock <= 2:
                advice_i18n = _pack_i18n_text("alert_advice_kiln_empty_saw_low", default="判断：锯解供给偏低。建议：检查锯机开机率、原木供给、班组出勤。")
            else:
                advice_i18n = _pack_i18n_text("alert_advice_kiln_empty_upstream", default="建议：检查上游节拍，优先补齐入窑前托盘准备。")
        elif status == "ready":
            if kiln_done_stock >= 20:
                advice_i18n = _pack_i18n_text("alert_advice_kiln_ready_secondary_slow", default="判断：二选处理偏慢。建议：二选增人/分线拣选，优先处理待二选积压。")
            elif product_count >= 60:
                advice_i18n = _pack_i18n_text("alert_advice_kiln_ready_shipping_limit", default="判断：可能受发货节拍影响。建议：联动物流与发运计划，加快出货。")
            else:
                advice_i18n = _pack_i18n_text("alert_advice_kiln_ready_handoff", default="建议：核对出窑与二选衔接节拍，避免窑口等待。")
        elif status == "unloading":
            advice_i18n = _pack_i18n_text("alert_advice_kiln_unloading_resource", default="建议：检查出窑班组人手与叉车/转运资源，必要时临时增援。")
        elif status == "loading":
            if sorting_stock <= 2:
                advice_i18n = _pack_i18n_text("alert_advice_kiln_loading_sort_low", default="判断：待入窑托盘不足。建议：提升拣选到待入窑转运效率。")
            else:
                advice_i18n = _pack_i18n_text("alert_advice_kiln_loading_organize", default="建议：检查入窑作业组织，缩短装窑等待。")
        elif status == "drying":
            advice_i18n = _pack_i18n_text("alert_advice_kiln_drying_check", default="建议：核对烘干程序与设备状态，确认温控曲线与点检记录。")
        elif status == "completed":
            advice_i18n = _pack_i18n_text("alert_advice_kiln_completed_flow", default="建议：完成后应尽快转“待出/出窑”，检查状态流转与值班执行。")

        rules.append(
            {
                "key": key,
                "level": level,
                "title": title_i18n["zh"],
                "title_i18n": title_i18n,
                "active": True,
                "text": f"{text_i18n['zh']} {advice_i18n['zh']}".strip(),
                "text_i18n": {
                    "zh": f"{text_i18n['zh']} {advice_i18n['zh']}".strip(),
                    "en": f"{text_i18n['en']} {advice_i18n['en']}".strip(),
                    "my": f"{text_i18n['my']} {advice_i18n['my']}".strip(),
                },
            }
        )
    return rules


def _kiln_metrics_from_stock(stock: dict) -> dict:
    kiln_status = stock.get("kiln_status", {}) if isinstance(stock, dict) else {}
    if not isinstance(kiln_status, dict):
        return {
            "kiln_active_ratio": 0.0,
            "kiln_overdue_empty": 0,
            "kiln_overdue_drying": 0,
            "kiln_overdue_ready": 0,
            "kiln_overdue_unloading": 0,
            "kiln_health": 60.0,
        }
    total = max(1, len(kiln_status))
    active_cnt = 0
    overdue_empty = 0
    overdue_drying = 0
    overdue_ready = 0
    overdue_unloading = 0
    for _, info in kiln_status.items():
        if not isinstance(info, dict):
            continue
        status = str(info.get("status") or "").strip().lower()
        hours = _to_float(info.get("status_duration_hours"), 0.0)
        if status != "empty":
            active_cnt += 1
        if status == "empty" and hours >= 24:
            overdue_empty += 1
        if status == "drying" and hours > 120:
            overdue_drying += 1
        if status == "ready" and hours >= 24:
            overdue_ready += 1
        if status == "unloading" and hours >= 24:
            overdue_unloading += 1
    active_ratio = max(0.0, min(1.0, float(active_cnt) / float(total)))
    health = 85.0 + active_ratio * 10.0 - overdue_empty * 20.0 - overdue_ready * 18.0 - overdue_unloading * 12.0
    health = max(0.0, min(100.0, health))
    return {
        "kiln_active_ratio": round(active_ratio, 4),
        "kiln_overdue_empty": int(overdue_empty),
        "kiln_overdue_drying": int(overdue_drying),
        "kiln_overdue_ready": int(overdue_ready),
        "kiln_overdue_unloading": int(overdue_unloading),
        "kiln_health": round(health, 1),
    }


def _append_history(history: list, stock: dict, now_ts: int) -> list:
    kiln_metrics = _kiln_metrics_from_stock(stock)
    point = {
        "ts": int(now_ts),
        "log_stock": round(_to_float(stock.get("log_stock"), 0.0), 4),
        "saw_stock": _to_int(stock.get("saw_stock"), 0),
        "dip_stock": _to_int(stock.get("dip_stock"), 0),
        "sorting_stock": _to_int(stock.get("sorting_stock"), 0),
        "kiln_done_stock": _to_int(stock.get("kiln_done_stock"), 0),
        "product_count": _to_int(stock.get("product_count"), 0),
        "kiln_active_ratio": _to_float(kiln_metrics.get("kiln_active_ratio"), 0.0),
        "kiln_overdue_empty": _to_int(kiln_metrics.get("kiln_overdue_empty"), 0),
        "kiln_overdue_drying": _to_int(kiln_metrics.get("kiln_overdue_drying"), 0),
        "kiln_overdue_ready": _to_int(kiln_metrics.get("kiln_overdue_ready"), 0),
        "kiln_overdue_unloading": _to_int(kiln_metrics.get("kiln_overdue_unloading"), 0),
        "kiln_health": _to_float(kiln_metrics.get("kiln_health"), 60.0),
    }
    history.append(point)
    return history


def _evaluate_trend_rules(history: list, cfg: dict, threshold_cfg: dict, lang: str = "zh") -> list[dict]:
    if not history:
        return []
    now_ts = int(time.time())
    window_sec = _to_int(cfg.get("trend_window_hours"), 6) * 3600
    cutoff = now_ts - window_sec
    older = None
    for p in history:
        if _to_int(p.get("ts"), 0) <= cutoff:
            older = p
    if older is None:
        older = history[0]
    latest = history[-1]

    older_sorting = _to_int(older.get("sorting_stock"), 0)
    latest_sorting = _to_int(latest.get("sorting_stock"), 0)
    sort_drop = older_sorting - latest_sorting
    older_kiln_done = _to_int(older.get("kiln_done_stock"), 0)
    latest_kiln_done = _to_int(latest.get("kiln_done_stock"), 0)
    kiln_done_drop = older_kiln_done - latest_kiln_done
    older_product = _to_int(older.get("product_count"), 0)
    latest_product = _to_int(latest.get("product_count"), 0)
    product_gain = max(0, latest_product - older_product)
    overdue_ready = _to_int(latest.get("kiln_overdue_ready"), 0)
    overdue_unloading = _to_int(latest.get("kiln_overdue_unloading"), 0)
    overdue_drying = _to_int(latest.get("kiln_overdue_drying"), 0)
    log_drop = _to_float(older.get("log_stock"), 0.0) - _to_float(latest.get("log_stock"), 0.0)
    kiln_max_trays = max(1, _to_int((threshold_cfg or {}).get("kiln_max_trays"), 70))
    kiln_done_warn = max(kiln_max_trays, _to_int((threshold_cfg or {}).get("kiln_done_stock_tray_max"), 200) // 2)
    trend_hours = _to_int(cfg.get("trend_window_hours"), 6)

    out = [
        {
            "key": "trend_sorting_backlog_no_load",
            "level": "L2",
            "title": _t("zh", "alert_title_trend_sorting_backlog", "待入窑库存积压"),
            "title_i18n": _pack_i18n_text("alert_title_trend_sorting_backlog", default="待入窑库存积压"),
            "active": (latest_sorting > kiln_max_trays) and (sort_drop <= 0),
            "text": _fmt_t(
                "zh",
                "alert_text_trend_sorting_backlog",
                "近{trend_hours}小时待入窑维持在 {sorting_stock} 托（超过单窑 {kiln_max_trays} 托），未见入窑消耗。",
                trend_hours=trend_hours,
                sorting_stock=latest_sorting,
                kiln_max_trays=kiln_max_trays,
            ),
            "text_i18n": _pack_i18n_text(
                "alert_text_trend_sorting_backlog",
                default="近{trend_hours}小时待入窑维持在 {sorting_stock} 托（超过单窑 {kiln_max_trays} 托），未见入窑消耗。",
                trend_hours=trend_hours,
                sorting_stock=latest_sorting,
                kiln_max_trays=kiln_max_trays,
            ),
        },
        {
            "key": "trend_kiln_done_backlog_no_secondary",
            "level": "L2",
            "title": _t("zh", "alert_title_trend_kiln_done_backlog", "待二选库存积压"),
            "title_i18n": _pack_i18n_text("alert_title_trend_kiln_done_backlog", default="待二选库存积压"),
            "active": (latest_kiln_done >= kiln_done_warn) and (kiln_done_drop <= 0),
            "text": _fmt_t(
                "zh",
                "alert_text_trend_kiln_done_backlog",
                "近{trend_hours}小时待二选维持在 {kiln_done_stock} 托（阈值 {warn_trays} 托），未见二选消耗。",
                trend_hours=trend_hours,
                kiln_done_stock=latest_kiln_done,
                warn_trays=kiln_done_warn,
            ),
            "text_i18n": _pack_i18n_text(
                "alert_text_trend_kiln_done_backlog",
                default="近{trend_hours}小时待二选维持在 {kiln_done_stock} 托（阈值 {warn_trays} 托），未见二选消耗。",
                trend_hours=trend_hours,
                kiln_done_stock=latest_kiln_done,
                warn_trays=kiln_done_warn,
            ),
        },
        {
            "key": "trend_finished_push_slow",
            "level": "L2",
            "title": _t("zh", "alert_title_trend_finished_push_slow", "成品推进偏慢"),
            "title_i18n": _pack_i18n_text("alert_title_trend_finished_push_slow", default="成品推进偏慢"),
            "active": (latest_kiln_done >= kiln_max_trays) and (product_gain <= 0),
            "text": _fmt_t(
                "zh",
                "alert_text_trend_finished_push_slow",
                "近{trend_hours}小时成品件数未增长（+{product_gain}），但待二选仍有 {kiln_done_stock} 托，建议检查二选与二次锯解节拍。",
                trend_hours=trend_hours,
                product_gain=product_gain,
                kiln_done_stock=latest_kiln_done,
            ),
            "text_i18n": _pack_i18n_text(
                "alert_text_trend_finished_push_slow",
                default="近{trend_hours}小时成品件数未增长（+{product_gain}），但待二选仍有 {kiln_done_stock} 托，建议检查二选与二次锯解节拍。",
                trend_hours=trend_hours,
                product_gain=product_gain,
                kiln_done_stock=latest_kiln_done,
            ),
        },
        {
            "key": "trend_kiln_stage_timing_block",
            "level": "L3" if (overdue_ready + overdue_unloading + overdue_drying) >= 2 else "L2",
            "title": _t("zh", "alert_title_trend_kiln_stage_timing", "窑段时长异常"),
            "title_i18n": _pack_i18n_text("alert_title_trend_kiln_stage_timing", default="窑段时长异常"),
            "active": (overdue_ready + overdue_unloading + overdue_drying) > 0,
            "text": _fmt_t(
                "zh",
                "alert_text_trend_kiln_stage_timing",
                "窑段出现超时：烘干超120小时 {overdue_drying} 台，完成待出超时 {overdue_ready} 台，出窑中超时 {overdue_unloading} 台。",
                overdue_drying=overdue_drying,
                overdue_ready=overdue_ready,
                overdue_unloading=overdue_unloading,
            ),
            "text_i18n": _pack_i18n_text(
                "alert_text_trend_kiln_stage_timing",
                default="窑段出现超时：烘干超120小时 {overdue_drying} 台，完成待出超时 {overdue_ready} 台，出窑中超时 {overdue_unloading} 台。",
                overdue_drying=overdue_drying,
                overdue_ready=overdue_ready,
                overdue_unloading=overdue_unloading,
            ),
        },
        {
            "key": "trend_log_drop",
            "level": "L2",
            "title": _t("zh", "alert_title_trend_log_drop", "原木库存下降过快"),
            "title_i18n": _pack_i18n_text("alert_title_trend_log_drop", default="原木库存下降过快"),
            "active": log_drop >= _to_float(cfg.get("trend_log_drop_mt"), 8.0),
            "text": _fmt_t("zh", "alert_text_trend_log_drop", "近{trend_hours}小时原木下降 {log_drop:.4f} MT", trend_hours=trend_hours, log_drop=log_drop),
            "text_i18n": _pack_i18n_text("alert_text_trend_log_drop", default="近{trend_hours}小时原木下降 {log_drop:.4f} MT", trend_hours=trend_hours, log_drop=log_drop),
        },
    ]
    return out


def evaluate_inventory_alerts(stock: dict, threshold_cfg: dict, lang: str = "zh") -> list[dict]:
    lc = _norm_lang(lang)
    now_ts = int(time.time())
    session = Session()
    try:
        cfg = get_alert_engine_config()
        events = _load_json(session, ALERT_EVENTS_KEY, [])
        history = _load_json(session, ALERT_HISTORY_KEY, [])
        state = _load_json(session, ALERT_STATE_KEY, {"last_notify_by_rule": {}})

        if not isinstance(events, list):
            events = []
        if not isinstance(history, list):
            history = []
        if not isinstance(state, dict):
            state = {"last_notify_by_rule": {}}
        if not isinstance(state.get("last_notify_by_rule"), dict):
            state["last_notify_by_rule"] = {}

        history = _append_history(history, stock, now_ts)
        min_ts = now_ts - _to_int(cfg.get("history_days"), 14) * 86400
        history = [p for p in history if _to_int(p.get("ts"), 0) >= min_ts]
        history = history[-3000:]

        rules = _build_rules(stock, cfg, threshold_cfg, history, lang=lc)
        rules.extend(_evaluate_trend_rules(history, cfg, threshold_cfg, lang=lc))
        rules.extend(_build_kiln_status_rules(stock, cfg, lang=lc))
        active_rules = {r["key"]: r for r in rules if bool(r.get("active"))}

        unresolved = {"open", "ack", "ignored"}

        # recover
        for ev in events:
            if str(ev.get("status") or "") not in unresolved:
                continue
            key = str(ev.get("rule_key") or "")
            if key not in active_rules:
                ev["status"] = "resolved"
                ev["resolved_at"] = now_ts
                ev["resolver"] = "system"
                note = str(ev.get("note") or "")
                if "条件恢复" not in note:
                    ev["note"] = (note + " | " if note else "") + "条件恢复自动关闭"

        # trigger/update
        for key, rule in active_rules.items():
            current = None
            for ev in reversed(events):
                if str(ev.get("rule_key") or "") == key and str(ev.get("status") or "") in unresolved:
                    current = ev
                    break

            if current:
                current["last_seen_at"] = now_ts
                current["seen_count"] = _to_int(current.get("seen_count"), 1) + 1
                # 非忽略状态，实时更新文案与等级
                if str(current.get("status") or "") != "ignored":
                    current["level"] = str(rule.get("level") or current.get("level") or "L1")
                    current["title"] = str(rule.get("title") or current.get("title") or "")
                    current["text"] = str(rule.get("text") or current.get("text") or "")
                    if isinstance(rule.get("title_i18n"), dict):
                        current["title_i18n"] = dict(rule.get("title_i18n") or {})
                    if isinstance(rule.get("text_i18n"), dict):
                        current["text_i18n"] = dict(rule.get("text_i18n") or {})
            else:
                ev = {
                    "id": f"AE{now_ts}{secrets.randbelow(100000):05d}",
                    "rule_key": key,
                    "level": str(rule.get("level") or "L1"),
                    "title": str(rule.get("title") or ""),
                    "text": str(rule.get("text") or ""),
                    "status": "open",
                    "created_at": now_ts,
                    "last_seen_at": now_ts,
                    "seen_count": 1,
                    "owner": "",
                    "note": "",
                }
                if isinstance(rule.get("title_i18n"), dict):
                    ev["title_i18n"] = dict(rule.get("title_i18n") or {})
                if isinstance(rule.get("text_i18n"), dict):
                    ev["text_i18n"] = dict(rule.get("text_i18n") or {})
                events.append(ev)

                dedup = _to_int(cfg.get("dedup_seconds"), 900)
                silence_until = _to_int(state.get("silence_until_ts"), 0)
                last_notify = _to_int(state["last_notify_by_rule"].get(key), 0)
                if _severity_rank(ev["level"]) >= 2 and now_ts >= silence_until and (now_ts - last_notify >= dedup):
                    _notify_l2_l3(ev["level"], ev["title"], ev["text"])
                    state["last_notify_by_rule"][key] = now_ts

        # keep tail
        events = events[-1500:]

        _save_json(session, ALERT_HISTORY_KEY, history)
        _save_json(session, ALERT_EVENTS_KEY, events)
        _save_json(session, ALERT_STATE_KEY, state)
        session.commit()

        active_events = [
            e for e in events
            if str(e.get("status") or "") in ("open", "ack")
        ]
        active_events.sort(key=lambda x: (_severity_rank(str(x.get("level") or "L1")) * -1, _to_int(x.get("created_at"), 0) * -1))

        items = []
        for e in active_events[:12]:
            title = _i18n_value(e.get("title_i18n"), lc, str(e.get("title") or ""))
            text = _i18n_value(e.get("text_i18n"), lc, str(e.get("text") or ""))
            owner = str(e.get("owner") or "").strip()
            if owner:
                suffix = _fmt_t(lc, "alert_owner_suffix", "（负责人:{owner}）", owner=owner)
            else:
                suffix = ""
            items.append(
                {
                    "id": str(e.get("id") or ""),
                    "level": _css_level(str(e.get("level") or "L1")),
                    "severity": str(e.get("level") or "L1"),
                    "text": f"[{str(e.get('level') or 'L1')}] {title}: {text}{suffix}",
                }
            )
        return items
    finally:
        session.close()


def _safe_ratio_score(a: float, b: float) -> float:
    x = max(0.0, float(a))
    y = max(0.0, float(b))
    if x <= 0 and y <= 0:
        return 60.0
    hi = max(x, y)
    lo = min(x, y)
    return max(0.0, min(100.0, (lo / hi) * 100.0))


def _front_stage_conversion_score(point: dict, history: list, history_timestamps: list[int] | None = None) -> float:
    """
    前段均衡（效率优先）：
    - 速度侧：关注 24h 内“锯解消耗”和“药浸消耗”是否同步推进。
    - 库存侧：锯解/药浸在制库存越少越好（次权重）。
    """
    ts = _to_int(point.get("ts"), int(time.time()))
    prev = _history_point_before_sorted(history, history_timestamps, ts - 24 * 3600) if history_timestamps else _history_point_before(history, ts - 24 * 3600)

    prev_saw = _to_int(prev.get("saw_stock"), _to_int(point.get("saw_stock"), 0))
    prev_dip = _to_int(prev.get("dip_stock"), _to_int(point.get("dip_stock"), 0))
    cur_saw = _to_int(point.get("saw_stock"), 0)
    cur_dip = _to_int(point.get("dip_stock"), 0)
    cur_sorting = _to_int(point.get("sorting_stock"), 0)

    saw_drop = max(0, prev_saw - cur_saw)
    dip_drop = max(0, prev_dip - cur_dip)
    saw_exec_score = _drop_ratio_score(prev_saw, cur_saw)
    dip_exec_score = _drop_ratio_score(prev_dip, cur_dip)
    stage_match_score = _safe_ratio_score(saw_drop, dip_drop)
    speed_score = saw_exec_score * 0.35 + dip_exec_score * 0.35 + stage_match_score * 0.30

    front_wip = max(0, cur_saw + cur_dip)
    all_front = max(1, front_wip + max(0, cur_sorting))
    inventory_share = float(front_wip) / float(all_front)
    inventory_score = max(0.0, min(100.0, (1.0 - inventory_share) * 100.0))

    # 速度权重高于库存权重
    score = speed_score * 0.65 + inventory_score * 0.35
    return max(0.0, min(100.0, score))


def _backlog_score(sorting_stock: int, kiln_done_stock: int) -> float:
    total = max(1, sorting_stock + kiln_done_stock)
    ratio = kiln_done_stock / total
    return max(0.0, min(100.0, 100.0 - ratio * 120.0))


def _product_band_score(product_count: int, ready: int, full: int, burst: int) -> float:
    c = int(product_count)
    if c < ready:
        return max(20.0, min(70.0, (c / max(1, ready)) * 70.0))
    if ready <= c <= full:
        return 95.0
    if full < c <= burst:
        return max(30.0, 95.0 - (c - full) * 2.0)
    return 10.0


def _product_health_score(point: dict, history: list, ready: int, full: int, burst: int, history_timestamps: list[int] | None = None) -> float:
    """
    成品健康（效率优先）：
    - 速度侧：关注 24h 内待二选消耗、成品增长与两者匹配度。
    - 库存侧：延用成品库存区间打分作为次权重。
    """
    ts = _to_int(point.get("ts"), int(time.time()))
    prev = _history_point_before_sorted(history, history_timestamps, ts - 24 * 3600) if history_timestamps else _history_point_before(history, ts - 24 * 3600)

    prev_kiln_done = _to_int(prev.get("kiln_done_stock"), _to_int(point.get("kiln_done_stock"), 0))
    prev_product = _to_int(prev.get("product_count"), _to_int(point.get("product_count"), 0))
    cur_kiln_done = _to_int(point.get("kiln_done_stock"), 0)
    cur_product = _to_int(point.get("product_count"), 0)

    kiln_done_drop = max(0, prev_kiln_done - cur_kiln_done)
    finished_gain = max(0, cur_product - prev_product)
    secondary_sort_speed = _drop_ratio_score(prev_kiln_done, cur_kiln_done)
    conversion_match = _safe_ratio_score(kiln_done_drop, finished_gain)

    if finished_gain > 0:
        finished_push = min(100.0, 80.0 + float(finished_gain) * 2.5)
    elif cur_kiln_done <= 2:
        finished_push = 72.0
    else:
        finished_push = 38.0

    efficiency_score = secondary_sort_speed * 0.35 + conversion_match * 0.35 + finished_push * 0.30
    inventory_score = _product_band_score(cur_product, ready, full, burst)
    score = efficiency_score * 0.60 + inventory_score * 0.40
    return max(0.0, min(100.0, score))


def _weighted_total_score(vec: dict, cfg: dict) -> float:
    wr = _to_float(cfg.get("weight_raw_security"), 20.0)
    wf = _to_float(cfg.get("weight_front_balance"), 20.0)
    wm = _to_float(cfg.get("weight_middle_flow"), 20.0)
    wb = _to_float(cfg.get("weight_backlog_health"), 20.0)
    wp = _to_float(cfg.get("weight_product_health"), 20.0)
    wk = 15.0
    total_w = max(1.0, wr + wf + wm + wb + wp + wk)
    score = (
        _to_float(vec.get("raw_security"), 0.0) * wr
        + _to_float(vec.get("front_balance"), 0.0) * wf
        + _to_float(vec.get("middle_flow"), 0.0) * wm
        + _to_float(vec.get("backlog_health"), 0.0) * wb
        + _to_float(vec.get("product_health"), 0.0) * wp
        + _to_float(vec.get("kiln_health"), 0.0) * wk
    ) / total_w
    return round(max(0.0, min(100.0, score)), 1)


def _apply_bonus(vec: dict, bonus: float, cfg: dict) -> dict:
    out = dict(vec or {})
    if bonus <= 0:
        out["total_score"] = _weighted_total_score(out, cfg)
        return out
    half = float(bonus) / 2.0
    out["middle_flow"] = round(min(100.0, _to_float(out.get("middle_flow"), 0.0) + half), 1)
    out["backlog_health"] = round(min(100.0, _to_float(out.get("backlog_health"), 0.0) + half), 1)
    out["total_score"] = _weighted_total_score(out, cfg)
    return out


def _smooth_with_prev(cur: dict, prev: dict, window_points: int, cfg: dict) -> dict:
    w = max(1, _to_int(window_points, 1))
    if w <= 1:
        out = dict(cur or {})
        out["total_score"] = _weighted_total_score(out, cfg)
        return out
    out = dict(cur or {})
    for k in ("raw_security", "front_balance", "middle_flow", "backlog_health", "product_health", "kiln_health"):
        c = _to_float((cur or {}).get(k), 0.0)
        p = _to_float((prev or {}).get(k), c)
        out[k] = round((c * (w - 1) + p) / float(w), 1)
    out["total_score"] = _weighted_total_score(out, cfg)
    return out


def _backlog_drop(history: list, begin_ts: int, end_ts: int) -> float:
    pts = [p for p in history if begin_ts <= _to_int(p.get("ts"), 0) <= end_ts]
    if len(pts) < 2:
        return 0.0
    pts.sort(key=lambda x: _to_int(x.get("ts"), 0))
    first = _to_float((pts[0] or {}).get("kiln_done_stock"), 0.0)
    last = _to_float((pts[-1] or {}).get("kiln_done_stock"), 0.0)
    return round(first - last, 2)


def _history_point_before(history: list, target_ts: int) -> dict:
    pts = [p for p in history if _to_int((p or {}).get("ts"), 0) <= target_ts]
    if not pts:
        return history[0] if history else {}
    pts.sort(key=lambda x: _to_int((x or {}).get("ts"), 0))
    return pts[-1] or {}


def _history_point_before_sorted(history: list, history_timestamps: list[int] | None, target_ts: int) -> dict:
    if not history:
        return {}
    if not history_timestamps:
        return _history_point_before(history, target_ts)
    idx = bisect_right(history_timestamps, int(target_ts)) - 1
    if idx < 0:
        return history[0] or {}
    if idx >= len(history):
        idx = len(history) - 1
    return history[idx] or {}


def _drop_ratio_score(prev_val: int, cur_val: int) -> float:
    prev_n = max(0, _to_int(prev_val, 0))
    cur_n = max(0, _to_int(cur_val, 0))
    if prev_n <= 0 and cur_n <= 0:
        return 100.0
    if prev_n <= 0 and cur_n > 0:
        return max(20.0, min(70.0, 70.0 - cur_n * 2.0))
    consumed = max(0, prev_n - cur_n)
    return max(0.0, min(100.0, (float(consumed) / float(max(1, prev_n))) * 100.0))


def _middle_stage_flow_score(point: dict, history: list, history_timestamps: list[int] | None = None) -> float:
    ts = _to_int(point.get("ts"), int(time.time()))
    prev = _history_point_before_sorted(history, history_timestamps, ts - 24 * 3600) if history_timestamps else _history_point_before(history, ts - 24 * 3600)

    prev_sorting = _to_int(prev.get("sorting_stock"), _to_int(point.get("sorting_stock"), 0))
    prev_kiln_done = _to_int(prev.get("kiln_done_stock"), _to_int(point.get("kiln_done_stock"), 0))
    prev_product = _to_int(prev.get("product_count"), _to_int(point.get("product_count"), 0))

    cur_sorting = _to_int(point.get("sorting_stock"), 0)
    cur_kiln_done = _to_int(point.get("kiln_done_stock"), 0)
    cur_product = _to_int(point.get("product_count"), 0)

    sorting_consume_score = _drop_ratio_score(prev_sorting, cur_sorting)
    kiln_done_consume_score = _drop_ratio_score(prev_kiln_done, cur_kiln_done)

    finished_gain = max(0, cur_product - prev_product)
    if finished_gain > 0:
        finish_push_score = min(100.0, 82.0 + float(finished_gain) * 2.0)
    elif cur_kiln_done <= prev_kiln_done:
        finish_push_score = 68.0
    else:
        finish_push_score = 42.0

    kiln_health = _to_float(point.get("kiln_health"), 60.0)
    overdue_ready = _to_int(point.get("kiln_overdue_ready"), 0)
    overdue_unloading = _to_int(point.get("kiln_overdue_unloading"), 0)
    overdue_drying = _to_int(point.get("kiln_overdue_drying"), 0)
    timing_score = kiln_health - overdue_ready * 12.0 - overdue_unloading * 10.0 - overdue_drying * 8.0
    timing_score = max(0.0, min(100.0, timing_score))

    speed_score = (
        sorting_consume_score * 0.30
        + kiln_done_consume_score * 0.30
        + finish_push_score * 0.25
        + timing_score * 0.15
    )

    # 库存仅做轻量约束，避免“高库存但有动作”被一票否决。
    queue_penalty = 0.0
    queue_penalty += max(0.0, (cur_sorting - 8) * 0.60)
    queue_penalty += max(0.0, (cur_kiln_done - 12) * 0.50)
    queue_penalty = min(18.0, queue_penalty)
    score = speed_score - queue_penalty
    return max(0.0, min(100.0, score))


def _make_efficiency_vector(
    point: dict,
    cfg: dict,
    history: list,
    daily_use: float | None = None,
    history_timestamps: list[int] | None = None,
) -> dict:
    log_stock = _to_float(point.get("log_stock"), 0.0)
    saw_stock = _to_int(point.get("saw_stock"), 0)
    dip_stock = _to_int(point.get("dip_stock"), 0)
    sorting_stock = _to_int(point.get("sorting_stock"), 0)
    kiln_done_stock = _to_int(point.get("kiln_done_stock"), 0)
    product_count = _to_int(point.get("product_count"), 0)

    daily_use = _estimate_daily_log_consumption(history) if daily_use is None else float(daily_use)
    days_left = (log_stock / daily_use) if daily_use > 0 else 7.0
    raw_sec = max(0.0, min(100.0, (days_left / 3.0) * 100.0))
    front_balance = _front_stage_conversion_score(point, history, history_timestamps=history_timestamps)
    middle_flow = _middle_stage_flow_score(point, history, history_timestamps=history_timestamps)
    backlog_health = _backlog_score(sorting_stock, kiln_done_stock)
    product_health = _product_health_score(
        point,
        history,
        _to_int(cfg.get("product_ready_threshold"), 26),
        _to_int(cfg.get("product_full_threshold"), 76),
        _to_int(cfg.get("product_burst_threshold"), 100),
        history_timestamps=history_timestamps,
    )
    kiln_health = max(0.0, min(100.0, _to_float(point.get("kiln_health"), 60.0)))
    # 窑效率会影响积压健康；中段流速已包含窑阶段纪律指标。
    backlog_health = round((backlog_health * 0.8) + (kiln_health * 0.2), 1)

    # 瓶颈模式：当二次分拣积压高时，避免图形“塌死”，保留改善空间（不造假）。
    if _to_int(cfg.get("enable_bottleneck_mode"), 1) == 1 and kiln_done_stock >= _to_int(cfg.get("bottleneck_kiln_done_threshold"), 40):
        relax = max(0.0, min(1.0, _to_float(cfg.get("bottleneck_relax_weight_pct"), 35.0) / 100.0))
        middle_flow = middle_flow * (1.0 - relax) + 50.0 * relax
        backlog_health = backlog_health * (1.0 - relax) + 55.0 * relax

    vec = {
        "raw_security": round(raw_sec, 1),
        "front_balance": round(front_balance, 1),
        "middle_flow": round(middle_flow, 1),
        "backlog_health": round(backlog_health, 1),
        "product_health": round(product_health, 1),
        "kiln_health": round(kiln_health, 1),
    }
    vec["total_score"] = _weighted_total_score(vec, cfg)
    return vec


def _period_avg_vector(history: list, cfg: dict, begin_ts: int, end_ts: int) -> dict:
    pts = [p for p in history if begin_ts <= _to_int(p.get("ts"), 0) <= end_ts]
    if not pts:
        return {"raw_security": 0.0, "front_balance": 0.0, "middle_flow": 0.0, "backlog_health": 0.0, "product_health": 0.0, "kiln_health": 0.0, "total_score": 0.0}
    acc = {"raw_security": 0.0, "front_balance": 0.0, "middle_flow": 0.0, "backlog_health": 0.0, "product_health": 0.0, "kiln_health": 0.0, "total_score": 0.0}
    for p in pts:
        v = _make_efficiency_vector(p, cfg, history)
        for k in acc.keys():
            acc[k] += _to_float(v.get(k), 0.0)
    n = float(len(pts))
    return {k: round(acc[k] / n, 1) for k in acc.keys()}


def _period_avg_vector_precomputed(precomputed: list[tuple[int, dict]], begin_ts: int, end_ts: int) -> dict:
    pts = [vec for ts, vec in precomputed if begin_ts <= ts <= end_ts]
    if not pts:
        return {"raw_security": 0.0, "front_balance": 0.0, "middle_flow": 0.0, "backlog_health": 0.0, "product_health": 0.0, "kiln_health": 0.0, "total_score": 0.0}
    acc = {"raw_security": 0.0, "front_balance": 0.0, "middle_flow": 0.0, "backlog_health": 0.0, "product_health": 0.0, "kiln_health": 0.0, "total_score": 0.0}
    for vec in pts:
        for k in acc.keys():
            acc[k] += _to_float(vec.get(k), 0.0)
    n = float(len(pts))
    return {k: round(acc[k] / n, 1) for k in acc.keys()}


def _efficiency_summary(history: list, cfg: dict, lang: str = "zh") -> dict:
    signature = _efficiency_cache_signature(history, cfg, lang)
    cached_sig = str(_EFFICIENCY_MEMORY_CACHE.get("signature") or "")
    cached_payload = _EFFICIENCY_MEMORY_CACHE.get("payload")
    if cached_sig == signature and isinstance(cached_payload, dict):
        return cached_payload

    payload = _compute_efficiency_summary(history, cfg, lang=lang)
    _EFFICIENCY_MEMORY_CACHE["signature"] = signature
    _EFFICIENCY_MEMORY_CACHE["payload"] = payload
    _EFFICIENCY_MEMORY_CACHE["generated_ts"] = int(time.time())
    return payload


def _build_ai_metric_insights(efficiency: dict, throughput: dict, intelligence: dict, lang: str = "zh") -> dict:
    lc = _norm_lang(lang)
    cur_day = (throughput or {}).get("current_day", {}) if isinstance(throughput, dict) else {}
    cmp_week = ((throughput or {}).get("comparison") or {}).get("week", {}) if isinstance(throughput, dict) else {}
    eff_cur = (efficiency or {}).get("current", {}) if isinstance(efficiency, dict) else {}
    eff_week = (efficiency or {}).get("week", {}) if isinstance(efficiency, dict) else {}
    eff_week_prev = (efficiency or {}).get("week_prev", {}) if isinstance(efficiency, dict) else {}

    ratios = [
        ("药浸/锯解", _to_float(cur_day.get("ratio_dip_vs_saw"), 0.0), "Dip/Saw"),
        ("拣选/药浸", _to_float(cur_day.get("ratio_sort_vs_dip"), 0.0), "Sort/Dip"),
        ("二选/拣选", _to_float(cur_day.get("ratio_secondary_vs_sort"), 0.0), "Secondary/Sort"),
        ("成品/二选", _to_float(cur_day.get("ratio_product_vs_secondary"), 0.0), "Product/Secondary"),
    ]
    weakest_ratio = min(ratios, key=lambda item: item[1]) if ratios else ("-", 0.0, "-")

    losses = [
        ("原木→锯解", _to_float(cur_day.get("loss_raw_to_saw_rate_pct"), 0.0), "Raw->Saw"),
        ("入窑→出窑", _to_float(cur_day.get("loss_kiln_in_to_out_rate_pct"), 0.0), "Kiln In->Out"),
        ("出窑→成品", _to_float(cur_day.get("loss_out_to_product_rate_pct"), 0.0), "Out->Product"),
    ]
    highest_loss = max(losses, key=lambda item: item[1]) if losses else ("-", 0.0, "-")

    week_mom = cmp_week.get("mom_pct")
    week_mom = None if week_mom is None else round(_to_float(week_mom, 0.0), 1)
    middle_delta = round(_to_float(eff_week.get("middle_flow"), 0.0) - _to_float(eff_week_prev.get("middle_flow"), 0.0), 1)
    back_delta = round(_to_float(eff_week.get("backlog_health"), 0.0) - _to_float(eff_week_prev.get("backlog_health"), 0.0), 1)
    root_name = str((((intelligence or {}).get("priority_stage") or {}).get("name")) or (((intelligence or {}).get("root_bottleneck") or {}).get("name")) or "-")

    if lc == "en":
        throughput_summary = f"AI reads today's weakest yield link at {weakest_ratio[2]} ({weakest_ratio[1]:.1f}%)."
        throughput_action = f"Treat {root_name} as the first improvement lane, and especially watch the {weakest_ratio[2]} conversion."
        loss_summary = f"AI sees the largest loss currently at {highest_loss[2]} ({highest_loss[1]:.1f}%)."
        loss_action = "Check whether this is a normal process loss, a material-quality issue, or a handoff/tooling issue."
        trend_summary = f"Weekly finished output is {'up' if (week_mom or 0) >= 0 else 'down'} {abs(week_mom or 0):.1f}% vs previous week; middle-flow delta {middle_delta:+.1f}, backlog-health delta {back_delta:+.1f}."
        trend_action = "If output is not improving while middle/back sections stay weak, treat it as a sustained issue instead of a one-day fluctuation."
    elif lc == "my":
        throughput_summary = f"AI အမြင်အရ ယနေ့ အနည်းဆုံးထွက်နှုန်းက {weakest_ratio[0]} ({weakest_ratio[1]:.1f}%) ဖြစ်ပါသည်။"
        throughput_action = f"{root_name} ကို ပထမဦးစားပေးတိုးမြှင့်ပြီး {weakest_ratio[0]} အချိုးကို အနီးကပ်စောင့်ကြည့်ပါ။"
        loss_summary = f"AI အမြင်အရ လက်ရှိဆုံးရှုံးမှုအမြင့်ဆုံးအပိုင်းမှာ {highest_loss[0]} ({highest_loss[1]:.1f}%) ဖြစ်ပါသည်။"
        loss_action = "ပုံမှန် process loss လား၊ ကုန်ကြမ်း quality ပြဿနာလား၊ handoff/tooling ပြဿနာလားဆိုတာ ခွဲကြည့်ပါ။"
        trend_summary = f"ဒီအပတ်ကုန်ချောထွက်အားသည် အရင်အပတ်နှင့်ယှဉ်လျှင် {'တက်' if (week_mom or 0) >= 0 else 'ကျ'} {abs(week_mom or 0):.1f}% ဖြစ်ပြီး middle-flow {middle_delta:+.1f}၊ backlog-health {back_delta:+.1f} ဖြစ်ပါသည်။"
        trend_action = "ထွက်အားမတက်သေးဘဲ အလယ်ပိုင်း/နောက်ပိုင်း အားနည်းနေလျှင် တစ်ရက်တည်းပြဿနာမဟုတ်ဘဲ ဆက်တိုက်ပြဿနာအဖြစ် ကိုင်တွယ်ပါ။"
    else:
        throughput_summary = f"AI 判断今天最弱的产比链更像在「{weakest_ratio[0]}」，当前只有 {weakest_ratio[1]:.1f}%。"
        throughput_action = f"先按「{root_name}」去提产，同时重点盯住「{weakest_ratio[0]}」这段转化。"
        loss_summary = f"AI 判断当前损耗最高的环节在「{highest_loss[0]}」，损耗率约 {highest_loss[1]:.1f}%。"
        loss_action = "先区分这是正常工艺损耗，还是原料质量、承接节拍、工具设备导致的异常损耗。"
        trend_summary = f"本周成品产出较上周{'上升' if (week_mom or 0) >= 0 else '下降'} {abs(week_mom or 0):.1f}%，同时中段流速 {middle_delta:+.1f}、积压健康 {back_delta:+.1f}。"
        trend_action = "如果成品还没起色，但中段和后段一直偏弱，就按持续性问题处理，不要只当成某一天波动。"

    return {
        "throughput": {"summary": throughput_summary, "action": throughput_action},
        "yield_loss": {"summary": loss_summary, "action": loss_action},
        "trend": {"summary": trend_summary, "action": trend_action},
    }


def _throughput_ai_signature(cfg: dict, throughput: dict, lang: str) -> str:
    payload = {
        "lang": _norm_lang(lang),
        "coeffs": {
            "spec_override": _to_float((cfg or {}).get("throughput_spec_tray_m3_override"), 0.0),
            "raw_mt_to_m3_factor": _to_float((cfg or {}).get("raw_mt_to_m3_factor"), 1.0),
            "kiln_green_to_dry_shrinkage_pct": _to_float((cfg or {}).get("kiln_green_to_dry_shrinkage_pct"), 7.5),
        },
        "current_day": ((throughput or {}).get("current_day") or {}) if isinstance(throughput, dict) else {},
        "current_week": ((throughput or {}).get("current_week") or {}) if isinstance(throughput, dict) else {},
        "comparison": ((throughput or {}).get("comparison") or {}) if isinstance(throughput, dict) else {},
    }
    text = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


def _efficiency_cache_signature(history: list, cfg: dict, lang: str) -> str:
    lc = _norm_lang(lang)
    payload = {
        "lang": lc,
        "cfg": {
            "product_ready_threshold": _to_int((cfg or {}).get("product_ready_threshold"), 26),
            "product_full_threshold": _to_int((cfg or {}).get("product_full_threshold"), 76),
            "product_burst_threshold": _to_int((cfg or {}).get("product_burst_threshold"), 100),
            "enable_bottleneck_mode": _to_int((cfg or {}).get("enable_bottleneck_mode"), 1),
            "bottleneck_kiln_done_threshold": _to_int((cfg or {}).get("bottleneck_kiln_done_threshold"), 40),
            "bottleneck_relax_weight_pct": _to_float((cfg or {}).get("bottleneck_relax_weight_pct"), 35.0),
            "improve_bonus_2day": _to_float((cfg or {}).get("improve_bonus_2day"), 10.0),
            "improve_bonus_3day": _to_float((cfg or {}).get("improve_bonus_3day"), 5.0),
            "smooth_day_window_points": _to_int((cfg or {}).get("smooth_day_window_points"), 3),
            "smooth_week_window_points": _to_int((cfg or {}).get("smooth_week_window_points"), 3),
            "weight_raw_security": _to_int((cfg or {}).get("weight_raw_security"), 20),
            "weight_front_balance": _to_int((cfg or {}).get("weight_front_balance"), 20),
            "weight_middle_flow": _to_int((cfg or {}).get("weight_middle_flow"), 20),
            "weight_backlog_health": _to_int((cfg or {}).get("weight_backlog_health"), 20),
            "weight_product_health": _to_int((cfg or {}).get("weight_product_health"), 20),
        },
        # 效率看板只依赖库存/托数/窑健康等信号，保留这些字段即可准确失效缓存。
        "history": [
            {
                "ts": _to_int((p or {}).get("ts"), 0),
                "log_stock": _to_float((p or {}).get("log_stock"), 0.0),
                "saw_stock": _to_int((p or {}).get("saw_stock"), 0),
                "dip_stock": _to_int((p or {}).get("dip_stock"), 0),
                "sorting_stock": _to_int((p or {}).get("sorting_stock"), 0),
                "kiln_done_stock": _to_int((p or {}).get("kiln_done_stock"), 0),
                "product_count": _to_int((p or {}).get("product_count"), 0),
                "kiln_health": _to_float((p or {}).get("kiln_health"), 0.0),
                "kiln_overdue_ready": _to_int((p or {}).get("kiln_overdue_ready"), 0),
                "kiln_overdue_unloading": _to_int((p or {}).get("kiln_overdue_unloading"), 0),
                "kiln_overdue_drying": _to_int((p or {}).get("kiln_overdue_drying"), 0),
            }
            for p in (history or [])
        ],
    }
    text = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


def _compute_efficiency_summary(history: list, cfg: dict, lang: str = "zh") -> dict:
    lc = _norm_lang(lang)
    radar_labels = [
        _t(lc, "radar_axis_raw_security", "原木保障"),
        _t(lc, "radar_axis_front_balance", "前段均衡"),
        _t(lc, "radar_axis_middle_flow", "中段流速"),
        _t(lc, "radar_axis_backlog_health", "积压健康"),
        _t(lc, "radar_axis_product_health", "成品健康"),
        _t(lc, "radar_axis_kiln_efficiency", "窑效率"),
    ]
    if not history:
        z = {"raw_security": 0.0, "front_balance": 0.0, "middle_flow": 0.0, "backlog_health": 0.0, "product_health": 0.0, "kiln_health": 0.0, "total_score": 0.0}
        return {
            "current": z,
            "day": z,
            "week": z,
            "month": z,
            "day_prev": z,
            "week_prev": z,
            "month_prev": z,
            "radar_labels": radar_labels,
            "radar": {"current": [0, 0, 0, 0, 0, 0], "day": [0, 0, 0, 0, 0, 0], "week": [0, 0, 0, 0, 0, 0], "month": [0, 0, 0, 0, 0, 0]},
        }
    now_ts = int(time.time())
    now_dt = datetime.now()
    day = 86400
    history_sorted = sorted(history, key=lambda x: _to_int((x or {}).get("ts"), 0))
    history_timestamps = [_to_int((p or {}).get("ts"), 0) for p in history_sorted]
    daily_use = _estimate_daily_log_consumption(history_sorted)
    precomputed = [
        (
            ts,
            _make_efficiency_vector(
                point,
                cfg,
                history_sorted,
                daily_use=daily_use,
                history_timestamps=history_timestamps,
            ),
        )
        for ts, point in zip(history_timestamps, history_sorted)
    ]

    current = precomputed[-1][1]
    day_start, day_end = _period_ts_range("day", now_dt)
    week_start, week_end = _period_ts_range("week", now_dt)
    month_start, month_end = _period_ts_range("month", now_dt)
    day_prev = _period_avg_vector_precomputed(precomputed, day_start - day, day_start)
    week_prev_start, week_prev_end = _period_ts_range("week_prev", now_dt)
    month_prev_start, month_prev_end = _period_ts_range("month_prev", now_dt)
    day_vec = _period_avg_vector_precomputed(precomputed, day_start, day_end)
    week_vec = _period_avg_vector_precomputed(precomputed, week_start, week_end)
    month_vec = _period_avg_vector_precomputed(precomputed, month_start, month_end)
    week_prev = _period_avg_vector_precomputed(precomputed, week_prev_start, week_prev_end)
    month_prev = _period_avg_vector_precomputed(precomputed, month_prev_start, month_prev_end)

    drop_today = _backlog_drop(history_sorted, day_start, day_end)
    drop_prev_day = _backlog_drop(history_sorted, day_start - day, day_start)
    drop_prev2_day = _backlog_drop(history_sorted, day_start - 2 * day, day_start - day)
    bonus = 0.0
    if drop_today > 0 and drop_prev_day > 0:
        bonus += _to_float(cfg.get("improve_bonus_2day"), 10.0)
    if drop_today > 0 and drop_prev_day > 0 and drop_prev2_day > 0:
        bonus += _to_float(cfg.get("improve_bonus_3day"), 5.0)

    current = _apply_bonus(current, bonus, cfg)
    day_vec = _apply_bonus(day_vec, bonus, cfg)
    week_vec = _apply_bonus(week_vec, bonus, cfg)
    month_vec = _apply_bonus(month_vec, bonus, cfg)

    day_vec = _smooth_with_prev(day_vec, day_prev, _to_int(cfg.get("smooth_day_window_points"), 3), cfg)
    week_vec = _smooth_with_prev(week_vec, week_prev, _to_int(cfg.get("smooth_week_window_points"), 3), cfg)

    def _vec6(v):
        return [v.get("raw_security", 0), v.get("front_balance", 0), v.get("middle_flow", 0), v.get("backlog_health", 0), v.get("product_health", 0), v.get("kiln_health", 0)]

    return {
        "current": current,
        "day": day_vec,
        "week": week_vec,
        "month": month_vec,
        "day_prev": day_prev,
        "week_prev": week_prev,
        "month_prev": month_prev,
        "radar_labels": radar_labels,
        "radar": {
            "current": _vec6(current),
            "day": _vec6(day_vec),
            "week": _vec6(week_vec),
            "month": _vec6(month_vec),
        },
    }


def _build_ai_calibrated_throughput(session, cfg: dict, throughput: dict, lang: str = "zh") -> dict:
    lc = _norm_lang(lang)
    current_coeffs = {
        "spec_tray_m3_override": round(_to_float((cfg or {}).get("throughput_spec_tray_m3_override"), 0.0), 4),
        "raw_mt_to_m3_factor": round(_to_float((cfg or {}).get("raw_mt_to_m3_factor"), 1.0), 4),
        "kiln_green_to_dry_shrinkage_pct": round(_to_float((cfg or {}).get("kiln_green_to_dry_shrinkage_pct"), 7.5), 3),
    }
    if not ALERT_AI_CALIBRATION_ENABLED:
        return {
            "signature": "disabled",
            "generated_ts": int(time.time()),
            "source": "disabled",
            "summary": "AI 系数校准已关闭，当前沿用系统系数。",
            "reason": "",
            "action": "",
            "current_coefficients": current_coeffs,
            "recommended_coefficients": dict(current_coeffs),
            "show_recommendation": False,
            "calculated": throughput,
        }

    signature = _throughput_ai_signature(cfg, throughput, lc)
    now_ts = int(time.time())
    cached = _load_json(session, ALERT_AI_THROUGHPUT_CACHE_KEY, {})
    if isinstance(cached, dict):
        cached_sig = str(cached.get("signature") or "")
        cached_ts = _to_int(cached.get("generated_ts"), 0)
        if cached_sig == signature and (now_ts - cached_ts) <= 6 * 3600:
            return cached

    cur_day = ((throughput or {}).get("current_day") or {}) if isinstance(throughput, dict) else {}
    cur_week = ((throughput or {}).get("current_week") or {}) if isinstance(throughput, dict) else {}
    cmp_week = (((throughput or {}).get("comparison") or {}).get("week") or {}) if isinstance(throughput, dict) else {}
    prompt_payload = {
        "language": lc,
        "goal": "校准木材厂环节产比/损耗/趋势的计算系数，给出建议值。",
        "current_coefficients": current_coeffs,
        "snapshot": {
            "day": {
                "saw_m3": cur_day.get("saw_m3"),
                "dip_m3": cur_day.get("dip_m3"),
                "sort_m3": cur_day.get("sort_m3"),
                "secondary_m3": cur_day.get("secondary_m3"),
                "product_m3": cur_day.get("product_m3"),
                "ratio_dip_vs_saw": cur_day.get("ratio_dip_vs_saw"),
                "ratio_sort_vs_dip": cur_day.get("ratio_sort_vs_dip"),
                "ratio_secondary_vs_sort": cur_day.get("ratio_secondary_vs_sort"),
                "ratio_product_vs_secondary": cur_day.get("ratio_product_vs_secondary"),
                "loss_raw_to_saw_rate_pct": cur_day.get("loss_raw_to_saw_rate_pct"),
                "loss_kiln_in_to_out_rate_pct": cur_day.get("loss_kiln_in_to_out_rate_pct"),
                "loss_out_to_product_rate_pct": cur_day.get("loss_out_to_product_rate_pct"),
            },
            "week": {
                "product_m3": cur_week.get("product_m3"),
                "mom_pct": cmp_week.get("mom_pct"),
                "yoy_pct": cmp_week.get("yoy_pct"),
                "loss_raw_to_saw_rate_pct": cur_week.get("loss_raw_to_saw_rate_pct"),
                "loss_kiln_in_to_out_rate_pct": cur_week.get("loss_kiln_in_to_out_rate_pct"),
                "loss_out_to_product_rate_pct": cur_week.get("loss_out_to_product_rate_pct"),
            },
        },
    }
    if lc == "en":
        system_prompt = "You are AIF's throughput calibration AI. Return JSON only."
    elif lc == "my":
        system_prompt = "သင်သည် AIF ၏ throughput calibration AI ဖြစ်သည်။ JSON ပဲထုတ်ပါ။"
    else:
        system_prompt = "你是 AIF 的产比损耗系数校准 AI，只输出 JSON。"
    user_prompt = (
        "请基于下面的快照，判断当前系统系数是否偏离现场现实，并给出建议系数。\n"
        "要求：\n"
        "1. 只输出 JSON。\n"
        "2. 建议值不要离谱，尽量在现场可接受的小范围调整。\n"
        "3. 如果当前值已经合理，也可以建议维持不变。\n"
        "4. 输出字段："
        "{\"recommended\":{\"spec_tray_m3_override\":0.0,\"raw_mt_to_m3_factor\":1.0,\"kiln_green_to_dry_shrinkage_pct\":7.5},"
        "\"summary\":\"一句摘要\","
        "\"reason\":\"一句理由\","
        "\"action\":\"一句建议\"}\n"
        f"{json.dumps(prompt_payload, ensure_ascii=False, separators=(',', ':'))}"
    )

    recommended = dict(current_coeffs)
    summary = ""
    reason = ""
    action = ""
    source = "fallback"
    try:
        raw = ask_ai(user_prompt, system_prompt=system_prompt, max_tokens=180, timeout=28)
        try:
            parsed = json.loads(raw)
        except Exception:
            parsed = json.loads(_extract_first_json_object(raw))
        rec = parsed.get("recommended", {}) if isinstance(parsed, dict) and isinstance(parsed.get("recommended"), dict) else {}
        recommended = {
            "spec_tray_m3_override": round(max(0.0, min(5.0, _to_float(rec.get("spec_tray_m3_override"), current_coeffs["spec_tray_m3_override"]))), 4),
            "raw_mt_to_m3_factor": round(max(0.1, min(3.0, _to_float(rec.get("raw_mt_to_m3_factor"), current_coeffs["raw_mt_to_m3_factor"]))), 4),
            "kiln_green_to_dry_shrinkage_pct": round(max(0.0, min(30.0, _to_float(rec.get("kiln_green_to_dry_shrinkage_pct"), current_coeffs["kiln_green_to_dry_shrinkage_pct"]))), 3),
        }
        summary = str(parsed.get("summary") or "").strip()
        reason = str(parsed.get("reason") or "").strip()
        action = str(parsed.get("action") or "").strip()
        source = "ai"
    except Exception:
        if lc == "en":
            summary = "AI calibration is temporarily unavailable, so current coefficients are kept."
            reason = "No valid AI calibration result was returned."
            action = "Keep current coefficients and review again after more production data accumulates."
        elif lc == "my":
            summary = "AI calibration မရရှိသေးသောကြောင့် လက်ရှိ coefficient များကို ဆက်သုံးထားသည်။"
            reason = "မှန်ကန်သော AI calibration result မပြန်လာပါ။"
            action = "လက်ရှိ coefficient များကို ဆက်သုံးပြီး ထုတ်လုပ်မှုဒေတာပိုစုဆောင်းပြီးနောက် ပြန်စစ်ပါ။"
        else:
            summary = "AI 校准暂不可用，当前先沿用系统系数。"
            reason = "本轮没有拿到有效的 AI 系数校准结果。"
            action = "先沿用当前系数，等更多生产数据累积后再复核。"

    cfg_ai = dict(cfg or {})
    cfg_ai["throughput_spec_tray_m3_override"] = recommended["spec_tray_m3_override"]
    cfg_ai["raw_mt_to_m3_factor"] = recommended["raw_mt_to_m3_factor"]
    cfg_ai["kiln_green_to_dry_shrinkage_pct"] = recommended["kiln_green_to_dry_shrinkage_pct"]
    calculated = _build_stage_throughput_payload(lang=lc, cfg=cfg_ai)
    out = {
        "signature": signature,
        "generated_ts": now_ts,
        "generated_at": _format_ts(now_ts),
        "source": source,
        "current_coefficients": current_coeffs,
        "recommended_coefficients": recommended,
        "summary": summary,
        "reason": reason,
        "action": action,
        "calculated": calculated,
    }
    spec_delta = abs(_to_float(recommended.get("spec_tray_m3_override"), 0.0) - _to_float(current_coeffs.get("spec_tray_m3_override"), 0.0))
    raw_delta = abs(_to_float(recommended.get("raw_mt_to_m3_factor"), 1.0) - _to_float(current_coeffs.get("raw_mt_to_m3_factor"), 1.0))
    shrink_delta = abs(_to_float(recommended.get("kiln_green_to_dry_shrinkage_pct"), 7.5) - _to_float(current_coeffs.get("kiln_green_to_dry_shrinkage_pct"), 7.5))
    out["show_recommendation"] = bool(
        source == "ai" and (
            spec_delta >= 0.03 or
            raw_delta >= 0.05 or
            shrink_delta >= 0.8
        )
    )
    _save_json(session, ALERT_AI_THROUGHPUT_CACHE_KEY, out)
    session.commit()
    return out


def update_alert_event(event_id: str, action: str, operator: str, owner: str = "", note: str = "") -> tuple[bool, str]:
    eid = str(event_id or "").strip()
    act = str(action or "").strip().lower()
    if not eid:
        return False, "缺少预警ID"
    if act not in {"ack", "ignore", "resolve", "reopen"}:
        return False, "不支持的操作"

    session = Session()
    try:
        events = _load_json(session, ALERT_EVENTS_KEY, [])
        if not isinstance(events, list):
            events = []
        target = None
        for e in reversed(events):
            if str(e.get("id") or "") == eid:
                target = e
                break
        if not target:
            return False, "未找到预警"

        now_ts = int(time.time())
        if act == "ack":
            target["status"] = "ack"
            target["ack_at"] = now_ts
        elif act == "ignore":
            target["status"] = "ignored"
            target["ignored_at"] = now_ts
        elif act == "resolve":
            target["status"] = "resolved"
            target["resolved_at"] = now_ts
            target["resolver"] = str(operator or "")
        elif act == "reopen":
            target["status"] = "open"
            target["reopened_at"] = now_ts

        if owner:
            target["owner"] = str(owner).strip()
        if note:
            old = str(target.get("note") or "")
            merged = (old + " | " if old else "") + str(note).strip()
            target["note"] = merged[:500]

        _save_json(session, ALERT_EVENTS_KEY, events)
        session.commit()
        return True, "ok"
    finally:
        session.close()


def _weekly_stats(events: list) -> dict:
    now_ts = int(time.time())
    cutoff = now_ts - 7 * 86400
    week = [e for e in events if _to_int(e.get("created_at"), 0) >= cutoff]
    by_level = {"L1": 0, "L2": 0, "L3": 0}
    resolved = 0
    total_resolve_secs = 0
    for e in week:
        lv = str(e.get("level") or "L1").upper()
        if lv not in by_level:
            lv = "L1"
        by_level[lv] += 1
        if str(e.get("status") or "") == "resolved" and _to_int(e.get("resolved_at"), 0) > 0:
            resolved += 1
            total_resolve_secs += max(0, _to_int(e.get("resolved_at"), 0) - _to_int(e.get("created_at"), 0))
    total = len(week)
    resolve_rate = round((resolved / total) * 100.0, 1) if total > 0 else 0.0
    avg_resolve_hours = round((total_resolve_secs / 3600.0 / resolved), 2) if resolved > 0 else 0.0
    return {
        "total": total,
        "by_level": by_level,
        "resolved": resolved,
        "resolve_rate": resolve_rate,
        "avg_resolve_hours": avg_resolve_hours,
    }


def get_alert_center_payload(limit_recent: int = 120, lang: str = "zh", include_forecast: bool = True) -> dict:
    lc = _norm_lang(lang)
    session = Session()
    try:
        events = _load_json(session, ALERT_EVENTS_KEY, [])
        versions = _load_json(session, ALERT_THRESHOLD_VERSIONS_KEY, [])
        state = _load_json(session, ALERT_STATE_KEY, {"silence_until_ts": 0})
        if not isinstance(events, list):
            events = []
        if not isinstance(versions, list):
            versions = []
        if not isinstance(state, dict):
            state = {"silence_until_ts": 0}

        active = [e for e in events if str(e.get("status") or "") in ("open", "ack", "ignored")]
        active.sort(key=lambda x: (_severity_rank(str(x.get("level") or "L1")) * -1, _to_int(x.get("created_at"), 0) * -1))

        recent = sorted(events, key=lambda x: _to_int(x.get("created_at"), 0), reverse=True)[:max(10, _to_int(limit_recent, 120))]
        for arr in (active, recent):
            for e in arr:
                e["title"] = _i18n_value(e.get("title_i18n"), lc, str(e.get("title") or ""))
                e["text"] = _i18n_value(e.get("text_i18n"), lc, str(e.get("text") or ""))
                e["level_css"] = _css_level(str(e.get("level") or "L1"))
                e["created_at_text"] = _format_ts(_to_int(e.get("created_at"), 0))
                e["last_seen_at_text"] = _format_ts(_to_int(e.get("last_seen_at"), 0))
                e["resolved_at_text"] = _format_ts(_to_int(e.get("resolved_at"), 0))

        cfg = get_alert_engine_config()
        weekly = _weekly_stats(events)
        efficiency = _efficiency_summary(_load_json(session, ALERT_HISTORY_KEY, []), cfg=cfg, lang=lc)
        throughput = _build_stage_throughput_payload(lang=lc, cfg=cfg)
        throughput_ai = _build_ai_calibrated_throughput(session, cfg=cfg, throughput=throughput, lang=lc)
        intelligence = build_factory_intelligence(_build_stock_snapshot_for_intelligence(lc), efficiency, throughput, lang=lc)
        metric_ai = _build_ai_metric_insights(efficiency, throughput, intelligence, lang=lc)
        traceability = build_traceability_snapshot(lang=lc, limit=8)
        traceability_links = _build_traceability_links(lc, intelligence, traceability)
        forecast = {}
        if include_forecast:
            from web.services.forecast_service import build_forecast_payload
            forecast = build_forecast_payload(lang=lc, stock=_build_stock_snapshot_for_intelligence(lc), intelligence=intelligence)
        versions = sorted(versions, key=lambda x: _to_int(x.get("ts"), 0), reverse=True)[:30]
        for v in versions:
            v["ts_text"] = _format_ts(_to_int(v.get("ts"), 0))

        silence_until = _to_int(state.get("silence_until_ts"), 0)
        try:
            from web.services.ai_monitor_service import get_cached_deep_monitor
            ai_deep_monitor = get_cached_deep_monitor(lc)
        except Exception:
            ai_deep_monitor = {}

        return {
            "active": active,
            "recent": recent,
            "weekly": weekly,
            "efficiency": efficiency,
            "throughput": throughput,
            "throughput_ai": throughput_ai,
            "factory_intelligence": intelligence,
            "metric_ai": metric_ai,
            "forecast": forecast,
            "traceability": traceability,
            "traceability_links": traceability_links,
            "ai_deep_monitor": ai_deep_monitor,
            "versions": versions,
            "engine_cfg": cfg,
            "silence_until_ts": silence_until,
            "silence_until_text": _format_ts(silence_until) if silence_until > int(time.time()) else "-",
        }
    finally:
        session.close()


def set_alert_silence(minutes: int, operator: str = "") -> int:
    now_ts = int(time.time())
    mins = max(0, _to_int(minutes, 0))
    until_ts = now_ts + mins * 60
    session = Session()
    try:
        state = _load_json(session, ALERT_STATE_KEY, {"last_notify_by_rule": {}})
        if not isinstance(state, dict):
            state = {"last_notify_by_rule": {}}
        if not isinstance(state.get("last_notify_by_rule"), dict):
            state["last_notify_by_rule"] = {}
        state["silence_until_ts"] = until_ts
        state["silence_set_by"] = str(operator or "")
        state["silence_set_at"] = now_ts
        _save_json(session, ALERT_STATE_KEY, state)
        session.commit()
    finally:
        session.close()
    return until_ts
