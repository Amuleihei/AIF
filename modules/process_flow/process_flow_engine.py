import json
import re
from datetime import datetime
from pathlib import Path
from web.data_store import get_flow_data, save_flow_data


DATA_FILE = Path.home() / "AIF/data/process_flow/flow.json"


DEFAULT = {
    "saw_tray_pool": 0,          # 上锯后待药浸托
    "dip_tray_pool": 0,          # 药浸后待分拣托
    "selected_tray_pool": 0,     # 分拣后待入窑托
    "selected_loose_pcs": 0,     # 分拣未满托余料(根)（不计入托数）
    "kiln_done_tray_pool": 0,    # 出窑后待二次拣选托
    "selected_trays": {},        # {tray_id: tray_data}
    "saw_machine_totals": {},    # {1..6: {"mt": x, "tray": y}}
    "saw_machine_daily": {},     # {YYYY-MM-DD: {1..6: {"mt":x,"tray":y,"bark":z,"dust":k}}}
    "dip_chem_bag_total": 0,     # 药剂累计(袋)
    "bark_tray_total": 0,        # 树皮累计(托)
    "dust_bag_total": 0,         # 木渣累计(袋)
    "second_sort_ok_m3": 0.0,    # 二次拣选成品体积
    "second_sort_ab_m3": 0.0,    # AB体积
    "second_sort_bc_m3": 0.0,    # BC体积
    "second_sort_loss_m3": 0.0,  # 正常损耗(去除段)
    "second_sort_records": [],   # 二次拣选明细
}


def _to_int(v, default=None):
    try:
        return int(v)
    except Exception:
        return default


def _to_float(v, default=None):
    try:
        return float(v)
    except Exception:
        return default


def _today_tag():
    return datetime.now().strftime("%y%m%d")


def _today_date():
    return datetime.now().strftime("%Y-%m-%d")


def _sync_pool_count(d):
    d["selected_tray_pool"] = len(d.get("selected_trays", {}))
    # Only sync kiln_done_tray_pool when tray-level details exist.
    if "kiln_done_trays" in d and isinstance(d.get("kiln_done_trays"), list):
        d["kiln_done_tray_pool"] = len(d.get("kiln_done_trays") or [])


def _sync_ledger(delta: dict):
    try:
        from modules.ledger.production_ledger_engine import record_delta
        record_delta(delta)
    except Exception:
        pass


def _parse_spec(token: str):
    """
    支持:
    84
    84x21
    950x84x21
    """
    parts = token.lower().replace("mm", "").split("x")
    parts = [p.strip() for p in parts if p.strip()]

    if len(parts) == 1:
        w = _to_int(parts[0])
        if w is None:
            return None
        return 950, w, 21

    if len(parts) == 2:
        w = _to_int(parts[0])
        t = _to_int(parts[1])
        if w is None or t is None:
            return None
        return 950, w, t

    if len(parts) == 3:
        l = _to_int(parts[0])
        w = _to_int(parts[1])
        t = _to_int(parts[2])
        if l is None or w is None or t is None:
            return None
        return l, w, t

    return None


def _next_auto_id(d, prefix="S"):
    tray_map = d.get("selected_trays", {})
    base = f"{prefix}{_today_tag()}"
    i = 1
    while True:
        tid = f"{base}{i:03d}"
        if tid not in tray_map:
            return tid
        i += 1


def _expand_ids(base_id: str, count: int):
    if count <= 1:
        return [base_id]
    return [f"{base_id}-{i:02d}" for i in range(1, count + 1)]


def _build_tray(tray_id: str, length_mm: int, width_mm: int, thick_mm: int, pcs: int):
    return {
        "id": tray_id,
        "length_mm": length_mm,
        "width_mm": width_mm,
        "thick_mm": thick_mm,
        "pcs": pcs,
        # 窑模块材积计算使用这个字段
        "spec": f"{width_mm}x{pcs}",
        "full_spec": f"{length_mm}x{width_mm}x{thick_mm}",
    }


