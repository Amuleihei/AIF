from __future__ import annotations

from datetime import datetime, timedelta

from modules.storage.db_doc_store import load_doc, save_doc


DOC_KEY = "forecast_history_v1"


def _safe_float(raw, default=0.0) -> float:
    try:
        if raw in (None, ""):
            return float(default)
        return float(raw)
    except Exception:
        return float(default)


def _safe_int(raw, default=0) -> int:
    try:
        if raw in (None, ""):
            return int(default)
        return int(float(raw))
    except Exception:
        return int(default)


def _round1(value: float) -> float:
    try:
        return round(float(value), 1)
    except Exception:
        return 0.0


def _round4(value: float) -> float:
    try:
        return round(float(value), 4)
    except Exception:
        return 0.0


def _lang_pack(lang: str) -> dict:
    lc = str(lang or "zh").strip().lower()
    if lc == "en":
        return {
            "title": "Forecast",
            "summary_ok": "Tomorrow should stay broadly stable, but the system still recommends protecting the middle-stage handoff.",
            "summary_warn": "Tomorrow is likely to face pressure around {risk}, so action should start before the next shift.",
            "risk_raw": "raw-material feed",
            "risk_kiln": "kiln-feed handoff",
            "risk_back": "post-kiln carry",
            "risk_hr": "staffing coverage",
            "risk_finance": "cash support",
            "action_raw": "Confirm tomorrow's raw-log intake and keep the front stage from starving the kiln feed.",
            "action_kiln": "Protect sorting and kiln-loading pace first so empty kilns do not expand.",
            "action_back": "Pull secondary sorting, finished push, and shipment handoff forward before backlog grows.",
            "action_hr": "Re-check staffing and machine coverage before tomorrow's first production segment.",
            "action_finance": "Reserve cash for tomorrow's production-critical spending before non-urgent payouts.",
            "tomorrow_saw": "Tomorrow saw output",
            "tomorrow_sort": "Tomorrow kiln-feed trays",
            "tomorrow_finish": "Tomorrow finished pcs",
            "tomorrow_m3": "Tomorrow finished m³",
            "next_risk": "Tomorrow top risk",
            "basis": "Forecast basis",
        }
    if lc == "my":
        return {
            "title": "နောက်ရက်ခန့်မှန်း",
            "summary_ok": "မနက်ဖြန် အခြေအနေ အများအားဖြင့် တည်ငြိမ်နိုင်ပေမယ့် အလယ်ပိုင်း လက်ခံနှုန်းကို ဆက်ထိန်းရပါမယ်။",
            "summary_warn": "မနက်ဖြန် {risk} ပတ်ဝန်းကျင်မှာ ဖိအားတက်နိုင်သဖြင့် နောက်တစ်ကြိမ်အလုပ်စမီ ကြိုတင်ပြင်ဆင်သင့်ပါတယ်။",
            "risk_raw": "ရှေ့ပိုင်းကုန်ကြမ်းဖြည့်တင်းမှု",
            "risk_kiln": "မီးဖိုဝင်လက်ခံနှုန်း",
            "risk_back": "မီးဖိုထွက်နောက်ပိုင်းလက်ခံနှုန်း",
            "risk_hr": "ဝန်ထမ်းအင်အားဖုံးလွှမ်းမှု",
            "risk_finance": "ငွေကြေးပံ့ပိုးမှု",
            "action_raw": "မနက်ဖြန် ထင်းဝင်မည့်ပမာဏကို အတည်ပြုပြီး မီးဖိုရှေ့ feed မပြတ်စေရန် ထိန်းပါ။",
            "action_kiln": "ရွေးချယ်နှင့် မီးဖိုတင်နှုန်းကို အရင်ကာကွယ်ပြီး အလွတ်မီးဖို မတိုးစေပါနဲ့။",
            "action_back": "ဒုတိယရွေး၊ ကုန်ချောတင်ဆက်မှု၊ ပို့ဆောင်လက်ခံမှုကို backlog မတိုးခင် အရင်ဆွဲတင်ပါ။",
            "action_hr": "မနက်ဖြန် အလုပ်စမီ ဝန်ထမ်းနှင့် စက်ဖုံးလွှမ်းမှုကို ပြန်စစ်ပါ။",
            "action_finance": "မနက်ဖြန် ထုတ်လုပ်မှုအတွက် အရေးကြီးသုံးစွဲမှုကို အရင်ပံ့ပိုးပြီးမှ အရေးမကြီးသေးသောပေးချေမှုများကို ဆောင်ရွက်ပါ။",
            "tomorrow_saw": "မနက်ဖြန် လွှဖြတ်ခန့်မှန်း",
            "tomorrow_sort": "မနက်ဖြန် မီးဖိုဝင်ခန့်မှန်း",
            "tomorrow_finish": "မနက်ဖြန် ကုန်ချောအရေအတွက်",
            "tomorrow_m3": "မနက်ဖြန် ကုန်ချော m³",
            "next_risk": "မနက်ဖြန် အဓိကအန္တရာယ်",
            "basis": "ခန့်မှန်းအခြေခံ",
        }
    return {
        "title": "预测层",
        "summary_ok": "按当前节奏看，明天整体还能维持，但中段衔接仍要继续盯紧。",
        "summary_warn": "按当前数据看，明天更可能在「{risk}」附近起压，建议今天就先做预处理。",
        "risk_raw": "前段供料",
        "risk_kiln": "入窑衔接",
        "risk_back": "窑后承接",
        "risk_hr": "人手覆盖",
        "risk_finance": "资金支撑",
        "action_raw": "先确认明天原木入库和前段供料，避免窑前继续断料。",
        "action_kiln": "优先保拣选和装窑节拍，避免空窑继续扩大。",
        "action_back": "把二选、成品推进和发货承接提前安排，别等后段继续堆高。",
        "action_hr": "明天开工前先复核班组和机台覆盖，别等开工后才补人。",
        "action_finance": "优先保障明天生产关键支出，再处理非紧急付款。",
        "tomorrow_saw": "明日锯解预测",
        "tomorrow_sort": "明日待入窑预测",
        "tomorrow_finish": "明日成品件数预测",
        "tomorrow_m3": "明日成品 m³ 预测",
        "next_risk": "明日主风险",
        "basis": "预测依据",
    }


