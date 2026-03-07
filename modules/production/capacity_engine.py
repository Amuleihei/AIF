import json
from pathlib import Path


DATA_FILE = Path.home() / "AIF/data/production/capacity.json"


def default_data():
    return {
        "daily_capacity": 50.0,  # m³/天
        "work_days": 26
    }


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