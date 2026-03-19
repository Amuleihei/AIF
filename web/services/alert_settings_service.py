from web.models import Session, TgSetting


KEY_PREFIX = "alert_threshold:"

DEFAULT_ALERT_SETTINGS = {
    "log_stock_mt_min": 80.0,
    "sorting_stock_tray_min": 20,
    "kiln_done_stock_tray_max": 200,
    "product_shippable_tray_min": 300,
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


def get_alert_settings() -> dict:
    session = Session()
    out = dict(DEFAULT_ALERT_SETTINGS)
    try:
        for field in DEFAULT_ALERT_SETTINGS.keys():
            row = session.query(TgSetting).filter_by(key=_setting_key(field)).first()
            if not row:
                continue
            raw = str(row.value or "").strip()
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