def _parse_saw_input(text: str, parts: list[str]):
    """
    兼容两种格式:
    1) 旧格式: 上锯 缅吨 托数 [树皮托] [木渣袋]
    2) 新格式(空格可省):
       上锯3吨 成品2托 树皮2托 木渣5袋 [锯号3]
       上锯3成品2托树皮2托木渣5袋3号锯
    返回: (mt, trays, bark_tray, dust_bag, saw_no, err)
    """
    # 旧格式优先
    if len(parts) in (3, 4, 5):
        mt = _to_float(parts[1])
        trays = _to_int(parts[2])
        bark_tray = _to_int(parts[3], 0) if len(parts) >= 4 else 0
        dust_bag = _to_int(parts[4], 0) if len(parts) >= 5 else 0
        if (
            mt is not None and trays is not None and trays > 0
            and bark_tray is not None and bark_tray >= 0
            and dust_bag is not None and dust_bag >= 0
        ):
            return mt, trays, bark_tray, dust_bag, None, None

    saw_no = None
    m_saw = re.search(r"(?:锯号|锯机)\s*([1-6])|([1-6])号锯", text)
    if m_saw:
        saw_no = _to_int(m_saw.group(1) or m_saw.group(2))

    mt = None
    m_mt = re.search(r"上锯\s*([0-9]+(?:\.[0-9]+)?)", text)
    if m_mt:
        mt = _to_float(m_mt.group(1))
    if mt is None:
        m_mt = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*(?:缅吨|吨|MT|mt)", text)
        if m_mt:
            mt = _to_float(m_mt.group(1))

    bark_tray = 0
    m_bark = re.search(r"树皮\s*([0-9]+)\s*托", text)
    if m_bark:
        bark_tray = _to_int(m_bark.group(1), 0) or 0

    dust_bag = 0
    m_dust = re.search(r"木渣\s*([0-9]+)\s*袋", text)
    if m_dust:
        dust_bag = _to_int(m_dust.group(1), 0) or 0

    trays = None
    m_prod = re.search(r"(?:成品|半成品|产出|出)\s*([0-9]+)\s*托", text)
    if m_prod:
        trays = _to_int(m_prod.group(1))
    else:
        for m in re.finditer(r"([0-9]+)\s*托", text):
            prefix = text[max(0, m.start() - 4):m.start()]
            if "树皮" in prefix:
                continue
            trays = _to_int(m.group(1))
            break

    if mt is None or mt <= 0:
        return None, None, None, None, None, "❌ 未识别上锯吨数（示例: 上锯3吨 ...）"
    if trays is None or trays <= 0:
        return None, None, None, None, None, "❌ 未识别成品托数（示例: 成品2托）"
    if bark_tray < 0 or dust_bag < 0:
        return None, None, None, None, None, "❌ 树皮托/木渣袋数值错误"

    return mt, trays, bark_tray, dust_bag, saw_no, None