def _load_recent_daily_reports(lang: str, days: int = 3) -> list[dict]:
    from web.services.daily_report_service import build_daily_report

    reports: list[dict] = []
    total = max(1, min(7, int(days or 3)))
    for offset in range(total):
        day = (datetime.now() - timedelta(days=offset)).strftime("%Y-%m-%d")
        try:
            reports.append(build_daily_report(day, lang=lang, include_forecast=False))
        except Exception:
            continue
    return reports


def _weighted_avg(values: list[float]) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return float(values[0])
    weights = list(range(len(values), 0, -1))
    total = sum(weights)
    return sum(float(v) * w for v, w in zip(values, weights)) / float(total or 1)


def _today_str() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _tomorrow_str() -> str:
    return (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")


def _load_history() -> list[dict]:
    data = load_doc(DOC_KEY, default=[])
    return data if isinstance(data, list) else []


def _save_history(rows: list[dict]) -> None:
    save_doc(DOC_KEY, rows[-90:] if isinstance(rows, list) else [])


def _upsert_history_record(record: dict) -> None:
    rows = _load_history()
    target_day = str(record.get("target_day") or "").strip()
    source_day = str(record.get("source_day") or "").strip()
    out: list[dict] = []
    replaced = False
    for row in rows:
        if not isinstance(row, dict):
            continue
        if str(row.get("target_day") or "") == target_day and str(row.get("source_day") or "") == source_day:
            out.append(record)
            replaced = True
        else:
            out.append(row)
    if not replaced:
        out.append(record)
    _save_history(out)


def _collect_actual_summary(day_text: str) -> dict:
    from web.services.daily_report_service import build_daily_report

    try:
        report = build_daily_report(day_text, lang="zh", include_forecast=False)
        summary = report.get("summary", {}) if isinstance(report.get("summary"), dict) else {}
        return {
            "saw_output_trays": _safe_float(summary.get("saw_output_trays"), 0.0),
            "sort_trays": _safe_float(summary.get("sort_trays"), 0.0),
            "finished_pcs": _safe_float(summary.get("finished_pcs"), 0.0),
        }
    except Exception:
        return {}


def _calibration_snapshot(history: list[dict]) -> dict:
    checked: list[dict] = []
    changed = False
    today = _today_str()
    for row in history:
        if not isinstance(row, dict):
            continue
        target_day = str(row.get("target_day") or "").strip()
        if target_day and target_day < today and not isinstance(row.get("actual"), dict):
            actual = _collect_actual_summary(target_day)
            if actual:
                row["actual"] = actual
                changed = True
        checked.append(row)
    if changed:
        _save_history(checked)

    completed = [row for row in checked if isinstance(row, dict) and isinstance(row.get("actual"), dict) and isinstance(row.get("predictions"), dict)]
    if not completed:
        return {"sample_size": 0, "hit_rate": None, "avg_abs_error": None}

    hits = 0
    total = 0
    error_acc = 0.0
    for row in completed[-7:]:
        preds = row.get("predictions", {}) if isinstance(row.get("predictions"), dict) else {}
        actual = row.get("actual", {}) if isinstance(row.get("actual"), dict) else {}
        p = _safe_float(preds.get("tomorrow_finished_pcs"), 0.0)
        a = _safe_float(actual.get("finished_pcs"), 0.0)
        if a > 0 and abs(p - a) / a <= 0.35:
            hits += 1
        total += 1
        error_acc += abs(p - a)
    return {
        "sample_size": total,
        "hit_rate": _round1((hits / total) * 100.0) if total > 0 else None,
        "avg_abs_error": _round1(error_acc / total) if total > 0 else None,
    }


def build_forecast_payload(lang: str = "zh", stock: dict | None = None, intelligence: dict | None = None) -> dict:
    lp = _lang_pack(lang)
    stock = stock if isinstance(stock, dict) else {}
    intelligence = intelligence if isinstance(intelligence, dict) else {}
    reports = _load_recent_daily_reports(lang=lang, days=3)

    saw_series: list[float] = []
    sort_series: list[float] = []
    finished_series: list[float] = []
    finished_m3_series: list[float] = []
    for rpt in reports:
        summary = rpt.get("summary", {}) if isinstance(rpt.get("summary"), dict) else {}
        saw_series.append(_safe_float(summary.get("saw_output_trays"), 0))
        sort_series.append(_safe_float(summary.get("sort_trays"), 0))
        finished_series.append(_safe_float(summary.get("finished_pcs"), 0))
        finished_m3_series.append(_safe_float((rpt.get("inventory_snapshot") or {}).get("finished_product_m3"), 0.0))

    current_sorting = _safe_int(stock.get("sorting_stock"), 0)
    current_kiln_done = _safe_int(stock.get("kiln_done_stock"), 0)
    current_log_stock = _safe_float(stock.get("log_stock"), 0.0)
    current_product_m3 = _safe_float(stock.get("product_m3"), 0.0)
    current_product_count = _safe_int(stock.get("product_count"), 0)

    predicted_saw = max(0.0, _weighted_avg(saw_series))
    predicted_sort = max(0.0, (_weighted_avg(sort_series) * 0.7) + (current_sorting * 0.3))
    predicted_finish = max(0.0, _weighted_avg(finished_series))
    avg_piece_m3 = (_weighted_avg(finished_m3_series) / max(1.0, _weighted_avg(finished_series))) if finished_series and _weighted_avg(finished_series) > 0 else 0.06
    predicted_finish_m3 = max(0.0, predicted_finish * avg_piece_m3)

    priority_stage = ((intelligence.get("priority_stage") or {}) if isinstance(intelligence, dict) else {}) or {}
    pressure_stage = ((intelligence.get("pressure_stage") or {}) if isinstance(intelligence, dict) else {}) or {}
    stage_name = str(priority_stage.get("name") or pressure_stage.get("name") or "").strip()

    from modules.hr.hr_engine import get_hr_employees_payload
    from modules.finance.finance_engine import load as load_finance

    hr_payload = get_hr_employees_payload()
    active = _safe_int(hr_payload.get("employee_active"), 0)
    absent = _safe_int(hr_payload.get("absent_today_count"), 0)
    saw_stats = hr_payload.get("saw_operation_stats", {}) if isinstance(hr_payload.get("saw_operation_stats"), dict) else {}
    configured_machines = _safe_int(saw_stats.get("configured_machine_count"), 0)
    running_machines = _safe_int(saw_stats.get("running_machine_count"), 0)

    finance = load_finance()
    accounts = finance.get("accounts", {}) if isinstance(finance.get("accounts"), dict) else {}
    available_cash = _safe_float(accounts.get("cash"), 0.0) + _safe_float(accounts.get("bank"), 0.0)
    risk_drivers: list[str] = []

    top_risk = lp["risk_kiln"]
    if current_log_stock <= max(8.0, predicted_saw * 0.6):
        top_risk = lp["risk_raw"]
        risk_drivers.append(f"log_stock={_round4(current_log_stock)}")
    elif current_kiln_done >= max(8, int(predicted_finish)):
        top_risk = lp["risk_back"]
        risk_drivers.append(f"kiln_done_stock={current_kiln_done}")
    elif active > 0 and absent >= max(2, int(active * 0.18)):
        top_risk = lp["risk_hr"]
        risk_drivers.append(f"absent={absent}/{active}")
    elif available_cash <= 0:
        top_risk = lp["risk_finance"]
        risk_drivers.append(f"cash={_round1(available_cash)}")
    else:
        risk_drivers.append(f"sorting_stock={current_sorting}")

    if configured_machines > 0:
        risk_drivers.append(f"saw_running={running_machines}/{configured_machines}")
    if stage_name:
        risk_drivers.append(stage_name)

    if top_risk == lp["risk_raw"]:
        actions = [lp["action_raw"], lp["action_kiln"]]
    elif top_risk == lp["risk_back"]:
        actions = [lp["action_back"], lp["action_hr"]]
    elif top_risk == lp["risk_hr"]:
        actions = [lp["action_hr"], lp["action_kiln"]]
    elif top_risk == lp["risk_finance"]:
        actions = [lp["action_finance"], lp["action_kiln"]]
    else:
        actions = [lp["action_kiln"], lp["action_back"]]

    summary = lp["summary_ok"]
    if top_risk:
        summary = lp["summary_warn"].format(risk=top_risk)

    basis = [
        f"{lp['tomorrow_saw']}: {_round1(predicted_saw)}",
        f"{lp['tomorrow_sort']}: {_round1(predicted_sort)}",
        f"{lp['tomorrow_finish']}: {_safe_int(round(predicted_finish), 0)}",
    ]
    if stage_name:
        basis.append(stage_name)
    if configured_machines > 0:
        basis.append(f"{running_machines}/{configured_machines}")
    if current_product_count > 0 or current_product_m3 > 0:
        basis.append(f"{current_product_count} pcs / {_round4(current_product_m3)} m³")

    history = _load_history()
    calibration = _calibration_snapshot(history)
    result = {
        "template_version": "forecast_v1",
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "target_day": _tomorrow_str(),
        "summary": summary,
        "top_risk": top_risk,
        "actions": actions[:3],
        "basis": basis[:5],
        "risk_drivers": risk_drivers[:5],
        "calibration": calibration,
        "predictions": {
            "tomorrow_saw_trays": _round1(predicted_saw),
            "tomorrow_sort_trays": _round1(predicted_sort),
            "tomorrow_finished_pcs": _safe_int(round(predicted_finish), 0),
            "tomorrow_finished_m3": _round4(predicted_finish_m3),
        },
    }
    _upsert_history_record(
        {
            "source_day": _today_str(),
            "target_day": result["target_day"],
            "generated_at": result["generated_at"],
            "predictions": dict(result.get("predictions") or {}),
            "top_risk": result.get("top_risk"),
            "risk_drivers": list(result.get("risk_drivers") or []),
        }
    )
    return result
