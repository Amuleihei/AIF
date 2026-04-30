from __future__ import annotations

from datetime import datetime
from typing import Any

from modules.hr.hr_engine import get_hr_employees_payload
from web.services.alert_settings_service import get_ai_capacity_settings


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value in (None, ""):
            return float(default)
        return float(value)
    except Exception:
        return float(default)


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        if value in (None, ""):
            return int(default)
        return int(float(value))
    except Exception:
        return int(default)


def _lang_pack(lang: str) -> dict[str, str]:
    lc = str(lang or "zh").strip().lower()
    if lc == "en":
        return {
            "equipment_title": "Equipment & Quality",
            "summary_good": "Core equipment and yield look broadly stable, but the plant should keep watching the stage that most deserves improvement.",
            "summary_warn": "Equipment capacity or quality loss is already weakening the plant's next output step, so this should be corrected before the next shift.",
            "risk_saw_gap": "Band-saw output is below the configured target.",
            "risk_secondary_gap": "Secondary sorting finished output is below the daily target.",
            "risk_saw_loss": "Saw-to-dip loss is elevated today.",
            "risk_secondary_loss": "Secondary-to-finished conversion is weak today.",
            "risk_saw_machine_idle": "Too many band-saw machines are idle.",
            "risk_need_secondary_machine": "Secondary sorting backlog suggests equipment expansion may be needed if this keeps repeating.",
            "action_saw_staff": "Re-check whether band-saw staffing, helper coverage, or QC coverage is below target before blaming the raw-material side only.",
            "action_secondary_machine": "If secondary backlog remains high for multiple days, evaluate whether another table saw or fixture is needed instead of solving it only with overtime.",
            "action_quality": "Track loss together with stage handoff and machine usage, so quality loss is not treated as a separate issue from capacity.",
            "review_title": "Period Review",
            "review_no_prev": "No prior period baseline is available yet, so this review is built from the current period only.",
            "review_improved": "This period improved overall, but the weakest lift still needs targeted follow-up.",
            "review_declined": "This period slowed down overall, and the next cycle should focus on the weakest output chain first.",
            "collab_title": "Role Collaboration",
            "role_hr": "HR",
            "role_finance": "Finance",
            "role_security": "Security",
            "role_equipment": "Equipment",
            "role_office": "Office",
            "summary_follow": "Keep equipment, handoff, and loss review aligned with \"{stage}\".",
            "review_action_1": "Review why \"{label}\" was the weakest change this period ({delta:+.1f}).",
            "review_action_2": "Standardize and copy the effective practice from \"{label}\".",
            "review_action_3": "Next period, first build on the current finished-output base of {m3:.1f} m3 / {pcs} pcs.",
        }
    if lc == "my":
        return {
            "equipment_title": "စက်ပစ္စည်းနှင့် အရည်အသွေး",
            "summary_good": "အဓိကစက်ပစ္စည်းနှင့် yield အခြေအနေ အများအားဖြင့် တည်ငြိမ်သော်လည်း အရင်တိုးမြှင့်သင့်သောအပိုင်းကို ဆက်စောင့်ကြည့်ရပါမည်။",
            "summary_warn": "စက်ပစ္စည်းစွမ်းရည် သို့မဟုတ် အရည်အသွေးဆုံးရှုံးမှုကြောင့် နောက်တစ်ဆင့်ထုတ်လုပ်မှုကို အားနည်းစေနေပြီး နောက် shift မတိုင်မီ ပြင်ဆင်သင့်ပါသည်။",
            "risk_saw_gap": "Band-saw ထွက်အားသည် သတ်မှတ်ထားသောနေ့စဉ်ပစ်မှတ်ထက် လျော့နည်းနေသည်။",
            "risk_secondary_gap": "ဒုတိယရွေး ကုန်ချောထွက်အားသည် နေ့စဉ်ပစ်မှတ်ထက် လျော့နည်းနေသည်။",
            "risk_saw_loss": "ယနေ့ လွှဖြတ်မှ ဆေးစိမ်သို့ ဆုံးရှုံးနှုန်း မြင့်နေသည်။",
            "risk_secondary_loss": "ယနေ့ ဒုတိယရွေးမှ ကုန်ချောသို့ ပြောင်းလဲနှုန်း အားနည်းနေသည်။",
            "risk_saw_machine_idle": "Band-saw စက်များ အလွတ်ထားရမှု များနေသည်။",
            "risk_need_secondary_machine": "ဒုတိယရွေး backlog ဆက်လက်မြင့်နေပါက စက်တိုးချဲ့ရန် စဉ်းစားသင့်ပါသည်။",
            "action_saw_staff": "ကုန်ကြမ်းဘက်ကိုသာ မစွပ်စွဲမီ band-saw လူအင်အား၊ helper နှင့် QC coverage တို့ target လိုက်မီမီ ရှိ/မရှိကို အရင်စစ်ပါ။",
            "action_secondary_machine": "ဒုတိယရွေး backlog များနေမှု ဆက်လက်ဖြစ်နေပါက overtime နဲ့ပဲ မဖုံးလွှမ်းဘဲ နောက်ထပ် table saw သို့မဟုတ် fixture လိုမလို ပြန်သုံးသပ်ပါ။",
            "action_quality": "ဆုံးရှုံးမှုကို stage handoff နှင့် machine အသုံးပြုမှုတို့နဲ့ တွဲကြည့်ပြီး အရည်အသွေးပြဿနာကို capacity ပြဿနာနဲ့ ခွဲမထားပါနှင့်။",
            "review_title": "ကာလပြန်လည်သုံးသပ်ချက်",
            "review_no_prev": "ယခင်ကာလ baseline မရှိသေးသောကြောင့် လက်ရှိကာလအပေါ်အခြေခံပြီးသာ သုံးသပ်ထားသည်။",
            "review_improved": "ဒီကာလမှာ အလုံးစုံတိုးတက်သော်လည်း အနည်းဆုံးတိုးတက်မှုရှိသော chain ကို ဆက်ပြီး အာရုံစိုက်ရပါမည်။",
            "review_declined": "ဒီကာလမှာ အလုံးစုံနှေးကွေးလာပြီး နောက်ကာလမှာ အနည်းဆုံး output chain ကို အရင်ကာကွယ်သင့်ပါသည်။",
            "collab_title": "အခန်းကဏ္ဍပူးပေါင်းမှု",
            "role_hr": "HR",
            "role_finance": "ငွေကြေး",
            "role_security": "လုံခြုံရေး",
            "role_equipment": "စက်ပစ္စည်း",
            "role_office": "ရုံး",
            "summary_follow": "စက်ပစ္စည်း၊ handoff နှင့် loss စစ်ဆေးမှုကို 「{stage}」 နဲ့ ကိုက်ညီအောင် ဆက်ကြည့်ပါ။",
            "review_action_1": "ဒီကာလမှာ \"{label}\" က ဘာကြောင့် အနည်းဆုံးပြောင်းလဲမှု ဖြစ်သလဲ ({delta:+.1f}) ကို အရင်ပြန်ကြည့်ပါ။",
            "review_action_2": "\"{label}\" မှာ ရလာတဲ့ practice ကောင်းကို စံချိန်တင်ပြီး ပြန်ကူးပါ။",
            "review_action_3": "နောက်ကာလမှာ လက်ရှိ ကုန်ချော {m3:.1f} m3 / {pcs} ခု အခြေခံပေါ်ကနေ အရင်တစ်ဆင့်တိုးပါ။",
        }
    return {
        "equipment_title": "设备与质量闭环",
        "summary_good": "关键设备与产线损耗整体可控，但仍要围绕当前最该提升的环节继续盯设备和质量口径。",
        "summary_warn": "设备能力或质量损耗已经在拖累下一步产出，这块要在下个班次前先纠偏。",
        "risk_saw_gap": "带锯产出低于现场配置目标。",
        "risk_secondary_gap": "二选成品产出低于日目标。",
        "risk_saw_loss": "今日锯解到药浸损耗偏高。",
        "risk_secondary_loss": "今日二选到成品转化偏弱。",
        "risk_saw_machine_idle": "带锯空置台数偏多。",
        "risk_need_secondary_machine": "二选积压已提示设备能力可能不够，若连续出现应评估增设备。",
        "action_saw_staff": "先核对带锯主锯、副锯、QC 是否低于目标，再决定是不是单纯的原料问题。",
        "action_secondary_machine": "如果二选连续多天积压偏高，不要只靠加班，应该同步评估增加台锯或夹具位。",
        "action_quality": "把损耗和交接、机台利用率一起看，别把质量问题和产能问题拆开处理。",
        "review_title": "周/月复盘",
        "review_no_prev": "当前还没有上一周期基线，这轮复盘先按本周期实际数据做判断。",
        "review_improved": "本周期整体有提升，但最弱那条链还需要下一周期继续追。",
        "review_declined": "本周期整体放缓，下一周期要先守住最弱输出链。",
        "collab_title": "角色协同建议",
        "role_hr": "HR",
        "role_finance": "财务",
        "role_security": "保安",
        "role_equipment": "电工/设备",
        "role_office": "办公室",
        "summary_follow": "当前更该围绕「{stage}」看设备、交接和损耗。",
        "review_action_1": "先复盘「{label}」这一项为什么是本周期最弱变化（{delta:+.1f}）。",
        "review_action_2": "把「{label}」的有效做法沉淀下来并复制。",
        "review_action_3": "下周期先围绕成品 {m3:.1f} m3 / {pcs} 件的基础再提一档。",
    }


