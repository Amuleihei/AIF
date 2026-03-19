import json
import os
import time
import secrets
from datetime import datetime
from urllib import request as urllib_request

from tg_bot.config import get_bot_token
from web.models import Session, TgSetting, TgUserRole


ALERT_EVENTS_KEY = "alert_engine_events_v1"
ALERT_HISTORY_KEY = "alert_engine_stock_history_v1"
ALERT_STATE_KEY = "alert_engine_state_v1"
ALERT_ENGINE_CFG_KEY = "alert_engine_config_v1"
ALERT_THRESHOLD_VERSIONS_KEY = "alert_threshold_versions_v1"


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


def _build_rules(stock: dict, cfg: dict, threshold_cfg: dict, history: list) -> list[dict]:
    log_min = _to_float(threshold_cfg.get("log_stock_mt_min"), 80.0)
    product_full = _to_int(cfg.get("product_full_threshold"), 76)
    product_burst = _to_int(cfg.get("product_burst_threshold"), 100)

    log_stock = _to_float(stock.get("log_stock"), 0.0)
    product_count = _to_int(stock.get("product_count"), 0)

    daily_use = _estimate_daily_log_consumption(history)
    days_left = (log_stock / daily_use) if daily_use > 0 else 999.0
    return [
        {
            "key": "log_stock_need_buy",
            "level": "L1",
            "title": "原木需采购",
            "active": log_stock < log_min and days_left <= 3.0,
            "text": f"原木库存 {log_stock:.4f} MT，按近3天消耗估算可用约 {days_left:.1f} 天",
        },
        {
            "key": "log_stock_urgent_buy",
            "level": "L2",
            "title": "原木急需采购",
            "active": log_stock < log_min and days_left <= 2.0,
            "text": f"原木库存 {log_stock:.4f} MT，按近3天消耗估算可用约 {days_left:.1f} 天",
        },
        {
            "key": "log_stock_tomorrow_risk",
            "level": "L3",
            "title": "原木明天断料风险",
            "active": log_stock < log_min and days_left <= 1.0,
            "text": f"原木库存 {log_stock:.4f} MT，按近3天消耗估算可用约 {days_left:.1f} 天",
        },
        {
            "key": "product_stock_full",
            "level": "L2",
            "title": "成品库存满仓",
            "active": product_count > product_full,
            "text": f"成品库存 {product_count} 件，超过满仓阈值 {product_full} 件",
        },
        {
            "key": "product_stock_burst",
            "level": "L3",
            "title": "成品库存爆满",
            "active": product_count > product_burst,
            "text": f"成品库存 {product_count} 件，超过爆满阈值 {product_burst} 件",
        },
    ]


def _append_history(history: list, stock: dict, now_ts: int) -> list:
    point = {
        "ts": int(now_ts),
        "log_stock": round(_to_float(stock.get("log_stock"), 0.0), 4),
        "saw_stock": _to_int(stock.get("saw_stock"), 0),
        "dip_stock": _to_int(stock.get("dip_stock"), 0),
        "sorting_stock": _to_int(stock.get("sorting_stock"), 0),
        "kiln_done_stock": _to_int(stock.get("kiln_done_stock"), 0),
        "product_count": _to_int(stock.get("product_count"), 0),
    }
    history.append(point)
    return history


def _evaluate_trend_rules(history: list, cfg: dict) -> list[dict]:
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

    sort_drop = _to_int(older.get("sorting_stock"), 0) - _to_int(latest.get("sorting_stock"), 0)
    log_drop = _to_float(older.get("log_stock"), 0.0) - _to_float(latest.get("log_stock"), 0.0)

    out = [
        {
            "key": "trend_sorting_drop",
            "level": "L2",
            "title": "待入窑库存下降过快",
            "active": sort_drop >= _to_int(cfg.get("trend_sort_drop_trays"), 15),
            "text": f"近{_to_int(cfg.get('trend_window_hours'), 6)}小时待入窑下降 {sort_drop} 托",
        },
        {
            "key": "trend_log_drop",
            "level": "L2",
            "title": "原木库存下降过快",
            "active": log_drop >= _to_float(cfg.get("trend_log_drop_mt"), 8.0),
            "text": f"近{_to_int(cfg.get('trend_window_hours'), 6)}小时原木下降 {log_drop:.4f} MT",
        },
    ]
    return out


