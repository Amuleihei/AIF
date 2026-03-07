import re
from datetime import datetime, timedelta


def _int(m: re.Match | None, group: int = 1) -> int | None:
    if not m:
        return None
    try:
        return int(m.group(group))
    except Exception:
        return None


def _build_kiln_trays(kid: str, count: int) -> list[dict]:
    kid = (kid or "").strip().upper()
    count = max(int(count or 0), 0)
    trays: list[dict] = []
    for i in range(1, count + 1):
        trays.append({"id": f"{kid}{i:03d}", "spec": "84x21", "count": 1})
    return trays


def _force_set_stage_pool(stage: str, trays: int) -> str:
    from modules.process_flow.process_flow_engine import load as flow_load, save as flow_save

    trays = int(trays)
    if trays < 0:
        return "❌ 数值错误"

    d = flow_load()

    if stage == "上锯待药浸":
        d["saw_tray_pool"] = trays
    elif stage == "药浸待分拣":
        d["dip_tray_pool"] = trays
    elif stage == "出窑待二拣":
        d["kiln_done_tray_pool"] = trays
        # Keep in sync with tray-level details if present/used by `ss`.
        d["kiln_done_trays"] = [{"id": None, "spec": "84x21"} for _ in range(max(trays, 0))]
    elif stage == "分拣待入窑":
        # selected_tray_pool is derived from selected_trays; create placeholder trays
        now_tag = datetime.now().strftime("%Y%m%d%H%M%S")
        tray_map: dict[str, dict] = {}
        for i in range(1, trays + 1):
            tid = f"F{now_tag}{i:03d}"
            tray_map[tid] = {"id": tid, "spec": "84x21", "full_spec": "84x21", "pcs": 0}
        d["selected_trays"] = tray_map
        d["selected_loose_pcs"] = int(d.get("selected_loose_pcs", 0) or 0)
    else:
        return "❌ 未识别指令"

    flow_save(d)
    return f"✅ 强制更新成功: {stage} = {trays} 托"


