from pathlib import Path
from datetime import datetime
from modules.storage.db_doc_store import append_list_item


DATA_FILE = Path.home() / "AIF/data/kiln/unload_events.jsonl"
DOC_KEY = "kiln_unload_events_v1"


def _append_jsonl(obj: dict) -> None:
    append_list_item(DOC_KEY, obj, legacy_file=DATA_FILE)


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