def build_equipment_quality_snapshot(
    *,
    lang: str = "zh",
    stock: dict | None = None,
    factory_intelligence: dict | None = None,
    daily_report: dict | None = None,
    throughput_day: dict | None = None,
) -> dict[str, Any]:
    lp = _lang_pack(lang)
    stock = stock if isinstance(stock, dict) else {}
    factory_intelligence = factory_intelligence if isinstance(factory_intelligence, dict) else {}
    daily_report = daily_report if isinstance(daily_report, dict) else {}
    throughput_day = throughput_day if isinstance(throughput_day, dict) else {}
    hr_payload = get_hr_employees_payload()
    team_live = hr_payload.get("team_live_stats", {}) if isinstance(hr_payload.get("team_live_stats"), dict) else {}
    saw_stats = hr_payload.get("saw_operation_stats", {}) if isinstance(hr_payload.get("saw_operation_stats"), dict) else {}
    capacity = get_ai_capacity_settings()

    saw_target_trays = max(1, _safe_int(capacity.get("band_saw_machine_count"), 6) * _safe_int(capacity.get("band_saw_daily_target_trays_per_machine"), 4))
    secondary_target_pcs = max(1, _safe_int(capacity.get("secondary_daily_finish_target_pcs"), 15))
    expected_saw_staff = (
        _safe_int(capacity.get("band_saw_primary_target"), 6)
        + _safe_int(capacity.get("band_saw_assistant_target"), 6)
        + _safe_int(capacity.get("band_saw_qc_target"), 6)
    )

    summary = daily_report.get("summary", {}) if isinstance(daily_report.get("summary"), dict) else {}
    yield_loss = daily_report.get("yield_loss", {}) if isinstance(daily_report.get("yield_loss"), dict) else {}
    saw_actual_trays = _safe_float(summary.get("saw_output_trays"), _safe_float(throughput_day.get("saw_trays"), 0.0))
    finished_actual_pcs = None
    if summary.get("finished_pcs") not in (None, ""):
        finished_actual_pcs = _safe_float(summary.get("finished_pcs"), 0.0)
    saw_gap = round(saw_actual_trays - saw_target_trays, 1)
    secondary_gap = round(float(finished_actual_pcs) - secondary_target_pcs, 1) if finished_actual_pcs is not None else None

    saw_team = team_live.get("saw", {}) if isinstance(team_live.get("saw"), dict) else {}
    sorting_team = team_live.get("sorting", {}) if isinstance(team_live.get("sorting"), dict) else {}
    equipment_team = team_live.get("equipment", {}) if isinstance(team_live.get("equipment"), dict) else {}
    secondary_machine_count = _safe_int(capacity.get("secondary_saw_machine_count"), 3)
    running_machine_count = _safe_int(saw_stats.get("running_machine_count"), 0)
    configured_machine_count = _safe_int(saw_stats.get("configured_machine_count"), _safe_int(capacity.get("band_saw_machine_count"), 6))
    saw_util_pct = round((running_machine_count / max(1, configured_machine_count)) * 100.0, 1)
    saw_staff_total = _safe_int(saw_team.get("total"), 0)
    saw_staff_gap = saw_staff_total - expected_saw_staff
    secondary_backlog = _safe_int(stock.get("kiln_done_stock"), 0)
    saw_loss_pct = _safe_float(yield_loss.get("saw_to_dip_loss_rate_pct"), 0.0)
    secondary_loss_pct = _safe_float(yield_loss.get("secondary_to_finish_loss_rate_pct"), 0.0)

    risks: list[str] = []
    actions: list[str] = []
    if saw_gap < 0:
        risks.append(lp["risk_saw_gap"] + f" ({int(abs(saw_gap))}托)")
    if secondary_gap is not None and secondary_gap < 0:
        risks.append(lp["risk_secondary_gap"] + f" ({int(abs(secondary_gap))}件)")
    if saw_loss_pct >= 25:
        risks.append(lp["risk_saw_loss"] + f" ({round(saw_loss_pct, 1)}%)")
    if secondary_loss_pct >= 45:
        risks.append(lp["risk_secondary_loss"] + f" ({round(secondary_loss_pct, 1)}%)")
    if configured_machine_count > 0 and running_machine_count < configured_machine_count:
        risks.append(lp["risk_saw_machine_idle"] + f" ({running_machine_count}/{configured_machine_count})")
    if secondary_backlog >= max(20, secondary_machine_count * 8):
        risks.append(lp["risk_need_secondary_machine"] + f" ({secondary_backlog}托)")

    if saw_gap < 0 or saw_staff_gap < 0:
        actions.append(lp["action_saw_staff"])
    if secondary_backlog >= max(20, secondary_machine_count * 8):
        actions.append(lp["action_secondary_machine"])
    if saw_loss_pct >= 25 or secondary_loss_pct >= 45:
        actions.append(lp["action_quality"])
    if not actions:
        actions = [lp["action_quality"]]

    priority_name = str(((factory_intelligence.get("priority_stage") or {}) if isinstance(factory_intelligence, dict) else {}).get("name") or "").strip()
    summary_text = lp["summary_warn"] if risks else lp["summary_good"]
    if priority_name:
        summary_text = f"{summary_text} {lp['summary_follow'].format(stage=priority_name)}"

    return {
        "title": lp["equipment_title"],
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "summary": summary_text,
        "metrics": {
            "band_saw_target_trays": saw_target_trays,
            "band_saw_actual_trays": saw_actual_trays,
            "band_saw_gap_trays": saw_gap,
            "band_saw_utilization_pct": saw_util_pct,
            "band_saw_staff_target": expected_saw_staff,
            "band_saw_staff_total": saw_staff_total,
            "band_saw_staff_gap": saw_staff_gap,
            "secondary_target_pcs": secondary_target_pcs,
            "secondary_actual_pcs": finished_actual_pcs,
            "secondary_gap_pcs": secondary_gap,
            "secondary_backlog_trays": secondary_backlog,
            "secondary_machine_count": secondary_machine_count,
            "sorting_team_total": _safe_int(sorting_team.get("total"), 0),
            "equipment_team_total": _safe_int(equipment_team.get("total"), 0),
            "saw_to_dip_loss_pct": round(saw_loss_pct, 1),
            "secondary_to_finish_loss_pct": round(secondary_loss_pct, 1),
        },
        "risks": risks[:5],
        "actions": actions[:4],
    }


