import json
from pathlib import Path
from datetime import datetime


DATA_FILE = Path.home() / "AIF/data/kiln/unload_events.jsonl"


def _append_jsonl(obj: dict) -> None:
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(DATA_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def log_unload_event(
    kid: str,
    trays: int,
    m3: float | None = None,
    source: str = "operator",
    meta: dict | None = None,
):
    """
    Append a kiln-unload event for later reconciliation / ledger rebuild.
    - trays can be negative for admin correction.
    """
    try:
        trays_i = int(trays)
    except Exception:
        return

    if trays_i == 0:
        return

    payload: dict = {
        "time": datetime.now().isoformat(timespec="seconds"),
        "kid": (kid or "").strip().upper(),
        "trays": trays_i,
        "source": source,
    }

    if m3 is not None:
        try:
            payload["m3"] = float(m3)
        except Exception:
            pass

    if isinstance(meta, dict) and meta:
        payload["meta"] = meta

    try:
        _append_jsonl(payload)
    except Exception:
        # logging failure must never break production commands
        return

