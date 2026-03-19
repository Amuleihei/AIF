from pathlib import Path
from modules.storage.db_doc_store import load_doc, save_doc


DATA_FILE = Path.home() / "AIF/data/finance/cost.json"
DOC_KEY = "finance_cost_v1"


def default_data():
    return {
        "raw_material": 0,
        "labor": 0,
        "energy": 0
    }


def load():
    return load_doc(DOC_KEY, default_data(), legacy_file=DATA_FILE)


def save(d):
    save_doc(DOC_KEY, d)


# =====================================================

def handle_cost(text):

    data = load()

    if text.startswith("成本"):

        _, k, v = text.split()
        v = float(v)

        if k not in data:
            return "❌ 类型错误"

        data[k] += v
        save(data)

        return f"💸 {k} 成本 +{v}"

    if text == "成本统计":

        total = sum(data.values())

        return (
            f"原料: {data['raw_material']}\n"
            f"人工: {data['labor']}\n"
            f"能源: {data['energy']}\n"
            f"总计: {total}"
        )

    return None
