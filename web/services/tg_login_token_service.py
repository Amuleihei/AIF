import json
import secrets
import time
from datetime import datetime

from web.models import Session, TgSetting


_TOKEN_PREFIX = "tg_login:token:"


def _loads(raw: str) -> dict:
    try:
        obj = json.loads(str(raw or "{}"))
        return obj if isinstance(obj, dict) else {}
    except Exception:
        return {}


def _dumps(obj: dict) -> str:
    return json.dumps(obj or {}, ensure_ascii=False, separators=(",", ":"))


def issue_tg_login_token(uid: str, ttl_seconds: int = 3600) -> str:
    uid_text = str(uid or "").strip()
    if not uid_text:
        raise ValueError("uid required")

    now_ts = int(time.time())
    exp_ts = now_ts + max(60, int(ttl_seconds))
    token = secrets.token_urlsafe(24)
    payload = {
        "uid": uid_text,
        "token": token,
        "exp_ts": exp_ts,
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }

    session = Session()
    try:
        key = f"{_TOKEN_PREFIX}{token}"
        row = session.query(TgSetting).filter_by(key=key).first()
        if not row:
            row = TgSetting(key=key, value=_dumps(payload))
            session.add(row)
        else:
            row.value = _dumps(payload)
        session.commit()
        return token
    finally:
        session.close()


def verify_tg_login_token(token: str) -> dict:
    tok = str(token or "").strip()
    if not tok:
        return {"ok": False, "reason": "empty"}

    session = Session()
    try:
        key = f"{_TOKEN_PREFIX}{tok}"
        row = session.query(TgSetting).filter_by(key=key).first()
        if not row:
            return {"ok": False, "reason": "not_found"}
        payload = _loads(row.value)
        uid = str(payload.get("uid") or "").strip()
        exp_ts = int(payload.get("exp_ts") or 0)
        now_ts = int(time.time())
        if not uid:
            return {"ok": False, "reason": "missing_uid"}
        if exp_ts <= 0 or now_ts > exp_ts:
            return {"ok": False, "reason": "expired", "uid": uid}
        return {"ok": True, "uid": uid}
    finally:
        session.close()


def build_tg_login_link(base_url: str, token: str) -> str:
    base = str(base_url or "").strip().rstrip("/")
    tok = str(token or "").strip()
    if not base or not tok:
        return ""
    return f"{base}/tg/mini?tg_login_token={tok}"

