import json
from pathlib import Path
from datetime import datetime
from copy import deepcopy


DATA_FILE = Path.home() / "AIF/data/ledger/production_ledger.json"


# =====================================================
# 默认结构
# =====================================================

DEFAULT_DAY = {
    "log_mt": 0.0,          # 原木消耗
    "saw_mt": 0.0,          # 上锯量
    "saw_m3": 0.0,          # 上锯体积(兼容报表)
    "saw_tray": 0,          # 锯解托
    "dip_tank": 0,          # 药浸罐次
    "dip_tray": 0,          # 药浸托
    "dip_chem": False,      # 是否用药
    "dip_bag": 0,           # 药剂袋数
    "select_tray": 0,       # 拣选托
    "kiln_tray": 0,         # 入窑托
    "kiln_in_m3": 0.0,      # 入窑体积(兼容报表)
    "kiln_out_m3": 0.0,     # 出窑体积(兼容报表)
    "kiln_out_tray": 0,     # 出窑托（用于日报口径）
    "pack_pkg": 0,          # 成品件数（包/托数口径）
    "pack_pcs": 0,          # 打包件数
    "pack_m3": 0.0,         # 成品立方
    "product_m3": 0.0,      # 成品立方(兼容报表)
    "ab_m3": 0.0,           # AB料
    "bc_m3": 0.0,           # BC料
    "bark_tray": 0,         # 树皮产量(托)
    "dust_bag": 0,          # 木渣产量(袋)
    "bark_sale": 0.0,       # 树皮销售
    "dust_sale": 0.0        # 木渣销售
}


# =====================================================
# 工具
# =====================================================

def as_float(v):
    try:
        return float(v)
    except Exception:
        return None


def as_int(v):
    try:
        return int(v)
    except Exception:
        return None


def today():
    return datetime.now().strftime("%Y-%m-%d")


def load():
    if not DATA_FILE.exists():
        save({})
        return {}
    try:
        d = json.load(open(DATA_FILE))
        changed = False
        for day, rec in d.items():
            if not isinstance(rec, dict):
                continue
            for k, v in DEFAULT_DAY.items():
                if k not in rec:
                    rec[k] = v
                    changed = True
        if changed:
            save(d)
        return d
    except:
        save({})
        return {}


def save(d):
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(DATA_FILE, "w") as f:
        json.dump(d, f, indent=2, ensure_ascii=False)


def ensure_day(d, day):
    if day not in d:
        d[day] = DEFAULT_DAY.copy()
    else:
        # 老数据自动补齐新字段
        for k, v in DEFAULT_DAY.items():
            d[day].setdefault(k, v)
    return d


INT_FIELDS = {
    "saw_tray", "dip_tank", "dip_tray", "dip_bag",
    "select_tray", "kiln_tray", "kiln_out_tray", "pack_pkg", "pack_pcs", "bark_tray", "dust_bag"
}
FLOAT_FIELDS = {
    "log_mt", "saw_mt", "saw_m3", "kiln_in_m3", "kiln_out_m3",
    "pack_m3", "product_m3", "ab_m3", "bc_m3", "bark_sale", "dust_sale",
}
# 这些命令已由业务模块自动联动，默认禁止手工再记，避免重叠累计。
AUTO_SYNC_COMMANDS = {"原木", "入窑", "打包", "AB", "BC"}


def record_delta(delta: dict, day: str | None = None) -> bool:
    """
    增量写入台账（给业务模块调用）。
    返回 True/False，不抛异常，避免影响主流程。
    """
    try:
        data = load()
        target_day = day or today()
        data = ensure_day(data, target_day)
        r = data[target_day]

        for key, value in delta.items():
            if key == "dip_chem":
                if value:
                    r["dip_chem"] = True
                continue

            if key in INT_FIELDS:
                iv = as_int(value)
                if iv is None:
                    continue
                r[key] += iv
                continue

            if key in FLOAT_FIELDS:
                fv = as_float(value)
                if fv is None:
                    continue
                r[key] += fv
                continue

        save(data)
        return True
    except Exception:
        return False


