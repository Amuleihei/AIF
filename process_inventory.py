import json
from pathlib import Path

DATA_FILE = Path("~/AIF/data/process_inventory.json").expanduser()

STAGES = [
    "raw_log",
    "sawing",
    "treatment",
    "sorting",
    "kiln_in",
    "drying",
    "packing",
    "finished"
]


# ================= 初始化 =================

def load():
    if not DATA_FILE.exists():
        data = {s: 0.0 for s in STAGES}
        save(data)
        return data

    return json.loads(DATA_FILE.read_text())


def save(data):
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    DATA_FILE.write_text(json.dumps(data, indent=2))


# ================= 入厂 =================

def raw_in(v):
    data = load()
    data["raw_log"] += v
    save(data)
    return f"原木入厂 +{v} m³"


# ================= 流转 =================

def move(stage_from, stage_to, v):
    data = load()

    if data[stage_from] < v:
        return f"{stage_from} 库存不足"

    data[stage_from] -= v
    data[stage_to] += v

    save(data)
    return f"{stage_from} → {stage_to} : {v} m³"


# ================= 出货 =================

def ship(v):
    data = load()

    if data["finished"] < v:
        return "成品库存不足"

    data["finished"] -= v
    save(data)
    return f"出货 {v} m³"


# ================= 报表 =================

def report():
    data = load()

    txt = "🏭 工序库存：\n"

    names = {
        "raw_log": "原木",
        "sawing": "锯解",
        "treatment": "药浸",
        "sorting": "拣选",
        "kiln_in": "入窑",
        "drying": "烘干",
        "packing": "打包",
        "finished": "成品"
    }

    for s in STAGES:
        txt += f"{names[s]}：{data[s]} m³\n"

    return txt