def _force_kiln(text: str) -> str | None:
    """
    Admin-only force commands for kiln states, e.g.
    - 强制 B窑烘干中 共计55托 已运行78小时
    - 强制 A窑出窑 15托 剩余30托
    - 强制 C窑空
    """
    from modules.kiln.kiln_io import load_data, save_data

    m_kid = re.search(r"\b([ABCD])\b\s*窑?", text, re.I) or re.search(r"([ABCD])\s*窑", text, re.I)
    kid = (m_kid.group(1).upper() if m_kid else None)
    if not kid:
        return None

    # counts
    total = _int(re.search(r"(?:共计|合计)\s*(\d+)\s*托", text))
    remain = _int(re.search(r"(?:剩余|剩)\s*(\d+)\s*托", text))
    out = _int(re.search(r"(?:出窑|已出)\s*(\d+)\s*托", text))

    # hours
    hours = (
        _int(re.search(r"(?:已运行|运行|已烘干|烘干)\s*(\d+)\s*小时", text))
        or _int(re.search(r"(\d+)\s*h\b", text, re.I))
    )

    data = load_data()
    k = data.get(kid) or {"trays": [], "status": "empty", "start": None, "completed_time": None, "last_volume": 0.0}

    def set_trays(n: int):
        k["trays"] = _build_kiln_trays(kid, n)

    now = datetime.now()
    t = text

    # empty/reset
    if ("空窑" in t) or re.search(r"\b空\b", t):
        k["trays"] = []
        k["status"] = "empty"
        k["start"] = None
        k["completed_time"] = None
        data[kid] = k
        save_data(data)
        return f"✅ 强制更新成功\n{kid}窑: 空"

    # drying
    if ("烘干中" in t) or ("正在烘干" in t) or ("开始烘干" in t):
        tray_cnt = total if total is not None else _int(re.search(r"(\d+)\s*托", t))
        if tray_cnt is None:
            return "❌ 格式: 强制 B窑烘干中 共计55托 已运行78小时"
        set_trays(tray_cnt)
        k["status"] = "drying"
        if hours is not None and hours >= 0:
            k["start"] = (now - timedelta(hours=hours)).isoformat(timespec="seconds")
        else:
            k["start"] = now.isoformat(timespec="seconds")
        k["completed_time"] = None
        data[kid] = k
        save_data(data)
        htxt = f"{hours}小时" if hours is not None else "-"
        return f"✅ 强制更新成功\n{kid}窑: 烘干中 ({len(k['trays'])} 托, 已运行 {htxt})"

    # loading
    if ("入窑中" in t) or ("正在入窑" in t):
        tray_cnt = total if total is not None else _int(re.search(r"(\d+)\s*托", t))
        if tray_cnt is None:
            return "❌ 格式: 强制 A窑入窑中 共计40托"
        set_trays(tray_cnt)
        k["status"] = "loading"
        k["start"] = None
        k["completed_time"] = None
        data[kid] = k
        save_data(data)
        return f"✅ 强制更新成功\n{kid}窑: 入窑中 ({len(k['trays'])} 托)"

    # ready to unload
    if ("烘干完成待出" in t) or ("待出" in t):
        tray_cnt = total if total is not None else _int(re.search(r"(\d+)\s*托", t))
        if tray_cnt is None:
            return "❌ 格式: 强制 C窑烘干完成待出 共计60托"
        set_trays(tray_cnt)
        k["status"] = "ready_unload"
        if hours is not None and hours >= 0:
            k["start"] = (now - timedelta(hours=hours)).isoformat(timespec="seconds")
        data[kid] = k
        save_data(data)
        return f"✅ 强制更新成功\n{kid}窑: 烘干完成待出 ({len(k['trays'])} 托)"

    # unloading / partial unload
    if ("出窑" in t) or ("出窑中" in t) or ("正在出窑" in t):
        if remain is None:
            if total is not None and out is not None:
                remain = max(total - out, 0)
            elif total is not None:
                remain = total
        if remain is None:
            return "❌ 格式: 强制 A窑出窑 15托 剩余30托"

        total_trays = total
        if total_trays is None and remain is not None and out is not None:
            total_trays = remain + out

        out_trays = out
        if out_trays is None and total_trays is not None:
            out_trays = max(int(total_trays) - int(remain), 0)
        out_trays = int(out_trays or 0)

        prev_applied = int(k.get("unloading_out_applied", 0) or 0)
        delta = 0

        set_trays(remain)
        if remain > 0:
            k["status"] = "unloading"
            k["completed_time"] = None
            if total_trays is not None:
                k["unloading_total_trays"] = int(total_trays)
            k["unloading_out_trays"] = out_trays

            # Make force idempotent: apply only the delta vs previous applied value.
            delta = out_trays - prev_applied
            if delta > 0:
                try:
                    from modules.process_flow.process_flow_engine import add_kiln_done_trays
                    add_kiln_done_trays(delta)
                except Exception:
                    pass

            if delta:
                try:
                    from modules.kiln.kiln_event_log import log_unload_event
                    log_unload_event(
                        kid,
                        delta,
                        m3=None,
                        source="admin_force",
                        meta={"prev_applied": prev_applied, "new_out": out_trays, "remain": remain, "total": total_trays},
                    )
                except Exception:
                    pass
            k["unloading_out_applied"] = out_trays
        else:
            k["trays"] = []
            k["status"] = "completed"
            k["start"] = None
            k["completed_time"] = now.isoformat(timespec="seconds")
            k.pop("unloading_total_trays", None)
            k.pop("unloading_out_trays", None)
            k.pop("unloading_out_applied", None)

        data[kid] = k
        save_data(data)

        extra = ""
        if delta > 0:
            extra = f"\n出窑待二拣: +{delta} 托（累计已出 {out_trays} 托）"
        elif delta < 0:
            extra = (
                f"\n⚠️ 已出托数从 {prev_applied} 托更正为 {out_trays} 托（减少 {abs(delta)} 托）。"
                "\n⚠️ 为避免误扣库存，系统不会自动回滚“出窑待二拣”托池。"
                "\n👉 请另用：强制 出窑待二拣 X托（绝对值修正）"
            )
        if total_trays is not None:
            return f"✅ 强制更新成功\n{kid}窑: 出窑中（{int(total_trays)}托，剩{remain}托）{extra}"
        return f"✅ 强制更新成功\n{kid}窑: 出窑中（剩{remain}托）{extra}"

    # completed
    if ("已完成" in t) or ("完成" in t):
        k["trays"] = []
        k["status"] = "completed"
        k["start"] = None
        k["completed_time"] = now.isoformat(timespec="seconds")
        data[kid] = k
        save_data(data)
        return f"✅ 强制更新成功\n{kid}窑: 已完成"

    return "❌ 未识别指令"