def _sum_saw_daily(flow: dict, day: str) -> dict:
    day_map = ((flow.get("saw_machine_daily") or {}).get(day) or {})
    if not isinstance(day_map, dict) or not day_map:
        return {}

    saw_mt = 0.0
    saw_tray = 0
    bark_tray = 0
    dust_bag = 0

    for rec in day_map.values():
        if not isinstance(rec, dict):
            continue
        saw_mt += float(rec.get("mt", 0) or 0)
        saw_tray += int(rec.get("tray", 0) or 0)
        bark_tray += int(rec.get("bark", 0) or 0)
        dust_bag += int(rec.get("dust", 0) or 0)

    return {
        "saw_mt": saw_mt,
        "saw_tray": saw_tray,
        "bark_tray": bark_tray,
        "dust_bag": dust_bag,
    }


def _sum_second_sort_daily(flow: dict, day: str) -> dict:
    recs = flow.get("second_sort_records") or []
    if not isinstance(recs, list):
        return {}

    pack_pkg = 0
    pack_pcs = 0
    pack_m3 = 0.0
    ab_m3 = 0.0
    bc_m3 = 0.0
    found = 0

    for rec in recs:
        if not isinstance(rec, dict):
            continue
        t = rec.get("time")
        if not isinstance(t, str) or not t.startswith(day):
            continue
        found += 1
        trays = int(rec.get("trays", 0) or 0)
        pcs = int(rec.get("pcs", 0) or 0)
        pack_pkg += trays
        pack_pcs += trays * pcs
        pack_m3 += float(rec.get("ok_m3", 0) or 0)
        ab_m3 += float(rec.get("ab_m3", 0) or 0)
        bc_m3 += float(rec.get("bc_m3", 0) or 0)

    if found == 0:
        return {}

    out = {
        "pack_pkg": pack_pkg,
        "pack_m3": pack_m3,
        "product_m3": pack_m3,
        "ab_m3": ab_m3,
        "bc_m3": bc_m3,
    }
    # 仅在能计算时覆盖 pack_pcs，避免把旧有效值误置 0
    if pack_pcs > 0:
        out["pack_pcs"] = pack_pcs
    return out


def _sum_kiln_completed_daily(kiln: dict, day: str) -> dict:
    if not isinstance(kiln, dict):
        return {}
    trays = 0
    m3 = 0.0
    for k in kiln.values():
        if not isinstance(k, dict):
            continue
        t = k.get("completed_time")
        if not isinstance(t, str) or not t.startswith(day):
            continue
        trays += int(k.get("last_trays", 0) or 0)
        m3 += float(k.get("last_volume", 0) or 0)
    if trays <= 0 and m3 <= 0:
        return {}
    out = {}
    if trays > 0:
        out["kiln_out_tray"] = trays
    if m3 > 0:
        out["kiln_out_m3"] = m3
    return out


def _sum_kiln_unload_events_daily(day: str) -> dict:
    """
    Sum kiln unload events for the given day.
    This is the only reliable way to rebuild 'kiln_out_tray' when unloading spans multiple days.
    """
    try:
        events_file = Path.home() / "AIF/data/kiln/unload_events.jsonl"
        if not events_file.exists():
            return {}
        trays = 0
        m3 = 0.0
        m3_known = False
        found = 0
        with open(events_file, "r", encoding="utf-8") as f:
            for line in f:
                line = (line or "").strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except Exception:
                    continue
                if not isinstance(obj, dict):
                    continue
                t = obj.get("time")
                if not isinstance(t, str) or not t.startswith(day):
                    continue
                found += 1
                try:
                    trays += int(obj.get("trays", 0) or 0)
                except Exception:
                    pass
                if "m3" in obj:
                    try:
                        m3 += float(obj.get("m3", 0) or 0.0)
                        m3_known = True
                    except Exception:
                        pass
        if found == 0:
            return {}

        out: dict = {
            "kiln_out_tray": max(0, int(trays)),
        }
        if m3_known:
            out["kiln_out_m3"] = max(0.0, float(m3))
        return out
    except Exception:
        return {}


def _normalize_record(rec: dict) -> None:
    for key in INT_FIELDS:
        rec[key] = int(rec.get(key, 0) or 0)
        if rec[key] < 0:
            rec[key] = 0
    for key in FLOAT_FIELDS:
        rec[key] = float(rec.get(key, 0) or 0.0)
    rec["dip_chem"] = bool(rec.get("dip_chem", False) or rec.get("dip_bag", 0))
    rec["product_m3"] = float(rec.get("pack_m3", 0) or 0.0)


