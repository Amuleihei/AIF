import json
from pathlib import Path
from datetime import datetime


ORDER_FILE = Path.home() / "AIF/data/order/orders.json"
PLAN_FILE = Path.home() / "AIF/data/planning/plans.json"


# =====================================================
# 默认数据
# =====================================================

def default_plan():
    return {"plans": [], "next_id": 1}


# =====================================================
# 工具
# =====================================================

def load_json(p, default):

    if not p.exists():
        d = default()
        save_json(p, d)
        return d

    try:
        return json.load(open(p))
    except Exception:
        d = default()
        save_json(p, d)
        return d


def save_json(p, d):

    p.parent.mkdir(parents=True, exist_ok=True)

    with open(p, "w") as f:
        json.dump(d, f, indent=2, ensure_ascii=False)


# =====================================================
# 从订单生成计划
# =====================================================

def generate_plan():

    orders = load_json(ORDER_FILE, lambda: {"orders": []})["orders"]
    plan_data = load_json(PLAN_FILE, default_plan)

    created = 0

    for o in orders:

        if o["status"] != "待生产":
            continue

        pid = plan_data["next_id"]

        plan = {
            "id": pid,
            "order_id": o["id"],
            "product": o["product"],
            "qty": o["qty"],
            "status": "计划中",
            "time": datetime.now().isoformat(timespec="seconds")
        }

        plan_data["plans"].append(plan)
        plan_data["next_id"] += 1

        o["status"] = "已排产"
        created += 1

    save_json(ORDER_FILE, {"orders": orders})
    save_json(PLAN_FILE, plan_data)

    if created == 0:
        return "⚠️ 无可排产订单"

    return f"🧠 已生成 {created} 个生产计划"


# =====================================================
# 查看计划
# =====================================================

def list_plans():

    d = load_json(PLAN_FILE, default_plan)

    if not d["plans"]:
        return "📭 无生产计划"

    lines = ["🧠 生产计划"]

    for p in d["plans"]:
        lines.append(
            f"#{p['id']} 订单#{p['order_id']} {p['product']} {p['qty']} [{p['status']}]"
        )

    return "\n".join(lines)


# =====================================================
# 修改状态
# =====================================================

def update_plan(parts):

    try:
        pid = int(parts[1])
        status = parts[2]
    except:
        return "❌ 格式: 计划状态 ID 状态"

    d = load_json(PLAN_FILE, default_plan)

    for p in d["plans"]:
        if p["id"] == pid:
            p["status"] = status
            save_json(PLAN_FILE, d)
            return f"🔄 计划 #{pid} → {status}"

    return "❌ 未找到计划"


# =====================================================
# TG入口
# =====================================================

def handle_planning(text):

    parts = text.split()

    if not parts:
        return None

    cmd = parts[0]

    if text in ("排产", "生成计划"):
        return generate_plan()

    if text in ("计划", "生产计划"):
        return list_plans()

    if cmd == "计划状态":
        return update_plan(parts)

    return None