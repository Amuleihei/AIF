import json
import re
from pathlib import Path
from datetime import datetime
from web.data_store import get_inventory_data, save_inventory_data

DATA_FILE = Path.home() / "AIF/data/inventory/inventory.json"
GRADE_SEP = "#"

# =====================================================
# 默认结构
# =====================================================

DEFAULT = {
    "raw": {},
    "wip": {},
    "product": {},  # 件级成品
    "meta": {},     # 操作元信息（用于撤销/对账）
}


# =====================================================
# 工具
# =====================================================

def ensure_structure(d):

    # 补齐三层结构
    for k in DEFAULT:
        if k not in d:
            d[k] = {}

    # ⭐ 自动升级旧版成品结构 + 统一为「编号#等级」作为唯一键
    # 目的：允许同一编号同时存在 AB / BC 两件成品（用户口径为 编号+等级 对齐）
    new_product: dict[str, dict] = {}

    def _norm_grade(g: str | None) -> str | None:
        gg = (g or "").strip().upper()
        if gg in {"AB", "BC"}:
            return gg
        return None

    def _canon(code: str, grade: str | None) -> str:
        if grade:
            return f"{code}{GRADE_SEP}{grade}"
        return code

    for code, item in (d.get("product", {}) or {}).items():
        if not code:
            continue

        # 旧结构（float / int）
        if not isinstance(item, dict):
            try:
                item = {
                    "spec": "未知",
                    "grade": "未知",
                    "pcs": 0,
                    "volume": float(item),
                    "status": "库存",
                }
            except Exception:
                continue

        g = _norm_grade(item.get("grade"))
        if g:
            item["grade"] = g

        # 若 key 已包含分隔符，尽量保持（兼容已升级的数据）
        if isinstance(code, str) and (GRADE_SEP in code):
            new_key = code
        else:
            new_key = _canon(code, g)

        # 避免覆盖：若发生冲突，保留两条（用原 key 兜底）
        if new_key in new_product and new_key != code and code not in new_product:
            new_product[code] = item
        else:
            new_product[new_key] = item

    d["product"] = new_product
    if not isinstance(d.get("meta"), dict):
        d["meta"] = {}

    return d


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _set_last_product_in(meta: dict, ids: list[str], action: str = "create") -> None:
    if not isinstance(meta, dict):
        return
    meta["last_product_in"] = {
        "time": _now_iso(),
        "action": action,
        "ids": ids,
    }


def load():
    try:
        d = get_inventory_data()
    except Exception:
        d = DEFAULT.copy()
    d = ensure_structure(d)
    save(d)
    return d


def save(d):
    save_inventory_data(d)


def sync_ledger(delta: dict):
    try:
        from modules.ledger.production_ledger_engine import record_delta
        record_delta(delta)
    except Exception:
        # 台账联动失败不应影响主业务
        pass


def parse_amount(text: str):
    m = re.search(r"(-?\d+(?:\.\d+)?)", text)
    if not m:
        return None
    try:
        return float(m.group(1))
    except Exception:
        return None


# =====================================================
# ⭐ 批量编号解析（工业级）
# 支持：
# 022
# 022 076
# 022、076
# 022-085
# 022-085、099、102-155
# =====================================================

def parse_codes(text):

    # 支持从多种“成品编号批量类”指令中提取编号列表
    text = (
        text.replace("：", "")
        .replace("成品发货", "")
        .replace("成品删除", "")
        .replace("删除成品", "")
        .replace("成品查询", "")
        .replace("成品查看", "")
        .replace("成品更正", "")
        .replace("成品修改", "")
        .replace("成品强制删除", "")
        .replace("成品强制更正", "")
        .strip()
    )

    parts = re.split(r"[、,，\s]+", text)

    codes = []

    for p in parts:

        if not p:
            continue

        # 兼容两类：
        # 1) 区间：022-085（仅支持 3 位数字区间，避免误把 0304-051 这种真实编号当区间）
        # 2) 真实编号：0304-051 / 250301-01 等，原样返回
        if re.fullmatch(r"\d{3}-\d{3}", p):
            a, b = p.split("-")
            start = int(a)
            end = int(b)
            if start <= end:
                for i in range(start, end + 1):
                    codes.append(str(i).zfill(3))
                continue

        codes.append(p)

    return codes


