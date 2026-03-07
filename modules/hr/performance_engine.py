import json
from pathlib import Path


DATA_FILE = Path.home() / "AIF/data/hr/performance.json"


def default_data():
    return {"records": []}


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

def handle_performance(text):

    data = load()

    if text.startswith("产量记录"):

        _, name, v = text.split()

        data["records"].append({
            "name": name,
            "value": float(v)
        })

        save(data)

        return f"📊 {name} 产量 {v}"

    if text == "人效排行":

        if not data["records"]:
            return "📄 无数据"

        stat = {}

        for r in data["records"]:
            stat[r["name"]] = stat.get(r["name"], 0) + r["value"]

        ranked = sorted(stat.items(), key=lambda x: x[1], reverse=True)

        return "\n".join(
            f"{i+1}. {n} — {v}"
            for i, (n, v) in enumerate(ranked)
        )

    return None