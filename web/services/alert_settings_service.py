from web.models import Session, TgSetting


KEY_PREFIX = "alert_threshold:"
AI_MONITOR_KEY_PREFIX = "ai_monitor:"

DEFAULT_ALERT_SETTINGS = {
    "log_stock_mt_min": 80.0,
    "sorting_stock_tray_min": 20,
    "kiln_done_stock_tray_max": 200,
    "product_shippable_tray_min": 300,
    "kiln_max_trays": 70,
}

DEFAULT_AI_MONITOR_SETTINGS = {
    "active_start": "16:00",
    "active_end": "20:00",
    "idle_monitor_hours": 3,
    "db_change_settle_minutes": 15,
    "deep_monitor_min_gap_minutes": 15,
}

AI_CAPACITY_KEY_PREFIX = "ai_capacity:"

DEFAULT_AI_CAPACITY_SETTINGS = {
    "band_saw_machine_count": 6,
    "band_saw_primary_target": 6,
    "band_saw_assistant_target": 6,
    "band_saw_qc_target": 6,
    "band_saw_daily_target_trays_per_machine": 4,
    "secondary_saw_machine_count": 3,
    "secondary_saw_operator_target": 3,
    "secondary_daily_finish_target_pcs": 15,
}


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


def _setting_key(name: str) -> str:
    return f"{KEY_PREFIX}{name}"


def _ai_monitor_setting_key(name: str) -> str:
    return f"{AI_MONITOR_KEY_PREFIX}{name}"


def _ai_capacity_setting_key(name: str) -> str:
    return f"{AI_CAPACITY_KEY_PREFIX}{name}"


def _normalize_hhmm(value, default: str) -> str:
    raw = str(value or "").strip()
    if not raw:
        return default
    try:
        hour_s, minute_s = raw.split(":", 1)
        hour = max(0, min(23, int(hour_s)))
        minute = max(0, min(59, int(minute_s)))
        return f"{hour:02d}:{minute:02d}"
    except Exception:
        return default


def get_alert_settings() -> dict:
    session = Session()
    out = dict(DEFAULT_ALERT_SETTINGS)
    try:
        for field in DEFAULT_ALERT_SETTINGS.keys():
            row = session.query(TgSetting).filter_by(key=_setting_key(field)).first()
            if not row:
                continue
            raw = str(row.value or "").strip()
            if field == "kiln_max_trays":
                out[field] = max(1, _to_int(raw, out[field]))
                continue
            if field.endswith("_min") and "tray" in field:
                out[field] = max(0, _to_int(raw, out[field]))
            elif field.endswith("_max") and "tray" in field:
                out[field] = max(0, _to_int(raw, out[field]))
            else:
                out[field] = max(0.0, _to_float(raw, out[field]))
        return out
    finally:
        session.close()


def save_alert_settings(values: dict) -> dict:
    data = dict(DEFAULT_ALERT_SETTINGS)
    data.update(values or {})
    normalized = {
        "log_stock_mt_min": round(max(0.0, _to_float(data.get("log_stock_mt_min"), DEFAULT_ALERT_SETTINGS["log_stock_mt_min"])), 4),
        "sorting_stock_tray_min": max(0, _to_int(data.get("sorting_stock_tray_min"), DEFAULT_ALERT_SETTINGS["sorting_stock_tray_min"])),
        "kiln_done_stock_tray_max": max(0, _to_int(data.get("kiln_done_stock_tray_max"), DEFAULT_ALERT_SETTINGS["kiln_done_stock_tray_max"])),
        "product_shippable_tray_min": max(0, _to_int(data.get("product_shippable_tray_min"), DEFAULT_ALERT_SETTINGS["product_shippable_tray_min"])),
        "kiln_max_trays": max(1, _to_int(data.get("kiln_max_trays"), DEFAULT_ALERT_SETTINGS["kiln_max_trays"])),
    }

    session = Session()
    try:
        for field, value in normalized.items():
            key = _setting_key(field)
            row = session.query(TgSetting).filter_by(key=key).first()
            if not row:
                row = TgSetting(key=key, value=str(value))
                session.add(row)
            else:
                row.value = str(value)
        session.commit()
        return normalized
    finally:
        session.close()


