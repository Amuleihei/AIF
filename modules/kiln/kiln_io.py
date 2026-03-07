import json
from pathlib import Path


DATA_FILE = Path.home() / "AIF/data/kiln/kilns.json"


# =====================================================
# 默认窑结构
# =====================================================

def default_data():
    return {
        "A": {"trays": [], "status": "empty", "start": None, "completed_time": None, "last_volume": 0.0},
        "B": {"trays": [], "status": "empty", "start": None, "completed_time": None, "last_volume": 0.0},
        "C": {"trays": [], "status": "empty", "start": None, "completed_time": None, "last_volume": 0.0},
        "D": {"trays": [], "status": "empty", "start": None, "completed_time": None, "last_volume": 0.0},
    }


# =====================================================
# 读取数据
# =====================================================

def load_data():

    if not DATA_FILE.exists():
        data = default_data()
        save_data(data)
        return data

    try:
        d = json.load(open(DATA_FILE))
        changed = False
        for k in ("A", "B", "C", "D"):
            d.setdefault(k, default_data()[k])
            for kk, vv in default_data()[k].items():
                if kk not in d[k]:
                    d[k][kk] = vv
                    changed = True

            # -------------------------------------------------
            # 兼容修复：历史“强制出窑剩余”曾出现
            # status=completed 但同时存在 unloading_* 字段，
            # 且 trays 为空、last_trays>0（此时 last_trays 实际被当作“剩余托数”）。
            # 会导致现场执行 “A窑出窑” 报 “窑内为空”。
            # 这里自动迁移为：status=unloading + 用占位托填充 trays（仅用于计数/继续出窑）。
            # -------------------------------------------------
            kiln = d.get(k, {}) or {}
            try:
                trays = kiln.get("trays") or []
                status = (kiln.get("status") or "").strip().lower()
                last_trays = int(kiln.get("last_trays", 0) or 0)
                has_unloading_meta = any(
                    key in kiln for key in ("unloading_total_trays", "unloading_out_trays", "unloading_out_applied")
                )
            except Exception:
                trays = []
                status = ""
                last_trays = 0
                has_unloading_meta = False

            # 兼容修复：已完成但 status 丢失（避免界面显示为空）
            if (not status) and (not trays) and kiln.get("completed_time"):
                kiln["status"] = "completed"
                d[k] = kiln
                changed = True

            if has_unloading_meta and status == "completed" and (not trays) and last_trays > 0:
                kid = k
                kiln["trays"] = [
                    {"id": f"{kid}{i:03d}", "spec": "84x21", "count": 1}
                    for i in range(1, last_trays + 1)
                ]
                kiln["status"] = "unloading"
                kiln["completed_time"] = None
                d[k] = kiln
                changed = True
        if changed:
            save_data(d)
        return d
    except Exception:
        data = default_data()
        save_data(data)
        return data


# =====================================================
# 保存数据
# =====================================================

def save_data(data):

    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)

    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
