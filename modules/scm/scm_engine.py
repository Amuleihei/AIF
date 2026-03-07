import json
from pathlib import Path
from datetime import datetime


DATA_FILE = Path.home() / "AIF/data/scm/scm.json"


# =====================================================
# 默认数据
# =====================================================

def default_data():
    return {
        "suppliers": {},
        "purchases": [],
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
    except Exception:
        d = default_data()
        save(d)
        return d


def save(d):

    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)

    with open(DATA_FILE, "w") as f:
        json.dump(d, f, indent=2, ensure_ascii=False)


# =====================================================
# 添加供应商
# =====================================================

def add_supplier(d, parts):

    try:
        name = parts[1]
    except:
        return "❌ 格式: 添加供应商 名称"

    if name in d["suppliers"]:
        return "⚠️ 已存在"

    d["suppliers"][name] = {
        "created": datetime.now().isoformat(timespec="seconds")
    }

    save(d)

    return f"🌐 已添加供应商 {name}"


# =====================================================
# 创建采购
# =====================================================

def create_purchase(d, parts):

    try:
        supplier = parts[1]
        item = parts[2]
        qty = float(parts[3])
    except:
        return "❌ 格式: 采购 供应商 物料 数量"

    if supplier not in d["suppliers"]:
        return "❌ 未知供应商"

    pid = d["next_id"]

    p = {
        "id": pid,
        "supplier": supplier,
        "item": item,
        "qty": qty,
        "status": "在途",
        "time": datetime.now().isoformat(timespec="seconds")
    }

    d["purchases"].append(p)
    d["next_id"] += 1

    save(d)

    return f"📦 采购单 #{pid} 已创建"


# =====================================================
# 到货
# =====================================================

def receive_goods(d, parts):

    try:
        pid = int(parts[1])
    except:
        return "❌ 格式: 到货 ID"

    for p in d["purchases"]:
        if p["id"] == pid:
            p["status"] = "已到货"
            save(d)
            return f"📥 采购单 #{pid} 已到货"

    return "❌ 未找到采购单"


# =====================================================
# 采购列表
# =====================================================

def list_purchases(d):

    if not d["purchases"]:
        return "📭 无采购记录"

    lines = ["📦 采购列表"]

    for p in d["purchases"]:
        lines.append(
            f"#{p['id']} {p['supplier']} {p['item']} {p['qty']} [{p['status']}]"
        )

    return "\n".join(lines)


# =====================================================
# TG入口
# =====================================================

def handle_scm(text):

    d = load()

    parts = text.split()

    if not parts:
        return None

    cmd = parts[0]

    if cmd == "添加供应商":
        return add_supplier(d, parts)

    if cmd == "到货":
        return receive_goods(d, parts)

    if text in ("采购列表", "采购"):
        return list_purchases(d)

    if cmd == "采购":
        return create_purchase(d, parts)

    return None
