import json
import os

DATA_FILE = os.path.expanduser("~/AIF/data/inventory_data.json")


def load_data():
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


# ===============================
# 原木入厂
# ===============================
def add_logs(volume):
    data = load_data()
    data["logs_raw_m3"] += volume
    save_data(data)
    return f"原木入库 +{volume} m³"


# ===============================
# 锯解（原木 → 锯材）
# ===============================
def saw(volume_in, volume_out):
    data = load_data()

    if data["logs_raw_m3"] < volume_in:
        return "原木不足"

    data["logs_raw_m3"] -= volume_in
    data["sawn_m3"] += volume_out

    save_data(data)
    return "锯解完成"


# ===============================
# 药浸
# ===============================
def treat(volume):
    data = load_data()

    if data["sawn_m3"] < volume:
        return "锯材不足"

    data["sawn_m3"] -= volume
    data["treated_m3"] += volume

    save_data(data)
    return "药浸完成"


# ===============================
# 拣选
# ===============================
def sort(volume):
    data = load_data()

    if data["treated_m3"] < volume:
        return "药浸库存不足"

    data["treated_m3"] -= volume
    data["sorted_m3"] += volume

    save_data(data)
    return "拣选完成"


# ===============================
# 入窑
# ===============================
def kiln_load(volume):
    data = load_data()

    if data["sorted_m3"] < volume:
        return "拣选库存不足"

    data["sorted_m3"] -= volume
    data["kiln_wait_m3"] += volume

    save_data(data)
    return "已入窑"


# ===============================
# 烘干完成
# ===============================
def kiln_done(volume_out):
    data = load_data()

    if data["kiln_wait_m3"] < volume_out:
        return "窑内库存不足"

    data["kiln_wait_m3"] -= volume_out
    data["dry_m3"] += volume_out

    save_data(data)
    return "烘干完成"


# ===============================
# 打包
# ===============================
def pack(volume):
    data = load_data()

    if data["dry_m3"] < volume:
        return "干材不足"

    data["dry_m3"] -= volume
    data["packed_m3"] += volume

    save_data(data)
    return "打包完成"


# ===============================
# 出货
# ===============================
def ship(volume):
    data = load_data()

    if data["packed_m3"] < volume:
        return "成品不足"

    data["packed_m3"] -= volume
    data["shipped_m3"] += volume

    save_data(data)
    return "出货完成"


# ===============================
# 查询库存
# ===============================
def report():
    data = load_data()
    return json.dumps(data, ensure_ascii=False, indent=2)
