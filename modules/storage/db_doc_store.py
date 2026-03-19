import json
from pathlib import Path
from typing import Any

from web.models import Session, SystemConfig


KEY_PREFIX = "jsondoc:"


def _full_key(key: str) -> str:
    return f"{KEY_PREFIX}{str(key or '').strip()}"


def load_doc(key: str, default: Any, legacy_file: str | Path | None = None) -> Any:
    """
    Unified DB document storage.
    - Primary source: unified.db / system_config.key=jsondoc:<key>
    - One-time migration: if DB missing and legacy JSON file exists, import it.
    """
    fk = _full_key(key)
    session = Session()
    try:
        row = session.query(SystemConfig).filter_by(key=fk).first()
        if row and str(row.value or "").strip():
            try:
                return json.loads(row.value)
            except Exception:
                return default

        if legacy_file:
            p = Path(legacy_file)
            if p.exists():
                try:
                    data = json.loads(p.read_text(encoding="utf-8"))
                    save_doc(key, data)
                    return data
                except Exception:
                    # jsonl fallback (one json object per line) -> list
                    if isinstance(default, list):
                        try:
                            arr = []
                            for line in p.read_text(encoding="utf-8").splitlines():
                                s = (line or "").strip()
                                if not s:
                                    continue
                                arr.append(json.loads(s))
                            save_doc(key, arr)
                            return arr
                        except Exception:
                            pass
        return default
    finally:
        session.close()


def save_doc(key: str, data: Any) -> None:
    fk = _full_key(key)
    payload = json.dumps(data, ensure_ascii=False)
    session = Session()
    try:
        row = session.query(SystemConfig).filter_by(key=fk).first()
        if not row:
            session.add(SystemConfig(key=fk, value=payload))
        else:
            row.value = payload
        session.commit()
    finally:
        session.close()


def append_list_item(key: str, item: Any, legacy_file: str | Path | None = None) -> None:
    data = load_doc(key, default=[], legacy_file=legacy_file)
    if not isinstance(data, list):
        data = []
    data.append(item)
    save_doc(key, data)
