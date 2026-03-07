import json
from pathlib import Path
import re


DATA_FILE = Path.home() / "AIF/data/packing/pallets.json"


# =====================================================
# 默认数据
# =====================================================

def default_data():
    return {
        "pallets": [],
        "next_id": 1
    }


# =====================================================
# 读写
# =====================================================

def load():

    if not DATA_FILE.exists():
        d = default_data()
        save(d)
        return d

    try:
        return json.load(open(DATA_FILE))
    except:
        d = default_data()
        save(d)
        return d


def save(d):

    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)

    with open(DATA_FILE, "w") as f:
        json.dump(d, f, indent=2, ensure_ascii=False)


# =====================================================
# 体积计算（mm → m³）
# =====================================================

def volume(piece):

    # piece = "950x84x22x297"
    L, W, T, N = map(float, piece.split("x"))

    return (L/1000) * (W/1000) * (T/1000) * N


# =====================================================
# 解析规格字符串
# =====================================================

def parse(text):

    # 支持：84x297 71x378 60x405 46x39
    pairs = re.findall(r"(\d+)x(\d+)", text)

    specs = []

    for w, n in pairs:

        # 默认长度950 厚度22
        specs.append(f"950x{w}x22x{n}")

    return specs


# =====================================================
# 创建托盘
# =====================================================

def new_pallet(d, text):

    specs = parse(text)

    if not specs:
        return "❌ 未识别规格"

    pid = d["next_id"]

    v = sum(volume(s) for s in specs)

    pallet = {
        "id": pid,
        "specs": specs,
        "volume": v
    }

    d["pallets"].append(pallet)
    d["next_id"] += 1

    save(d)

    return f"📦 托#{pid} 创建成功 {v:.3f} m³"


# =====================================================
# 库存统计
# =====================================================

def inventory(d):

    if not d["pallets"]:
        return "📦 无托盘"

    total_v = sum(p["volume"] for p in d["pallets"])

    return f"📦 托数: {len(d['pallets'])}\n总材积: {total_v:.2f} m³"


# =====================================================
# 托列表
# =====================================================

def list_pallets(d):

    if not d["pallets"]:
        return "📭 无托盘"

    lines = ["📦 托列表"]

    for p in d["pallets"]:
        lines.append(
            f"#{p['id']} {p['volume']:.2f} m³"
        )

    return "\n".join(lines)


# =====================================================
# TG入口
# =====================================================

def handle_packing(text):

    d = load()

    if text.startswith("打包"):

        t = text.replace("打包", "").strip()
        return new_pallet(d, t)

    if text in ("托库存", "成品库存"):
        return inventory(d)

    if text in ("托列表", "托盘"):
        return list_pallets(d)

    return None