# =====================================================
# ⭐ TG入口
# =====================================================

def _grade_key(grade: str | None) -> str | None:
    g = (grade or "").strip().upper()
    if g in {"AB", "BC"}:
        return g
    return None


def _canon_pid(code: str, grade: str | None) -> str:
    g = _grade_key(grade)
    if g:
        return f"{code}{GRADE_SEP}{g}"
    return code


def _split_pid(pid: str) -> tuple[str, str | None]:
    if not isinstance(pid, str):
        return str(pid), None
    if GRADE_SEP in pid:
        base, g = pid.split(GRADE_SEP, 1)
        gg = _grade_key(g)
        return base, gg
    return pid, None


def _find_pid_variants(prod: dict, base_code: str) -> list[str]:
    if not isinstance(prod, dict):
        return []
    out: list[str] = []
    for pid in prod.keys():
        b, _ = _split_pid(pid)
        if b == base_code:
            out.append(pid)
    return sorted(out)


def _pid_display(pid: str, item: dict | None = None) -> str:
    base, g = _split_pid(pid)
    if not g and isinstance(item, dict):
        g = _grade_key(item.get("grade"))
    if g:
        return f"{base} {g}"
    return base


def _product_delta(item: dict) -> dict:
    pcs = int(item.get("pcs", 0) or 0)
    vol = float(item.get("volume", 0) or 0)
    grade = _grade_key(item.get("grade"))

    # pack_pkg: 件数（按“包/托”计，一条成品编号=1件）
    # pack_pcs: 根数（板材根数）
    delta = {"pack_pkg": 1, "pack_pcs": pcs, "pack_m3": vol, "product_m3": vol}
    if grade == "AB":
        delta["ab_m3"] = vol
    elif grade == "BC":
        delta["bc_m3"] = vol
    return delta


def _expand_product_ids(base_id: str, count: int) -> list[str]:
    if count <= 1:
        return [base_id]
    return [f"{base_id}-{i:02d}" for i in range(1, count + 1)]


def _scale_delta(delta: dict, n: int) -> dict:
    if n == 1:
        return delta
    scaled: dict[str, float | int] = {}
    for k, v in delta.items():
        scaled[k] = v * n
    return scaled


def _delta_diff(old: dict, new: dict) -> dict:
    diff: dict[str, float | int] = {}
    for k in set(old) | set(new):
        a = old.get(k, 0)
        b = new.get(k, 0)
        if a == b:
            continue
        diff[k] = b - a
    return diff