def _saw_team_report(d):
    # 总量采用今日台账，确保包含所有“上锯”记录（即便未标锯号）
    try:
        from modules.ledger.production_ledger_engine import load as ledger_load, today as ledger_today
        ledger = ledger_load()
        day = ledger_today()
        rec = ledger.get(day, {})
        total_mt = float(rec.get("saw_mt", 0.0))
        total_tray = int(rec.get("saw_tray", 0))
        total_bark = int(rec.get("bark_tray", 0))
        total_dust = int(rec.get("dust_bag", 0))
    except Exception:
        total_mt = 0.0
        total_tray = 0
        total_bark = 0
        total_dust = 0

    day_key = _today_date()
    daily = d.get("saw_machine_daily", {}).get(day_key, {})

    lines = [
        f"🪚 锯工组统计（{day_key}）",
        f"总上锯: {total_mt:.2f} 吨",
        f"总成品: {total_tray} 托",
        f"总树皮: {total_bark} 托",
        f"总木渣: {total_dust} 袋",
    ]

    machine_mt = 0.0
    machine_tray = 0
    machine_bark = 0
    machine_dust = 0
    has_machine = False

    for i in range(1, 7):
        r = daily.get(str(i), {})
        mt = _to_float(r.get("mt"), 0.0) or 0.0
        tray = _to_int(r.get("tray"), 0) or 0
        bark = _to_int(r.get("bark"), 0) or 0
        dust = _to_int(r.get("dust"), 0) or 0
        if mt > 0 or tray > 0 or bark > 0 or dust > 0:
            has_machine = True
            lines.append(f"{i}号锯: {mt:.2f}吨 | 成品{tray}托 | 树皮{bark}托 | 木渣{dust}袋")
        machine_mt += mt
        machine_tray += tray
        machine_bark += bark
        machine_dust += dust

    if not has_machine:
        lines.append("1-6号锯: 今日暂无带锯号记录")

    un_mt = max(0.0, total_mt - machine_mt)
    un_tray = max(0, total_tray - machine_tray)
    un_bark = max(0, total_bark - machine_bark)
    un_dust = max(0, total_dust - machine_dust)
    if un_mt > 0 or un_tray > 0 or un_bark > 0 or un_dust > 0:
        lines.append(f"未标锯号: {un_mt:.2f}吨 | 成品{un_tray}托 | 树皮{un_bark}托 | 木渣{un_dust}袋")

    return "\n".join(lines)


def _single_saw_report(d, saw_no: int):
    day_key = _today_date()
    daily = d.get("saw_machine_daily", {}).get(day_key, {})
    r = daily.get(str(saw_no), {})
    mt = _to_float(r.get("mt"), 0.0) or 0.0
    tray = _to_int(r.get("tray"), 0) or 0
    bark = _to_int(r.get("bark"), 0) or 0
    dust = _to_int(r.get("dust"), 0) or 0
    return (
        f"🪚 {saw_no}号锯统计（{day_key}）\n"
        f"上锯: {mt:.2f} 吨\n"
        f"成品: {tray} 托\n"
        f"树皮: {bark} 托\n"
        f"木渣: {dust} 袋"
    )


def load():
    try:
        d = get_flow_data()
    except Exception:
        d = {}

    changed = False
    for k, v in DEFAULT.items():
        if k not in d:
            if isinstance(v, dict):
                d[k] = {}
            else:
                d[k] = v
            changed = True
    if not isinstance(d.get("selected_loose_pcs"), int):
        d["selected_loose_pcs"] = _to_int(d.get("selected_loose_pcs"), 0) or 0
        changed = True

    if not isinstance(d.get("selected_trays"), dict):
        d["selected_trays"] = {}
        changed = True
    if not isinstance(d.get("saw_machine_totals"), dict):
        d["saw_machine_totals"] = {}
        changed = True
    if not isinstance(d.get("saw_machine_daily"), dict):
        d["saw_machine_daily"] = {}
        changed = True

    _sync_pool_count(d)

    if changed:
        save(d)

    return d


def save(d):
    _sync_pool_count(d)
    save_flow_data(d)


def reserve_selected_trays(count: int):
    """
    给窑模块调用：仅按数量预留（兼容旧命令）。
    """
    d = load()
    have = d.get("selected_tray_pool", 0)
    if have < count:
        return False, f"❌ 分拣托不足（当前 {have} 托，需 {count} 托）"

    # 旧式按规格入窑：顺序消费待入窑编号
    tray_map = d.get("selected_trays", {})
    removed = 0
    for tid in list(tray_map.keys()):
        tray_map.pop(tid, None)
        removed += 1
        if removed >= count:
            break
    d["selected_trays"] = tray_map
    save(d)
    return True, None


