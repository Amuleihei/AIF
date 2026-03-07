import re
from datetime import datetime, timedelta

from .kiln_io import load_data, save_data
from .kiln_model import empty_kiln
from .kiln_calc import total_volume


MAX_TRAYS = 60
DRY_HOURS = 120


def sync_ledger(delta: dict):
    try:
        from modules.ledger.production_ledger_engine import record_delta
        record_delta(delta)
    except Exception:
        # 台账联动失败不应影响窑主流程
        pass


# =====================================================
# 窑ID
# =====================================================

def norm(k):

    if not k:
        return None

    k = k.upper().strip()
    k = k.replace("窑", "")
    k = k.replace("KILN_", "")
    k = k.replace("KILN-", "")

    return k if k in ["A", "B", "C", "D"] else None


# =====================================================
# ⭐ 托号生成
# =====================================================

def generate_tray_ids(kid, existing, n):

    start = len(existing) + 1

    ids = []
    for i in range(start, start + n):
        ids.append(f"{kid}{i:03d}")

    return ids


# =====================================================
# ⭐ 解析规格 + 托数
# =====================================================

def parse_input(text):

    """
    Support:
      - 84x21 10托
      - 95x71x10+95x46x5 15托
      - 批次001 95x71x10+95x46x5
    Returns:
      (specs_expanded, count, batch_id)
    """

    # ---------- 托数 ----------
    m = re.search(r"(\d+)\s*(托|tray|Tr|ထောင့်)\b", text, re.I)
    count_in_text = int(m.group(1)) if m else None

    # ---------- 规格（可带数量：AxBxN） ----------
    triplets = re.findall(r"(\d+)x(\d+)(?:x(\d+))?", text)
    if not triplets:
        return None, None, None

    has_qty = any(c for _, _, c in triplets)
    if has_qty and any((c is None or c == "") for _, _, c in triplets):
        return "❌ 混合规格格式错误：若使用 规格x数量，请每个规格都带数量（例：95x71x10+95x46x5）", None, None

    # ---------- 批次编号（可选）：取第一个规格前的非空 token ----------
    batch_id = None
    # remove leading kiln/action words and normalize separators
    head = re.sub(r"^(?:kiln_)?[ABCD]窑?入窑\\s*", "", text.strip(), flags=re.I)
    head = re.sub(r"^(?:kiln\\s*[ABCD]\\s*load\\s*)", "", head.strip(), flags=re.I)
    first_spec_pos = None
    mpos = re.search(r"\d+x\d+(?:x\d+)?", head)
    if mpos:
        first_spec_pos = mpos.start()
    if first_spec_pos is not None and first_spec_pos > 0:
        prefix = head[:first_spec_pos].strip()
        # take first token if present
        if prefix:
            batch_id = re.split(r"[、,，\s]+", prefix)[0].strip() or None

    if has_qty:
        expanded: list[str] = []
        for a, b, c in triplets:
            n = int(c)
            expanded.extend([f"{a}x{b}"] * n)
        count = len(expanded)
        if count_in_text is not None and count_in_text != count:
            return f"❌ 托数不一致：规格合计{count}托 != 输入{count_in_text}托", None, None
        return expanded, count, batch_id

    # no qty -> legacy behavior
    specs = [f"{a}x{b}" for a, b, _ in triplets]
    count = count_in_text if count_in_text is not None else 1
    return specs, count, batch_id


# =====================================================
# ⭐ 入窑
# =====================================================

