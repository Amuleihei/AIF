from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any
from uuid import uuid4

from modules.finance.cost_engine import load as load_cost, save as save_cost
from modules.finance.finance_engine import expense, income, load as load_finance, save as save_finance, transfer
from modules.hr.hr_engine import get_hr_payroll_preview
from modules.storage.db_doc_store import load_doc, save_doc


FINANCE_ACCOUNTS = [
    {"value": "cash", "label_zh": "现金账户", "label_en": "Cash Account", "label_my": "ငွေသားအကောင့်"},
    {"value": "bank", "label_zh": "银行账户", "label_en": "Bank Account", "label_my": "ဘဏ်အကောင့်"},
]

FINANCE_CATEGORIES = [
    {"value": "sales_income", "type": "income", "label_zh": "销售回款", "label_en": "Sales Income", "label_my": "အရောင်းဝင်ငွေ"},
    {"value": "other_income", "type": "income", "label_zh": "其他收入", "label_en": "Other Income", "label_my": "အခြားဝင်ငွေ"},
    {"value": "raw_material", "type": "expense", "label_zh": "原木采购", "label_en": "Raw Material", "label_my": "ကုန်ကြမ်းဝယ်ယူမှု"},
    {"value": "chemicals", "type": "expense", "label_zh": "药剂辅料", "label_en": "Chemicals", "label_my": "ဆေးနှင့် အထောက်အပံ့ပစ္စည်း"},
    {"value": "labor", "type": "expense", "label_zh": "人工工资", "label_en": "Labor", "label_my": "လုပ်သားခ"},
    {"value": "energy", "type": "expense", "label_zh": "能源锅炉", "label_en": "Energy", "label_my": "စွမ်းအင်"},
    {"value": "maintenance", "type": "expense", "label_zh": "设备维修", "label_en": "Maintenance", "label_my": "စက်ပြုပြင်ထိန်းသိမ်း"},
    {"value": "logistics", "type": "expense", "label_zh": "物流发运", "label_en": "Logistics", "label_my": "ပို့ဆောင်ရေး"},
    {"value": "office", "type": "expense", "label_zh": "办公室费用", "label_en": "Office Expense", "label_my": "ရုံးအသုံးစရိတ်"},
    {"value": "security", "type": "expense", "label_zh": "安保后勤", "label_en": "Security & Support", "label_my": "လုံခြုံရေးနှင့် အထောက်အပံ့"},
    {"value": "other_expense", "type": "expense", "label_zh": "其他支出", "label_en": "Other Expense", "label_my": "အခြားအသုံးစရိတ်"},
]
PAYROLL_BATCH_DOC_KEY = "finance_payroll_batches_v1"
ARAP_DOC_KEY = "finance_arap_v1"


def _pack(lang: str) -> str:
    lc = str(lang or "zh").strip().lower()
    return lc if lc in ("zh", "en", "my") else "zh"


def _label(item: dict[str, Any], lang: str) -> str:
    lc = _pack(lang)
    if lc == "en":
        return str(item.get("label_en") or item.get("label_zh") or item.get("value") or "")
    if lc == "my":
        return str(item.get("label_my") or item.get("label_zh") or item.get("value") or "")
    return str(item.get("label_zh") or item.get("value") or "")


def _category_map(lang: str) -> dict[str, str]:
    return {str(item["value"]): _label(item, lang) for item in FINANCE_CATEGORIES}


def _account_map(lang: str) -> dict[str, str]:
    return {str(item["value"]): _label(item, lang) for item in FINANCE_ACCOUNTS}


def _safe_float(v: Any, dv: float = 0.0) -> float:
    try:
        return float(v)
    except Exception:
        return dv


def _parse_iso(ts: str) -> datetime | None:
    try:
        return datetime.fromisoformat(str(ts or ""))
    except Exception:
        return None


def _date_span(mode: str) -> tuple[datetime, datetime]:
    now = datetime.now()
    if mode == "month":
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end = now
        return start, end
    if mode == "week":
        start = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
        end = now
        return start, end
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return start, now


