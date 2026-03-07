import json
from pathlib import Path


DATA_FILE = Path.home() / "AIF/data/hr/payroll.json"


def default_data():
    return {
        "salary": {},   # 日薪
        "piece": {},    # 计件单价
        "records": []
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
# TG入口
# =====================================================

def handle_payroll(text):

    data = load()

    # ================= 设置日薪 =================

    if text.startswith("设置日薪"):

        _, name, v = text.split()
        data["salary"][name] = float(v)

        save(data)

        return f"💰 {name} 日薪 {v}"

    # ================= 设置计件 =================

    if text.startswith("设置计件"):

        _, name, v = text.split()
        data["piece"][name] = float(v)

        save(data)

        return f"🧮 {name} 计件 {v}"

    # ================= 记录计件 =================

    if text.startswith("计件"):

        _, name, qty = text.split()

        if name not in data["piece"]:
            return "❌ 未设置计件单价"

        pay = float(qty) * data["piece"][name]

        data["records"].append({
            "name": name,
            "qty": float(qty),
            "pay": pay
        })

        save(data)

        return f"💵 {name} 计件收入 {pay:.2f}"

    # ================= 工资查询 =================

    if text == "工资统计":

        total = sum(r["pay"] for r in data["records"])

        return f"💰 本期工资支出 {total:.2f}"

    return None