def build_role_collaboration_plan(
    *,
    lang: str = "zh",
    factory_intelligence: dict | None = None,
    equipment_quality: dict | None = None,
    forecast: dict | None = None,
) -> dict[str, Any]:
    lp = _lang_pack(lang)
    factory_intelligence = factory_intelligence if isinstance(factory_intelligence, dict) else {}
    equipment_quality = equipment_quality if isinstance(equipment_quality, dict) else {}
    forecast = forecast if isinstance(forecast, dict) else {}

    root = (factory_intelligence.get("priority_stage") or {}) if isinstance(factory_intelligence.get("priority_stage"), dict) else {}
    pressure = (factory_intelligence.get("pressure_stage") or {}) if isinstance(factory_intelligence.get("pressure_stage"), dict) else {}
    root_name = str(root.get("name") or "-").strip()
    pressure_name = str(pressure.get("name") or "-").strip()
    forecast_risk = str(forecast.get("top_risk") or "").strip()
    eq_metrics = equipment_quality.get("metrics", {}) if isinstance(equipment_quality.get("metrics"), dict) else {}
    secondary_gap = _safe_float(eq_metrics.get("secondary_gap_pcs"), 0.0)
    saw_gap = _safe_float(eq_metrics.get("band_saw_gap_trays"), 0.0)
    saw_idle = _safe_float(eq_metrics.get("band_saw_utilization_pct"), 0.0) < 100.0

    def _row(role_label: str, summary: str, action: str) -> dict[str, str]:
        return {"role": role_label, "summary": summary, "action": action}

    lc = str(lang or "zh").strip().lower()
    if lc == "en":
        if "Front" in root_name or "前段" in root_name:
            hr = _row(lp["role_hr"], f"Keep sawing, dipping, forklift, and transfer staffing aligned with {root_name}.", "Protect front-stage staffing continuity before moving people elsewhere.")
            finance = _row(lp["role_finance"], f"Back raw logs, chemicals, fuel, and upstream transport for {root_name}.", "Delay non-critical payouts until front-stage supply is safe.")
            equipment = _row(lp["role_equipment"], "Protect band-saw, dipping, and transfer equipment uptime first.", "Clear faults that break feed continuity.")
            office = _row(lp["role_office"], "Push purchasing, arrivals, paperwork, and front-stage handoff.", "Finish tomorrow's front-stage paperwork and coordination first.")
        elif "Back" in root_name or "后段" in root_name:
            hr = _row(lp["role_hr"], f"Stabilize secondary sorting, kiln-out handoff, and finished push around {root_name}.", "Fill critical back-stage roles before approving non-critical leave.")
            finance = _row(lp["role_finance"], f"Fund shipment, packing, urgent support materials, and overtime for {root_name}.", "Use cash to unblock back-stage carry first.")
            equipment = _row(lp["role_equipment"], "Protect table saws, packing points, and post-kiln equipment first.", "Fix small faults that slow secondary sorting or kiln-out carry.")
            office = _row(lp["role_office"], "Push customer contact, shipment paperwork, logistics, and finished handoff.", "Do not let the back stage stall on communication.")
        else:
            hr = _row(lp["role_hr"], f"Keep sorting, kiln loading, and kiln-out pacing stable around {root_name}.", "Avoid losing key people during lunch, shift handoff, and after 16:00.")
            finance = _row(lp["role_finance"], f"Back sorting, kiln loading, dipping, and continuous production around {root_name}.", "Protect continuity before non-critical payments.")
            equipment = _row(lp["role_equipment"], "Protect loading, kiln-out, forklift, and transfer equipment first.", "Fix faults that slow middle-stage rhythm.")
            office = _row(lp["role_office"], "Hold shift handoff, statistics, communication, and site coordination together.", "Do not let the middle stage lose planning continuity.")
        if saw_gap < 0 and saw_idle:
            equipment["action"] += " Also find why the band-saw line is not fully open."
        if secondary_gap < 0:
            hr["action"] += " Re-check staffing and equipment together when secondary output keeps missing target."
        if forecast_risk:
            office["summary"] += f" Tomorrow's top risk is \"{forecast_risk}\"."
        summary = f"All roles should align around \"{root_name}\", while visible pressure is showing in \"{pressure_name}\"."
    elif lc == "my":
        if "Front" in root_name or "前段" in root_name:
            hr = _row(lp["role_hr"], f"{root_name} ကို ဗဟိုထားပြီး လွှဖြတ်၊ ဆေးစိမ်၊ forklift နှင့် transfer လူအင်အားကို ထိန်းပါ။", "ရှေ့ပိုင်း လူအင်အားမကျသွားအောင် အရင်ကာကွယ်ပြီးမှ အခြားနေရာသို့ ရွှေ့ပါ။")
            finance = _row(lp["role_finance"], f"{root_name} အတွက် ကုန်ကြမ်း၊ ဆေး၊ လောင်စာနှင့် upstream ပို့ဆောင်မှုကို အရင်ပံ့ပိုးပါ။", "ရှေ့ပိုင်း supply မလုံလောက်မချင်း non-critical payout များကို နောက်သို့ရွှေ့ပါ။")
            equipment = _row(lp["role_equipment"], "Band-saw၊ ဆေးစိမ်နှင့် transfer စက်များ uptime ကို အရင်ကာကွယ်ပါ။", "Feed continuity ကို ဖျက်နေသော fault များကို အရင်ရှင်းပါ။")
            office = _row(lp["role_office"], "ဝယ်ယူမှု၊ ရောက်ရှိမှု၊ စာရွက်စာတမ်းနှင့် ရှေ့ပိုင်း handoff ကို အရင်တွန်းပါ။", "မနက်ဖြန်ရှေ့ပိုင်းအတွက် လိုအပ်သည့် coordination ကို အရင်ပြီးစီးစေပါ။")
        elif "Back" in root_name or "后段" in root_name:
            hr = _row(lp["role_hr"], f"{root_name} ကို ဗဟိုထားပြီး ဒုတိယရွေး၊ kiln-out handoff နှင့် finished push ကို တည်ငြိမ်စေပါ။", "နောက်ပိုင်း critical role များကို အရင်ဖြည့်ပြီးမှ non-critical leave ကို အတည်ပြုပါ။")
            finance = _row(lp["role_finance"], f"{root_name} အတွက် shipment၊ packing၊ urgent support material နှင့် overtime ကို အရင်ပံ့ပိုးပါ။", "ငွေကို နောက်ပိုင်း handoff ဖြေလျှော့ရန် အရင်သုံးပါ။")
            equipment = _row(lp["role_equipment"], "Table saw၊ packing point နှင့် post-kiln စက်များကို အရင်ကာကွယ်ပါ။", "ဒုတိယရွေး သို့မဟုတ် kiln-out handoff နှေးစေသော fault သေးသေးများကို အရင်ရှင်းပါ။")
            office = _row(lp["role_office"], "Customer၊ shipment paperwork၊ logistics နှင့် finished handoff ကို အရင်တွန်းပါ။", "နောက်ပိုင်းကို communication ကြောင့် မနောက်ကျစေပါနှင့်။")
        else:
            hr = _row(lp["role_hr"], f"{root_name} ကို ဗဟိုထားပြီး sorting၊ kiln loading နှင့် kiln-out pacing ကို တည်ငြိမ်စေပါ။", "နေ့လယ်၊ shift handoff နှင့် 16:00 နောက်ပိုင်း key people မကျသွားစေပါနှင့်။")
            finance = _row(lp["role_finance"], f"{root_name} အတွက် sorting၊ kiln loading၊ dipping နှင့် continuous production ကို အရင်ပံ့ပိုးပါ။", "Continuity ကို အရင်ကာကွယ်ပြီးမှ non-critical payment များလုပ်ပါ။")
            equipment = _row(lp["role_equipment"], "Loading၊ kiln-out၊ forklift နှင့် transfer စက်များကို အရင်ကာကွယ်ပါ။", "အလယ်ပိုင်း rhythm ကို နှေးစေသော fault များကို အရင်ပြင်ပါ။")
            office = _row(lp["role_office"], "Shift handoff၊ statistics၊ communication နှင့် site coordination ကို ဆက်ထားပါ။", "အလယ်ပိုင်း plan continuity မပြတ်စေပါနှင့်။")
        if saw_gap < 0 and saw_idle:
            equipment["action"] += " Band-saw line မပြည့်မပြည့် ဖွင့်ထားရသည့် အကြောင်းရင်းကိုပါ ရှာပါ။"
        if secondary_gap < 0:
            hr["action"] += " ဒုတိယရွေး target ဆက်လက်မမီလျှင် လူအင်အားနှင့် စက်နှစ်ဖက်လုံးကို တပြိုင်တည်းပြန်စစ်ပါ။"
        if forecast_risk:
            office["summary"] += f" မနက်ဖြန် အဓိကအန္တရာယ်မှာ \"{forecast_risk}\" ဖြစ်သည်။"
        summary = f"အခန်းကဏ္ဍအားလုံးသည် \"{root_name}\" ကို ဗဟိုထားပြီး ပူးပေါင်းရမည်ဖြစ်ပြီး လက်ရှိဖိအားမှာ \"{pressure_name}\" တွင် ပိုမြင်ရသည်။"
    else:
        if "前段" in root_name or "Front" in root_name:
            hr = _row(lp["role_hr"], f"围绕「{root_name}」补稳锯解、药浸、叉车与转运。", "先保前段关键岗位与班次连贯，再谈跨组调人。")
            finance = _row(lp["role_finance"], f"围绕「{root_name}」优先保原木、药剂、燃料和上游运输支出。", "非紧急付款往后排，先保前段不断料。")
            equipment = _row(lp["role_equipment"], "优先保带锯、药浸和转运设备可用率。", "先处理影响供料的故障和临停。")
            office = _row(lp["role_office"], "优先催采购、到货、单据和前段交接。", "先把明天前段要用到的单据、计划和电话催办到位。")
        elif "后段" in root_name or "Back" in root_name:
            hr = _row(lp["role_hr"], f"围绕「{root_name}」补稳二选、出窑承接和成品推进。", "关键后段岗位优先补齐，非关键调休后让。")
            finance = _row(lp["role_finance"], f"围绕「{root_name}」优先保发货、包装、后段加班和紧急辅料。", "用钱先解决后段承接，不要平均撒。")
            equipment = _row(lp["role_equipment"], "优先保台锯、包装位和出窑后的关键设备。", "后段卡住时，先处理二选位和出窑承接的小故障。")
            office = _row(lp["role_office"], "优先催客户、发货单据、物流协调与成品交接。", "不要让后段再卡在沟通和单据上。")
        else:
            hr = _row(lp["role_hr"], f"围绕「{root_name}」稳住拣选、装窑、出窑节拍。", "午餐、交班和16点后尽量别让中段掉人。")
            finance = _row(lp["role_finance"], f"围绕「{root_name}」优先保装窑、拣选、药浸和连续生产支出。", "先保中段不停顿，再安排非关键付款。")
            equipment = _row(lp["role_equipment"], "优先保装窑、出窑、叉车和中段传递设备。", "先修影响中段节拍的设备问题。")
            office = _row(lp["role_office"], "优先盯交班、统计、沟通和现场协调。", "确保中段信息和计划别断档。")
        if saw_gap < 0 and saw_idle:
            equipment["action"] += " 同时追带锯为何没开满。"
        if secondary_gap < 0:
            hr["action"] += " 二选持续差目标时要同步复核人手与设备。"
        if forecast_risk:
            office["summary"] += f" 明日主风险是「{forecast_risk}」。"
        summary = f"当前应围绕「{root_name}」协同发力，现场压力主要显示在「{pressure_name}」。"

    rows = [hr, finance, equipment, office]
    return {
        "title": lp["collab_title"],
        "summary": summary,
        "rows": rows,
    }


