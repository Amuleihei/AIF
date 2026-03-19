from pathlib import Path
from modules.storage.db_doc_store import load_doc, save_doc


DATA_FILE = Path.home() / "AIF/data/hr/kpi.json"
DOC_KEY = "hr_kpi_v1"


def default_data():
    return {"scores": {}}


def load():
    return load_doc(DOC_KEY, default_data(), legacy_file=DATA_FILE)


def save(d):
    save_doc(DOC_KEY, d)


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