def load_kiln(kid, text):

    kid = norm(kid)
    if not kid:
        return "❌ 无此窑"

    data = load_data()

    if kid not in data:
        data[kid] = empty_kiln()

    specs, count, batch_id = parse_input(text)

    if isinstance(specs, str) and specs.startswith("❌"):
        return specs
    if not specs:
        return "❌ 未识别规格"

    current = len(data[kid]["trays"])

    if current + count > MAX_TRAYS:
        return f"❌ 超出容量（最多 {MAX_TRAYS} 托）"

    # 入窑托来自“拣选待入窑托池”
    try:
        from modules.process_flow.process_flow_engine import reserve_selected_trays
        ok, msg = reserve_selected_trays(count)
        if not ok:
            return msg
    except Exception:
        # 兼容：联动异常时不阻断窑主流程
        pass

    # ---------- 生成托号 ----------
    tray_ids = generate_tray_ids(kid, data[kid]["trays"], count)

    # ---------- 写入 ----------
    expanded = isinstance(specs, list) and len(specs) == count
    for i, tid in enumerate(tray_ids):
        spec_val = specs[i] if expanded else "+".join(specs)
        tray = {"id": tid, "spec": spec_val, "count": 1}
        if batch_id:
            tray["batch"] = batch_id
        data[kid]["trays"].append(tray)

    data[kid]["status"] = "loading"
    data[kid]["completed_time"] = None

    save_data(data)
    sync_ledger({"kiln_tray": count})

    v = total_volume(data[kid]["trays"])

    return (
        f"🔥 kiln_{kid} 入窑成功\n"
        f"新增托: {count} 托\n"
        f"当前托数: {len(data[kid]['trays'])} 托\n"
        f"材积: {v:.2f} m³"
    )


def unload_kiln_by_tray_ids(kid, ids: list[str]):
    kid = norm(kid)
    if not kid:
        return "❌ 无此窑"

    ids = [str(x).strip() for x in (ids or []) if str(x).strip()]
    if not ids:
        return "❌ 未提供托编号"

    data = load_data()
    k = data.get(kid) or empty_kiln()
    trays = k.get("trays") or []
    if not isinstance(trays, list) or not trays:
        return "❌ 窑内为空"

    idset = {x.upper() for x in ids}
    removed = []
    remain = []
    for t in trays:
        tid = str((t or {}).get("id") or "").upper()
        if tid and tid in idset:
            removed.append(t)
        else:
            remain.append(t)

    missing = sorted([x for x in idset if x not in {str((t or {}).get('id') or '').upper() for t in trays}])
    if not removed:
        if missing:
            return "❌ 未找到托编号: " + " ".join(missing)
        return "⚠️ 无操作"

    removed_count = len(removed)
    removed_v = total_volume(removed)

    prev_out = int(k.get("unloading_out_trays", 0) or 0)
    prev_total = k.get("unloading_total_trays")
    if prev_total is None:
        prev_total = prev_out + len(trays)
    try:
        total_i = int(prev_total)
    except Exception:
        total_i = prev_out + len(trays)

    k["trays"] = remain
    if remain:
        k["status"] = "unloading"
        k["completed_time"] = None
        k["unloading_total_trays"] = total_i
        k["unloading_out_trays"] = prev_out + removed_count
        k["unloading_out_applied"] = prev_out + removed_count
    else:
        k["status"] = "completed"
        k["start"] = None
        k["completed_time"] = datetime.now().isoformat(timespec="seconds")
        k["last_volume"] = float(k.get("last_volume", 0) or 0) + removed_v
        k["last_trays"] = total_i
        k.pop("unloading_total_trays", None)
        k.pop("unloading_out_trays", None)
        k.pop("unloading_out_applied", None)

    data[kid] = k
    save_data(data)

    sync_ledger({"kiln_out_m3": removed_v, "kiln_out_tray": removed_count})
    try:
        from modules.kiln.kiln_event_log import log_unload_event
        log_unload_event(kid, removed_count, removed_v, source="operator", meta={"method": "by_tray_ids"})
    except Exception:
        pass
    try:
        from modules.process_flow.process_flow_engine import add_kiln_done_tray_items
        add_kiln_done_tray_items(removed)
    except Exception:
        try:
            from modules.process_flow.process_flow_engine import add_kiln_done_trays
            add_kiln_done_trays(removed_count)
        except Exception:
            pass

    msg = f"📦 {kid}窑出窑(按托编号)\n已出: {removed_count}托 | 剩余: {len(remain)}托"
    if missing:
        msg += "\n⚠️ 未找到: " + " ".join(missing)
    return msg


