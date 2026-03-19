from pathlib import Path
from modules.storage.db_doc_store import load_doc, save_doc


DATA_FILE = Path.home() / "AIF/data/production/capacity.json"
DOC_KEY = "production_capacity_v1"


def default_data():
    return {
        "daily_capacity": 50.0,  # m³/天
        "work_days": 26
    }


def load():
    return load_doc(DOC_KEY, default_data(), legacy_file=DATA_FILE)


def save(d):
    save_doc(DOC_KEY, d)


# =====================================================
# TG入口
# =====================================================

def handle_capacity(text):

    data = load()

    if text == "日产能":
        return f"🏭 日产能 {data['daily_capacity']} m³"

    if text == "月产能":
        m = data["daily_capacity"] * data["work_days"]
        return f"🏭 月产能 {m:.1f} m³"

    if text.startswith("设置日产能"):

        try:
            v = float(text.split()[-1])
            data["daily_capacity"] = v
            save(data)
            return f"✅ 日产能设为 {v}"
        except:
            return "❌ 格式：设置日产能 数值"

    return None