def evaluate_inventory_alerts(stock: dict, threshold_cfg: dict) -> list[dict]:
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

        rules = _build_rules(stock, cfg, threshold_cfg, history)
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
            owner = str(e.get("owner") or "").strip()
            suffix = f"（负责人:{owner}）" if owner else ""
            items.append(
                {
                    "id": str(e.get("id") or ""),
                    "level": _css_level(str(e.get("level") or "L1")),
                    "severity": str(e.get("level") or "L1"),
                    "text": f"[{str(e.get('level') or 'L1')}] {str(e.get('title') or '')}: {str(e.get('text') or '')}{suffix}",
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


def _weighted_total_score(vec: dict, cfg: dict) -> float:
    wr = _to_float(cfg.get("weight_raw_security"), 20.0)
    wf = _to_float(cfg.get("weight_front_balance"), 20.0)
    wm = _to_float(cfg.get("weight_middle_flow"), 20.0)
    wb = _to_float(cfg.get("weight_backlog_health"), 20.0)
    wp = _to_float(cfg.get("weight_product_health"), 20.0)
    total_w = max(1.0, wr + wf + wm + wb + wp)
    score = (
        _to_float(vec.get("raw_security"), 0.0) * wr
        + _to_float(vec.get("front_balance"), 0.0) * wf
        + _to_float(vec.get("middle_flow"), 0.0) * wm
        + _to_float(vec.get("backlog_health"), 0.0) * wb
        + _to_float(vec.get("product_health"), 0.0) * wp
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
    for k in ("raw_security", "front_balance", "middle_flow", "backlog_health", "product_health"):
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


def _make_efficiency_vector(point: dict, cfg: dict, history: list) -> dict:
    log_stock = _to_float(point.get("log_stock"), 0.0)
    saw_stock = _to_int(point.get("saw_stock"), 0)
    dip_stock = _to_int(point.get("dip_stock"), 0)
    sorting_stock = _to_int(point.get("sorting_stock"), 0)
    kiln_done_stock = _to_int(point.get("kiln_done_stock"), 0)
    product_count = _to_int(point.get("product_count"), 0)

    daily_use = _estimate_daily_log_consumption(history)
    days_left = (log_stock / daily_use) if daily_use > 0 else 7.0
    raw_sec = max(0.0, min(100.0, (days_left / 3.0) * 100.0))
    front_balance = _safe_ratio_score(saw_stock, dip_stock)
    middle_flow = _safe_ratio_score(sorting_stock, max(1, kiln_done_stock))
    backlog_health = _backlog_score(sorting_stock, kiln_done_stock)
    product_health = _product_band_score(
        product_count,
        _to_int(cfg.get("product_ready_threshold"), 26),
        _to_int(cfg.get("product_full_threshold"), 76),
        _to_int(cfg.get("product_burst_threshold"), 100),
    )

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
    }
    vec["total_score"] = _weighted_total_score(vec, cfg)
    return vec


def _period_avg_vector(history: list, cfg: dict, begin_ts: int, end_ts: int) -> dict:
    pts = [p for p in history if begin_ts <= _to_int(p.get("ts"), 0) <= end_ts]
    if not pts:
        return {"raw_security": 0.0, "front_balance": 0.0, "middle_flow": 0.0, "backlog_health": 0.0, "product_health": 0.0, "total_score": 0.0}
    acc = {"raw_security": 0.0, "front_balance": 0.0, "middle_flow": 0.0, "backlog_health": 0.0, "product_health": 0.0, "total_score": 0.0}
    for p in pts:
        v = _make_efficiency_vector(p, cfg, history)
        for k in acc.keys():
            acc[k] += _to_float(v.get(k), 0.0)
    n = float(len(pts))
    return {k: round(acc[k] / n, 1) for k in acc.keys()}


def _efficiency_summary(history: list, cfg: dict) -> dict:
    if not history:
        z = {"raw_security": 0.0, "front_balance": 0.0, "middle_flow": 0.0, "backlog_health": 0.0, "product_health": 0.0, "total_score": 0.0}
        return {
            "current": z,
            "day": z,
            "week": z,
            "month": z,
            "day_prev": z,
            "week_prev": z,
            "month_prev": z,
            "radar_labels": ["原木保障", "前段均衡", "中段流速", "积压健康", "成品健康"],
            "radar": {"current": [0, 0, 0, 0, 0], "day": [0, 0, 0, 0, 0], "week": [0, 0, 0, 0, 0], "month": [0, 0, 0, 0, 0]},
        }
    now_ts = int(time.time())
    day = 86400
    week = 7 * day
    month = 30 * day

    current = _make_efficiency_vector(history[-1], cfg, history)
    day_vec = _period_avg_vector(history, cfg, now_ts - day, now_ts)
    week_vec = _period_avg_vector(history, cfg, now_ts - week, now_ts)
    month_vec = _period_avg_vector(history, cfg, now_ts - month, now_ts)
    day_prev = _period_avg_vector(history, cfg, now_ts - 2 * day, now_ts - day)
    week_prev = _period_avg_vector(history, cfg, now_ts - 2 * week, now_ts - week)
    month_prev = _period_avg_vector(history, cfg, now_ts - 2 * month, now_ts - month)

    # 改善加分：积压连续下降就奖励“中段流速/积压健康”
    drop_today = _backlog_drop(history, now_ts - day, now_ts)
    drop_prev_day = _backlog_drop(history, now_ts - 2 * day, now_ts - day)
    drop_prev2_day = _backlog_drop(history, now_ts - 3 * day, now_ts - 2 * day)
    bonus = 0.0
    if drop_today > 0 and drop_prev_day > 0:
        bonus += _to_float(cfg.get("improve_bonus_2day"), 10.0)
    if drop_today > 0 and drop_prev_day > 0 and drop_prev2_day > 0:
        bonus += _to_float(cfg.get("improve_bonus_3day"), 5.0)

    current = _apply_bonus(current, bonus, cfg)
    day_vec = _apply_bonus(day_vec, bonus, cfg)
    week_vec = _apply_bonus(week_vec, bonus, cfg)
    month_vec = _apply_bonus(month_vec, bonus, cfg)

    # 平滑：按配置窗口与前一周期做混合，避免图形剧烈抖动
    day_vec = _smooth_with_prev(day_vec, day_prev, _to_int(cfg.get("smooth_day_window_points"), 3), cfg)
    week_vec = _smooth_with_prev(week_vec, week_prev, _to_int(cfg.get("smooth_week_window_points"), 3), cfg)

    def _vec5(v):
        return [v.get("raw_security", 0), v.get("front_balance", 0), v.get("middle_flow", 0), v.get("backlog_health", 0), v.get("product_health", 0)]

    return {
        "current": current,
        "day": day_vec,
        "week": week_vec,
        "month": month_vec,
        "day_prev": day_prev,
        "week_prev": week_prev,
        "month_prev": month_prev,
        "radar_labels": ["原木保障", "前段均衡", "中段流速", "积压健康", "成品健康"],
        "radar": {
            "current": _vec5(current),
            "day": _vec5(day_vec),
            "week": _vec5(week_vec),
            "month": _vec5(month_vec),
        },
    }


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


def get_alert_center_payload(limit_recent: int = 120) -> dict:
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
                e["level_css"] = _css_level(str(e.get("level") or "L1"))
                e["created_at_text"] = _format_ts(_to_int(e.get("created_at"), 0))
                e["last_seen_at_text"] = _format_ts(_to_int(e.get("last_seen_at"), 0))
                e["resolved_at_text"] = _format_ts(_to_int(e.get("resolved_at"), 0))

        weekly = _weekly_stats(events)
        efficiency = _efficiency_summary(_load_json(session, ALERT_HISTORY_KEY, []), cfg=get_alert_engine_config())
        versions = sorted(versions, key=lambda x: _to_int(x.get("ts"), 0), reverse=True)[:30]
        for v in versions:
            v["ts_text"] = _format_ts(_to_int(v.get("ts"), 0))

        cfg = get_alert_engine_config()
        silence_until = _to_int(state.get("silence_until_ts"), 0)
        return {
            "active": active,
            "recent": recent,
            "weekly": weekly,
            "efficiency": efficiency,
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