def load_kiln_by_ids(kid, ids: list[str]):
    kid = norm(kid)
    if not kid:
        return "❌ 无此窑"

    data = load_data()
    if kid not in data:
        data[kid] = empty_kiln()

    try:
        from modules.process_flow.process_flow_engine import take_selected_trays_by_ids
        ok, msg, trays = take_selected_trays_by_ids(ids)
        if not ok:
            return msg
    except Exception:
        return "❌ 分拣编号系统不可用"

    if not trays:
        return "❌ 未提供有效编号"

    current = len(data[kid]["trays"])
    if current + len(trays) > MAX_TRAYS:
        return f"❌ 超出容量（最多 {MAX_TRAYS} 托）"

    for t in trays:
        data[kid]["trays"].append({
            "id": t.get("id"),
            "spec": t.get("spec", "84x0"),
            "count": 1,
            "full_spec": t.get("full_spec", ""),
            "pcs": t.get("pcs", 0),
        })

    data[kid]["status"] = "loading"
    data[kid]["completed_time"] = None
    save_data(data)
    sync_ledger({"kiln_tray": len(trays)})

    v = total_volume(data[kid]["trays"])
    return (
        f"🔥 kiln_{kid} 入窑成功（按编号）\n"
        f"新增托: {len(trays)} 托\n"
        f"当前托数: {len(data[kid]['trays'])} 托\n"
        f"材积: {v:.2f} m³"
    )


# =====================================================
# ⭐ 点火
# =====================================================

def start_drying(kid):

    kid = norm(kid)
    if not kid:
        return "❌ 无此窑"

    data = load_data()

    if kid not in data or not data[kid]["trays"]:
        return "❌ 窑内为空"

    data[kid]["status"] = "drying"
    data[kid]["start"] = datetime.now().isoformat()

    save_data(data)

    return f"🔥 {kid}窑开始烘干"


# =====================================================
# ⭐ 出窑
# =====================================================

def unload_kiln(kid):

    kid = norm(kid)
    if not kid:
        return "❌ 无此窑"

    data = load_data()

    if kid not in data or not data[kid]["trays"]:
        return "❌ 窑内为空"

    removed = list(data[kid]["trays"])
    tray_count = len(removed)
    v = total_volume(removed)

    data[kid]["status"] = "unloading"
    save_data(data)

    data[kid]["trays"] = []
    data[kid]["status"] = "completed"
    data[kid]["start"] = None
    data[kid]["completed_time"] = datetime.now().isoformat(timespec="seconds")
    data[kid]["last_volume"] = v
    data[kid]["last_trays"] = tray_count

    save_data(data)
    sync_ledger({"kiln_out_m3": v, "kiln_out_tray": tray_count})
    try:
        from modules.kiln.kiln_event_log import log_unload_event
        log_unload_event(kid, tray_count, v, source="operator", meta={"method": "full"})
    except Exception:
        pass
    try:
        from modules.process_flow.process_flow_engine import add_kiln_done_tray_items
        add_kiln_done_tray_items(removed)
    except Exception:
        try:
            from modules.process_flow.process_flow_engine import add_kiln_done_trays
            add_kiln_done_trays(tray_count)
        except Exception:
            pass

    return (
        f"📦 {kid}窑出窑完成\n"
        f"材积: {v:.2f} m³"
    )

def _parse_unload_payload(text: str):
    """
    Support legacy formats like:
      - A窑出窑 14托
      - A窑出窑 95x71+95x46 1托
      - kiln A unload 95x71+95x46 1tray
      - A窑出窑 95x84 297 8托  (middle number ignored)
    Returns: (spec_key|None, out_trays|None)
    """
    if not text:
        return None, None

    # trays
    m = re.search(r"(\d+)\s*(托|tray|Tr|ထောင့်)\b", text, re.I)
    out_trays = int(m.group(1)) if m else None

    # specs
    specs = re.findall(r"(\d+)x(\d+)", text)
    spec_key = None
    if specs:
        spec_key = "+".join([f"{a}x{b}" for a, b in specs])

    return spec_key, out_trays