def _compute_flow(records: list[dict[str, Any]], mode: str) -> dict[str, float]:
    start, end = _date_span(mode)
    income_total = 0.0
    expense_total = 0.0
    transfer_total = 0.0
    for row in records:
        if not isinstance(row, dict):
            continue
        dt = _parse_iso(str(row.get("time") or ""))
        if not dt or dt < start or dt > end:
            continue
        typ = str(row.get("type") or "").strip()
        amt = _safe_float(row.get("amount"), 0.0)
        if typ == "income":
            income_total += amt
        elif typ == "expense":
            expense_total += amt
        elif typ == "transfer":
            transfer_total += amt
    return {
        "income": round(income_total, 2),
        "expense": round(expense_total, 2),
        "net": round(income_total - expense_total, 2),
        "transfer": round(transfer_total, 2),
    }


def _load_payroll_batches() -> list[dict[str, Any]]:
    data = load_doc(PAYROLL_BATCH_DOC_KEY, default=[], legacy_file=None)
    return data if isinstance(data, list) else []


def _save_payroll_batches(rows: list[dict[str, Any]]) -> None:
    save_doc(PAYROLL_BATCH_DOC_KEY, rows if isinstance(rows, list) else [])


def _load_arap_items() -> list[dict[str, Any]]:
    data = load_doc(ARAP_DOC_KEY, default=[], legacy_file=None)
    return data if isinstance(data, list) else []


def _save_arap_items(rows: list[dict[str, Any]]) -> None:
    save_doc(ARAP_DOC_KEY, rows if isinstance(rows, list) else [])