def _clamp_ab_bc(rec: dict) -> bool:
    total = float(rec.get("ab_m3", 0) or 0) + float(rec.get("bc_m3", 0) or 0)
    pack = float(rec.get("pack_m3", 0) or 0)
    if total <= pack + 1e-9 or total <= 0 or pack < 0:
        return False
    ratio = (pack / total) if total > 0 else 0.0
    rec["ab_m3"] = float(rec.get("ab_m3", 0) or 0) * ratio
    rec["bc_m3"] = float(rec.get("bc_m3", 0) or 0) * ratio
    return True


def rebuild_ledger(day: str | None = None) -> str:
    """
    Rebuild ledger values from traceable sources.
    - If day is provided: rebuild that day.
    - If day is None: rebuild all existing days.
    """
    data = load()
    if not isinstance(data, dict):
        data = {}

    # Load sources once for consistency.
    try:
        from modules.process_flow.process_flow_engine import load as flow_load
        flow = flow_load()
    except Exception:
        flow = {}
    try:
        from modules.kiln.kiln_io import load_data as kiln_load
        kiln = kiln_load()
    except Exception:
        kiln = {}

    if day:
        targets = [day]
    else:
        targets = sorted([d for d in data.keys() if isinstance(d, str)])
        if not targets:
            targets = [today()]

    lines = ["🧾 台账更正完成"]
    changed_days = 0

    for d in targets:
        ensure_day(data, d)
        rec = data[d]
        before = deepcopy(rec)

        _normalize_record(rec)

        notes = []
        saw = _sum_saw_daily(flow, d)
        if saw:
            rec.update(saw)
            notes.append("上锯/树皮/木渣按锯号日报重算")

        ss = _sum_second_sort_daily(flow, d)
        if ss:
            rec.update(ss)
            notes.append("成品/AB/BC按二拣记录重算")

        kiln_out = _sum_kiln_unload_events_daily(d)
        if kiln_out:
            rec.update(kiln_out)
            notes.append("出窑按出窑事件重算")
        else:
            kiln_out = _sum_kiln_completed_daily(kiln, d)
            if kiln_out:
                rec.update(kiln_out)
                notes.append("出窑按窑完成记录重算")

        if _clamp_ab_bc(rec):
            notes.append("AB+BC 超出成品体积，已按比例收敛")

        diffs = []
        for k in DEFAULT_DAY.keys():
            a = before.get(k)
            b = rec.get(k)
            if a != b:
                diffs.append(k)

        if diffs:
            changed_days += 1
            lines.append(f"{d}: 已更正 {len(diffs)} 项 -> {', '.join(diffs[:8])}{' ...' if len(diffs) > 8 else ''}")
            if notes:
                lines.append(f"  依据: {'；'.join(notes)}")
        else:
            lines.append(f"{d}: 无变化")

    save(data)
    lines.append(f"共处理: {len(targets)} 天；变更: {changed_days} 天")
    return "\n".join(lines)


# =====================================================
# TG入口
# =====================================================