def reserve_kiln_done_trays(count: int):
    """
    预留“出窑待二拣”托（用于把某些成品入库视为二次分拣完成时的联动扣减）。
    """
    ok, msg, _items = take_kiln_done_trays(count)
    return ok, msg


def take_kiln_done_trays(count: int):
    """
    Take trays from kiln-done pool.
    If tray-level details exist, pop from d['kiln_done_trays'] FIFO.
    Returns: (ok, msg, items)
    """
    d = load()
    have = _to_int(d.get("kiln_done_tray_pool"), 0) or 0
    need = int(count or 0)
    if need <= 0:
        return False, "❌ 托数错误", []
    if have < need:
        return False, f"❌ 出窑托不足（当前 {have} 托，需 {need} 托）", []

    items: list[dict] = []
    if "kiln_done_trays" in d and isinstance(d.get("kiln_done_trays"), list):
        lst = d.get("kiln_done_trays") or []
        if lst:
            items = lst[:need]
            d["kiln_done_trays"] = lst[need:]
        # kiln_done_tray_pool will be synced from list on save()
    else:
        d["kiln_done_tray_pool"] = have - need

    save(d)
    return True, None, items


def take_selected_trays_by_ids(ids: list[str]):
    """
    给窑模块调用：按编号取托并从待入窑池删除。
    """
    d = load()
    tray_map = d.get("selected_trays", {})
    selected = []
    missing = []

    for raw in ids:
        tid = raw.strip()
        if not tid:
            continue
        if tid in tray_map:
            selected.append(tray_map[tid])
            continue

        # 支持简写：后缀唯一匹配
        candidates = [k for k in tray_map if k.endswith(tid)]
        if len(candidates) == 1:
            selected.append(tray_map[candidates[0]])
        else:
            missing.append(tid)

    if missing:
        return False, f"❌ 未找到分拣编号: {' '.join(missing)}", []

    for t in selected:
        tray_map.pop(t["id"], None)

    d["selected_trays"] = tray_map
    save(d)
    return True, None, selected


def add_kiln_done_trays(count: int):
    """
    给窑模块调用：出窑后进入“待二次拣选托池”。
    """
    d = load()
    if "kiln_done_trays" in d and isinstance(d.get("kiln_done_trays"), list):
        # Keep tray-level list as source of truth when present.
        for _ in range(max(int(count or 0), 0)):
            d["kiln_done_trays"].append({"id": None, "spec": "?"})
    else:
        d["kiln_done_tray_pool"] = (_to_int(d.get("kiln_done_tray_pool"), 0) or 0) + count
    save(d)


def add_kiln_done_tray_items(trays: list[dict]):
    """
    Append tray-level details for kiln-done pool, so `ss` can reference kiln-in specs.
    Each item should contain at least: {id, spec}.
    """
    if not isinstance(trays, list) or not trays:
        return

    d = load()
    if "kiln_done_trays" not in d or not isinstance(d.get("kiln_done_trays"), list):
        # Migrate existing numeric pool into placeholders, so counts remain consistent.
        existing = _to_int(d.get("kiln_done_tray_pool"), 0) or 0
        d["kiln_done_trays"] = [{"id": None, "spec": "?"} for _ in range(max(existing, 0))]

    for t in trays:
        if not isinstance(t, dict):
            continue
        tid = str(t.get("id") or "").strip() or None
        spec = str(t.get("full_spec") or t.get("spec") or "").strip()
        if not spec:
            spec = "?"
        d["kiln_done_trays"].append({"id": tid, "spec": spec})

    save(d)


def _kiln_done_spec_summary(d: dict, limit: int = 10) -> tuple[int, list[tuple[str, int]]]:
    """
    Returns: (total_trays, [(spec, count), ...])
    """
    total = _to_int(d.get("kiln_done_tray_pool"), 0) or 0
    if "kiln_done_trays" not in d or not isinstance(d.get("kiln_done_trays"), list):
        return total, []
    lst = d.get("kiln_done_trays") or []
    if not lst:
        return total, []

    m: dict[str, int] = {}
    for t in lst:
        if not isinstance(t, dict):
            continue
        spec = str(t.get("spec") or "?").strip() or "?"
        m[spec] = m.get(spec, 0) + 1

    items = sorted(m.items(), key=lambda kv: (-kv[1], kv[0]))[:limit]
    return len(lst), items