def get_ai_monitor_settings() -> dict:
    session = Session()
    out = dict(DEFAULT_AI_MONITOR_SETTINGS)
    try:
        for field in DEFAULT_AI_MONITOR_SETTINGS.keys():
            row = session.query(TgSetting).filter_by(key=_ai_monitor_setting_key(field)).first()
            if not row:
                continue
            raw = str(row.value or "").strip()
            if field in ("active_start", "active_end"):
                out[field] = _normalize_hhmm(raw, out[field])
            else:
                out[field] = max(1, _to_int(raw, out[field]))
        return out
    finally:
        session.close()


def save_ai_monitor_settings(values: dict) -> dict:
    data = dict(DEFAULT_AI_MONITOR_SETTINGS)
    data.update(values or {})
    normalized = {
        "active_start": _normalize_hhmm(data.get("active_start"), DEFAULT_AI_MONITOR_SETTINGS["active_start"]),
        "active_end": _normalize_hhmm(data.get("active_end"), DEFAULT_AI_MONITOR_SETTINGS["active_end"]),
        "idle_monitor_hours": max(1, _to_int(data.get("idle_monitor_hours"), DEFAULT_AI_MONITOR_SETTINGS["idle_monitor_hours"])),
        "db_change_settle_minutes": max(5, _to_int(data.get("db_change_settle_minutes"), DEFAULT_AI_MONITOR_SETTINGS["db_change_settle_minutes"])),
        "deep_monitor_min_gap_minutes": max(5, _to_int(data.get("deep_monitor_min_gap_minutes"), DEFAULT_AI_MONITOR_SETTINGS["deep_monitor_min_gap_minutes"])),
    }

    session = Session()
    try:
        for field, value in normalized.items():
            key = _ai_monitor_setting_key(field)
            row = session.query(TgSetting).filter_by(key=key).first()
            if not row:
                row = TgSetting(key=key, value=str(value))
                session.add(row)
            else:
                row.value = str(value)
        session.commit()
        return normalized
    finally:
        session.close()


def get_ai_capacity_settings() -> dict:
    session = Session()
    out = dict(DEFAULT_AI_CAPACITY_SETTINGS)
    try:
        for field in DEFAULT_AI_CAPACITY_SETTINGS.keys():
            row = session.query(TgSetting).filter_by(key=_ai_capacity_setting_key(field)).first()
            if not row:
                continue
            out[field] = max(0, _to_int(str(row.value or "").strip(), out[field]))
        return out
    finally:
        session.close()


def save_ai_capacity_settings(values: dict) -> dict:
    data = dict(DEFAULT_AI_CAPACITY_SETTINGS)
    data.update(values or {})
    normalized = {
        "band_saw_machine_count": max(1, _to_int(data.get("band_saw_machine_count"), DEFAULT_AI_CAPACITY_SETTINGS["band_saw_machine_count"])),
        "band_saw_primary_target": max(0, _to_int(data.get("band_saw_primary_target"), DEFAULT_AI_CAPACITY_SETTINGS["band_saw_primary_target"])),
        "band_saw_assistant_target": max(0, _to_int(data.get("band_saw_assistant_target"), DEFAULT_AI_CAPACITY_SETTINGS["band_saw_assistant_target"])),
        "band_saw_qc_target": max(0, _to_int(data.get("band_saw_qc_target"), DEFAULT_AI_CAPACITY_SETTINGS["band_saw_qc_target"])),
        "band_saw_daily_target_trays_per_machine": max(1, _to_int(data.get("band_saw_daily_target_trays_per_machine"), DEFAULT_AI_CAPACITY_SETTINGS["band_saw_daily_target_trays_per_machine"])),
        "secondary_saw_machine_count": max(1, _to_int(data.get("secondary_saw_machine_count"), DEFAULT_AI_CAPACITY_SETTINGS["secondary_saw_machine_count"])),
        "secondary_saw_operator_target": max(0, _to_int(data.get("secondary_saw_operator_target"), DEFAULT_AI_CAPACITY_SETTINGS["secondary_saw_operator_target"])),
        "secondary_daily_finish_target_pcs": max(1, _to_int(data.get("secondary_daily_finish_target_pcs"), DEFAULT_AI_CAPACITY_SETTINGS["secondary_daily_finish_target_pcs"])),
    }

    session = Session()
    try:
        for field, value in normalized.items():
            key = _ai_capacity_setting_key(field)
            row = session.query(TgSetting).filter_by(key=key).first()
            if not row:
                row = TgSetting(key=key, value=str(value))
                session.add(row)
            else:
                row.value = str(value)
        session.commit()
        return normalized
    finally:
        session.close()
