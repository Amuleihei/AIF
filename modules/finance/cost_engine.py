import json
from pathlib import Path


DATA_FILE = Path.home() / "AIF/data/finance/cost.json"


def default_data():
    return {
        "raw_material": 0,
        "labor": 0,
        "energy": 0
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