def stage_inventory(d):
    ratio = ""
    if d["second_sort_ok_m3"] > 0:
        ab_pct = d["second_sort_ab_m3"] / d["second_sort_ok_m3"] * 100
        bc_pct = d["second_sort_bc_m3"] / d["second_sort_ok_m3"] * 100
        ratio = f"\n二拣AB/BC: {ab_pct:.1f}% / {bc_pct:.1f}%"

    loose = _to_int(d.get("selected_loose_pcs"), 0) or 0
    loose_line = f"分拣未满托: {loose} 根\n" if loose > 0 else ""

    return (
        "📦 各工序库存\n"
        f"上锯待药浸(锯解托): {d['saw_tray_pool']} 托\n"
        f"药浸待分拣(锯解托): {d['dip_tray_pool']} 托\n"
        f"药剂累计: {d.get('dip_chem_bag_total', 0)} 袋\n"
        f"树皮累计: {d.get('bark_tray_total', 0)} 托\n"
        f"木渣累计: {d.get('dust_bag_total', 0)} 袋\n"
        f"分拣待入窑(入窑托): {d['selected_tray_pool']} 托\n"
        f"{loose_line}"
        f"出窑待二拣(入窑托): {d['kiln_done_tray_pool']} 托\n"
        f"二次拣选成品: {d['second_sort_ok_m3']:.2f} m³\n"
        f"二次拣选AB: {d['second_sort_ab_m3']:.2f} m³\n"
        f"二次拣选BC: {d['second_sort_bc_m3']:.2f} m³\n"
        f"二次拣选损耗: {d['second_sort_loss_m3']:.2f} m³"
        f"{ratio}"
    )


def tray_list(d, limit=30):
    tray_map = d.get("selected_trays", {})
    if not tray_map:
        return "📋 分拣编号\n无待入窑编号"

    lines = ["📋 分拣编号（待入窑）"]
    i = 0
    for tid in sorted(tray_map.keys()):
        t = tray_map.get(tid) or {}
        pcs = t.get("pcs")
        pcs_text = f"{pcs}根" if isinstance(pcs, int) and pcs > 0 else "-根"
        lines.append(f"{tid} | {t.get('full_spec','?')} | {pcs_text}")
        i += 1
        if i >= limit:
            break
    if len(tray_map) > limit:
        lines.append(f"... 其余 {len(tray_map)-limit} 条")
    return "\n".join(lines)


def tray_export_kiln_load(d, kid: str = "A", per_line: int = 20, limit: int = 200) -> str:
    """
    Export selected tray IDs into multi-line 'X窑入窑 ...' commands for copy-paste.
    """
    tray_map = d.get("selected_trays", {})
    if not tray_map:
        return "📋 待入窑导出\n无待入窑编号"

    kid = (kid or "A").strip().upper()
    if kid not in ("A", "B", "C", "D"):
        kid = "A"

    try:
        per_line = int(per_line)
    except Exception:
        per_line = 20
    per_line = max(5, min(per_line, 40))

    ids = sorted(list(tray_map.keys()))[: max(1, int(limit))]

    lines = [
        f"📋 待入窑导出（可复制粘贴，一行一条）",
        f"合计: {len(tray_map)} 托；本次导出: {len(ids)} 托",
        "",
    ]

    for i in range(0, len(ids), per_line):
        chunk = ids[i : i + per_line]
        lines.append(f"{kid}窑入窑 " + " ".join(chunk))

    if len(tray_map) > len(ids):
        lines.append("")
        lines.append(f"⚠️ 超过导出上限 {limit} 托，未全部导出。可用：待入窑导出 {kid} {per_line} 500")

    return "\n".join(lines)