def normalize_force_payload(payload: str) -> str:
    p = (payload or "").strip()
    if not p:
        return ""

    # common typos/aliases -> canonical
    p = (
        p.replace("待二捡", "待二拣")
        .replace("二捡", "二拣")
    ).strip()

    # allow shorthand: "强制 待二拣 40托"
    if p.startswith("待二拣"):
        p = "出窑" + p

    return p


def handle_admin_force(text: str):
    t = (text or "").strip()
    if not t:
        return None
    if not t.startswith("强制"):
        return None

    payload = t[len("强制"):].strip()
    if not payload or payload in ("帮助", "help", "?"):
        return (
            "🧰 强制录入（管理员）\n"
            "窑:\n"
            " - 强制 B窑烘干中 共计55托 已运行78小时\n"
            " - 强制 A窑出窑 15托 剩余30托\n"
            " - 强制 C窑入窑中 共计40托\n"
            " - 强制 D窑烘干完成待出 共计60托\n"
            " - 强制 A窑空\n"
            "分拣入库:\n"
            " - 强制 分拣入库 编号 规格 根数 托数\n"
            "   例: 强制 分拣入库 0303-01 95x71 297 1\n"
            "工序托池:\n"
            " - 强制 上锯待药浸 100托\n"
            " - 强制 药浸待分拣 80托\n"
            " - 强制 分拣待入窑 60托\n"
            " - 强制 出窑待二拣 40托\n"
            " - 强制 待二拣 40托"
            "\n原木库存（绝对值修正）:\n"
            " - 强制 原木库存 23.9961\n"
            "\n分拣余料:\n"
            " - 强制 分拣未满托 886根"
            "\n今日台账（绝对值修正）:\n"
            " - 强制 今日台账 上锯投入 10.7522\n"
            " - 强制 今日台账 上锯产出 12\n"
            " - 强制 今日台账 出窑 35\n"
            " - 强制 今日台账 成品件数 81\n"
            "台账重算:\n"
            " - 强制 重算台账\n"
            " - 强制 重算台账 2026-03-04\n"
            " - 强制 累计台账更正"
        )

    payload = normalize_force_payload(payload)

    # force sorting-in (selected trays) without consuming dip pool
    # 强制 分拣入库 0303-01 95x71 297 1
    m_sort_in = re.match(r"(?:分拣入库|分拣入窑|拣选入库)\s+(\S+)\s+(\S+)\s+(\d+)\s*(\d+)?$", payload)
    if m_sort_in:
        base_id = m_sort_in.group(1).strip()
        spec_token = m_sort_in.group(2).strip()
        pcs = int(m_sort_in.group(3))
        trays = int(m_sort_in.group(4) or 1)
        if pcs <= 0 or trays <= 0:
            return "❌ 数值错误"

        try:
            from modules.process_flow.process_flow_engine import load as flow_load, save as flow_save, _parse_spec, _build_tray, _expand_ids
            d = flow_load()
            d.setdefault("selected_trays", {})
            if not isinstance(d.get("selected_trays"), dict):
                d["selected_trays"] = {}

            parsed = _parse_spec(spec_token)
            if not parsed:
                return "❌ 规格错误（支持: 84 / 84x21 / 950x84x21）"
            length_mm, width_mm, thick_mm = parsed

            ids = _expand_ids(base_id, trays)
            for tid in ids:
                if tid in d["selected_trays"]:
                    return f"❌ 编号重复: {tid}"

            for tid in ids:
                d["selected_trays"][tid] = _build_tray(tid, length_mm, width_mm, thick_mm, pcs)

            flow_save(d)
            id_text = " ".join(ids[:6]) + (" ..." if len(ids) > 6 else "")
            return (
                f"✅ 强制分拣入库成功 {trays} 托\n"
                f"规格: {length_mm}x{width_mm}x{thick_mm}\n"
                f"根数: {pcs} 根/托\n"
                f"编号: {id_text}"
            )
        except Exception:
            return "❌ 分拣入库写入失败"

    # raw logs stock absolute set
    m_raw = re.match(r"(?:原木库存|原木)\s*(-?\d+(?:\.\d+)?)\s*(?:MT|吨|缅吨|တန်)?$", payload, re.I)
    if m_raw:
        v = float(m_raw.group(1))
        if v < 0:
            return "❌ 数值错误"
        try:
            from modules.inventory.inventory_engine import load as inv_load, save as inv_save
            inv = inv_load()
            inv.setdefault("raw", {})
            inv["raw"]["原木"] = v
            inv_save(inv)
            return f"✅ 强制更新成功: 原木库存 = {v} MT"
        except Exception:
            return "❌ 原木库存写入失败"

    # stage pools
    m_pool = re.match(r"(上锯待药浸|药浸待分拣|分拣待入窑|出窑待二拣)\s*(\d+)\s*托", payload)
    if m_pool:
        stage = m_pool.group(1)
        trays = int(m_pool.group(2))
        return _force_set_stage_pool(stage, trays)

    m_loose = re.match(r"(?:分拣未满托|未满托|余料)\s*(\d+)\s*根", payload)
    if m_loose:
        pcs = int(m_loose.group(1))
        if pcs < 0:
            return "❌ 数值错误"
        from modules.process_flow.process_flow_engine import load as flow_load, save as flow_save
        d = flow_load()
        d["selected_loose_pcs"] = pcs
        flow_save(d)
        return f"✅ 强制更新成功: 分拣未满托 = {pcs} 根"

    # today ledger absolute set
    m_led = re.match(r"今日台账\s+(\S+)\s+(-?\d+(?:\.\d+)?)", payload)
    if m_led:
        key = m_led.group(1).strip()
        val = float(m_led.group(2))
        from modules.ledger.production_ledger_engine import load as led_load, save as led_save, ensure_day, today as led_today
        data = led_load()
        day = led_today()
        ensure_day(data, day)
        r = data[day]

        key_map = {
            "saw_mt": "saw_mt",
            "上锯投入": "saw_mt",
            "saw_tray": "saw_tray",
            "上锯产出": "saw_tray",
            "kiln_out_tray": "kiln_out_tray",
            "出窑": "kiln_out_tray",
            "pack_pkg": "pack_pkg",
            "成品件数": "pack_pkg",
        }
        target = key_map.get(key)
        if not target:
            return "❌ 未识别指令"

        if target in ("saw_tray", "kiln_out_tray", "pack_pkg"):
            r[target] = int(val)
        else:
            r[target] = float(val)
        led_save(data)
        return f"✅ 强制更新成功: 今日台账 {target} = {r[target]}"

    # ledger rebuild (from traceable sources)
    m_rebuild = re.match(r"(?:重算台账|台账更正)\s*(\d{4}-\d{2}-\d{2}|今日)?$", payload)
    if m_rebuild:
        token = (m_rebuild.group(1) or "").strip()
        day = None
        if token and token != "今日":
            day = token
        from modules.ledger.production_ledger_engine import rebuild_ledger
        return rebuild_ledger(day=day)

    if payload in ("累计台账更正", "重算累计台账"):
        from modules.ledger.production_ledger_engine import rebuild_ledger
        return rebuild_ledger(day=None)

    # kiln force
    r = _force_kiln(payload)
    if r:
        return r

    return "❌ 未识别指令"