def _filter_records(
    records: list[dict[str, Any]],
    *,
    date_from: str = "",
    date_to: str = "",
    record_type: str = "",
    account: str = "",
    keyword: str = "",
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    begin = datetime.fromisoformat(f"{date_from}T00:00:00") if date_from else None
    end = datetime.fromisoformat(f"{date_to}T23:59:59") if date_to else None
    kw = str(keyword or "").strip().lower()
    for row in records:
        if not isinstance(row, dict):
            continue
        dt = _parse_iso(str(row.get("time") or ""))
        if begin and (not dt or dt < begin):
            continue
        if end and (not dt or dt > end):
            continue
        if record_type and str(row.get("type") or "").strip() != record_type:
            continue
        row_account = str(row.get("account") or "").strip()
        if account:
            if account not in row_account.split("->"):
                continue
        if kw:
            blob = " ".join(
                [
                    str(row.get("note") or ""),
                    str(row.get("ref_no") or ""),
                    str(row.get("category") or ""),
                    row_account,
                ]
            ).lower()
            if kw not in blob:
                continue
        out.append(row)
    return out


def _recent_payroll_batches(lang: str, limit: int = 12) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in sorted((r for r in _load_payroll_batches() if isinstance(r, dict)), key=lambda x: str(x.get("posted_at") or ""), reverse=True)[:limit]:
        item = dict(row)
        item["account_label"] = _account_map(lang).get(str(item.get("account") or ""), str(item.get("account") or "-"))
        item["posted_at_text"] = str(item.get("posted_at") or "").replace("T", " ")[:16]
        out.append(item)
    return out


def _recent_records(records: list[dict[str, Any]], lang: str, limit: int = 18) -> list[dict[str, Any]]:
    category_map = _category_map(lang)
    account_map = _account_map(lang)
    out: list[dict[str, Any]] = []
    for row in sorted((r for r in records if isinstance(r, dict)), key=lambda x: str(x.get("time") or ""), reverse=True)[:limit]:
        item = dict(row)
        item["category_label"] = category_map.get(str(item.get("category") or ""), str(item.get("category") or "-"))
        account = str(item.get("account") or "")
        if "->" in account:
            src, dst = account.split("->", 1)
            item["account_label"] = f"{account_map.get(src, src)} -> {account_map.get(dst, dst)}"
        else:
            item["account_label"] = account_map.get(account, account or "-")
        item["time_text"] = str(item.get("time") or "").replace("T", " ")[:16]
        out.append(item)
    return out


def _expense_breakdown(records: list[dict[str, Any]], lang: str, limit: int = 6) -> list[dict[str, Any]]:
    start, end = _date_span("month")
    category_map = _category_map(lang)
    bucket: dict[str, float] = {}
    for row in records:
        if not isinstance(row, dict) or str(row.get("type") or "") != "expense":
            continue
        dt = _parse_iso(str(row.get("time") or ""))
        if not dt or dt < start or dt > end:
            continue
        key = str(row.get("category") or "other_expense")
        bucket[key] = bucket.get(key, 0.0) + _safe_float(row.get("amount"), 0.0)
    out = [{"category": k, "label": category_map.get(k, k), "amount": round(v, 2)} for k, v in bucket.items()]
    out.sort(key=lambda x: x["amount"], reverse=True)
    return out[:limit]


def _ar_item_title(kind: str, lang: str) -> str:
    lc = _pack(lang)
    if str(kind) == "receivable":
        return {"zh": "应收", "en": "Receivable", "my": "ရရန်ငွေ"}[lc]
    return {"zh": "应付", "en": "Payable", "my": "ပေးရန်ငွေ"}[lc]


def _open_arap_snapshot(lang: str) -> dict[str, Any]:
    rows = _load_arap_items()
    out_rows: list[dict[str, Any]] = []
    totals = {"receivable": 0.0, "payable": 0.0}
    for row in rows:
        if not isinstance(row, dict):
            continue
        amount = round(_safe_float(row.get("amount"), 0.0), 2)
        settled = round(_safe_float(row.get("settled_amount"), 0.0), 2)
        remaining = round(max(0.0, amount - settled), 2)
        status = str(row.get("status") or "open").strip() or "open"
        if remaining <= 0 and status != "paid":
            status = "paid"
        item = dict(row)
        item["amount"] = amount
        item["settled_amount"] = settled
        item["remaining_amount"] = remaining
        item["title"] = _ar_item_title(str(row.get("kind") or ""), lang)
        item["created_at_text"] = str(item.get("created_at") or "").replace("T", " ")[:16]
        item["updated_at_text"] = str(item.get("updated_at") or "").replace("T", " ")[:16]
        out_rows.append(item)
        if remaining > 0:
            kind = str(item.get("kind") or "")
            totals[kind] = round(totals.get(kind, 0.0) + remaining, 2)
    open_items = [row for row in out_rows if float(row.get("remaining_amount", 0)) > 0]
    open_items.sort(key=lambda x: (str(x.get("due_date") or "9999-12-31"), str(x.get("created_at") or "")))
    return {
        "all": out_rows,
        "open": open_items,
        "receivable_open_total": totals["receivable"],
        "payable_open_total": totals["payable"],
    }


def _month_close_summary(records: list[dict[str, Any]], costs: dict[str, Any], arap: dict[str, Any], lang: str) -> dict[str, Any]:
    month = _compute_flow(records, "month")
    recv = round(_safe_float(arap.get("receivable_open_total"), 0.0), 2)
    pay = round(_safe_float(arap.get("payable_open_total"), 0.0), 2)
    total_cost = round(_safe_float((costs or {}).get("total"), 0.0), 2)
    operating_margin = round(month.get("income", 0.0) - total_cost, 2)
    projected = round(month.get("net", 0.0) + recv - pay, 2)
    lc = _pack(lang)
    if lc == "en":
        summary = f"This month net cashflow is {month['net']:.2f} KS, open receivables {recv:.2f} KS, and open payables {pay:.2f} KS."
        advice = [
            "Collect overdue receivables before expanding non-critical spending." if recv > pay else "Keep payables aligned with production-critical vendors first.",
            f"Tracked costs this month are {total_cost:.2f} KS; operating spread is {operating_margin:.2f} KS.",
            f"Projected close position is {projected:.2f} KS after open receivables and payables.",
        ]
    elif lc == "my":
        summary = f"ဒီလ net cashflow {month['net']:.2f} KS၊ ရရန်ငွေ {recv:.2f} KS နှင့် ပေးရန်ငွေ {pay:.2f} KS ရှိပါသည်။"
        advice = [
            "မဖြစ်မနေမဟုတ်သော အသုံးစရိတ်မတိုးခင် overdue ရရန်ငွေကို အရင်သိမ်းပါ။" if recv > pay else "ပေးရန်ငွေကို ထုတ်လုပ်မှုအရေးကြီးသော vendor များအတွက် အရင်ကိုက်ညီအောင် ထားပါ။",
            f"ဒီလ tracked cost {total_cost:.2f} KS ဖြစ်ပြီး operating spread {operating_margin:.2f} KS ဖြစ်ပါသည်။",
            f"ရရန်ငွေ၊ ပေးရန်ငွေ ထည့်တွက်ပါက projected close position {projected:.2f} KS ဖြစ်ပါသည်။",
        ]
    else:
        summary = f"本月净现金流 {month['net']:.2f} KS，未收回款 {recv:.2f} KS，未付账款 {pay:.2f} KS。"
        advice = [
            "如果未收大于未付，先催回应收，再放宽非关键支出。" if recv > pay else "如果未付压力更大，先保证生产关键供应商的付款节奏。",
            f"本月已记录成本 {total_cost:.2f} KS，经营价差 {operating_margin:.2f} KS。",
            f"把未收和未付一起算进去，月结预估头寸约 {projected:.2f} KS。",
        ]
    return {
        "summary": summary,
        "month_income": round(month.get("income", 0.0), 2),
        "month_expense": round(month.get("expense", 0.0), 2),
        "month_net": round(month.get("net", 0.0), 2),
        "open_receivable": recv,
        "open_payable": pay,
        "cost_total": total_cost,
        "operating_margin": operating_margin,
        "projected_close": projected,
        "advice": advice[:3],
    }


def _build_finance_ai(factory_intelligence: dict, records: list[dict[str, Any]], balances: dict[str, float], cost_data: dict[str, Any], lang: str) -> dict[str, Any]:
    lc = _pack(lang)
    root = (factory_intelligence or {}).get("root_bottleneck", {}) if isinstance(factory_intelligence, dict) else {}
    root_name = str(root.get("name") or "").strip()
    root_reason = str(root.get("reason") or "").strip()
    today_flow = _compute_flow(records, "day")
    month_flow = _compute_flow(records, "month")
    cash = round(_safe_float(balances.get("cash"), 0.0), 2)
    bank = round(_safe_float(balances.get("bank"), 0.0), 2)
    total_funds = round(cash + bank, 2)
    top_cost_key = max(cost_data, key=lambda k: _safe_float(cost_data.get(k), 0.0)) if isinstance(cost_data, dict) and cost_data else "raw_material"
    top_cost_val = _safe_float(cost_data.get(top_cost_key), 0.0) if isinstance(cost_data, dict) else 0.0
    top_cost_label = {
        "raw_material": {"zh": "原料", "en": "raw material", "my": "ကုန်ကြမ်း"},
        "labor": {"zh": "人工", "en": "labor", "my": "လုပ်သားခ"},
        "energy": {"zh": "能源", "en": "energy", "my": "စွမ်းအင်"},
    }.get(top_cost_key, {"zh": top_cost_key, "en": top_cost_key, "my": top_cost_key})

    if lc == "en":
        summary = f"Available funds are {total_funds:.2f} KS, with today's net cashflow at {today_flow['net']:.2f} KS."
        if "Back" in root_name or "后段" in root_name:
            support = f"The plant's current improvement priority is {root_name}, so finance should back secondary sorting, finished push, shipping, and critical overtime first."
        elif "Middle" in root_name or "中段" in root_name:
            support = f"The plant's current improvement priority is {root_name}, so finance should prioritize kiln loading, dipping, sorting handoff, and operating continuity."
        elif "Front" in root_name or "前段" in root_name:
            support = f"The plant's current improvement priority is {root_name}, so finance should first protect raw-material purchases, upstream transport, and fuel or chemical supply."
        else:
            support = "Finance should keep resources aligned with the plant's current improvement priority."
        risks = []
        if total_funds <= 0:
            risks.append("Current available funds are empty, so payment support may block operations.")
        if month_flow["expense"] > month_flow["income"] and month_flow["expense"] > 0:
            risks.append("This month's expenses are higher than income, so cash discipline needs attention.")
        if top_cost_val > 0:
            risks.append(f"The largest tracked cost bucket is {top_cost_label['en']} at {top_cost_val:.2f}.")
        actions = [support]
        actions.append(f"Use finance to back the current improvement priority: {root_reason or 'keep funding matched to the stage that needs lifting most.'}")
        if month_flow["expense"] > month_flow["income"]:
            actions.append("Delay non-critical spending and keep payments focused on production-critical items.")
        return {"summary": summary, "support": support, "risks": risks[:3], "actions": actions[:3]}

    if lc == "my":
        summary = f"လက်ရှိသုံးနိုင်သောငွေ {total_funds:.2f} KS ရှိပြီး ဒီနေ့ net cashflow မှာ {today_flow['net']:.2f} KS ဖြစ်ပါသည်။"
        if "Back" in root_name or "后段" in root_name:
            support = f"စက်ရုံရဲ့ လက်ရှိတိုးမြှင့်ဦးစားပေးအပိုင်းမှာ {root_name} ဖြစ်သောကြောင့် ဘဏ္ဍာရေးက ဒုတိယရွေး၊ ကုန်ချောတင်ဆက်မှု၊ ပို့ဆောင်ရေး နှင့် အဓိက overtime ကို အရင်ထောက်ပံ့သင့်ပါသည်။"
        elif "Middle" in root_name or "中段" in root_name:
            support = f"စက်ရုံရဲ့ လက်ရှိတိုးမြှင့်ဦးစားပေးအပိုင်းမှာ {root_name} ဖြစ်သောကြောင့် ဘဏ္ဍာရေးက မီးဖိုတင်ခြင်း၊ ဆေးစိမ်၊ ရွေးချယ်မှု handoff နှင့် လည်ပတ်မှုမပြတ်စေရန် အရင်ထောက်ပံ့သင့်ပါသည်။"
        elif "Front" in root_name or "前段" in root_name:
            support = f"စက်ရုံရဲ့ လက်ရှိတိုးမြှင့်ဦးစားပေးအပိုင်းမှာ {root_name} ဖြစ်သောကြောင့် ဘဏ္ဍာရေးက ကုန်ကြမ်းဝယ်ယူမှု၊ upstream ပို့ဆောင်မှု နှင့် fuel/chemical supply ကို အရင်ကာကွယ်သင့်ပါသည်။"
        else:
            support = "ဘဏ္ဍာရေးက စက်ရုံရဲ့ လက်ရှိတိုးမြှင့်ဦးစားပေးအပိုင်းနဲ့ ကိုက်ညီအောင် ငွေကြေးထောက်ပံ့မှုကို ညှိသင့်ပါသည်။"
        risks = []
        if total_funds <= 0:
            risks.append("လက်ရှိသုံးနိုင်သောငွေ မရှိတော့သဖြင့် လုပ်ငန်းထောက်ပံ့မှု ပိတ်မိနိုင်ပါသည်။")
        if month_flow["expense"] > month_flow["income"] and month_flow["expense"] > 0:
            risks.append("ဒီလ အသုံးစရိတ်က ဝင်ငွေထက်များနေသဖြင့် cash discipline ကို စောင့်ကြည့်သင့်ပါသည်။")
        if top_cost_val > 0:
            risks.append(f"လက်ရှိအများဆုံး tracked cost မှာ {top_cost_label['my']} {top_cost_val:.2f} ဖြစ်ပါသည်။")
        actions = [support]
        actions.append(f"ဘဏ္ဍာရေးလုပ်ဆောင်ချက်ကို လက်ရှိတိုးမြှင့်ဦးစားပေးအပိုင်းနဲ့ တိုက်ရိုက်ချိတ်ပါ: {root_reason or 'အရင်ဆွဲတင်ရမည့်အပိုင်းကို ပိုမိုထောက်ပံ့ပါ။'}")
        if month_flow["expense"] > month_flow["income"]:
            actions.append("မဖြစ်မနေမဟုတ်သော အသုံးစရိတ်များကို နောက်ဆုတ်ပြီး ထုတ်လုပ်မှုအရေးကြီးသော အရာများကိုသာ ဦးစားပေးပါ။")
        return {"summary": summary, "support": support, "risks": risks[:3], "actions": actions[:3]}

    summary = f"当前可动用资金 {total_funds:.2f} KS，今日净现金流 {today_flow['net']:.2f} KS。"
    if "后段" in root_name or "Back" in root_name:
        support = f"当前工厂最该优先提升的环节更像在「{root_name}」，财务应优先保障二选、成品推进、发运和关键加班，不要把钱分散到次要事项。"
    elif "中段" in root_name or "Middle" in root_name:
        support = f"当前工厂最该优先提升的环节更像在「{root_name}」，财务应优先保障装窑、药浸、拣选衔接和中段连续运转。"
    elif "前段" in root_name or "Front" in root_name:
        support = f"当前工厂最该优先提升的环节更像在「{root_name}」，财务应先保原木采购、前段转运、燃料和药剂供应。"
    else:
        support = "财务要围绕当前工厂提升重点配资金，先保关键线，再控非关键支出。"
    risks = []
    if total_funds <= 0:
        risks.append("当前可动用资金接近 0，后续采购和现场支撑容易卡死。")
    if month_flow["expense"] > month_flow["income"] and month_flow["expense"] > 0:
        risks.append("本月支出已高于收入，现金压力开始抬头。")
    if top_cost_val > 0:
        risks.append(f"当前累计成本里，「{top_cost_label['zh']}」最高，已到 {top_cost_val:.2f}。")
    actions = [support]
    actions.append(f"财务动作要直接支撑当前提升重点：{root_reason or '先把钱投到最该拉升的环节。'}")
    if month_flow["expense"] > month_flow["income"]:
        actions.append("非关键支出先压住，把可用资金优先投向当前提升重点和连续生产。")
    return {"summary": summary, "support": support, "risks": risks[:3], "actions": actions[:3]}


def get_finance_dashboard_payload(
    lang: str = "zh",
    factory_intelligence: dict | None = None,
    *,
    date_from: str = "",
    date_to: str = "",
    record_type: str = "",
    account: str = "",
    keyword: str = "",
) -> dict[str, Any]:
    lang = _pack(lang)
    fin = load_finance()
    cost = load_cost()
    accounts = fin.get("accounts", {}) if isinstance(fin.get("accounts"), dict) else {}
    records = fin.get("records", []) if isinstance(fin.get("records"), list) else []

    filtered_records = _filter_records(
        records,
        date_from=date_from,
        date_to=date_to,
        record_type=record_type,
        account=account,
        keyword=keyword,
    )
    payload = {
        "accounts": {
            "cash": round(_safe_float(accounts.get("cash"), 0.0), 2),
            "bank": round(_safe_float(accounts.get("bank"), 0.0), 2),
            "total": round(_safe_float(accounts.get("cash"), 0.0) + _safe_float(accounts.get("bank"), 0.0), 2),
        },
        "today": _compute_flow(records, "day"),
        "week": _compute_flow(records, "week"),
        "month": _compute_flow(records, "month"),
        "recent_records": _recent_records(filtered_records, lang),
        "expense_breakdown": _expense_breakdown(records, lang),
        "payroll_batches": _recent_payroll_batches(lang),
        "costs": {
            "raw_material": round(_safe_float(cost.get("raw_material"), 0.0), 2),
            "labor": round(_safe_float(cost.get("labor"), 0.0), 2),
            "energy": round(_safe_float(cost.get("energy"), 0.0), 2),
            "total": round(_safe_float(cost.get("raw_material"), 0.0) + _safe_float(cost.get("labor"), 0.0) + _safe_float(cost.get("energy"), 0.0), 2),
        },
        "account_choices": [{"value": item["value"], "label": _label(item, lang)} for item in FINANCE_ACCOUNTS],
        "income_categories": [{"value": item["value"], "label": _label(item, lang)} for item in FINANCE_CATEGORIES if item.get("type") == "income"],
        "expense_categories": [{"value": item["value"], "label": _label(item, lang)} for item in FINANCE_CATEGORIES if item.get("type") == "expense"],
        "category_label_map": _category_map(lang),
        "account_label_map": _account_map(lang),
        "record_filter": {
            "date_from": date_from,
            "date_to": date_to,
            "record_type": record_type,
            "account": account,
            "keyword": keyword,
        },
    }
    arap = _open_arap_snapshot(lang)
    payload["arap"] = arap
    payload["month_close"] = _month_close_summary(records, payload["costs"], arap, lang)
    payload["ai_finance"] = _build_finance_ai(factory_intelligence or {}, records, payload["accounts"], payload["costs"], lang)
    return payload


def apply_finance_form(action: str, form: dict[str, Any], operator: str = "") -> tuple[bool, str]:
    fin = load_finance()
    cost = load_cost()
    act = str(action or "").strip().lower()
    amount = max(0.0, _safe_float(form.get("amount"), 0.0))
    note = str(form.get("note") or "").strip()
    ref_no = str(form.get("ref_no") or "").strip()
    category = str(form.get("category") or "").strip()
    account = str(form.get("account") or "cash").strip() or "cash"

    if act in ("income", "expense") and amount <= 0:
        return False, "❌ 金额必须大于 0"
    if act in ("income", "expense") and not note:
        return False, "❌ 备注不能为空"

    if act == "income":
        msg = income(fin, amount, note, account=account, category=category, ref_no=ref_no, operator=operator)
        save_finance(fin)
        return True, msg
    if act == "expense":
        msg = expense(fin, amount, note, account=account, category=category, ref_no=ref_no, operator=operator)
        if str(msg).startswith("❌"):
            return False, msg
        save_finance(fin)
        return True, msg
    if act == "transfer":
        src = str(form.get("src_account") or "cash").strip() or "cash"
        dst = str(form.get("dst_account") or "bank").strip() or "bank"
        if src == dst:
            return False, "❌ 转出与转入账户不能相同"
        if amount <= 0:
            return False, "❌ 转账金额必须大于 0"
        msg = transfer(fin, amount, src, dst, note=note, ref_no=ref_no, operator=operator)
        if str(msg).startswith("❌"):
            return False, msg
        save_finance(fin)
        return True, msg
    if act == "cost":
        cost_key = str(form.get("cost_key") or "").strip()
        if cost_key not in ("raw_material", "labor", "energy"):
            return False, "❌ 成本类型错误"
        if amount <= 0:
            return False, "❌ 成本金額必须大于 0"
        cost[cost_key] = round(_safe_float(cost.get(cost_key), 0.0) + amount, 2)
        save_cost(cost)
        sync_expense = str(form.get("sync_expense") or "").strip() in ("1", "true", "on", "yes")
        if sync_expense:
            msg = expense(fin, amount, note or f"成本入账:{cost_key}", account=account, category=category or cost_key, ref_no=ref_no, operator=operator)
            if str(msg).startswith("❌"):
                return False, msg
            save_finance(fin)
            return True, f"✅ 成本已记录，并同步支出 {amount:.2f} KS"
        return True, f"✅ 成本已记录 {amount:.2f} KS"
    if act in ("receivable_add", "payable_add"):
        kind = "receivable" if act == "receivable_add" else "payable"
        party = str(form.get("party") or "").strip()
        due_date = str(form.get("due_date") or "").strip()
        if amount <= 0:
            return False, "❌ 金额必须大于 0"
        if not party:
            return False, "❌ 往来单位不能为空"
        items = _load_arap_items()
        item = {
            "id": uuid4().hex[:12],
            "kind": kind,
            "party": party,
            "amount": round(amount, 2),
            "settled_amount": 0.0,
            "status": "open",
            "due_date": due_date,
            "ref_no": ref_no,
            "note": note,
            "operator": operator,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
        items.append(item)
        _save_arap_items(items[-400:])
        return True, f"✅ {_ar_item_title(kind, 'zh')}已登记：{party} {amount:.2f} KS"
    if act in ("receivable_settle", "payable_settle"):
        kind = "receivable" if act == "receivable_settle" else "payable"
        item_id = str(form.get("item_id") or "").strip()
        settle_amount = max(0.0, _safe_float(form.get("settle_amount"), 0.0))
        settle_account = str(form.get("settle_account") or "cash").strip() or "cash"
        settle_note = str(form.get("settle_note") or "").strip()
        items = _load_arap_items()
        row = next((item for item in items if isinstance(item, dict) and str(item.get("id") or "") == item_id and str(item.get("kind") or "") == kind), None)
        if not row:
            return False, "❌ 往来项目不存在"
        remaining = round(max(0.0, _safe_float(row.get("amount"), 0.0) - _safe_float(row.get("settled_amount"), 0.0)), 2)
        if settle_amount <= 0:
            return False, "❌ 结清金额必须大于 0"
        if settle_amount > remaining:
            return False, "❌ 结清金额不能大于未结金额"
        base_note = settle_note or str(row.get("note") or "").strip() or str(row.get("party") or "").strip()
        if kind == "receivable":
            msg = income(fin, settle_amount, f"应收回款 | {base_note}", account=settle_account, category="sales_income", ref_no=str(row.get("ref_no") or row.get("id") or ""), operator=operator)
        else:
            msg = expense(fin, settle_amount, f"应付付款 | {base_note}", account=settle_account, category="other_expense", ref_no=str(row.get("ref_no") or row.get("id") or ""), operator=operator)
        if str(msg).startswith("❌"):
            return False, msg
        row["settled_amount"] = round(_safe_float(row.get("settled_amount"), 0.0) + settle_amount, 2)
        row["status"] = "paid" if row["settled_amount"] >= _safe_float(row.get("amount"), 0.0) else "partial"
        row["updated_at"] = datetime.now().isoformat()
        row["settled_at"] = datetime.now().isoformat() if row["status"] == "paid" else row.get("settled_at")
        save_finance(fin)
        _save_arap_items(items[-400:])
        return True, f"✅ {_ar_item_title(kind, 'zh')}已结清 {settle_amount:.2f} KS"
    return False, "❌ 未知财务操作"


def post_payroll_to_finance(
    *,
    asof: str,
    name: str = "",
    account: str = "cash",
    operator: str = "",
    batch_ref: str = "",
    note: str = "",
) -> tuple[bool, str]:
    preview = get_hr_payroll_preview(asof=asof, name=name)
    rows = preview.get("rows", []) if isinstance(preview.get("rows"), list) else []
    rows = [row for row in rows if isinstance(row, dict) and _safe_float(row.get("net"), 0.0) > 0]
    if not rows:
        return False, "❌ 当前工资试算没有可入账数据"

    final_asof = str(preview.get("asof") or asof or "").strip()
    scope = str(name or "ALL").strip() or "ALL"
    ref = str(batch_ref or "").strip() or f"PAYROLL-{final_asof}-{scope}"
    batches = _load_payroll_batches()
    for batch in batches:
        if not isinstance(batch, dict):
            continue
        if str(batch.get("batch_ref") or "").strip() == ref:
            return False, f"❌ 发薪批次已存在: {ref}"
        if str(batch.get("asof") or "").strip() == final_asof and str(batch.get("scope") or "").strip() == scope:
            return False, f"❌ {final_asof} 的工资批次已入账，请勿重复发薪"

    fin = load_finance()
    records = fin.get("records", []) if isinstance(fin.get("records"), list) else []
    for row in records:
        if not isinstance(row, dict):
            continue
        row_ref = str(row.get("ref_no") or "").strip()
        if row_ref == ref or row_ref.startswith(f"{ref}:"):
            return False, f"❌ 发薪批次已存在: {ref}"

    total = 0.0
    for row in rows:
        emp_name = str(row.get("name") or "").strip() or "-"
        period = str(row.get("period") or final_asof).strip()
        net_amount = round(_safe_float(row.get("net"), 0.0), 2)
        if net_amount <= 0:
            continue
        line_note = str(note or "").strip()
        base_note = f"工资发放 {period} | {emp_name}"
        if line_note:
            base_note += f" | {line_note}"
        msg = expense(
            fin,
            net_amount,
            base_note,
            account=account,
            category="labor",
            ref_no=f"{ref}:{emp_name}",
            operator=operator,
        )
        if str(msg).startswith("❌"):
            return False, msg
        total += net_amount

    save_finance(fin)
    cost = load_cost()
    cost["labor"] = round(_safe_float(cost.get("labor"), 0.0) + total, 2)
    save_cost(cost)
    batches.append(
        {
            "batch_ref": ref,
            "asof": final_asof,
            "scope": scope,
            "employee_count": len(rows),
            "total_amount": round(total, 2),
            "account": account,
            "operator": operator,
            "note": note,
            "posted_at": datetime.now().isoformat(),
            "status": "posted",
        }
    )
    _save_payroll_batches(batches[-200:])
    return True, f"✅ 工资已入账，共 {len(rows)} 人，合计 {total:.2f} KS，批次 {ref}"