def _handle_sorting(d, parts):
    # 分拣 编号 规格 根数 [托数]
    # 分拣 规格 根数 [托数]  (自动编号)
    if len(parts) < 3:
        return "❌ 格式: 分拣 [编号] 规格 根数 [托数]"

    has_id = ("-" in parts[1]) or any(ch.isalpha() for ch in parts[1])
    if has_id:
        if len(parts) < 4:
            return "❌ 格式: 分拣 编号 规格 根数 [托数]"
        base_id = parts[1]
        spec_token = parts[2]
        pcs = _to_int(parts[3])
        tray_count = _to_int(parts[4], 1) if len(parts) > 4 else 1
    else:
        base_id = None
        spec_token = parts[1]
        pcs = _to_int(parts[2])
        tray_count = _to_int(parts[3], 1) if len(parts) > 3 else 1

    if pcs is None or pcs <= 0 or tray_count is None or tray_count <= 0:
        return "❌ 数值错误"

    parsed = _parse_spec(spec_token)
    if not parsed:
        return "❌ 规格错误（支持: 84 / 84x21 / 950x84x21）"
    length_mm, width_mm, thick_mm = parsed

    if d["dip_tray_pool"] < tray_count:
        return f"❌ 药浸托不足（当前 {d['dip_tray_pool']} 托，需 {tray_count} 托）"

    if base_id:
        ids = _expand_ids(base_id, tray_count)
    else:
        ids = [_next_auto_id(d) for _ in range(tray_count)]

    for tid in ids:
        if tid in d["selected_trays"]:
            return f"❌ 编号重复: {tid}"

    for tid in ids:
        d["selected_trays"][tid] = _build_tray(tid, length_mm, width_mm, thick_mm, pcs)

    d["dip_tray_pool"] -= tray_count
    save(d)
    _sync_ledger({"select_tray": tray_count})

    id_text = " ".join(ids[:6]) + (" ..." if len(ids) > 6 else "")
    return (
        f"🧰 分拣完成 {tray_count} 托\n"
        f"规格: {length_mm}x{width_mm}x{thick_mm}\n"
        f"根数: {pcs} 根/托\n"
        f"编号: {id_text}"
    )


