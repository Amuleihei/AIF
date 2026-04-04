import json
import math
import shlex
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from modules.storage.db_doc_store import load_doc, save_doc
from web.models import Session, SawMachineRecord


DATA_FILE = Path.home() / "AIF/data/hr/hr.json"
DOC_KEY = "hr_main_v2"
DATE_FMT = "%Y-%m-%d"


def _today() -> str:
    return datetime.now().strftime(DATE_FMT)


def _default_org() -> dict[str, Any]:
    return {
        "teams": [
            {"name": "办公室", "positions": ["财务", "统计", "经理"]},
            {"name": "锯工组", "positions": ["锯工", "副锯工", "锯工QC"]},
            {"name": "药浸&烘干组", "positions": ["药浸烘干控制(同岗)", "锅炉工"]},
            {"name": "拣选组", "positions": ["拣选QC", "拣选员", "二选修正人员"]},
            {"name": "采购组", "positions": ["采购兼司机"]},
            {"name": "设备保障", "positions": ["电工", "叉车司机"]},
            {"name": "安保组", "positions": ["保安"]},
        ],
        "salary_types": {
            "日薪": {"payout_cycle": "weekly", "desc": "按周发放"},
            "月薪": {"payout_cycle": "semi_monthly", "desc": "每15天发放"},
            "计件": {"payout_cycle": "weekly", "desc": "按件核算，建议按周结算"},
        },
        "attendance": {
            "overtime_multipliers": [1.5, 2.0],
            "default_overtime_multiplier": 1.5,
        },
        "saw_piecework": {
            "enabled": 1,
            "default_unit_price": 0.0,
            "bindings": [],
        },
        "notes": [
            "药浸师与烘干房控制为同一人可用岗位: 药浸烘干控制(同岗)",
            "司机与采购同一人可用岗位: 采购兼司机",
            "当前锯工可设置为计件工",
            "可在 HR 设置中配置锯工与锯号映射，系统会按单台锯托数自动计件",
        ],
    }


def default_data() -> dict[str, Any]:
    return {
        "schema_version": 2,
        "org": _default_org(),
        "employees": {},
        "attendance_records": [],
        "piecework_records": [],
        "reward_penalty_records": [],
    }


def save(d: dict[str, Any]) -> None:
    save_doc(DOC_KEY, d)


def _safe_load() -> dict[str, Any]:
    raw = load_doc(DOC_KEY, default_data(), legacy_file=DATA_FILE)
    if not isinstance(raw, dict):
        raw = default_data()
        save(raw)
        return raw
    return _migrate(raw)


def _migrate(raw: dict[str, Any]) -> dict[str, Any]:
    # 新结构直接透传，仅做缺省兜底
    if _to_int(raw.get("schema_version"), 0) >= 2:
        if not isinstance(raw, dict):
            return default_data()
        out = raw
        if not isinstance(out.get("org"), dict):
            out["org"] = _default_org()
        if not isinstance(out.get("employees"), dict):
            out["employees"] = {}
        if not isinstance(out.get("attendance_records"), list):
            out["attendance_records"] = []
        if not isinstance(out.get("piecework_records"), list):
            out["piecework_records"] = []
        if not isinstance(out.get("reward_penalty_records"), list):
            out["reward_penalty_records"] = []
        out["schema_version"] = 2
        save(out)
        return out

    d = default_data()
    if not isinstance(raw, dict):
        return d

    old_emps = raw.get("employees")
    if isinstance(old_emps, dict):
        for name, item in old_emps.items():
            if not isinstance(item, dict):
                continue
            salary = float(item.get("salary", 0) or 0)
            status = str(item.get("status", "在岗") or "在岗")
            role = str(item.get("role", "未设置") or "未设置")
            d["employees"][str(name)] = {
                "name": str(name),
                "age": int(item.get("age", 0) or 0),
                "ethnicity": str(item.get("ethnicity", "") or ""),
                "religion": str(item.get("religion", "") or ""),
                "join_date": str(item.get("join_date", _today()) or _today()),
                "team": str(item.get("team", _guess_team(role)) or _guess_team(role)),
                "position": role,
                "salary_type": str(item.get("salary_type", "月薪") or "月薪"),
                "salary_value": salary,
                "payout_cycle": str(item.get("payout_cycle", _default_cycle(str(item.get("salary_type", "月薪"))))),
                "status": status,
                "left_date": str(item.get("left_date", "") or ""),
                "left_reason": str(item.get("left_reason", "") or ""),
                "last_checkin": str(item.get("last_checkin", "") or ""),
                "tags": list(item.get("tags", [])) if isinstance(item.get("tags"), list) else [],
                "contact": {
                    "phone": str(item.get("phone", "") or ""),
                    "id_no": str(item.get("id_no", "") or ""),
                    "address": str(item.get("address", "") or ""),
                    "emergency_contact": str(item.get("emergency_contact", "") or ""),
                },
                "extra": {
                    "skill_level": str(item.get("skill_level", "") or ""),
                    "contract_type": str(item.get("contract_type", "") or ""),
                    "bank_account": str(item.get("bank_account", "") or ""),
                },
            }

    if isinstance(raw.get("org"), dict):
        d["org"] = raw["org"]
    if isinstance(raw.get("attendance_records"), list):
        d["attendance_records"] = raw["attendance_records"]
    if isinstance(raw.get("piecework_records"), list):
        d["piecework_records"] = raw["piecework_records"]
    if isinstance(raw.get("reward_penalty_records"), list):
        d["reward_penalty_records"] = raw["reward_penalty_records"]

    save(d)
    return d


def _split(text: str) -> list[str]:
    try:
        return shlex.split(text)
    except Exception:
        return str(text or "").split()


def _to_float(v: Any, dv: float = 0.0) -> float:
    try:
        return float(v)
    except Exception:
        return dv


def _to_int(v: Any, dv: int = 0) -> int:
    try:
        return int(v)
    except Exception:
        return dv


def _parse_date(v: str, default_today: bool = True) -> str:
    s = str(v or "").strip()
    if not s:
        return _today() if default_today else ""
    try:
        return datetime.strptime(s, DATE_FMT).strftime(DATE_FMT)
    except Exception:
        return _today() if default_today else ""


def _default_cycle(salary_type: str) -> str:
    st = str(salary_type or "").strip()
    if st == "日薪":
        return "weekly"
    if st == "月薪":
        return "semi_monthly"
    return "weekly"


def _guess_team(position: str) -> str:
    p = str(position or "")
    mapping = [
        ("办公室", ("财务", "统计", "经理")),
        ("锯工组", ("锯工", "副锯工", "锯工QC")),
        ("药浸&烘干组", ("药浸", "烘干", "锅炉")),
        ("拣选组", ("拣选", "二选", "QC")),
        ("采购组", ("采购", "司机")),
        ("设备保障", ("电工", "叉车")),
        ("安保组", ("保安",)),
    ]
    for team, kws in mapping:
        if any(k in p for k in kws):
            return team
    return "未分组"