def unload_kiln_partial(kid, out_trays: int, spec_key: str | None = None):
    kid = norm(kid)
    if not kid:
        return "❌ 无此窑"

    try:
        out_trays = int(out_trays)
    except Exception:
        return "❌ 数值错误"
    if out_trays <= 0:
        return "❌ 托数错误"

    data = load_data()
    if kid not in data:
        data[kid] = empty_kiln()

    trays = data[kid].get("trays") or []
    if not isinstance(trays, list) or not trays:
        return "❌ 窑内为空"

    # select trays to unload
    selected_idx: list[int] = []
    if spec_key:
        for i, t in enumerate(trays):
            if not isinstance(t, dict):
                continue
            s = str(t.get("spec") or "")
            if s == spec_key or spec_key in s:
                selected_idx.append(i)
                if len(selected_idx) >= out_trays:
                    break
        if not selected_idx:
            return f"❌ 未找到匹配规格: {spec_key}"
    else:
        selected_idx = list(range(min(out_trays, len(trays))))

    if len(selected_idx) < out_trays:
        return f"❌ 托数不足：可出 {len(selected_idx)} 托"

    # build removed trays list
    removed = [trays[i] for i in selected_idx]
    remain = [t for j, t in enumerate(trays) if j not in set(selected_idx)]

    removed_count = len(removed)
    removed_v = total_volume(removed)

    # update kiln status/progress
    prev_out = int(data[kid].get("unloading_out_trays", 0) or 0)
    prev_total = data[kid].get("unloading_total_trays")
    if prev_total is None:
        # initialize total = remaining + already_out + this_out
        prev_total = prev_out + len(trays)
    try:
        total_i = int(prev_total)
    except Exception:
        total_i = prev_out + len(trays)

    data[kid]["trays"] = remain
    if remain:
        data[kid]["status"] = "unloading"
        data[kid]["completed_time"] = None
        data[kid]["unloading_total_trays"] = total_i
        data[kid]["unloading_out_trays"] = prev_out + removed_count
        # Keep applied in sync for operator-driven partial unload, so overview/detail stays consistent.
        data[kid]["unloading_out_applied"] = prev_out + removed_count
    else:
        data[kid]["status"] = "completed"
        data[kid]["start"] = None
        data[kid]["completed_time"] = datetime.now().isoformat(timespec="seconds")
        data[kid]["last_volume"] = float(data[kid].get("last_volume", 0) or 0) + removed_v
        data[kid]["last_trays"] = total_i
        data[kid].pop("unloading_total_trays", None)
        data[kid].pop("unloading_out_trays", None)
        data[kid].pop("unloading_out_applied", None)

    save_data(data)

    # sync flow + ledger for the portion actually unloaded
    sync_ledger({"kiln_out_m3": removed_v, "kiln_out_tray": removed_count})
    try:
        from modules.kiln.kiln_event_log import log_unload_event
        meta = {"method": "partial"}
        if spec_key:
            meta["spec"] = spec_key
        log_unload_event(kid, removed_count, removed_v, source="operator", meta=meta)
    except Exception:
        pass
    try:
        from modules.process_flow.process_flow_engine import add_kiln_done_tray_items
        add_kiln_done_tray_items(removed)
    except Exception:
        try:
            from modules.process_flow.process_flow_engine import add_kiln_done_trays
            add_kiln_done_trays(removed_count)
        except Exception:
            pass

    spec_note = f" ({spec_key})" if spec_key else ""
    if remain:
        return f"📦 {kid}窑出窑记录{spec_note}\n已出: {removed_count}托 | 剩余: {len(remain)}托"
    return f"📦 {kid}窑出窑完成{spec_note}\n材积: {removed_v:.2f} m³"


# =====================================================
# ⭐ 出窑详情（不执行出窑）
# =====================================================