def handle_process_flow(text):
    d = load()
    raw = text.strip()
    parts = text.split()
    if not parts:
        return None

    cmd = parts[0]

    # 上锯 3.2 12  -> MT + 托
    if cmd == "上锯" or raw.startswith("上锯"):
        mt, trays, bark_tray, dust_bag, saw_no, err = _parse_saw_input(text, parts)
        if err:
            return (
                f"{err}\n"
                "格式1: 上锯 缅吨 托数 [树皮托] [木渣袋]\n"
                "格式2: 上锯3吨 成品2托 树皮2托 木渣5袋 [锯号3]"
            )

        # 原木库存联动：上锯投入视为原木消耗
        raw_warn = ""
        try:
            from modules.inventory.inventory_engine import load as inv_load, save as inv_save
            inv = inv_load()
            cur = float((inv.get("raw") or {}).get("原木", 0) or 0.0)
            if cur < mt - 1e-9:
                (inv.setdefault("raw", {}))["原木"] = 0.0
                raw_warn = "\n⚠️ 原木库存不足，已扣到 0（请管理员强制对齐）"
            else:
                (inv.setdefault("raw", {}))["原木"] = cur - float(mt)
            inv_save(inv)
        except Exception:
            # 库存联动失败不阻断生产录入
            pass

        d["saw_tray_pool"] += trays
        d["bark_tray_total"] = (_to_int(d.get("bark_tray_total"), 0) or 0) + bark_tray
        d["dust_bag_total"] = (_to_int(d.get("dust_bag_total"), 0) or 0) + dust_bag
        if saw_no:
            key = str(saw_no)
            rec = d["saw_machine_totals"].get(key, {"mt": 0.0, "tray": 0})
            rec["mt"] = (_to_float(rec.get("mt"), 0.0) or 0.0) + mt
            rec["tray"] = (_to_int(rec.get("tray"), 0) or 0) + trays
            d["saw_machine_totals"][key] = rec
            day_key = _today_date()
            day_map = d["saw_machine_daily"].setdefault(day_key, {})
            day_rec = day_map.get(key, {"mt": 0.0, "tray": 0, "bark": 0, "dust": 0})
            day_rec["mt"] = (_to_float(day_rec.get("mt"), 0.0) or 0.0) + mt
            day_rec["tray"] = (_to_int(day_rec.get("tray"), 0) or 0) + trays
            day_rec["bark"] = (_to_int(day_rec.get("bark"), 0) or 0) + bark_tray
            day_rec["dust"] = (_to_int(day_rec.get("dust"), 0) or 0) + dust_bag
            day_map[key] = day_rec
            d["saw_machine_daily"][day_key] = day_map
        save(d)
        _sync_ledger({
            "log_mt": mt,
            "saw_mt": mt,
            "saw_tray": trays,
            "bark_tray": bark_tray,
            "dust_bag": dust_bag,
        })
        saw_text = f"，锯号{saw_no}" if saw_no else ""
        return f"🪚 上锯完成：投入 {mt:.2f} MT，产出 {trays} 托，树皮{bark_tray}托 木渣{dust_bag}袋{saw_text}{raw_warn}"

    # 药浸 2 / 药浸 2 药
    if cmd == "药浸":
        if len(parts) < 2:
            return "❌ 格式: 药浸 罐次 [托数] [药剂袋数]"
        tanks = _to_int(parts[1])
        if tanks is None or tanks <= 0:
            return "❌ 数值错误"

        trays = tanks * 4
        chem_bags = 0
        if len(parts) >= 3:
            trays = _to_int(parts[2])
            if trays is None or trays <= 0:
                return "❌ 托数错误"
        if len(parts) >= 4:
            bag_token = parts[3].replace("袋", "")
            chem_bags = _to_int(bag_token)
            if chem_bags is None or chem_bags < 0:
                return "❌ 药剂袋数错误"

        if d["saw_tray_pool"] < trays:
            return f"❌ 上锯托不足（当前 {d['saw_tray_pool']} 托，需 {trays} 托）"
        d["saw_tray_pool"] -= trays
        d["dip_tray_pool"] += trays
        d["dip_chem_bag_total"] = (_to_int(d.get("dip_chem_bag_total"), 0) or 0) + chem_bags
        save(d)
        _sync_ledger({
            "dip_tank": tanks,
            "dip_tray": trays,
            "dip_chem": chem_bags > 0,
            "dip_bag": chem_bags,
        })
        return f"🧪 药浸完成 {tanks} 罐（{trays} 托，药剂 {chem_bags} 袋）"

    # 分拣 ...（带编号/规格/根数）
    if cmd in ("分拣", "拣选"):
        return _handle_sorting(d, parts)

    # 二次拣选 6 1.8 1.0 0.8
    if cmd == "二次拣选":
        # ✅ 日常：ss / 二次拣选（仅输出参考入窑规格，不改数据）
        if len(parts) == 1:
            total, items = _kiln_done_spec_summary(d)
            lines = ["📦 二次拣选（参考入窑规格）", f"待二拣: {int(d.get('kiln_done_tray_pool', 0) or 0)} 托"]
            if items:
                lines.append("规格汇总:")
                for spec, cnt in items:
                    lines.append(f"- {spec}: {cnt}托")
                if total > sum(c for _, c in items):
                    lines.append(f"... 其余 {total - sum(c for _, c in items)} 托")
            else:
                lines.append("⚠️ 暂无规格明细（旧数据/未记录出窑托明细）")
            lines.append("")
            lines.append("补数据(只扣待二拣): ss 10托")
            return "\n".join(lines)

        # ✅ 补数据：ss X托 / 二次拣选 X托（只扣待二拣托池，并记录规格参考）
        m_trays = re.fullmatch(r"二次拣选\s*(\d+)\s*(?:托|tray|tr|Tr|ထောင့်)?$", raw.strip(), re.I)
        if m_trays:
            trays = _to_int(m_trays.group(1))
            if trays is None or trays <= 0:
                return "❌ 托数错误"
            ok, msg, items = take_kiln_done_trays(trays)
            if not ok:
                return msg

            spec_lines = []
            spec_summary: dict[str, int] = {}
            if items:
                m: dict[str, int] = {}
                for t in items:
                    if not isinstance(t, dict):
                        continue
                    spec = str(t.get("spec") or "?").strip() or "?"
                    m[spec] = m.get(spec, 0) + 1
                for spec, cnt in sorted(m.items(), key=lambda kv: (-kv[1], kv[0])):
                    spec_lines.append(f"- {spec}: {cnt}托")
                    spec_summary[spec] = int(cnt)

            d["second_sort_records"].append({
                "time": datetime.now().isoformat(timespec="seconds"),
                "trays": trays,
                "mode": "ss_trays_only",
                "ok_m3": 0.0,
                "ab_m3": 0.0,
                "bc_m3": 0.0,
                "loss_m3": 0.0,
                "spec_summary": spec_summary,
            })
            save(d)

            out = f"✅ 二次拣选补数据完成\n扣减待二拣: {trays} 托"
            if spec_lines:
                out += "\n规格参考:\n" + "\n".join(spec_lines)
            return out

        return "❌ 格式:\n- ss\n- ss 10托"

    if text in ("二次拣选记录", "二拣记录"):
        recs = d.get("second_sort_records", [])
        if not recs:
            return "📄 无二次拣选记录"
        lines = ["📄 二次拣选记录"]
        for r in recs[-20:]:
            total = (r.get("ab_m3", 0) + r.get("bc_m3", 0))
            ab_pct = (r.get("ab_m3", 0) / total * 100) if total > 0 else 0
            bc_pct = (r.get("bc_m3", 0) / total * 100) if total > 0 else 0
            lines.append(
                f"{r.get('time','?')} | {r.get('trays',0)}托 | "
                f"成品{r.get('ok_m3',0):.2f} | AB{r.get('ab_m3',0):.2f} "
                f"BC{r.get('bc_m3',0):.2f} | AB/BC {ab_pct:.1f}/{bc_pct:.1f}%"
            )
        return "\n".join(lines)

    if text in ("工序库存", "流程库存", "工序状态"):
        return stage_inventory(d)

    if text in ("分拣列表", "待入窑编号", "分拣编号"):
        return tray_list(d)

    m_export = re.fullmatch(r"(?:待入窑导出|分拣导出)(?:\s*([ABCD]))?(?:\s*(\d+))?(?:\s*(\d+))?", raw.strip(), re.I)
    if m_export:
        kid = (m_export.group(1) or "A").upper()
        per_line = int(m_export.group(2) or 20)
        limit = int(m_export.group(3) or 200)
        return tray_export_kiln_load(d, kid=kid, per_line=per_line, limit=limit)

    if text in ("锯工组统计", "今日锯工组", "锯机统计", "锯组统计"):
        return _saw_team_report(d)

    m = re.fullmatch(r"(?:锯号\s*([1-6])|([1-6])号锯)(?:统计|数据|产值)?", raw)
    if m:
        saw_no = _to_int(m.group(1) or m.group(2))
        if saw_no is None:
            return "❌ 锯号错误（1-6）"
        return _single_saw_report(d, saw_no)

    # 交给其他模块（例如 production/process_flow 的“流转”）
    return None
