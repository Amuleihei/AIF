from pathlib import Path
from datetime import datetime
from modules.storage.db_doc_store import load_doc, save_doc


DATA_FILE = Path.home() / "AIF/data/workflow/workflow.json"
DOC_KEY = "workflow_v1"


# =====================================================
# 默认数据
# =====================================================

def default_data():
    return {"logs": []}


# =====================================================
# 读写
# =====================================================

def load():
    return load_doc(DOC_KEY, default_data(), legacy_file=DATA_FILE)


def save(d):
    save_doc(DOC_KEY, d)


# =====================================================
# 记录事件
# =====================================================

def log_event(event, detail):

    d = load()

    d["logs"].append({
        "time": datetime.now().isoformat(timespec="seconds"),
        "event": event,
        "detail": detail
    })

    save(d)


# =====================================================
# 自动规则（可扩展）
# =====================================================

def trigger(event, payload):

    # 示例规则：发货自动记录事件
    if event == "shipping":
        log_event("发货完成", payload)

    # 示例规则：入窑事件
    if event == "kiln_load":
        log_event("入窑", payload)

    # 示例规则：生产完成
    if event == "production_done":
        log_event("生产完成", payload)


# =====================================================
# 查看日志
# =====================================================

def view_logs():

    d = load()

    if not d["logs"]:
        return "📭 无流程记录"

    lines = ["🤖 系统事件"]

    for r in d["logs"][-20:]:
        lines.append(
            f"{r['time']} | {r['event']} | {r['detail']}"
        )

    return "\n".join(lines)


# =====================================================
# TG入口
# =====================================================

def handle_workflow(text):

    if text in ("流程日志", "系统日志", "事件日志"):
        return view_logs()

    return None