def unload_detail(kid):
    kid = norm(kid)
    if not kid:
        return "❌ 无此窑"

    data = load_data()
    k = data.get(kid) or empty_kiln()

    trays = k.get("trays") or []
    tray_count = len(trays) if isinstance(trays, list) else 0
    status = (k.get("status") or "empty").strip().lower()

    lines = [f"📦 {kid}窑出窑详情"]

    # 基础信息
    total = k.get("unloading_total_trays")
    out = k.get("unloading_out_trays")
    applied = k.get("unloading_out_applied")
    completed_time = k.get("completed_time")
    last_trays = k.get("last_trays")

    lines.append(f"状态: {status}")
    lines.append(f"当前窑内: {tray_count} 托")

    if status == "unloading":
        if total is not None:
            try:
                lines.append(f"本轮总托: {int(total)} 托")
            except Exception:
                lines.append(f"本轮总托: {total}")
        if out is not None:
            try:
                lines.append(f"已出窑: {int(out)} 托")
            except Exception:
                lines.append(f"已出窑: {out}")
        if applied is not None:
            try:
                lines.append(f"已写入待二拣: {int(applied)} 托")
            except Exception:
                lines.append(f"已写入待二拣: {applied}")
        lines.append(f"剩余未出: {tray_count} 托")
        lines.append("操作: 继续全量出窑用 `A窑出窑`（会清空剩余托）")
        lines.append("提示: 若需要录“分批出窑/剩余”，用管理员 `强制 A窑出窑 已出X托 剩Y托`")
        return "\n".join(lines)

    if status in ("completed", "ready_unload"):
        if last_trays is not None:
            try:
                lines.append(f"上次记录: {int(last_trays)} 托")
            except Exception:
                lines.append(f"上次记录: {last_trays} 托")
        if completed_time:
            lines.append(f"完成时间: {completed_time}")
        lines.append("提示: 如需继续出窑，请先用管理员强制把窑状态恢复为出窑中并补剩余托数。")
        return "\n".join(lines)

    if status == "empty":
        lines.append("提示: 当前为空窑，无需出窑。")
        return "\n".join(lines)

    # drying/loading 等状态
    if status == "drying":
        start = k.get("start")
        if start:
            lines.append(f"开始时间: {start}")
        lines.append("提示: 烘干中不可出窑。")
        return "\n".join(lines)

    if status == "loading":
        lines.append("提示: 入窑中不可出窑。")
        return "\n".join(lines)

    return "\n".join(lines)


# =====================================================
# ⭐ 状态
# =====================================================

def kiln_status():

    data = load_data()
    now = datetime.now()

    lines = ["🔥 窑状态"]

    running = 0
    total_trays = 0
    changed = False

    for k in ["A", "B", "C", "D"]:

        v = data.get(k, empty_kiln())

        trays = len(v["trays"])
        total_trays += trays

        status = v.get("status", "empty")

        if status == "drying" and v.get("start"):
            start = datetime.fromisoformat(v["start"])
            remain = (start + timedelta(hours=DRY_HOURS)) - now
            if remain.total_seconds() > 0:
                h = int(remain.total_seconds() / 3600)
                running += 1
                lines.append(f"{k}窑: 🔥开始烘干/烘干中 ({trays}托, 剩{h}h)")
            else:
                if status != "ready_unload":
                    v["status"] = "ready_unload"
                    changed = True
                lines.append(f"{k}窑: 📦烘干完成待出 ({trays}托)")
            continue

        if status == "loading":
            running += 1 if trays > 0 else 0
            lines.append(f"{k}窑: 📥入窑中 ({trays}托)")
            continue

        if status == "ready_unload":
            lines.append(f"{k}窑: 📦烘干完成待出 ({trays}托)")
            continue

        if status == "unloading":
            running += 1 if trays > 0 else 0
            total = v.get("unloading_total_trays")
            if total is not None:
                try:
                    total_i = int(total)
                except Exception:
                    total_i = None
                if total_i is not None and total_i >= trays:
                    lines.append(f"{k}窑: 🚚出窑中 ({total_i}托, 剩{trays}托)")
                else:
                    lines.append(f"{k}窑: 🚚出窑中 ({trays}托)")
            else:
                lines.append(f"{k}窑: 🚚出窑中 ({trays}托)")
            continue

        if status == "completed":
            t = v.get("completed_time") or "-"
            last_trays = v.get("last_trays")
            if last_trays is not None:
                lines.append(f"{k}窑: ✅已完成 (上次{int(last_trays)}托 @ {t})")
            else:
                vol = float(v.get("last_volume", 0.0))
                lines.append(f"{k}窑: ✅已完成 (上次{vol:.2f}m³ @ {t})")
            continue

        lines.append(f"{k}窑: 空")

    lines.append(f"\n运行: {running}窑 | 总托: {total_trays}托")

    if changed:
        save_data(data)

    return "\n".join(lines)


