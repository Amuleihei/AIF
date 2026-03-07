import json
from pathlib import Path
from datetime import datetime


DATA_FILE = Path.home() / "AIF/data/hr/hr.json"


# =====================================================
# 默认数据
# =====================================================

def default_data():
    return {"employees": {}}


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
# 添加员工
# =====================================================

def add_employee(d, parts):

    try:
        name = parts[1]
        role = parts[2]
        salary = float(parts[3])
    except:
        return "❌ 格式: 添加员工 姓名 岗位 月薪"

    if name in d["employees"]:
        return "⚠️ 员工已存在"

    d["employees"][name] = {
        "role": role,
        "salary": salary,
        "status": "在岗",
        "last_checkin": None
    }

    save(d)

    return f"👤 已添加 {name} ({role})"


# =====================================================
# 上下班
# =====================================================

def checkin(d, name):

    if name not in d["employees"]:
        return "❌ 未找到员工"

    d["employees"][name]["last_checkin"] = datetime.now().isoformat(timespec="seconds")
    d["employees"][name]["status"] = "在岗"

    save(d)

    return f"🟢 {name} 已签到"


def checkout(d, name):

    if name not in d["employees"]:
        return "❌ 未找到员工"

    d["employees"][name]["status"] = "离岗"

    save(d)

    return f"🔴 {name} 已签退"


# =====================================================
# 员工列表
# =====================================================

def list_emp(d):

    if not d["employees"]:
        return "👥 无员工"

    lines = ["👥 员工列表"]

    for n, v in d["employees"].items():
        lines.append(f"{n} | {v['role']} | {v['status']}")

    return "\n".join(lines)


# =====================================================
# 工资表
# =====================================================

def payroll(d):

    if not d["employees"]:
        return "💰 无员工"

    total = 0
    lines = ["💰 月工资"]

    for n, v in d["employees"].items():
        s = v["salary"]
        total += s
        lines.append(f"{n}: {s:.2f}")

    lines.append(f"\n总工资: {total:.2f}")

    return "\n".join(lines)


# =====================================================
# TG入口
# =====================================================

def handle_hr(text):

    d = load()

    parts = text.split()

    if not parts:
        return None

    cmd = parts[0]

    if cmd == "添加员工":
        return add_employee(d, parts)

    if cmd == "签到" and len(parts) > 1:
        return checkin(d, parts[1])

    if cmd == "签退" and len(parts) > 1:
        return checkout(d, parts[1])

    if text in ("员工", "员工列表"):
        return list_emp(d)

    if text in ("工资", "工资表"):
        return payroll(d)

    return None