def build_period_review(report: dict, previous_report: dict | None = None, lang: str = "zh") -> dict[str, Any]:
    lp = _lang_pack(lang)
    report = report if isinstance(report, dict) else {}
    previous_report = previous_report if isinstance(previous_report, dict) else {}
    summary = report.get("summary", {}) if isinstance(report.get("summary"), dict) else {}
    prev_summary = previous_report.get("summary", {}) if isinstance(previous_report.get("summary"), dict) else {}

    current_finished_m3 = _safe_float(summary.get("finished_m3"), 0.0)
    prev_finished_m3 = _safe_float(prev_summary.get("finished_m3"), 0.0)
    current_finished_pcs = _safe_float(summary.get("finished_pcs"), 0.0)
    prev_finished_pcs = _safe_float(prev_summary.get("finished_pcs"), 0.0)
    current_saw = _safe_float(summary.get("saw_output_trays"), 0.0)
    prev_saw = _safe_float(prev_summary.get("saw_output_trays"), 0.0)
    current_sort = _safe_float(summary.get("sort_trays"), 0.0)
    prev_sort = _safe_float(prev_summary.get("sort_trays"), 0.0)

    deltas = [
        {"key": "finished_m3", "label": "成品m3", "delta": round(current_finished_m3 - prev_finished_m3, 1)},
        {"key": "finished_pcs", "label": "成品件数", "delta": round(current_finished_pcs - prev_finished_pcs, 1)},
        {"key": "saw_output_trays", "label": "锯解托数", "delta": round(current_saw - prev_saw, 1)},
        {"key": "sort_trays", "label": "拣选托数", "delta": round(current_sort - prev_sort, 1)},
    ]
    lag = min(deltas, key=lambda item: item["delta"]) if deltas else {"label": "-", "delta": 0.0}
    lead = max(deltas, key=lambda item: item["delta"]) if deltas else {"label": "-", "delta": 0.0}

    if not previous_report:
        summary_text = lp["review_no_prev"]
    elif current_finished_m3 >= prev_finished_m3:
        summary_text = lp["review_improved"]
    else:
        summary_text = lp["review_declined"]

    actions = [
        lp["review_action_1"].format(label=lag["label"], delta=lag["delta"]),
        lp["review_action_2"].format(label=lead["label"]),
        lp["review_action_3"].format(m3=current_finished_m3, pcs=int(current_finished_pcs)),
    ]

    return {
        "title": lp["review_title"],
        "summary": summary_text,
        "lead_metric": lead,
        "lag_metric": lag,
        "actions": actions,
    }