def handle_ledger(text):
    parts = text.split()
    if not parts:
        return None

    cmd = parts[0]

    # 新工序主链命令全部交给 process_flow_engine，避免重叠。
    if cmd in {"上锯", "药浸", "拣选", "分拣", "二次拣选"}:
        return None
    if cmd in AUTO_SYNC_COMMANDS:
        return (
            f"⚠️ {cmd} 已由业务指令自动联动，已拦截手工重复录入。\n"
            "请使用业务指令录入（如：原木入库/投料/成品入库/窑入窑）。"
        )

    data = load()
    day = today()
    data = ensure_day(data, day)
    r = data[day]

    # ================= 原木消耗 =================
    if cmd == "原木":
        if len(parts) != 2:
            return "❌ 格式: 原木 数量"
        v = as_float(parts[1])
        if v is None:
            return "❌ 数值错误"
        r["log_mt"] += v

    # ================= 上锯 =================
    elif cmd == "上锯":
        if len(parts) != 2:
            return "❌ 格式: 上锯 数量"
        v = as_float(parts[1])
        if v is None:
            return "❌ 数值错误"
        r["saw_mt"] += v

    # ================= 锯解托 =================
    elif cmd == "锯解":
        if len(parts) != 2:
            return "❌ 格式: 锯解 托数"
        v = as_int(parts[1])
        if v is None:
            return "❌ 数值错误"
        r["saw_tray"] += v

    # ================= 药浸 =================
    elif cmd == "药浸":
        if len(parts) < 3:
            return "❌ 格式: 药浸 罐数 托数 [药]"
        tank = as_int(parts[1])
        tray = as_int(parts[2])
        if tank is None or tray is None:
            return "❌ 数值错误"
        r["dip_tank"] += tank
        r["dip_tray"] += tray
        if len(parts) > 3 and parts[3] == "药":
            r["dip_chem"] = True

    # ================= 拣选 =================
    elif cmd == "拣选":
        if len(parts) != 2:
            return "❌ 格式: 拣选 托数"
        v = as_int(parts[1])
        if v is None:
            return "❌ 数值错误"
        r["select_tray"] += v

    # ================= 入窑 =================
    elif cmd == "入窑":
        if len(parts) != 2:
            return "❌ 格式: 入窑 托数"
        v = as_int(parts[1])
        if v is None:
            return "❌ 数值错误"
        r["kiln_tray"] += v

    # ================= 打包 =================
    elif cmd == "打包":
        if len(parts) != 3:
            return "❌ 格式: 打包 件数 体积"
        pcs = as_int(parts[1])
        m3 = as_float(parts[2])
        if pcs is None or m3 is None:
            return "❌ 数值错误"
        r["pack_pcs"] += pcs
        r["pack_m3"] += m3
        r["product_m3"] += m3

    # ================= AB料 =================
    elif cmd == "AB":
        if len(parts) != 2:
            return "❌ 格式: AB 数量"
        v = as_float(parts[1])
        if v is None:
            return "❌ 数值错误"
        r["ab_m3"] += v

    # ================= BC料 =================
    elif cmd == "BC":
        if len(parts) != 2:
            return "❌ 格式: BC 数量"
        v = as_float(parts[1])
        if v is None:
            return "❌ 数值错误"
        r["bc_m3"] += v

    # ================= 树皮 =================
    elif cmd == "树皮":
        if len(parts) != 2:
            return "❌ 格式: 树皮 金额"
        v = as_float(parts[1])
        if v is None:
            return "❌ 数值错误"
        r["bark_sale"] += v

    # ================= 木渣 =================
    elif cmd == "木渣":
        if len(parts) != 2:
            return "❌ 格式: 木渣 金额"
        v = as_float(parts[1])
        if v is None:
            return "❌ 数值错误"
        r["dust_sale"] += v

    # ================= 今日台账 =================
    elif text in ("今日生产", "生产日报", "今日台账"):

        rate = 0
        if r["kiln_tray"] > 0:
            rate = r["pack_m3"] / r["kiln_tray"]

        ab_pct = 0
        bc_pct = 0
        total = r["ab_m3"] + r["bc_m3"]

        if total > 0:
            ab_pct = r["ab_m3"] / total * 100
            bc_pct = r["bc_m3"] / total * 100

        return (
            "📊 今日生产台账\n"
            f"原木消耗: {r['log_mt']} MT\n"
            f"上锯: {r['saw_mt']} MT\n"
            f"锯解: {r['saw_tray']} 托\n"
            f"药浸: {r['dip_tank']}罐 {r['dip_tray']}托"
            f"{' (用药)' if r['dip_chem'] else ''} 药剂:{r.get('dip_bag',0)}袋\n"
            f"拣选: {r['select_tray']} 托\n"
            f"入窑: {r['kiln_tray']} 托\n"
            f"打包: {r['pack_pcs']} 件 {r['pack_m3']:.2f} m³\n"
            f"AB料: {r['ab_m3']:.2f} m³\n"
            f"BC料: {r['bc_m3']:.2f} m³\n"
            f"AB/BC占比: {ab_pct:.1f}% / {bc_pct:.1f}%\n"
            f"成品率: {rate:.2f} m³/托\n"
            f"树皮产量: {r.get('bark_tray',0)} 托\n"
            f"木渣产量: {r.get('dust_bag',0)} 袋\n"
            f"树皮销售: {r['bark_sale']:.2f} KS\n"
            f"木渣销售: {r['dust_sale']:.2f} KS"
        )

    else:
        return None

    save(data)
    return "✅ 已记录"
