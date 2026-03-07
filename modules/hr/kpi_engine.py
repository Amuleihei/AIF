import json
from pathlib import Path


DATA_FILE = Path.home() / "AIF/data/hr/kpi.json"


def default_data():
    return {"scores": {}}


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

def handle_kpi(text):

    data = load()

    if text.startswith("评分"):

        _, name, v = text.split()

        data["scores"][name] = float(v)

        save(data)

        return f"⭐ {name} KPI {v}"

    if text == "KPI排行":

        ranked = sorted(
            data["scores"].items(),
            key=lambda x: x[1],
            reverse=True
        )

        return "\n".join(
            f"{i+1}. {n} — {v}"
            for i, (n, v) in enumerate(ranked)
        ) if ranked else "📄 无KPI数据"

    return None