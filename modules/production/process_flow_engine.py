# modules/production/process_flow_engine.py

from pathlib import Path
from modules.storage.db_doc_store import load_doc, save_doc

DATA = Path("data/production/process_flow.json")
DOC_KEY = "production_process_flow_v1"


# ================= 数据读写 =================

def load():
    default = {
        "原木库存": 0.0,
        "锯解完成": 0.0,
        "烘干完成": 0.0,
        "包装完成": 0.0
    }
    return load_doc(DOC_KEY, default, legacy_file=DATA)


def save(d):
    save_doc(DOC_KEY, d)


# ================= TG入口 =================

def legacy_handle_process(text):

    data = load()

    # =========================================================
    # ⭐ 优先：生产主链联动（工业级）
    # =========================================================
    if text.startswith("流转"):
        parts = text.split()

        if len(parts) == 4:
            _, src, dst, v = parts

            try:
                v = float(v)
            except:
                return "❌ 数量必须为数字"

            try:
                # 调用核心生产链
                from modules.core.production_chain import transfer
                return transfer(src, dst, v)

            except Exception:
                # 如果主链异常，回退本地逻辑
                pass

    # =========================================================
    # 本地备用逻辑（保证系统不死）
    # =========================================================
    if text.startswith("流转"):
        try:
            _, src, dst, v = text.split()
            v = float(v)
        except:
            return "❌ 格式: 流转 来源 目标 数量"

        if src not in data or dst not in data:
            return "❌ 工序不存在"

        if data[src] < v:
            return "❌ 数量不足"

        data[src] -= v
        data[dst] += v
        save(data)

        return f"🔁 {src} → {dst} {v}"

    # =========================================================
    # 入库
    # =========================================================
    if text.startswith("入库"):
        parts = text.split()

        if len(parts) != 3:
            return "❌ 格式: 入库 工序 数量"

        _, stage, v = parts

        try:
            v = float(v)
        except:
            return "❌ 数量错误"

        if stage not in data:
            return "❌ 工序不存在"

        data[stage] += v
        save(data)

        return f"📥 {stage} +{v}"

    # =========================================================
    # 出库
    # =========================================================
    if text.startswith("出库"):
        parts = text.split()

        if len(parts) != 3:
            return "❌ 格式: 出库 工序 数量"

        _, stage, v = parts

        try:
            v = float(v)
        except:
            return "❌ 数量错误"

        if stage not in data:
            return "❌ 工序不存在"

        if data[stage] < v:
            return "❌ 数量不足"

        data[stage] -= v
        save(data)

        return f"📤 {stage} -{v}"

    # =========================================================
    # 查询
    # =========================================================
    if text in ("工序库存", "流程库存"):
        lines = ["🏭 工序库存："]

        for k, v in data.items():
            lines.append(f"{k}: {v}")

        return "\n".join(lines)

    return None
