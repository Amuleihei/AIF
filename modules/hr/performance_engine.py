from pathlib import Path
from modules.storage.db_doc_store import load_doc, save_doc


DATA_FILE = Path.home() / "AIF/data/hr/performance.json"
DOC_KEY = "hr_performance_v1"


def default_data():
    return {"records": []}


def load():
    return load_doc(DOC_KEY, default_data(), legacy_file=DATA_FILE)


def save(d):
    save_doc(DOC_KEY, d)


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