def handle_inventory(text):

    # =================================================
    # ⭐ 支持多行批量输入（Excel粘贴）
    # =================================================

    if "\n" in text:
        results = []

        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue

            r = handle_inventory(line)
            if r:
                results.append(r)

        return "\n".join(results)

    # =================================================

    data = load()

    # ================= 成品编号（仅列编号，便于盘点对账） =================
    if text in ("成品编号", "成品列表", "成品清单"):
        prod = data.get("product", {}) if isinstance(data.get("product"), dict) else {}
        codes = []
        for pid, item in prod.items():
            if not isinstance(item, dict):
                continue
            if item.get("status") != "库存":
                continue
            codes.append(_pid_display(pid, item))
        if not codes:
            return "📦 成品编号为空"
        codes = sorted(codes)
        return "📦 成品编号\n" + "\n".join(codes) + f"\n\n合计: {len(codes)} 件"

    # ================= 原木入库 =================

    if text.startswith("原木入库"):

        v = parse_amount(text)
        if v is None:
            return "❌ 格式：原木入库 数量"

        data["raw"]["原木"] = data["raw"].get("原木", 0) + v
        save(data)

        return f"🪵 原木库存 +{v}"


    # ================= 成品入库 =================
    # 成品入库 022 970x81x21 AB 517 0.853 [托数]

    if text.startswith("成品入库"):

        # 撤销上一条成品入库：
        # - 成品入库 -
        # - 成品入库 - 0305-001
        m_undo = re.fullmatch(r"成品入库\s*-\s*([^\s]+)?", text.strip())
        if m_undo:
            code = (m_undo.group(1) or "").strip()
            meta = data.get("meta", {}) if isinstance(data.get("meta"), dict) else {}
            last = meta.get("last_product_in") if isinstance(meta, dict) else None
            if not isinstance(last, dict) or not isinstance(last.get("ids"), list) or not last.get("ids"):
                return "❌ 无可撤销的成品入库记录"

            last_ids = [str(x) for x in last.get("ids", []) if x]
            ids_to_delete: list[str] = []

            if not code:
                ids_to_delete = last_ids
            else:
                # Only allow undo for the last recorded product-in action.
                if code in last_ids:
                    ids_to_delete = [code]
                elif any(pid.startswith(code + "-") for pid in last_ids):
                    ids_to_delete = [pid for pid in last_ids if pid.startswith(code + "-")]
                else:
                    return (
                        f"❌ 仅支持撤销上一条成品入库。\n"
                        f"上一条: {' '.join(last_ids)}\n"
                        f"如需删除历史库存请用：成品删除 {code}"
                    )

            # Validate deletable
            for pid in ids_to_delete:
                item = data.get("product", {}).get(pid)
                if not isinstance(item, dict):
                    return f"❌ 未找到成品编号：{pid}"
                if item.get("status") != "库存":
                    return f"❌ {pid} 状态为 {item.get('status')}，不可撤销"

            # Apply negative deltas + delete
            for pid in ids_to_delete:
                item = data["product"][pid]
                delta = _product_delta(item)
                if delta:
                    sync_ledger({k: -v for k, v in delta.items()})
                del data["product"][pid]
                # Return trays back to kiln-done pool (best-effort).
                try:
                    from modules.process_flow.process_flow_engine import add_kiln_done_trays
                    add_kiln_done_trays(1)
                except Exception:
                    pass

            # Clear last marker (avoid repeated accidental undos)
            if isinstance(meta, dict):
                meta.pop("last_product_in", None)
                data["meta"] = meta

            save(data)
            return f"🗑️ 已撤销成品入库: {' '.join(ids_to_delete)}"

        parts = text.split()

        if len(parts) not in (6, 7):
            return "❌ 格式：成品入库 编号 规格 等级 根数 体积 [托数]"

        trays = 1
        if len(parts) == 6:
            _, code, spec, grade, pcs, vol = parts
        else:
            _, code, spec, grade, pcs, vol, trays = parts

        try:
            pcs = int(pcs)
            vol = float(vol)
            trays = int(trays)
        except:
            return "❌ 数值错误"

        if trays <= 0:
            return "❌ 托数错误"

        if trays > 1:
            g = _grade_key(grade)
            ids_base = _expand_product_ids(code, trays)
            ids = [_canon_pid(pid, g) for pid in ids_base]
            for pid in ids:
                if pid in data["product"]:
                    return f"❌ 成品编号重复: {_pid_display(pid)}"
            # 成品入库默认来自“待二拣”转成品：先扣减托池，避免在制/待二拣与成品重叠。
            try:
                from modules.process_flow.process_flow_engine import reserve_kiln_done_trays
                ok, msg = reserve_kiln_done_trays(trays)
                if not ok:
                    return msg
            except Exception:
                pass
            for pid in ids:
                data["product"][pid] = {
                    "spec": spec,
                    "grade": g or grade,
                    "pcs": pcs,
                    "volume": vol,
                    "status": "库存",
                }
            _set_last_product_in(data.get("meta", {}), ids, action="create")
            save(data)
            sync_ledger(_scale_delta(_product_delta(data["product"][ids[0]]), trays))
            return (
                f"📦 成品入库完成 {trays} 托\n"
                f"编号: {code}\n"
                f"规格: {spec} | 等级: {(g or grade).strip().upper()}\n"
                f"根数: {pcs} 根/托 | 体积: {vol:.3f} m³/托"
            )

        new_item = {
            "spec": spec,
            "grade": _grade_key(grade) or grade,
            "pcs": pcs,
            "volume": vol,
            "status": "库存"
        }
        pid = _canon_pid(code, grade)
        existed = pid in data["product"] and isinstance(data["product"].get(pid), dict)
        old_item = data["product"].get(pid) if existed else None

        # 已发货的成品不允许直接用“成品入库”覆盖，避免篡改历史
        if existed and old_item and old_item.get("status") != "库存":
            return f"❌ {_pid_display(pid, old_item)} 状态为 {old_item.get('status')}，禁止更正。需强制更正请用：成品强制更正 {code} 规格 等级 根数 体积"

        data["product"][pid] = new_item
        if not existed:
            # 新建单号：成品入库默认来自“待二拣”转成品：入库同时扣减“待二拣托池”
            try:
                from modules.process_flow.process_flow_engine import reserve_kiln_done_trays
                ok, msg = reserve_kiln_done_trays(1)
                if not ok:
                    return msg
            except Exception:
                pass
            _set_last_product_in(data.get("meta", {}), [pid], action="create")
        else:
            _set_last_product_in(data.get("meta", {}), [pid], action="correct")
        save(data)

        if existed and old_item:
            diff = _delta_diff(_product_delta(old_item), _product_delta(new_item))
            if diff:
                sync_ledger(diff)
            return f"📦 成品入库已更正 {_pid_display(pid, new_item)}"

        sync_ledger(_product_delta(new_item))
        return f"📦 成品入库 {_pid_display(pid, new_item)}"

    # ================= 成品更正 / 修改 =================
    # 成品更正 022 970x81x21 AB 517 0.853 [托数]
    # 成品强制更正 022 970x81x21 AB 517 0.853 [托数]

    if text.startswith("成品更正") or text.startswith("成品修改") or text.startswith("成品强制更正"):

        force = text.startswith("成品强制更正")
        parts = text.split()

        if len(parts) not in (6, 7):
            return "❌ 格式：成品更正 编号 规格 等级 根数 体积 [托数]（强制：成品强制更正 ...）"

        trays = 1
        if len(parts) == 6:
            _, code, spec, grade, pcs, vol = parts
        else:
            _, code, spec, grade, pcs, vol, trays = parts

        try:
            trays = int(trays)
        except Exception:
            return "❌ 托数错误"

        if trays <= 0:
            return "❌ 托数错误"

        g = _grade_key(grade)
        ids_base = _expand_product_ids(code, trays)
        ids = [_canon_pid(pid, g) for pid in ids_base]

        for pid in ids:
            if pid not in data["product"] or not isinstance(data["product"].get(pid), dict):
                return f"❌ 未找到成品编号：{_pid_display(pid)}"

        try:
            pcs = int(pcs)
            vol = float(vol)
        except Exception:
            return "❌ 数值错误"

        deltas: list[dict] = []

        for pid in ids:
            old_item = data["product"][pid]
            if (not force) and old_item.get("status") != "库存":
                return f"❌ {_pid_display(pid, old_item)} 状态为 {old_item.get('status')}，禁止更正（如确需更正请用：成品强制更正 ...）"

            new_item = {
                "spec": spec,
                "grade": g or grade,
                "pcs": pcs,
                "volume": vol,
                "status": old_item.get("status", "库存"),
            }
            data["product"][pid] = new_item
            deltas.append(_delta_diff(_product_delta(old_item), _product_delta(new_item)))

        save(data)

        # 批量更正：汇总差额再写台账
        total: dict[str, float | int] = {}
        for dlt in deltas:
            for k, v in dlt.items():
                total[k] = total.get(k, 0) + v
        if total:
            sync_ledger(total)

        return f"✅ 成品更正成功 {code} {(g or grade).strip().upper()} ({trays}托)"

    # ================= 成品删除 =================
    # 成品删除 022-030、076
    # 成品强制删除 022-030、076

    if text.startswith("成品删除") or text.startswith("删除成品") or text.startswith("成品强制删除"):

        force = text.startswith("成品强制删除")
        codes = parse_codes(text)
        if not codes:
            return "❌ 格式：成品删除 编号(支持区间/逗号)（强制：成品强制删除 ...）"

        deleted: list[str] = []
        missing: list[str] = []
        blocked: list[str] = []

        for c in codes:
            if c in {"AB", "BC"}:
                continue

            # 兼容：新结构 pid=编号#等级；旧结构 pid=编号
            targets = []
            if c in data.get("product", {}):
                targets = [c]
            else:
                targets = _find_pid_variants(data.get("product", {}), c)

            if not targets:
                missing.append(c)
                continue

            for pid in targets:
                item = data["product"].get(pid)
                if not isinstance(item, dict):
                    missing.append(_pid_display(pid))
                    continue
                if (not force) and item.get("status") != "库存":
                    blocked.append(_pid_display(pid, item))
                    continue
                del data["product"][pid]
                deleted.append(_pid_display(pid, item))

        if deleted:
            save(data)

        msg = []
        if deleted:
            msg.append("🗑️ 已删除:\n" + " ".join(deleted))
        if missing:
            msg.append("❌ 未找到:\n" + " ".join(missing))
        if blocked:
            msg.append("⚠️ 非库存禁止删除:\n" + " ".join(blocked))

        return "\n".join(msg) if msg else "⚠️ 无操作"

    # ================= 成品查询（单号） =================

    if text.startswith("成品查询") or text.startswith("成品查看"):
        parts = text.split()
        if len(parts) not in (2, 3):
            return "❌ 格式：成品查询 编号 [等级]"
        code = parts[1]
        grade = parts[2] if len(parts) == 3 else None

        if grade:
            pid = _canon_pid(code, grade)
            item = data["product"].get(pid)
            if not isinstance(item, dict):
                return f"❌ 未找到：{code} {(grade or '').strip().upper()}"
            code_show = _pid_display(pid, item)
        else:
            targets = []
            if code in data.get("product", {}):
                targets = [code]
            else:
                targets = _find_pid_variants(data.get("product", {}), code)
            if not targets:
                return f"❌ 未找到：{code}"
            if len(targets) > 1:
                opts = "\n".join([f"- {_pid_display(pid, data['product'].get(pid))}" for pid in targets])
                return f"⚠️ 该编号存在多条记录，请带等级查询：\n{opts}\n\n示例：成品查询 {code} AB"
            pid = targets[0]
            item = data["product"].get(pid)
            if not isinstance(item, dict):
                return f"❌ 未找到：{code}"
            code_show = _pid_display(pid, item)
        return (
            "📦 成品信息\n"
            f"编号: {code_show}\n"
            f"规格: {item.get('spec','?')}\n"
            f"等级: {item.get('grade','?')}\n"
            f"根数: {item.get('pcs',0)}\n"
            f"体积: {item.get('volume',0)}\n"
            f"状态: {item.get('status','?')}"
        )


    # ================= 成品发货 =================

    if text.startswith("成品发货"):

        codes = parse_codes(text)

        shipped = []
        missing = []
        duplicated = []

        for c in codes:
            if c in {"AB", "BC"}:
                continue

            targets = []
            if c in data.get("product", {}):
                targets = [c]
            else:
                targets = _find_pid_variants(data.get("product", {}), c)

            if not targets:
                missing.append(c)
                continue

            for pid in targets:
                item = data["product"].get(pid)
                if not isinstance(item, dict):
                    missing.append(_pid_display(pid))
                    continue
                if item.get("status") != "库存":
                    duplicated.append(_pid_display(pid, item))
                    continue
                data["product"][pid]["status"] = "已发货"
                shipped.append(_pid_display(pid, item))

        save(data)

        msg = []

        if shipped:
            msg.append("🚚 已发货:\n" + " ".join(shipped))

        if missing:
            msg.append("❌ 未找到:\n" + " ".join(missing))

        if duplicated:
            msg.append("⚠️ 已发过:\n" + " ".join(duplicated))

        return "\n".join(msg)


    # ================= 旧口径命令（已停用） =================
    # 投料/完工 使用的是早期按吨 wip 的模型，已不再维护。
    # 继续放开会与“工序托池 + 台账”口径冲突，导致汇总被污染。
    if text.startswith("投料") or text.startswith("完工"):
        return (
            "⚠️ 该命令已停用（旧wip口径）。\n"
            "请改用：上锯 / 药浸 / 分拣 / 入窑 / 出窑 / 二次拣选，或管理员“强制 …”命令。"
        )

    # ================= 成品库存（件级+汇总） =================

    if text == "成品库存":

        lines = ["📦 成品库存"]

        found = False
        total_pcs = 0
        total_volume = 0
        total_packages = 0

        for pid, item in data["product"].items():

            if not isinstance(item, dict):
                continue

            if item.get("status") != "库存":
                continue

            found = True
            total_packages += 1

            pcs = item.get("pcs", 0)
            vol = item.get("volume", 0)

            total_pcs += pcs
            total_volume += vol

            lines.append(
                f"{_pid_display(pid, item)} | {item.get('spec','?')} | {item.get('grade','?')} | "
                f"{pcs}根 | {vol}m³"
            )

        if not found:
            return "📦 成品库存为空"

        # ===== 汇总 =====
        lines.append("\n——————————")
        lines.append("📊 合计:")
        lines.append(f"件数: {total_packages} 件")
        lines.append(f"根数: {total_pcs} 根")
        lines.append(f"体积: {round(total_volume,3)} m³")

        return "\n".join(lines)
    

    # ================= 全库存（工业级安全版） =================

    if text == "库存":

        lines = ["📦 库存状态"]

        # ---------- 原料 ----------
        lines.append("\n🪵 原料:")
        for k, v in data["raw"].items():
            lines.append(f"{k}: {v}")

        # ---------- 在制 ----------
        lines.append("\n⚙️ 在制:")
        if data["wip"]:
            for k, v in data["wip"].items():
                lines.append(f"{k}: {v}")
        else:
            # 若未使用“投料/完工”维护 wip，则用工序池+窑内托数作为在制口径
            try:
                from modules.utils.wip_calc import compute_wip_units
                w = compute_wip_units()
                lines.append(f"在制(锯解托): {int(w.get('wip_saw_tray',0) or 0)}托")
                lines.append(f"在制(入窑托): {int(w.get('wip_kiln_tray',0) or 0)}托")
                lines.append(f"待二拣(入窑托): {int(w.get('pending_2nd_sort',0) or 0)}托")
            except Exception:
                pass

        # ---------- 成品 ----------
        lines.append("\n📦 成品(件):")

        found = False

        for pid, item in data["product"].items():

            if not isinstance(item, dict):
                continue

            if item.get("status") != "库存":
                continue

            found = True
            lines.append(f"{_pid_display(pid, item)}: {item.get('volume', 0)} m³")

        if not found:
            lines.append("无库存")

        return "\n".join(lines)


    return None
