from pathlib import Path
from modules.storage.db_doc_store import load_doc, save_doc


DATA_FILE = Path.home() / "AIF/data/hr/shifts.json"
DOC_KEY = "hr_shifts_v1"


def default_data():
    return {"shifts": {}}


def load():
    return load_doc(DOC_KEY, default_data(), legacy_file=DATA_FILE)


def save(d):
    save_doc(DOC_KEY, d)


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
