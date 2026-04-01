import json
import secrets
from datetime import date, datetime

from web.models import Session, TgSetting


_UID_DAY_PREFIX = "daily_once_link:uidday:"
_TOKEN_PREFIX = "daily_once_link:token:"


def _norm_day(day_text: str | None = None) -> str:
    text = str(day_text or "").strip()
    if text:
        return text
    return date.today().isoformat()


def _loads(raw: str) -> dict:
    try:
        obj = json.loads(str(raw or "{}"))
        return obj if isinstance(obj, dict) else {}
    except Exception:
        return {}


def _dumps(obj: dict) -> str:
    return json.dumps(obj or {}, ensure_ascii=False, separators=(",", ":"))


def issue_daily_once_token(uid: str, day_text: str | None = None) -> str:
    day = _norm_day(day_text)
    uid_text = str(uid or "").strip()
    if not uid_text:
        raise ValueError("uid required")

    key_uid_day = f"{_UID_DAY_PREFIX}{day}:{uid_text}"
    session = Session()
    try:
        row = session.query(TgSetting).filter_by(key=key_uid_day).first()
        if row:
            payload = _loads(row.value)
            token = str(payload.get("token") or "").strip()
            if token:
                return token

        token = secrets.token_urlsafe(24)
        now_iso = datetime.now().isoformat(timespec="seconds")
        payload = {
            "uid": uid_text,
            "day": day,
            "token": token,
            "used": 0,
            "created_at": now_iso,
        }

        token_key = f"{_TOKEN_PREFIX}{token}"
        row_uid_day = session.query(TgSetting).filter_by(key=key_uid_day).first()
        if not row_uid_day:
            row_uid_day = TgSetting(key=key_uid_day, value=_dumps(payload))
            session.add(row_uid_day)
        else:
            row_uid_day.value = _dumps(payload)

        row_token = session.query(TgSetting).filter_by(key=token_key).first()
        if not row_token:
            row_token = TgSetting(key=token_key, value=_dumps(payload))
            session.add(row_token)
        else:
            row_token.value = _dumps(payload)

        session.commit()
        return token
    finally:
        session.close()


def consume_daily_once_token(token: str) -> dict:
    tok = str(token or "").strip()
    if not tok:
        return {"ok": False, "reason": "empty"}

    token_key = f"{_TOKEN_PREFIX}{tok}"
    session = Session()
    try:
        row = session.query(TgSetting).filter_by(key=token_key).first()
        if not row:
            return {"ok": False, "reason": "not_found"}

        payload = _loads(row.value)
        uid = str(payload.get("uid") or "").strip()
        day = _norm_day(str(payload.get("day") or ""))
        used = int(payload.get("used") or 0)
        if used == 1:
            return {"ok": False, "reason": "used", "uid": uid, "day": day}

        payload["used"] = 1
        payload["used_at"] = datetime.now().isoformat(timespec="seconds")
        row.value = _dumps(payload)

        if uid:
            uid_day_key = f"{_UID_DAY_PREFIX}{day}:{uid}"
            row_uid_day = session.query(TgSetting).filter_by(key=uid_day_key).first()
            if row_uid_day:
                row_uid_day.value = _dumps(payload)

        session.commit()
        return {"ok": True, "uid": uid, "day": day}
    except Exception:
        session.rollback()
        return {"ok": False, "reason": "error"}
    finally:
        session.close()


def verify_daily_temp_token(token: str) -> dict:
    tok = str(token or "").strip()
    if not tok:
        return {"ok": False, "reason": "empty"}

    token_key = f"{_TOKEN_PREFIX}{tok}"
    session = Session()
    try:
        row = session.query(TgSetting).filter_by(key=token_key).first()
        if not row:
            return {"ok": False, "reason": "not_found"}
        payload = _loads(row.value)
        uid = str(payload.get("uid") or "").strip()
        day = _norm_day(str(payload.get("day") or ""))
        # 临时链接有效期：当天 23:59:59 之前；跨天自动失效。
        if day != date.today().isoformat():
            return {"ok": False, "reason": "expired", "uid": uid, "day": day}
        return {"ok": True, "uid": uid, "day": day}
    finally:
        session.close()


def build_daily_once_link(base_url: str, token: str, lang: str = "zh") -> str:
    base = str(base_url or "").strip().rstrip("/")
    tok = str(token or "").strip()
    lc = str(lang or "zh").strip() or "zh"
    if not base or not tok:
        return ""
    return f"{base}/report/daily/once?token={tok}&lang={lc}"