def _parse_kv(parts: list[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for tok in parts:
        if "=" not in tok:
            continue
        k, v = tok.split("=", 1)
        kk = str(k).strip().lower()
        vv = str(v).strip()
        if kk:
            out[kk] = vv
    return out


def _ensure_org(d: dict[str, Any]) -> None:
    if not isinstance(d.get("org"), dict):
        d["org"] = _default_org()
    if not isinstance(d["org"].get("teams"), list):
        d["org"]["teams"] = _default_org()["teams"]
    if not isinstance(d["org"].get("salary_types"), dict):
        d["org"]["salary_types"] = _default_org()["salary_types"]
    if not isinstance(d["org"].get("attendance"), dict):
        d["org"]["attendance"] = _default_org()["attendance"]
    attendance_cfg = d["org"].get("attendance", {})
    if not isinstance(attendance_cfg.get("overtime_multipliers"), list):
        attendance_cfg["overtime_multipliers"] = list(_default_org()["attendance"]["overtime_multipliers"])
    cleaned_multipliers: list[float] = []
    for item in attendance_cfg.get("overtime_multipliers", []):
        val = round(_to_float(item, 0.0), 2)
        if val <= 0:
            continue
        if val not in cleaned_multipliers:
            cleaned_multipliers.append(val)
    if not cleaned_multipliers:
        cleaned_multipliers = list(_default_org()["attendance"]["overtime_multipliers"])
    attendance_cfg["overtime_multipliers"] = cleaned_multipliers
    default_mul = round(_to_float(attendance_cfg.get("default_overtime_multiplier"), 0.0), 2)
    if default_mul <= 0:
        default_mul = cleaned_multipliers[0]
    if default_mul not in cleaned_multipliers:
        cleaned_multipliers.append(default_mul)
    attendance_cfg["default_overtime_multiplier"] = default_mul
    d["org"]["attendance"] = attendance_cfg
    if not isinstance(d["org"].get("saw_piecework"), dict):
        d["org"]["saw_piecework"] = _default_org()["saw_piecework"]
    saw_cfg = d["org"].get("saw_piecework", {})
    if not isinstance(saw_cfg.get("enabled"), int):
        saw_cfg["enabled"] = 1 if bool(saw_cfg.get("enabled", 1)) else 0
    saw_cfg["default_unit_price"] = max(0.0, round(_to_float(saw_cfg.get("default_unit_price"), 0.0), 4))
    bindings = saw_cfg.get("bindings", [])
    if not isinstance(bindings, list):
        bindings = []
    clean_bindings: list[dict[str, Any]] = []
    seen_machine: set[int] = set()
    for item in bindings:
        if not isinstance(item, dict):
            continue
        machine_no = _to_int(item.get("machine_no"), 0)
        if machine_no < 1 or machine_no > 6 or machine_no in seen_machine:
            continue
        seen_machine.add(machine_no)
        primary_name = str(item.get("primary_name", "") or "").strip()
        assistant_name = str(item.get("assistant_name", "") or "").strip()
        legacy_name = str(item.get("employee_name", "") or "").strip()
        if not primary_name and legacy_name:
            primary_name = legacy_name
        clean_bindings.append(
            {
                "machine_no": machine_no,
                "primary_name": primary_name,
                "assistant_name": assistant_name,
                "unit_price": max(0.0, round(_to_float(item.get("unit_price"), 0.0), 4)),
            }
        )
    clean_bindings.sort(key=lambda x: _to_int(x.get("machine_no"), 0))
    saw_cfg["bindings"] = clean_bindings
    d["org"]["saw_piecework"] = saw_cfg
    if not isinstance(d["org"].get("notes"), list):
        d["org"]["notes"] = _default_org()["notes"]


def _employee_brief(name: str, e: dict[str, Any]) -> str:
    return (
        f"{name} | {e.get('team','未分组')}/{e.get('position','')} | "
        f"{e.get('salary_type','')}{_to_float(e.get('salary_value',0)):.2f} | {e.get('status','在岗')}"
    )


def _period_week(day_text: str) -> tuple[str, str]:
    dt = datetime.strptime(day_text, DATE_FMT)
    start = dt - timedelta(days=dt.weekday())
    end = start + timedelta(days=6)
    return start.strftime(DATE_FMT), end.strftime(DATE_FMT)


def _period_half_month(day_text: str) -> tuple[str, str]:
    dt = datetime.strptime(day_text, DATE_FMT)
    if dt.day <= 15:
        start = dt.replace(day=1)
        end = dt.replace(day=15)
    else:
        start = dt.replace(day=16)
        if dt.month == 12:
            nxt = dt.replace(year=dt.year + 1, month=1, day=1)
        else:
            nxt = dt.replace(month=dt.month + 1, day=1)
        end = nxt - timedelta(days=1)
    return start.strftime(DATE_FMT), end.strftime(DATE_FMT)


def _period_month(day_text: str) -> tuple[str, str]:
    dt = datetime.strptime(day_text, DATE_FMT)
    start = dt.replace(day=1)
    if dt.month == 12:
        nxt = dt.replace(year=dt.year + 1, month=1, day=1)
    else:
        nxt = dt.replace(month=dt.month + 1, day=1)
    end = nxt - timedelta(days=1)
    return start.strftime(DATE_FMT), end.strftime(DATE_FMT)


def _in_range(day_text: str, begin: str, end: str) -> bool:
    return begin <= day_text <= end


def _attendance_hours(d: dict[str, Any], name: str, begin: str, end: str) -> tuple[float, float, float]:
    regular_hours = 0.0
    overtime_hours = 0.0
    overtime_weighted_hours = 0.0
    for rec in d.get("attendance_records", []):
        if not isinstance(rec, dict):
            continue
        if str(rec.get("name", "")) != name:
            continue
        day = _parse_date(str(rec.get("date", "")))
        if _in_range(day, begin, end):
            rh = _to_float(rec.get("regular_hours"), -1.0)
            if rh < 0:
                # 兼容旧数据：days 字段按 8 小时/天折算
                rh = max(0.0, _to_float(rec.get("days"), 0.0) * 8.0)
            oh = max(0.0, _to_float(rec.get("overtime_hours"), 0.0))
            om = _to_float(rec.get("overtime_multiplier"), 1.5)
            if om <= 0:
                om = 1.5
            regular_hours += max(0.0, rh)
            overtime_hours += oh
            overtime_weighted_hours += oh * om
    return regular_hours, overtime_hours, overtime_weighted_hours


def _piece_income(d: dict[str, Any], name: str, begin: str, end: str) -> float:
    amt = 0.0
    for rec in d.get("piecework_records", []):
        if not isinstance(rec, dict):
            continue
        if str(rec.get("name", "")) != name:
            continue
        day = _parse_date(str(rec.get("date", "")))
        if _in_range(day, begin, end):
            amt += _to_float(rec.get("pay"), 0.0)
    return amt


def _piece_qty_manual(d: dict[str, Any], name: str, begin: str, end: str) -> float:
    qty = 0.0
    for rec in d.get("piecework_records", []):
        if not isinstance(rec, dict):
            continue
        if str(rec.get("name", "")) != name:
            continue
        day = _parse_date(str(rec.get("date", "")))
        if _in_range(day, begin, end):
            qty += max(0.0, _to_float(rec.get("qty"), 0.0))
    return qty


def _record_day_text(raw: Any) -> str:
    text = str(raw or "").strip()
    if not text:
        return ""
    if "T" in text:
        text = text.split("T", 1)[0]
    if " " in text:
        text = text.split(" ", 1)[0]
    return _parse_date(text, default_today=False)


def _piece_qty_from_saw_machine(d: dict[str, Any], name: str, begin: str, end: str) -> int:
    org = d.get("org", {}) if isinstance(d.get("org"), dict) else {}
    saw_cfg = org.get("saw_piecework", {}) if isinstance(org.get("saw_piecework"), dict) else {}
    if _to_int(saw_cfg.get("enabled"), 1) != 1:
        return 0
    raw_bindings = saw_cfg.get("bindings", [])
    if not isinstance(raw_bindings, list) or not raw_bindings:
        return 0
    binding = None
    for row in raw_bindings:
        if not isinstance(row, dict):
            continue
        primary_name = str(row.get("primary_name", "") or row.get("employee_name", "") or "").strip()
        assistant_name = str(row.get("assistant_name", "") or "").strip()
        if primary_name == name or assistant_name == name:
            binding = row
            break
    if not isinstance(binding, dict):
        return 0
    machine_no = _to_int(binding.get("machine_no"), 0)
    if machine_no < 1 or machine_no > 6:
        return 0

    session = None
    try:
        session = Session()
        rows = (
            session.query(SawMachineRecord.saw_trays, SawMachineRecord.created_at)
            .filter(SawMachineRecord.machine_no == machine_no)
            .all()
        )
        trays_total = 0
        for saw_trays, created_at in rows:
            day_text = _record_day_text(created_at)
            if not day_text or not _in_range(day_text, begin, end):
                continue
            trays_total += max(0, _to_int(saw_trays, 0))
        return trays_total
    except Exception:
        return 0
    finally:
        try:
            if session is not None:
                session.close()
        except Exception:
            pass


def _piece_income_from_saw_machine(d: dict[str, Any], name: str, begin: str, end: str) -> float:
    org = d.get("org", {}) if isinstance(d.get("org"), dict) else {}
    saw_cfg = org.get("saw_piecework", {}) if isinstance(org.get("saw_piecework"), dict) else {}
    if _to_int(saw_cfg.get("enabled"), 1) != 1:
        return 0.0
    raw_bindings = saw_cfg.get("bindings", [])
    if not isinstance(raw_bindings, list) or not raw_bindings:
        return 0.0
    binding = None
    for row in raw_bindings:
        if not isinstance(row, dict):
            continue
        primary_name = str(row.get("primary_name", "") or row.get("employee_name", "") or "").strip()
        assistant_name = str(row.get("assistant_name", "") or "").strip()
        if primary_name == name or assistant_name == name:
            binding = row
            break
    if not isinstance(binding, dict):
        return 0.0
    machine_no = _to_int(binding.get("machine_no"), 0)
    if machine_no < 1 or machine_no > 6:
        return 0.0

    emps = d.get("employees", {})
    emp = emps.get(name, {}) if isinstance(emps, dict) else {}
    # 计件单价优先使用员工档案（你在员工管理里维护的 11000/9000）。
    # 锯号绑定里的单价仅作为兜底，不再覆盖员工单价。
    rate = _to_float(emp.get("salary_value"), 0.0) if isinstance(emp, dict) else 0.0
    if rate <= 0:
        rate = _to_float(binding.get("unit_price"), 0.0)
    if rate <= 0:
        rate = _to_float(saw_cfg.get("default_unit_price"), 0.0)
    if rate <= 0:
        return 0.0
    session = None
    try:
        session = Session()
        rows = (
            session.query(SawMachineRecord.saw_trays, SawMachineRecord.created_at)
            .filter(SawMachineRecord.machine_no == machine_no)
            .all()
        )
        trays_total = 0
        for saw_trays, created_at in rows:
            day_text = _record_day_text(created_at)
            if not day_text or not _in_range(day_text, begin, end):
                continue
            trays_total += max(0, _to_int(saw_trays, 0))
        return round(float(trays_total) * float(rate), 2)
    except Exception:
        return 0.0
    finally:
        try:
            if session is not None:
                session.close()
        except Exception:
            pass


def _rp_income(d: dict[str, Any], name: str, begin: str, end: str) -> tuple[float, float]:
    reward = 0.0
    penalty = 0.0
    for rec in d.get("reward_penalty_records", []):
        if not isinstance(rec, dict):
            continue
        if str(rec.get("name", "")) != name:
            continue
        day = _parse_date(str(rec.get("date", "")))
        if not _in_range(day, begin, end):
            continue
        amount = max(0.0, _to_float(rec.get("amount"), 0.0))
        if str(rec.get("type", "")) == "奖励":
            reward += amount
        else:
            penalty += amount
    return reward, penalty


def _calc_pay_for_employee(d: dict[str, Any], name: str, e: dict[str, Any], asof: str, period_mode: str = "") -> dict[str, Any]:
    cycle = str(e.get("payout_cycle", _default_cycle(str(e.get("salary_type", "月薪")))))
    mode = str(period_mode or "").strip().lower()
    if mode in ("month", "natural_month"):
        begin, end = _period_month(asof)
    elif cycle == "semi_monthly":
        begin, end = _period_half_month(asof)
    else:
        begin, end = _period_week(asof)

    st = str(e.get("salary_type", "月薪"))
    salary_value = _to_float(e.get("salary_value"), 0.0)
    regular_hours, overtime_hours, overtime_weighted_hours = _attendance_hours(d, name, begin, end)
    attendance = (regular_hours + overtime_hours) / 8.0
    attendance_hours = regular_hours + overtime_hours
    base = 0.0
    piece_manual = 0.0
    piece_saw_auto = 0.0
    piece_qty_manual = 0.0
    piece_qty_saw = 0
    overtime_pay = 0.0
    hour_rate = 0.0

    if st == "日薪":
        hour_rate = salary_value / 8.0 if salary_value > 0 else 0.0
        # 无考勤时保持历史行为，按 7 天 * 8 小时估算
        used_regular_hours = regular_hours if regular_hours > 0 else 56.0
        base = used_regular_hours * hour_rate
        overtime_pay = overtime_weighted_hours * hour_rate
    elif st == "月薪":
        # 月薪统一按小时折算，默认 30天*8小时 = 240小时
        hour_rate = salary_value / 240.0 if salary_value > 0 else 0.0
        if attendance_hours > 0:
            base = regular_hours * hour_rate
            overtime_pay = overtime_weighted_hours * hour_rate
        else:
            # 无考勤时保留历史行为：半月基数兜底
            base = salary_value / 2.0
    else:
        piece_manual = _piece_income(d, name, begin, end)
        piece_qty_manual = _piece_qty_manual(d, name, begin, end)
        piece_saw_auto = _piece_income_from_saw_machine(d, name, begin, end)
        piece_qty_saw = _piece_qty_from_saw_machine(d, name, begin, end)
        base = piece_manual + piece_saw_auto

    reward, penalty = _rp_income(d, name, begin, end)
    net = base + overtime_pay + reward - penalty
    return {
        "name": name,
        "salary_type": st,
        "period": f"{begin}~{end}",
        "attendance_days": round(attendance, 2),
        "regular_hours": round(regular_hours, 2),
        "overtime_hours": round(overtime_hours, 2),
        "hour_rate": round(hour_rate, 4),
        "base": round(base, 2),
        "piece_manual": round(piece_manual, 2),
        "piece_saw_auto": round(piece_saw_auto, 2),
        "piece_qty_manual": round(piece_qty_manual, 3),
        "piece_qty_saw": int(piece_qty_saw),
        "piece_qty_total": round(piece_qty_manual + float(piece_qty_saw), 3),
        "overtime_pay": round(overtime_pay, 2),
        "reward": round(reward, 2),
        "penalty": round(penalty, 2),
        "net": round(net, 2),
    }


def _add_employee_v2(d: dict[str, Any], parts: list[str]) -> str:
    # 支持格式:
    # 1) 员工建档 姓名 年龄 民族 信仰 入职日期 职位 薪资类型 薪资值
    # 2) 员工建档 name=张三 age=30 ethnicity=汉 religion=佛教 join=2026-03-18 position=锯工 salary_type=计件 salary=0.8
    if len(parts) < 2:
        return "❌ 用法: 员工建档 姓名 年龄 民族 信仰 入职日期 职位 薪资类型 薪资值"

    kv = _parse_kv(parts[1:])
    if kv:
        name = kv.get("name", "")
        age = _to_int(kv.get("age"), 0)
        ethnicity = kv.get("ethnicity", "")
        religion = kv.get("religion", "")
        join_date = _parse_date(kv.get("join", _today()))
        position = kv.get("position", "未设置")
        salary_type = kv.get("salary_type", "月薪")
        salary_value = _to_float(kv.get("salary"), 0.0)
        team = kv.get("team", _guess_team(position))
    else:
        if len(parts) < 10:
            return "❌ 用法: 员工建档 姓名 年龄 民族 信仰 入职日期 职位 薪资类型 薪资值"
        name = parts[1]
        age = _to_int(parts[2], 0)
        ethnicity = parts[3]
        religion = parts[4]
        join_date = _parse_date(parts[5])
        position = parts[6]
        salary_type = parts[7]
        salary_value = _to_float(parts[8], 0.0)
        team = parts[9] if len(parts) >= 10 else _guess_team(position)

    if not name:
        return "❌ 姓名不能为空"
    if name in d["employees"]:
        return "⚠️ 员工已存在"
    if salary_type not in ("日薪", "月薪", "计件"):
        return "❌ 薪资类型仅支持: 日薪/月薪/计件"

    d["employees"][name] = {
        "name": name,
        "age": max(0, age),
        "ethnicity": ethnicity,
        "religion": religion,
        "join_date": join_date,
        "team": team or _guess_team(position),
        "position": position,
        "salary_type": salary_type,
        "salary_value": max(0.0, salary_value),
        "payout_cycle": _default_cycle(salary_type),
        "status": "在岗",
        "left_date": "",
        "left_reason": "",
        "last_checkin": "",
        "tags": [],
        "contact": {"phone": "", "id_no": "", "address": "", "emergency_contact": ""},
        "extra": {"skill_level": "", "contract_type": "", "bank_account": ""},
    }
    save(d)
    return f"✅ 已建档: {name} | {team}/{position} | {salary_type} {salary_value:.2f}"


def _employee_profile(d: dict[str, Any], name: str) -> str:
    e = d["employees"].get(name)
    if not isinstance(e, dict):
        return "❌ 未找到员工"
    lines = [
        f"👤 员工档案: {name}",
        f"状态: {e.get('status','在岗')}  入职: {e.get('join_date','')}",
        f"组织: {e.get('team','')}/{e.get('position','')}",
        f"薪资: {e.get('salary_type','')} {(_to_float(e.get('salary_value'),0)):.2f} | 发薪: {e.get('payout_cycle','')}",
        f"基础信息: 年龄{_to_int(e.get('age'),0)} 民族{e.get('ethnicity','-')} 信仰{e.get('religion','-')}",
    ]
    if str(e.get("status", "")) == "离职":
        lines.append(f"离职: {e.get('left_date','')} 原因: {e.get('left_reason','') or '-'}")
    return "\n".join(lines)


def _list_employees(d: dict[str, Any], status_filter: str = "全部") -> str:
    emps = d.get("employees", {})
    if not isinstance(emps, dict) or not emps:
        return "👥 无员工档案"
    lines = [f"👥 员工列表（{status_filter}）"]
    for name, e in emps.items():
        if not isinstance(e, dict):
            continue
        st = str(e.get("status", "在岗"))
        if status_filter != "全部" and st != status_filter:
            continue
        lines.append(_employee_brief(name, e))
    if len(lines) == 1:
        return "👥 无匹配员工"
    return "\n".join(lines)


def _checkin(d: dict[str, Any], name: str) -> str:
    e = d["employees"].get(name)
    if not isinstance(e, dict):
        return "❌ 未找到员工"
    if str(e.get("status", "")) == "离职":
        return "❌ 离职员工不能签到"
    e["last_checkin"] = datetime.now().isoformat(timespec="seconds")
    e["status"] = "在岗"
    save(d)
    return f"🟢 {name} 已签到"


def _checkout(d: dict[str, Any], name: str) -> str:
    e = d["employees"].get(name)
    if not isinstance(e, dict):
        return "❌ 未找到员工"
    if str(e.get("status", "")) != "离职":
        e["status"] = "离岗"
    save(d)
    return f"🔴 {name} 已签退"


def _resign(d: dict[str, Any], name: str, reason: str) -> str:
    e = d["employees"].get(name)
    if not isinstance(e, dict):
        return "❌ 未找到员工"
    e["status"] = "离职"
    e["left_date"] = _today()
    e["left_reason"] = (reason or "").strip()
    save(d)
    return f"✅ 已办理离职: {name} ({e['left_date']})"


def _rehire(d: dict[str, Any], name: str) -> str:
    e = d["employees"].get(name)
    if not isinstance(e, dict):
        return "❌ 未找到员工"
    e["status"] = "在岗"
    e["left_date"] = ""
    e["left_reason"] = ""
    save(d)
    return f"✅ 已复职: {name}"


def _record_attendance(d: dict[str, Any], name: str, days: float, day: str) -> str:
    if name not in d["employees"]:
        return "❌ 未找到员工"
    if days <= 0:
        return "❌ 出勤天数必须大于0"
    regular_hours = max(0.0, days * 8.0)
    d["attendance_records"].append({
        "name": name,
        "days": round(days, 2),
        "regular_hours": round(regular_hours, 2),
        "overtime_hours": 0.0,
        "date": _parse_date(day),
        "created_at": datetime.now().isoformat(timespec="seconds"),
    })
    save(d)
    return f"✅ 已记录出勤: {name} {days:.2f}天"


def add_hr_attendance_from_admin(
    name: str,
    regular_hours: str,
    overtime_hours: str,
    overtime_multiplier: str,
    day: str,
) -> tuple[bool, str, dict[str, Any]]:
    d = _safe_load()
    emps = d.get("employees", {})
    if not isinstance(emps, dict):
        return False, "❌ 员工数据异常", get_hr_employees_payload()

    emp_name = str(name or "").strip()
    if not emp_name or emp_name not in emps:
        return False, "❌ 请选择有效员工", get_hr_employees_payload()

    _ensure_org(d)
    attendance_cfg = d.get("org", {}).get("attendance", {})
    default_ot_m = _to_float(
        attendance_cfg.get("default_overtime_multiplier", 1.5) if isinstance(attendance_cfg, dict) else 1.5,
        1.5,
    )
    if default_ot_m <= 0:
        default_ot_m = 1.5

    reg_h = _to_float(str(regular_hours or "").strip() or 0, 0.0)
    ot_h = _to_float(str(overtime_hours or "").strip() or 0, 0.0)
    ot_m = _to_float(str(overtime_multiplier or "").strip() or default_ot_m, default_ot_m)
    if reg_h < 0 or ot_h < 0:
        return False, "❌ 工时不能为负数", get_hr_employees_payload()
    if ot_m <= 0:
        return False, "❌ 加班倍率必须大于0", get_hr_employees_payload()
    if reg_h == 0 and ot_h == 0:
        return False, "❌ 正常工时和加班工时不能同时为0", get_hr_employees_payload()

    final_day = _parse_date(str(day or "").strip(), default_today=True)
    d["attendance_records"].append({
        "name": emp_name,
        "days": round(reg_h / 8.0, 4),
        "regular_hours": round(reg_h, 2),
        "overtime_hours": round(ot_h, 2),
        "overtime_multiplier": round(ot_m, 2),
        "date": final_day,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "source": "admin_hr_employees",
    })
    save(d)
    return True, f"✅ 已记录考勤: {emp_name} 正常{reg_h:.2f}h 加班{ot_h:.2f}h x{ot_m:.2f}", get_hr_employees_payload()


def add_hr_special_task_from_admin(
    name: str,
    team: str,
    task_name: str,
    quantity: str,
    unit_price: str,
    day: str,
    note: str = "",
) -> tuple[bool, str, dict[str, Any]]:
    d = _safe_load()
    emps = d.get("employees", {})
    if not isinstance(emps, dict):
        return False, "❌ 员工数据异常", get_hr_employees_payload()

    emp_name = str(name or "").strip()
    team_name = str(team or "").strip()
    if not emp_name and not team_name:
        return False, "❌ 请至少选择员工或班组", get_hr_employees_payload()
    if emp_name:
        if emp_name not in emps:
            return False, "❌ 请选择有效员工", get_hr_employees_payload()
        e = emps.get(emp_name)
        if isinstance(e, dict) and str(e.get("status", "在岗")) == "离职":
            return False, "❌ 离职员工不能录入专项工作", get_hr_employees_payload()

    task = str(task_name or "").strip()
    if not task:
        return False, "❌ 专项工作内容不能为空", get_hr_employees_payload()

    qty = _to_float(str(quantity or "").strip() or 0, 0.0)
    price = _to_float(str(unit_price or "").strip() or 0, 0.0)
    if qty <= 0:
        return False, "❌ 数量必须大于0", get_hr_employees_payload()
    if price <= 0:
        return False, "❌ 单价必须大于0", get_hr_employees_payload()

    final_day = _parse_date(str(day or "").strip(), default_today=True)
    final_note = str(note or "").strip()
    amount = round(qty * price, 2)
    reason = f"专项工作:{task} 数量{qty:.3f} 单价{price:.2f}"
    if final_note:
        reason = f"{reason} 备注:{final_note}"

    rows = d.get("reward_penalty_records", [])
    if not isinstance(rows, list):
        rows = []
        d["reward_penalty_records"] = rows
    target_name = emp_name if emp_name else f"TEAM::{team_name}"
    beneficiary_type = "employee" if emp_name else "team"
    rows.append(
        {
            "name": target_name,
            "type": "奖励",
            "amount": amount,
            "reason": reason,
            "date": final_day,
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "source": "admin_hr_special_task",
            "beneficiary_type": beneficiary_type,
            "employee_name": emp_name,
            "team_name": team_name,
            "task_name": task,
            "quantity": round(qty, 3),
            "unit_price": round(price, 2),
            "note": final_note,
        }
    )
    save(d)
    target_label = team_name if team_name else emp_name
    target_prefix = "班组" if team_name else "员工"
    return True, f"✅ 已记录专项收入: {target_prefix}{target_label} {task} = {qty:.3f} x {price:.2f} = {amount:.2f}", get_hr_employees_payload()


def _find_attendance_record(d: dict[str, Any], name: str, day: str) -> dict[str, Any] | None:
    rows = d.get("attendance_records", [])
    if not isinstance(rows, list):
        return None
    for rec in reversed(rows):
        if not isinstance(rec, dict):
            continue
        if str(rec.get("name", "")) == name and str(rec.get("date", "")) == day:
            return rec
    return None


def _upsert_attendance_record(
    d: dict[str, Any],
    name: str,
    day: str,
    regular_hours: float | None = None,
    overtime_hours_delta: float | None = None,
    overtime_multiplier: float | None = None,
) -> None:
    rec = _find_attendance_record(d, name, day)
    now_text = datetime.now().isoformat(timespec="seconds")
    if rec is None:
        rec = {
            "name": name,
            "days": 0.0,
            "regular_hours": 0.0,
            "overtime_hours": 0.0,
            "overtime_multiplier": 1.5,
            "date": day,
            "created_at": now_text,
            "source": "admin_hr_cards",
        }
        rows = d.get("attendance_records", [])
        if not isinstance(rows, list):
            rows = []
            d["attendance_records"] = rows
        rows.append(rec)

    current_regular = max(0.0, _to_float(rec.get("regular_hours"), 0.0))
    current_ot = max(0.0, _to_float(rec.get("overtime_hours"), 0.0))
    current_mul = _to_float(rec.get("overtime_multiplier"), 1.5)
    if current_mul <= 0:
        current_mul = 1.5

    if regular_hours is not None:
        current_regular = max(0.0, float(regular_hours))
    if overtime_hours_delta is not None:
        current_ot = max(0.0, current_ot + float(overtime_hours_delta))
    if overtime_multiplier is not None and float(overtime_multiplier) > 0:
        current_mul = float(overtime_multiplier)

    rec["regular_hours"] = round(current_regular, 2)
    rec["overtime_hours"] = round(current_ot, 2)
    rec["overtime_multiplier"] = round(current_mul, 2)
    rec["days"] = round(current_regular / 8.0, 4)
    rec["date"] = day
    rec["updated_at"] = now_text
    rec["source"] = "admin_hr_cards"


def apply_hr_attendance_batch_from_admin(
    names: list[str] | None,
    action: str,
    day: str,
    overtime_hours: str = "",
    overtime_multiplier: str = "",
    special_hours: str = "",
) -> tuple[bool, str, dict[str, Any]]:
    d = _safe_load()
    _ensure_org(d)
    emps = d.get("employees", {})
    if not isinstance(emps, dict):
        return False, "❌ 员工数据异常", get_hr_employees_payload()

    selected = []
    for n in (names or []):
        name = str(n or "").strip()
        if name and name not in selected:
            selected.append(name)
    if not selected:
        return False, "❌ 请先选择员工", get_hr_employees_payload()

    final_day = _parse_date(str(day or "").strip(), default_today=True)
    attendance_cfg = d.get("org", {}).get("attendance", {})
    default_ot_m = _to_float(
        attendance_cfg.get("default_overtime_multiplier", 1.5) if isinstance(attendance_cfg, dict) else 1.5,
        1.5,
    )
    if default_ot_m <= 0:
        default_ot_m = 1.5

    act = str(action or "").strip().lower()
    if act not in ("present", "overtime", "special_off"):
        return False, "❌ 未知考勤动作", get_hr_employees_payload()

    ot_h = max(0.0, _to_float(str(overtime_hours or "").strip() or 0, 0.0))
    ot_m = _to_float(str(overtime_multiplier or "").strip() or default_ot_m, default_ot_m)
    if ot_m <= 0:
        return False, "❌ 加班倍率必须大于0", get_hr_employees_payload()
    sp_h = _to_float(str(special_hours or "").strip() or 0, 0.0)
    if act == "overtime" and ot_h <= 0:
        return False, "❌ 加班工时必须大于0", get_hr_employees_payload()
    if act == "special_off" and sp_h <= 0:
        return False, "❌ 特殊工时必须大于0", get_hr_employees_payload()

    updated = 0
    skipped = 0
    for name in selected:
        e = emps.get(name)
        if not isinstance(e, dict):
            skipped += 1
            continue
        if str(e.get("status", "在岗")) == "离职":
            skipped += 1
            continue

        # 出勤/加班 -> 在岗；下班(特殊工时) -> 离岗。
        # 确保点击动作后，员工状态立即可见地变化。
        if act in ("present", "overtime"):
            e["status"] = "在岗"
        elif act == "special_off":
            e["status"] = "离岗"

        if act == "present":
            _upsert_attendance_record(
                d=d,
                name=name,
                day=final_day,
                regular_hours=8.0,
            )
        elif act == "overtime":
            existing = _find_attendance_record(d, name, final_day)
            existing_regular = max(0.0, _to_float(existing.get("regular_hours"), 0.0)) if isinstance(existing, dict) else 0.0
            _upsert_attendance_record(
                d=d,
                name=name,
                day=final_day,
                regular_hours=max(existing_regular, 8.0),
                overtime_hours_delta=ot_h,
                overtime_multiplier=ot_m,
            )
        else:
            _upsert_attendance_record(
                d=d,
                name=name,
                day=final_day,
                regular_hours=max(0.0, sp_h),
            )
        updated += 1

    if updated <= 0:
        return False, "❌ 没有可更新的员工（可能均为离职）", get_hr_employees_payload()

    save(d)
    action_text = {
        "present": "出勤",
        "overtime": f"加班 {ot_h:.2f}h x{ot_m:.2f}",
        "special_off": f"下班(特殊工时) {sp_h:.2f}h",
    }.get(act, act)
    msg = f"✅ 已更新考勤: {action_text}，人数{updated}，日期{final_day}"
    if skipped > 0:
        msg += f"（跳过{skipped}人）"
    return True, msg, get_hr_employees_payload()


def _record_piecework(d: dict[str, Any], name: str, qty: float, unit_price: float | None, day: str) -> str:
    e = d["employees"].get(name)
    if not isinstance(e, dict):
        return "❌ 未找到员工"
    if qty <= 0:
        return "❌ 计件数量必须大于0"
    if unit_price is None or unit_price <= 0:
        if str(e.get("salary_type", "")) != "计件":
            return "❌ 该员工不是计件工，需明确传入单价"
        unit_price = _to_float(e.get("salary_value"), 0.0)
    if unit_price <= 0:
        return "❌ 计件单价无效"
    pay = qty * unit_price
    d["piecework_records"].append({
        "name": name,
        "qty": round(qty, 3),
        "unit_price": round(unit_price, 4),
        "pay": round(pay, 2),
        "date": _parse_date(day),
        "created_at": datetime.now().isoformat(timespec="seconds"),
    })
    save(d)
    return f"✅ 计件已登记: {name} 数量{qty:.3f} 单价{unit_price:.4f} 收入{pay:.2f}"


def _record_reward_penalty(d: dict[str, Any], name: str, typ: str, amount: float, reason: str, day: str) -> str:
    if name not in d["employees"]:
        return "❌ 未找到员工"
    if typ not in ("奖励", "处罚"):
        return "❌ 类型仅支持: 奖励/处罚"
    if amount <= 0:
        return "❌ 金额必须大于0"
    d["reward_penalty_records"].append({
        "name": name,
        "type": typ,
        "amount": round(amount, 2),
        "reason": (reason or "").strip(),
        "date": _parse_date(day),
        "created_at": datetime.now().isoformat(timespec="seconds"),
    })
    save(d)
    icon = "🏅" if typ == "奖励" else "⚠️"
    return f"{icon} 已记录{typ}: {name} {amount:.2f}"


def _list_reward_penalty(d: dict[str, Any], name: str = "") -> str:
    rows = d.get("reward_penalty_records", [])
    if not isinstance(rows, list) or not rows:
        return "📄 暂无奖惩记录"
    out = ["📄 奖惩记录(最近20条)"]
    for rec in rows[-20:][::-1]:
        if not isinstance(rec, dict):
            continue
        if name and str(rec.get("name", "")) != name:
            continue
        out.append(
            f"{rec.get('date','')} | {rec.get('name','')} | {rec.get('type','')} {(_to_float(rec.get('amount'),0)):.2f} | {rec.get('reason','')}"
        )
    if len(out) == 1:
        return "📄 暂无匹配奖惩记录"
    return "\n".join(out)


def _payroll(d: dict[str, Any], asof: str, name: str = "") -> str:
    emps = d.get("employees", {})
    if not isinstance(emps, dict) or not emps:
        return "💰 无员工档案"

    targets = [name] if name else list(emps.keys())
    rows: list[dict[str, Any]] = []
    total = 0.0
    for n in targets:
        e = emps.get(n)
        if not isinstance(e, dict):
            continue
        if str(e.get("status", "在岗")) == "离职":
            continue
        pay = _calc_pay_for_employee(d, n, e, asof)
        rows.append(pay)
        total += _to_float(pay.get("net"), 0.0)
    if not rows:
        return "💰 当前周期无可结算员工"
    lines = [f"💰 工资试算({asof})"]
    for r in rows:
        lines.append(
            f"{r['name']} | {r['salary_type']} | 周期{r['period']} | 工时{r.get('regular_hours',0):.2f}h + 加班{r.get('overtime_hours',0):.2f}h | 底薪{r['base']:.2f} +加班费{r.get('overtime_pay',0):.2f} +奖{r['reward']:.2f} -罚{r['penalty']:.2f} = {r['net']:.2f}"
        )
    lines.append(f"合计: {total:.2f}")
    return "\n".join(lines)


def _org_text(d: dict[str, Any]) -> str:
    _ensure_org(d)
    teams = d["org"].get("teams", [])
    lines = ["🏗️ HR组织架构"]
    for t in teams:
        if not isinstance(t, dict):
            continue
        positions = t.get("positions", [])
        lines.append(f"{t.get('name','未命名')}: {' / '.join(str(x) for x in positions)}")
    lines.append("薪资类型: 日薪(周发) / 月薪(15天发) / 计件")
    return "\n".join(lines)


def _help() -> str:
    return (
        "🧭 HR指令\n"
        "1) HR初始化岗位\n"
        "2) HR组织架构\n"
        "3) 员工建档 姓名 年龄 民族 信仰 入职日期 职位 薪资类型 薪资值 班组\n"
        "4) 员工建档 name=张三 age=30 ethnicity=汉 religion=佛教 join=2026-03-18 position=锯工 salary_type=计件 salary=0.8 team=锯工组\n"
        "5) 员工档案 姓名 / 员工列表 [在岗|离职|全部]\n"
        "6) 员工离职 姓名 原因 / 员工复职 姓名\n"
        "7) 奖励 姓名 金额 原因 / 处罚 姓名 金额 原因 / 奖惩记录 [姓名]\n"
        "8) 出勤 姓名 天数 [日期]（兼容旧版）\n"
        "9) 考勤 姓名 正常工时 [加班工时] [加班倍率] [日期]\n"
        "10) 计件登记 姓名 数量 [单价] [日期]\n"
        "11) 工资试算 [日期] [姓名]\n"
    )


def hr_recommendation_text() -> str:
    return (
        "🚀 前沿HR建议(建议分3阶段)\n"
        "阶段1 基建: 岗位与编制、员工主档、离职闭环、奖惩归档、工资试算自动化。\n"
        "阶段2 提效: 计件自动采集(从生产数据回写)、电子签核(入转调离)、15天发薪清单自动推送。\n"
        "阶段3 智能: 人效看板(班组/岗位/个人)、离职风险预警、技能矩阵与培训闭环、异常考勤识别。\n"
        "推荐补充字段: 手机、身份证、紧急联系人、合同类型、银行卡、技能等级、证书有效期。\n"
        "推荐制度: 轻量OKR + 周绩效复盘 + 奖惩透明化 + 班组人效排名(只看改进，不做惩罚导向)。"
    )


def get_hr_admin_payload() -> dict[str, Any]:
    d = _safe_load()
    _ensure_org(d)
    emps = d.get("employees", {})
    active = 0
    if isinstance(emps, dict):
        for e in emps.values():
            if not isinstance(e, dict):
                continue
            if str(e.get("status", "在岗")) != "离职":
                active += 1
    org = d.get("org", {}) if isinstance(d.get("org"), dict) else _default_org()
    teams = org.get("teams", []) if isinstance(org.get("teams"), list) else []
    salary_types = org.get("salary_types", {}) if isinstance(org.get("salary_types"), dict) else {}
    attendance_cfg = org.get("attendance", {}) if isinstance(org.get("attendance"), dict) else {}
    saw_cfg = org.get("saw_piecework", {}) if isinstance(org.get("saw_piecework"), dict) else {}
    overtime_multipliers_raw = attendance_cfg.get("overtime_multipliers", [])
    overtime_multipliers: list[float] = []
    if isinstance(overtime_multipliers_raw, list):
        for item in overtime_multipliers_raw:
            mv = round(_to_float(item, 0.0), 2)
            if mv <= 0:
                continue
            if mv not in overtime_multipliers:
                overtime_multipliers.append(mv)
    if not overtime_multipliers:
        overtime_multipliers = [1.5, 2.0]
    default_ot_multiplier = round(_to_float(attendance_cfg.get("default_overtime_multiplier"), overtime_multipliers[0]), 2)
    if default_ot_multiplier <= 0:
        default_ot_multiplier = overtime_multipliers[0]
    if default_ot_multiplier not in overtime_multipliers:
        overtime_multipliers.append(default_ot_multiplier)
    team_lines: list[str] = []
    team_rows: list[dict[str, str]] = []
    for item in teams:
        if not isinstance(item, dict):
            continue
        tname = str(item.get("name", "")).strip()
        positions = item.get("positions", [])
        pos_txt = ",".join(str(x).strip() for x in positions if str(x).strip()) if isinstance(positions, list) else ""
        if tname:
            team_lines.append(f"{tname}: {pos_txt}")
            team_rows.append({"name": tname, "positions_text": pos_txt})
    salary_lines: list[str] = []
    salary_rows: list[dict[str, str]] = []
    for st, cfg in salary_types.items():
        if not isinstance(cfg, dict):
            continue
        salary_lines.append(f"{st}|{cfg.get('payout_cycle','')}|{cfg.get('desc','')}")
        salary_rows.append(
            {
                "salary_type": str(st),
                "payout_cycle": str(cfg.get("payout_cycle", "") or ""),
                "desc": str(cfg.get("desc", "") or ""),
            }
        )
    if not team_rows:
        team_rows = [{"name": "", "positions_text": ""}]
    if not salary_rows:
        salary_rows = [
            {"salary_type": "日薪", "payout_cycle": "weekly", "desc": "按周发放"},
            {"salary_type": "月薪", "payout_cycle": "semi_monthly", "desc": "每15天发放"},
            {"salary_type": "计件", "payout_cycle": "weekly", "desc": "按件核算，建议按周结算"},
        ]
    overtime_rows = [{"multiplier": f"{m:.2f}".rstrip("0").rstrip(".")} for m in overtime_multipliers]
    saw_bindings_raw = saw_cfg.get("bindings", []) if isinstance(saw_cfg, dict) else []
    saw_binding_rows: list[dict[str, Any]] = []
    by_machine: dict[int, dict[str, Any]] = {}
    if isinstance(saw_bindings_raw, list):
        for row in saw_bindings_raw:
            if not isinstance(row, dict):
                continue
            machine_no = _to_int(row.get("machine_no"), 0)
            if machine_no < 1 or machine_no > 6:
                continue
            by_machine[machine_no] = row
    for machine_no in range(1, 7):
        row = by_machine.get(machine_no, {})
        saw_binding_rows.append(
            {
                "machine_no": machine_no,
                "primary_name": str(row.get("primary_name", "") or row.get("employee_name", "") or "").strip(),
                "assistant_name": str(row.get("assistant_name", "") or "").strip(),
                "unit_price": round(_to_float(row.get("unit_price"), 0.0), 4),
            }
        )
    saw_employee_options: list[str] = []
    if isinstance(emps, dict):
        for name, e in emps.items():
            if not isinstance(e, dict):
                continue
            if str(e.get("status", "在岗")) == "离职":
                continue
            team_text = str(e.get("team", "") or "").strip().lower()
            position_text = str(e.get("position", "") or "").strip().lower()
            is_saw_team = ("锯工组" in team_text) or ("saw" in team_text) or ("锯" in position_text) or ("saw" in position_text)
            if not is_saw_team:
                continue
            saw_employee_options.append(str(e.get("name", "") or name))
    saw_employee_options = sorted(set([x for x in saw_employee_options if x]))
    return {
        "org": org,
        "teams_json": json.dumps(org.get("teams", []), ensure_ascii=False, indent=2),
        "salary_types_json": json.dumps(org.get("salary_types", {}), ensure_ascii=False, indent=2),
        "teams_text": "\n".join(team_lines),
        "salary_types_text": "\n".join(salary_lines),
        "team_rows": team_rows,
        "salary_rows": salary_rows,
        "overtime_rows": overtime_rows,
        "overtime_default_multiplier": default_ot_multiplier,
        "saw_piecework_enabled": _to_int(saw_cfg.get("enabled"), 1) == 1,
        "saw_piecework_default_unit_price": round(_to_float(saw_cfg.get("default_unit_price"), 0.0), 4),
        "saw_binding_rows": saw_binding_rows,
        "saw_employee_options": saw_employee_options,
        "notes_text": "\n".join(org.get("notes", []) if isinstance(org.get("notes"), list) else []),
        "employee_total": len(emps) if isinstance(emps, dict) else 0,
        "employee_active": active,
    }


def get_hr_employees_payload() -> dict[str, Any]:
    d = _safe_load()
    _ensure_org(d)
    org = d.get("org", {}) if isinstance(d.get("org"), dict) else _default_org()
    teams = org.get("teams", []) if isinstance(org.get("teams"), list) else []
    salary_types = org.get("salary_types", {}) if isinstance(org.get("salary_types"), dict) else {}
    attendance_cfg = org.get("attendance", {}) if isinstance(org.get("attendance"), dict) else {}
    team_options: list[str] = []
    team_positions_map: dict[str, list[str]] = {}
    position_set: set[str] = set()
    for item in teams:
        if not isinstance(item, dict):
            continue
        team_name = str(item.get("name", "") or "").strip()
        if not team_name:
            continue
        raw_positions = item.get("positions", [])
        positions: list[str] = []
        if isinstance(raw_positions, list):
            for p in raw_positions:
                pv = str(p or "").strip()
                if not pv:
                    continue
                positions.append(pv)
                position_set.add(pv)
        team_options.append(team_name)
        team_positions_map[team_name] = positions
    salary_type_options = [str(k or "").strip() for k in salary_types.keys() if str(k or "").strip()]
    if not salary_type_options:
        salary_type_options = ["日薪", "月薪", "计件"]
    overtime_multiplier_options: list[float] = []
    raw_ot_options = attendance_cfg.get("overtime_multipliers", [])
    if isinstance(raw_ot_options, list):
        for item in raw_ot_options:
            mv = round(_to_float(item, 0.0), 2)
            if mv <= 0:
                continue
            if mv not in overtime_multiplier_options:
                overtime_multiplier_options.append(mv)
    if not overtime_multiplier_options:
        overtime_multiplier_options = [1.5, 2.0]
    overtime_default_multiplier = round(_to_float(attendance_cfg.get("default_overtime_multiplier"), overtime_multiplier_options[0]), 2)
    if overtime_default_multiplier <= 0:
        overtime_default_multiplier = overtime_multiplier_options[0]
    if overtime_default_multiplier not in overtime_multiplier_options:
        overtime_multiplier_options.append(overtime_default_multiplier)
    position_options = sorted(position_set)
    emps = d.get("employees", {})
    rows: list[dict[str, Any]] = []
    employee_options: list[str] = []
    active = 0
    left = 0
    if isinstance(emps, dict):
        for name, item in emps.items():
            e = item if isinstance(item, dict) else {}
            status = str(e.get("status", "在岗") or "在岗")
            if status == "离职":
                left += 1
            else:
                active += 1
                employee_options.append(str(e.get("name", "") or name))
            rows.append(
                {
                    "name": str(e.get("name", "") or name),
                    "team": str(e.get("team", "") or ""),
                    "position": str(e.get("position", "") or ""),
                    "salary_type": str(e.get("salary_type", "") or ""),
                    "salary_value": _to_float(e.get("salary_value", 0.0), 0.0),
                    "join_date": str(e.get("join_date", "") or ""),
                    "status": status,
                }
            )
    attendance_rows: list[dict[str, Any]] = []
    special_task_rows: list[dict[str, Any]] = []
    raw_attendance = d.get("attendance_records", [])
    today = _today()
    attended_today: set[str] = set()
    if isinstance(raw_attendance, list):
        # 出勤判断必须覆盖全部记录，避免记录顺序被人工调整后漏判“今日已出勤”。
        for rec in raw_attendance:
            if not isinstance(rec, dict):
                continue
            rh = _to_float(rec.get("regular_hours"), -1.0)
            if rh < 0:
                rh = max(0.0, _to_float(rec.get("days"), 0.0) * 8.0)
            oh = max(0.0, _to_float(rec.get("overtime_hours"), 0.0))
            rec_day = str(rec.get("date", "") or "")
            rec_name = str(rec.get("name", "") or "")
            if rec_day == today and rec_name and (rh > 0 or oh > 0):
                attended_today.add(rec_name)
            attendance_rows.append(
                {
                    "name": rec_name,
                    "date": rec_day,
                    "regular_hours": round(max(0.0, rh), 2),
                    "overtime_hours": round(oh, 2),
                    "overtime_multiplier": round(_to_float(rec.get("overtime_multiplier"), 1.5), 2),
                }
            )
    attendance_rows.sort(key=lambda x: (str(x.get("date", "")), str(x.get("name", ""))), reverse=True)
    raw_rp = d.get("reward_penalty_records", [])
    if isinstance(raw_rp, list):
        for rec in raw_rp:
            if not isinstance(rec, dict):
                continue
            if str(rec.get("source", "")) != "admin_hr_special_task":
                continue
            special_task_rows.append(
                {
                    "date": str(rec.get("date", "") or ""),
                    "beneficiary_type": str(rec.get("beneficiary_type", "") or "employee"),
                    "employee_name": str(rec.get("employee_name", "") or ""),
                    "team_name": str(rec.get("team_name", "") or ""),
                    "name": str(rec.get("employee_name", "") or rec.get("name", "") or ""),
                    "target_label": (
                        str(rec.get("team_name", "") or "")
                        if str(rec.get("beneficiary_type", "") or "employee") == "team"
                        else str(rec.get("employee_name", "") or rec.get("name", "") or "")
                    ),
                    "task_name": str(rec.get("task_name", "") or ""),
                    "quantity": round(max(0.0, _to_float(rec.get("quantity"), 0.0)), 3),
                    "unit_price": round(max(0.0, _to_float(rec.get("unit_price"), 0.0)), 2),
                    "amount": round(max(0.0, _to_float(rec.get("amount"), 0.0)), 2),
                    "note": str(rec.get("note", "") or ""),
                }
            )
    special_task_rows.sort(key=lambda x: (str(x.get("date", "")), str(x.get("name", ""))), reverse=True)
    for row in rows:
        if not isinstance(row, dict):
            continue
        raw_status = str(row.get("status", "") or "")
        name = str(row.get("name", "") or "")
        if raw_status == "离职":
            att_code = "left"
        elif raw_status == "离岗":
            att_code = "off"
        elif raw_status == "病假":
            att_code = "sick"
        elif raw_status == "休假":
            att_code = "leave"
        elif name and name in attended_today:
            att_code = "present"
        else:
            att_code = "absent"
        row["today_attendance_status"] = att_code
    absent_today_names = [
        str(r.get("name", "") or "")
        for r in rows
        if str(r.get("today_attendance_status", "") or "") == "absent" and str(r.get("name", "") or "").strip()
    ]
    rows.sort(key=lambda r: (0 if r.get("status") != "离职" else 1, str(r.get("name", ""))))
    return {
        "employee_total": len(rows),
        "employee_active": active,
        "employee_left": left,
        "rows": rows,
        "employee_options": sorted(set(employee_options)),
        "team_options": team_options,
        "position_options": position_options,
        "salary_type_options": salary_type_options,
        "overtime_multiplier_options": overtime_multiplier_options,
        "overtime_default_multiplier": overtime_default_multiplier,
        "team_positions_map": team_positions_map,
        "attendance_rows": attendance_rows[:20],
        "special_task_rows": special_task_rows[:20],
        "attendance_day": today,
        "absent_today_names": absent_today_names,
        "absent_today_count": len(absent_today_names),
    }


def get_hr_attendance_records(
    day_from: str = "",
    day_to: str = "",
    name: str = "",
    limit: int = 1000,
) -> list[dict[str, Any]]:
    d = _safe_load()
    rows = d.get("attendance_records", [])
    if not isinstance(rows, list):
        return []
    begin = _parse_date(str(day_from or "").strip(), default_today=False)
    end = _parse_date(str(day_to or "").strip(), default_today=False)
    who = str(name or "").strip()
    out: list[dict[str, Any]] = []
    for rec in rows:
        if not isinstance(rec, dict):
            continue
        rec_name = str(rec.get("name", "") or "")
        rec_day = _parse_date(str(rec.get("date", "") or ""), default_today=False)
        if who and rec_name != who:
            continue
        if begin and rec_day and rec_day < begin:
            continue
        if end and rec_day and rec_day > end:
            continue
        rh = _to_float(rec.get("regular_hours"), -1.0)
        if rh < 0:
            rh = max(0.0, _to_float(rec.get("days"), 0.0) * 8.0)
        row = {
            "date": rec_day or str(rec.get("date", "") or ""),
            "name": rec_name,
            "regular_hours": round(max(0.0, rh), 2),
            "overtime_hours": round(max(0.0, _to_float(rec.get("overtime_hours"), 0.0)), 2),
            "overtime_multiplier": round(_to_float(rec.get("overtime_multiplier"), 1.5), 2),
            "source": str(rec.get("source", "") or ""),
        }
        out.append(row)
    out.sort(key=lambda x: (str(x.get("date", "")), str(x.get("name", ""))), reverse=True)
    max_n = max(1, int(limit or 1))
    return out[:max_n]


def get_hr_payroll_preview(asof: str = "", name: str = "") -> dict[str, Any]:
    d = _safe_load()
    emps = d.get("employees", {})
    if not isinstance(emps, dict):
        return {"asof": "", "rows": [], "total_net": 0.0}
    final_asof = _parse_date(str(asof or "").strip(), default_today=True)
    who = str(name or "").strip()
    targets = [who] if who else sorted(emps.keys())
    rows: list[dict[str, Any]] = []
    total_net = 0.0
    for n in targets:
        e = emps.get(n)
        if not isinstance(e, dict):
            continue
        if str(e.get("status", "在岗")) == "离职":
            continue
        pay = _calc_pay_for_employee(d, n, e, final_asof, period_mode="natural_month")
        rows.append(pay)
        total_net += _to_float(pay.get("net"), 0.0)
    return {
        "asof": final_asof,
        "rows": rows,
        "total_net": round(total_net, 2),
    }


def add_hr_employee_from_admin(
    name: str,
    team: str,
    position: str,
    salary_type: str,
    salary_value: str,
    join_date: str,
) -> tuple[bool, str, dict[str, Any]]:
    d = _safe_load()
    _ensure_org(d)
    emps = d.get("employees", {})
    if not isinstance(emps, dict):
        emps = {}
        d["employees"] = emps

    emp_name = str(name or "").strip()
    if not emp_name:
        return False, "❌ 姓名不能为空", get_hr_employees_payload()
    if emp_name in emps:
        return False, f"❌ 员工已存在: {emp_name}", get_hr_employees_payload()

    final_team = str(team or "").strip() or "未分组"
    final_position = str(position or "").strip() or "未设置"
    final_salary_type = str(salary_type or "").strip() or "月薪"
    final_salary_value = _to_float(str(salary_value or "").strip() or 0, 0.0)
    final_join_date = _parse_date(str(join_date or "").strip(), default_today=True)
    final_cycle = _default_cycle(final_salary_type)
    org_salary_types = d.get("org", {}).get("salary_types", {})
    if isinstance(org_salary_types, dict):
        cfg = org_salary_types.get(final_salary_type, {})
        if isinstance(cfg, dict):
            final_cycle = str(cfg.get("payout_cycle", "") or final_cycle)

    emps[emp_name] = {
        "name": emp_name,
        "age": 0,
        "ethnicity": "",
        "religion": "",
        "join_date": final_join_date,
        "team": final_team,
        "position": final_position,
        "salary_type": final_salary_type,
        "salary_value": final_salary_value,
        "payout_cycle": final_cycle,
        "status": "在岗",
        "left_date": "",
        "left_reason": "",
        "last_checkin": "",
        "tags": [],
        "contact": {"phone": "", "id_no": "", "address": "", "emergency_contact": ""},
        "extra": {"skill_level": "", "contract_type": "", "bank_account": ""},
    }
    save(d)
    return True, f"✅ 已添加员工: {emp_name}", get_hr_employees_payload()


def update_hr_employee_from_admin(
    original_name: str,
    team: str,
    position: str,
    salary_type: str,
    salary_value: str,
    join_date: str,
    status: str,
) -> tuple[bool, str, dict[str, Any]]:
    d = _safe_load()
    _ensure_org(d)
    emps = d.get("employees", {})
    if not isinstance(emps, dict):
        return False, "❌ 员工数据异常", get_hr_employees_payload()

    emp_name = str(original_name or "").strip()
    if not emp_name:
        return False, "❌ 缺少员工姓名", get_hr_employees_payload()
    e = emps.get(emp_name)
    if not isinstance(e, dict):
        return False, f"❌ 未找到员工: {emp_name}", get_hr_employees_payload()

    final_team = str(team or "").strip() or str(e.get("team", "") or "未分组")
    final_position = str(position or "").strip() or str(e.get("position", "") or "未设置")
    final_salary_type = str(salary_type or "").strip() or str(e.get("salary_type", "") or "月薪")
    incoming_salary = str(salary_value or "").strip()
    final_salary_value = _to_float(incoming_salary, _to_float(e.get("salary_value", 0.0), 0.0)) if incoming_salary else _to_float(e.get("salary_value", 0.0), 0.0)

    incoming_join = str(join_date or "").strip()
    if incoming_join:
        final_join_date = _parse_date(incoming_join, default_today=False) or str(e.get("join_date", "") or "")
    else:
        final_join_date = str(e.get("join_date", "") or "")

    final_status = str(status or "").strip() or str(e.get("status", "在岗") or "在岗")
    if final_status not in ("在岗", "离岗", "离职", "病假", "休假"):
        final_status = str(e.get("status", "在岗") or "在岗")

    final_cycle = _default_cycle(final_salary_type)
    org_salary_types = d.get("org", {}).get("salary_types", {})
    if isinstance(org_salary_types, dict):
        cfg = org_salary_types.get(final_salary_type, {})
        if isinstance(cfg, dict):
            final_cycle = str(cfg.get("payout_cycle", "") or final_cycle)

    e["team"] = final_team
    e["position"] = final_position
    e["salary_type"] = final_salary_type
    e["salary_value"] = max(0.0, final_salary_value)
    e["join_date"] = final_join_date
    e["status"] = final_status
    e["payout_cycle"] = final_cycle
    if final_status == "离职":
        e["left_date"] = str(e.get("left_date", "") or _today())
    else:
        e["left_date"] = ""
        e["left_reason"] = ""

    save(d)
    return True, f"✅ 已更新员工: {emp_name}", get_hr_employees_payload()


def update_hr_employee_status_from_admin(
    original_name: str,
    status: str,
) -> tuple[bool, str, dict[str, Any]]:
    d = _safe_load()
    _ensure_org(d)
    emps = d.get("employees", {})
    if not isinstance(emps, dict):
        return False, "❌ 员工数据异常", get_hr_employees_payload()

    emp_name = str(original_name or "").strip()
    if not emp_name:
        return False, "❌ 缺少员工姓名", get_hr_employees_payload()
    e = emps.get(emp_name)
    if not isinstance(e, dict):
        return False, f"❌ 未找到员工: {emp_name}", get_hr_employees_payload()

    final_status = str(status or "").strip()
    if final_status not in ("在岗", "离岗", "离职", "病假", "休假"):
        return False, "❌ 状态无效", get_hr_employees_payload()

    e["status"] = final_status
    if final_status == "离职":
        e["left_date"] = str(e.get("left_date", "") or _today())
    else:
        e["left_date"] = ""
        e["left_reason"] = ""

    save(d)
    return True, f"✅ 已更新状态: {emp_name} -> {final_status}", get_hr_employees_payload()


def _parse_teams_text(text: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for ln in str(text or "").splitlines():
        s = ln.strip()
        if not s:
            continue
        if ":" not in s:
            raise ValueError(f"班组行缺少冒号: {s}")
        name, pos = s.split(":", 1)
        tname = name.strip()
        plist = [x.strip() for x in pos.split(",") if x.strip()]
        if not tname:
            raise ValueError(f"班组名为空: {s}")
        out.append({"name": tname, "positions": plist})
    return out


def _parse_salary_types_text(text: str) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for ln in str(text or "").splitlines():
        s = ln.strip()
        if not s:
            continue
        parts = [x.strip() for x in s.split("|")]
        if len(parts) < 1 or not parts[0]:
            raise ValueError(f"薪资类型行无效: {s}")
        stype = parts[0]
        cycle = parts[1] if len(parts) > 1 and parts[1] else _default_cycle(stype)
        desc = parts[2] if len(parts) > 2 else ""
        out[stype] = {"payout_cycle": cycle, "desc": desc}
    return out


def save_hr_admin_settings(
    teams_json: str,
    salary_types_json: str,
    notes_text: str,
    teams_text: str = "",
    salary_types_text: str = "",
    team_names: list[str] | None = None,
    team_positions: list[str] | None = None,
    salary_types_list: list[str] | None = None,
    salary_cycles: list[str] | None = None,
    salary_descs: list[str] | None = None,
    overtime_multipliers: list[str] | None = None,
    default_overtime_multiplier: str = "",
    saw_piecework_enabled: str = "",
    saw_default_unit_price: str = "",
    saw_bind_machine_no: list[str] | None = None,
    saw_bind_primary_name: list[str] | None = None,
    saw_bind_assistant_name: list[str] | None = None,
    saw_bind_unit_price: list[str] | None = None,
) -> tuple[bool, str, dict[str, Any]]:
    d = _safe_load()
    _ensure_org(d)
    try:
        use_row_mode = bool(any((team_names or [])) or any((salary_types_list or [])))
        if use_row_mode:
            teams = []
            tn = team_names or []
            tp = team_positions or []
            max_n = max(len(tn), len(tp))
            for i in range(max_n):
                name = str(tn[i] if i < len(tn) else "").strip()
                pos_text = str(tp[i] if i < len(tp) else "").strip()
                if not name:
                    continue
                plist = [x.strip() for x in pos_text.split(",") if x.strip()]
                teams.append({"name": name, "positions": plist})

            salary_types = {}
            stl = salary_types_list or []
            scl = salary_cycles or []
            sdl = salary_descs or []
            max_s = max(len(stl), len(scl), len(sdl))
            for i in range(max_s):
                st = str(stl[i] if i < len(stl) else "").strip()
                if not st:
                    continue
                cyc = str(scl[i] if i < len(scl) else "").strip() or _default_cycle(st)
                desc = str(sdl[i] if i < len(sdl) else "").strip()
                salary_types[st] = {"payout_cycle": cyc, "desc": desc}
        else:
            use_text_mode = bool(str(teams_text or "").strip() or str(salary_types_text or "").strip())
            if use_text_mode:
                teams = _parse_teams_text(teams_text)
                salary_types = _parse_salary_types_text(salary_types_text)
            else:
                teams = json.loads(str(teams_json or "").strip() or "[]")
                if not isinstance(teams, list):
                    raise ValueError("teams 必须是 JSON 数组")
                salary_types = json.loads(str(salary_types_json or "").strip() or "{}")
                if not isinstance(salary_types, dict):
                    raise ValueError("salary_types 必须是 JSON 对象")
    except Exception as e:
        return False, f"❌ HR设置格式错误: {e}", get_hr_admin_payload()

    notes = [x.strip() for x in str(notes_text or "").splitlines() if x.strip()]
    ot_values: list[float] = []
    for raw in (overtime_multipliers or []):
        text = str(raw or "").strip()
        if not text:
            continue
        mv = round(_to_float(text, 0.0), 2)
        if mv <= 0:
            continue
        if mv not in ot_values:
            ot_values.append(mv)
    if not ot_values:
        ot_values = list(_default_org()["attendance"]["overtime_multipliers"])
    default_ot = round(_to_float(str(default_overtime_multiplier or "").strip() or ot_values[0], ot_values[0]), 2)
    if default_ot <= 0:
        default_ot = ot_values[0]
    if default_ot not in ot_values:
        ot_values.append(default_ot)

    saw_enabled = 1 if str(saw_piecework_enabled or "").strip() in ("1", "true", "on", "yes") else 0
    saw_default_price = max(0.0, round(_to_float(str(saw_default_unit_price or "").strip() or 0.0, 0.0), 4))
    saw_bindings: list[dict[str, Any]] = []
    machine_seen: set[int] = set()
    machine_list = saw_bind_machine_no or []
    primary_list = saw_bind_primary_name or []
    assistant_list = saw_bind_assistant_name or []
    price_list = saw_bind_unit_price or []
    max_bind_n = max(len(machine_list), len(primary_list), len(assistant_list), len(price_list))
    for i in range(max_bind_n):
        machine_no = _to_int(machine_list[i] if i < len(machine_list) else 0, 0)
        if machine_no < 1 or machine_no > 6 or machine_no in machine_seen:
            continue
        machine_seen.add(machine_no)
        primary_name = str(primary_list[i] if i < len(primary_list) else "").strip()
        assistant_name = str(assistant_list[i] if i < len(assistant_list) else "").strip()
        unit_price = max(0.0, round(_to_float(price_list[i] if i < len(price_list) else 0.0, 0.0), 4))
        saw_bindings.append(
            {
                "machine_no": machine_no,
                "primary_name": primary_name,
                "assistant_name": assistant_name,
                "unit_price": unit_price,
            }
        )
    saw_bindings.sort(key=lambda x: _to_int(x.get("machine_no"), 0))

    d["org"]["teams"] = teams
    d["org"]["salary_types"] = salary_types
    d["org"]["attendance"] = {
        "overtime_multipliers": ot_values,
        "default_overtime_multiplier": default_ot,
    }
    d["org"]["saw_piecework"] = {
        "enabled": saw_enabled,
        "default_unit_price": saw_default_price,
        "bindings": saw_bindings,
    }
    d["org"]["notes"] = notes
    save(d)
    return True, "✅ HR组织与薪资规则已保存", get_hr_admin_payload()


def handle_hr(text: str):
    t = str(text or "").strip()
    if not t:
        return None
    d = _safe_load()
    _ensure_org(d)
    parts = _split(t)
    if not parts:
        return None
    cmd = parts[0]

    # 帮助与建议
    if t in ("HR", "hr", "HR帮助", "hr帮助", "人事帮助", "员工帮助"):
        return _help()
    if t in ("HR建议", "人事建议", "阿启建议"):
        return hr_recommendation_text()

    # 组织架构
    if t in ("HR初始化岗位", "初始化HR", "初始化岗位"):
        d["org"] = _default_org()
        save(d)
        return "✅ 已初始化HR组织架构与薪资规则"
    if t in ("HR组织架构", "组织架构", "岗位列表"):
        return _org_text(d)

    # 员工主档
    if cmd == "员工建档":
        return _add_employee_v2(d, parts)
    if cmd == "员工档案" and len(parts) >= 2:
        return _employee_profile(d, parts[1])
    if cmd in ("员工", "员工列表"):
        flt = parts[1] if len(parts) >= 2 and parts[1] in ("在岗", "离职", "全部") else "全部"
        return _list_employees(d, flt)

    # 上下班与离职
    if cmd == "签到" and len(parts) >= 2:
        return _checkin(d, parts[1])
    if cmd == "签退" and len(parts) >= 2:
        return _checkout(d, parts[1])
    if cmd == "员工离职" and len(parts) >= 2:
        reason = " ".join(parts[2:]) if len(parts) > 2 else ""
        return _resign(d, parts[1], reason)
    if cmd == "员工复职" and len(parts) >= 2:
        return _rehire(d, parts[1])

    # 奖惩
    if cmd in ("奖励", "处罚") and len(parts) >= 3:
        amount = _to_float(parts[2], -1.0)
        reason = " ".join(parts[3:]) if len(parts) > 3 else ""
        return _record_reward_penalty(d, parts[1], cmd, amount, reason, _today())
    if cmd == "奖惩" and len(parts) >= 4:
        typ = parts[2]
        amount = _to_float(parts[3], -1.0)
        reason = " ".join(parts[4:]) if len(parts) > 4 else ""
        return _record_reward_penalty(d, parts[1], typ, amount, reason, _today())
    if cmd == "奖惩记录":
        return _list_reward_penalty(d, parts[1] if len(parts) >= 2 else "")

    # 出勤 & 计件
    if cmd == "出勤" and len(parts) >= 3:
        days = _to_float(parts[2], -1.0)
        day = parts[3] if len(parts) >= 4 else _today()
        return _record_attendance(d, parts[1], days, day)
    if cmd == "考勤" and len(parts) >= 3:
        name = parts[1]
        regular_hours = _to_float(parts[2], -1.0)
        overtime_hours = _to_float(parts[3], 0.0) if len(parts) >= 4 else 0.0
        overtime_multiplier = 1.5
        day = _today()
        if len(parts) >= 5:
            maybe = str(parts[4]).strip()
            if _parse_date(maybe, default_today=False):
                day = maybe
            else:
                overtime_multiplier = _to_float(maybe, 1.5)
        if len(parts) >= 6:
            maybe_day = str(parts[5]).strip()
            if _parse_date(maybe_day, default_today=False):
                day = maybe_day
        ok, msg, _ = add_hr_attendance_from_admin(
            name,
            str(regular_hours),
            str(overtime_hours),
            str(overtime_multiplier),
            day,
        )
        return msg if ok else msg
    if cmd == "计件登记" and len(parts) >= 3:
        qty = _to_float(parts[2], -1.0)
        unit_price = None
        day = _today()
        if len(parts) >= 4:
            unit_price = _to_float(parts[3], 0.0)
            if math.isfinite(unit_price) and unit_price <= 0 and len(parts) >= 5:
                day = parts[4]
        if len(parts) >= 5 and _parse_date(parts[4], default_today=False):
            day = parts[4]
        return _record_piecework(d, parts[1], qty, unit_price, day)

    # 工资
    if cmd in ("工资", "工资表", "工资试算", "工资统计"):
        asof = _today()
        name = ""
        if len(parts) >= 2:
            d1 = _parse_date(parts[1], default_today=False)
            if d1:
                asof = d1
            else:
                name = parts[1]
        if len(parts) >= 3:
            name = parts[2]
        return _payroll(d, asof, name)

    return None
