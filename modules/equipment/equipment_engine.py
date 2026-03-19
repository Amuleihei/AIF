from pathlib import Path
from datetime import datetime
from modules.storage.db_doc_store import load_doc, save_doc


DATA_FILE = Path.home() / "AIF/data/equipment/equipment.json"
DOC_KEY = "equipment_v1"


# =====================================================
# 默认数据
# =====================================================

def default_data():
    return {"machines": {}}


# =====================================================
# 读写
# =====================================================

def load():
    return load_doc(DOC_KEY, default_data(), legacy_file=DATA_FILE)


def save(d):
    save_doc(DOC_KEY, d)


# =====================================================
# 添加设备
# =====================================================

def add_machine(d, parts):

    try:
        name = parts[1]
        mtype = parts[2]
    except:
        return "❌ 格式: 添加设备 名称 类型"

    if name in d["machines"]:
        return "⚠️ 设备已存在"

    d["machines"][name] = {
        "type": mtype,
        "status": "运行",
        "last_service": None,
        "fault": None
    }

    save(d)

    return f"⚙️ 已添加设备 {name} ({mtype})"


# =====================================================
# 故障
# =====================================================

def fault_machine(d, parts):

    try:
        name = parts[1]
        reason = parts[2]
    except:
        return "❌ 格式: 故障 设备 原因"

    if name not in d["machines"]:
        return "❌ 未找到设备"

    m = d["machines"][name]

    m["status"] = "故障"
    m["fault"] = reason

    save(d)

    return f"🔴 {name} 故障: {reason}"


# =====================================================
# 修复
# =====================================================

def repair_machine(d, parts):

    try:
        name = parts[1]
    except:
        return "❌ 格式: 修复 设备"

    if name not in d["machines"]:
        return "❌ 未找到设备"

    m = d["machines"][name]

    m["status"] = "运行"
    m["fault"] = None

    save(d)

    return f"🟢 {name} 已恢复运行"


# =====================================================
# 保养
# =====================================================

def service_machine(d, parts):

    try:
        name = parts[1]
    except:
        return "❌ 格式: 保养 设备"

    if name not in d["machines"]:
        return "❌ 未找到设备"

    m = d["machines"][name]

    m["last_service"] = datetime.now().isoformat(timespec="seconds")

    save(d)

    return f"🔧 {name} 已保养"


# =====================================================
# 停机 / 启动
# =====================================================

def stop_machine(d, parts):

    try:
        name = parts[1]
    except:
        return "❌ 格式: 停机 设备"

    if name not in d["machines"]:
        return "❌ 未找到设备"

    d["machines"][name]["status"] = "停机"

    save(d)

    return f"⛔ {name} 已停机"


def start_machine(d, parts):

    try:
        name = parts[1]
    except:
        return "❌ 格式: 启动 设备"

    if name not in d["machines"]:
        return "❌ 未找到设备"

    d["machines"][name]["status"] = "运行"

    save(d)

    return f"🚀 {name} 已启动"


# =====================================================
# 设备列表
# =====================================================

def list_machine(d):

    if not d["machines"]:
        return "⚙️ 无设备"

    lines = ["⚙️ 设备状态"]

    for n, v in d["machines"].items():

        s = v["status"]

        if s == "故障":
            s += f" ({v['fault']})"

        lines.append(f"{n} | {v['type']} | {s}")

    return "\n".join(lines)


# =====================================================
# TG入口
# =====================================================

def handle_equipment(text):

    d = load()

    parts = text.split()

    if not parts:
        return None

    cmd = parts[0]

    if cmd == "添加设备":
        return add_machine(d, parts)

    if cmd == "故障":
        return fault_machine(d, parts)

    if cmd == "修复":
        return repair_machine(d, parts)

    if cmd == "保养":
        return service_machine(d, parts)

    if cmd == "停机":
        return stop_machine(d, parts)

    if cmd == "启动":
        return start_machine(d, parts)

    if text in ("设备", "设备状态"):
        return list_machine(d)

    return None
