import json
from pathlib import Path


DATA_FILE = Path.home() / "AIF/data/hr/shifts.json"


def default_data():
    return {"shifts": {}}


def load():

    if not DATA_FILE.exists():
        data = default_data()
        save(data)
        return data

    try:
        return json.load(open(DATA_FILE))
    except Exception:
        data = default_data()
        save(data)
        return data


def save(d):

    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)

    with open(DATA_FILE, "w") as f:
        json.dump(d, f, indent=2, ensure_ascii=False)


# =====================================================

def handle_shift(text):

    data = load()

    if text.startswith("新增班组"):

        name = text.replace("新增班组", "").strip()
        data["shifts"][name] = []

        save(data)

        return f"👥 已创建班组: {name}"

    if text.startswith("分配"):

        _, staff, shift = text.split()

        if shift not in data["shifts"]:
            return "❌ 班组不存在"

        data["shifts"][shift].append(staff)

        save(data)

        return f"✅ {staff} → {shift}"

    if text == "班组情况":

        lines = []

        for k, v in data["shifts"].items():
            lines.append(f"{k}: {len(v)}人")

        return "\n".join(lines) if lines else "无班组"

    return None