# =====================================================
# ⭐ TG入口
# =====================================================

def handle_kiln(text):
    # 缅语/英文窑状态模糊匹配
    if text in ("窑状态", "要状态", "မီးဖိုအခြေအနေ", "မီးဖို အခြေအနေ", "kiln status"):
        return kiln_status()

    # 缅语动作模糊匹配（需包含窑号 A/B/C/D）
    if ("မီးဖို" in text) or ("kiln" in text.lower()):
        m_kid = re.search(r"([ABCD])", text, re.I)
        kid = m_kid.group(1).upper() if m_kid else None
        lower = text.lower()

        # detail first (avoid treating "unload detail" as action)
        if kid and (("detail" in lower) or ("details" in lower) or ("明细" in text) or ("详情" in text)):
            return unload_detail(kid)

        if kid and (("မီးဖွင့်" in text) or ("点火" in text) or ("fire" in lower)):
            return start_drying(kid)
        if kid and (("ထုတ်" in text) or ("出窑" in text) or ("unload" in lower)):
            spec_key, out_trays = _parse_unload_payload(text)
            if out_trays is not None:
                return unload_kiln_partial(kid, out_trays, spec_key=spec_key)
            # unload by tray ids: kiln A unload A001 A002
            tail = re.sub(r"(?i)^.*\\bunload\\b", "", text).strip()
            tokens = [p for p in re.split(r"[、,，\\s]+", tail) if p]
            tray_ids = [t for t in tokens if re.fullmatch(rf"{kid}\d{{3,}}", t.upper())]
            if tray_ids:
                return unload_kiln_by_tray_ids(kid, tray_ids)
            return unload_kiln(kid)
        if kid and (("ထည့်" in text) or ("入窑" in text) or ("load" in lower)):
            payload = text
            payload = payload.replace("မီးဖို", "").replace("ထည့်", "")
            payload = payload.replace("load", "").replace("Load", "")
            payload = re.sub(r"[ABCDabcd]", "", payload).strip()
            # 含规格走规格模式，否则按编号模式
            if re.search(r"\d+x\d+", payload):
                return load_kiln(kid, payload)
            ids = [p for p in re.split(r"[、,，\s]+", payload) if p]
            return load_kiln_by_ids(kid, ids)

    # 入窑
    m = re.match(r"(?:kiln_)?([ABCD])窑?入窑\s+(.+)", text, re.I)
    if m:
        payload = m.group(2).strip()
        if re.search(r"\d+x\d+", payload):
            return load_kiln(m.group(1), payload)
        ids = [p for p in re.split(r"[、,，\s]+", payload) if p]
        return load_kiln_by_ids(m.group(1), ids)

    # 点火
    m = re.match(r"(?:kiln_)?([ABCD])窑?点火", text, re.I)
    if m:
        return start_drying(m.group(1))

    # 出窑详情（必须先于出窑动作判断）
    m = re.fullmatch(r"(?:kiln_)?([ABCD])窑?出窑(?:详情|明细|进度)", text.strip(), re.I)
    if m:
        return unload_detail(m.group(1))

    # 出窑
    m = re.match(r"^(?:kiln_)?([ABCD])窑?出窑\b(.*)$", text.strip(), re.I)
    if m:
        kid = m.group(1)
        payload = (m.group(2) or "").strip()
        if not payload:
            return unload_kiln(kid)
        spec_key, out_trays = _parse_unload_payload(payload)
        if out_trays is not None:
            return unload_kiln_partial(kid, out_trays, spec_key=spec_key)
        # ids mode: A窑出窑 A001 A002 ...
        tokens = [p for p in re.split(r"[、,，\s]+", payload) if p]
        tray_ids = [t for t in tokens if re.fullmatch(rf"{kid.upper()}\d{{3,}}", t.upper())]
        if tray_ids:
            return unload_kiln_by_tray_ids(kid, tray_ids)
        # legacy payload present but no tray count -> default to full unload
        return unload_kiln(kid)

    return None
