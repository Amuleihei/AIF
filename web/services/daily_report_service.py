from __future__ import annotations

import os
import re
from datetime import datetime, date

from web.models import (
    Session,
    AdminAuditLog,
    LogEntry,
    SawRecord,
    DipRecord,
    SortRecord,
    TrayBatch,
    ProductBatch,
    ByproductRecord,
    FlowSecondSortRecord,
    InventoryProduct,
)
from web.i18n import LANGUAGES
from web.utils import get_stock_data

# 与 route_support 中口径一致，避免此服务层反向依赖路由层导致循环导入。
WASTE_SEGMENT_PRICE_PER_BAG_KS = 4000


def _report_labels(lang: str) -> dict:
    if lang == "en":
        return {
            "summary": {
                "log_in_mt": "Log In (MT)",
                "saw_log_consumed_mt": "Saw Consumed Logs (MT)",
                "saw_output_trays": "Saw Output Trays",
                "dip_cans": "Dip Runs",
                "dip_trays": "Dip Trays",
                "sort_trays": "Sort Trays",
                "kiln_load_trays": "Kiln Load Trays",
                "kiln_unload_trays": "Kiln Unload Trays",
                "secondary_trays": "Secondary Trays",
                "finished_pcs": "Finished PCS",
                "byproduct_bark_ks": "Bark Sales (Ks)",
                "byproduct_dust_bags_out": "Sawdust Sold (bags)",
                "byproduct_waste_segment_bags_out": "Waste Segment Sold (bags)",
            },
            "inventory_snapshot": {
                "log_stock_mt": "Log Stock (MT)",
                "saw_stock_tray": "Saw Stock (tray)",
                "dip_stock_tray": "Dip Stock (tray)",
                "sorting_stock_tray": "Pending Kiln Stock (tray)",
                "kiln_done_stock_tray": "Kiln Done Stock (tray)",
                "dust_bag_stock": "Sawdust Stock (bags)",
                "bark_stock_m3": "Bark Stock (m3)",
                "waste_segment_bag_stock": "Waste Segment Stock (bags)",
                "finished_product_count": "Finished Product Count",
                "finished_product_m3": "Finished Product Volume (m3)",
            },
            "breakdown": {
                "log_entries": "Log Entries",
                "saw_records": "Saw Records",
                "dip_records": "Dip Records",
                "sort_records": "Sort Records",
                "tray_batches": "Tray Batches",
                "product_batches": "Product Batches",
                "byproduct_records": "Byproduct Records",
            },
            "kiln_status": {
                "A": "Kiln A",
                "B": "Kiln B",
                "C": "Kiln C",
                "D": "Kiln D",
            },
            "yield_loss": {
                "saw_to_dip_output_rate_pct": "Saw->Dip Output Rate",
                "saw_to_dip_loss_rate_pct": "Saw->Dip Loss Rate",
                "dip_to_sort_output_rate_pct": "Dip->Sort Output Rate",
                "dip_to_sort_loss_rate_pct": "Dip->Sort Loss Rate",
                "sort_to_kiln_output_rate_pct": "Sort->Kiln Output Rate",
                "sort_to_kiln_loss_rate_pct": "Sort->Kiln Loss Rate",
                "secondary_to_finish_output_rate_pct": "Secondary->Finish Output Rate",
                "secondary_to_finish_loss_rate_pct": "Secondary->Finish Loss Rate",
                "finished_m3_per_log_mt": "Finished m3 / Saw MT",
            },
            "note": "kiln_unload_trays uses kiln unload logs; secondary_trays uses second_sort_records.",
        }
    if lang == "my":
        return {
            "summary": {
                "log_in_mt": "ထင်းဝင် (MT)",
                "saw_log_consumed_mt": "ခုတ်သုံး ထင်း (MT)",
                "saw_output_trays": "ခုတ်ထွက် ထပ်ခါး",
                "dip_cans": "ဆေးစိမ် ကြိမ်ရေ",
                "dip_trays": "ဆေးစိမ် ထပ်ခါး",
                "sort_trays": "ရွေးချယ် ထပ်ခါး",
                "kiln_load_trays": "မီးဖိုဝင် ထပ်ခါး",
                "kiln_unload_trays": "မီးဖိုထုတ် ထပ်ခါး",
                "secondary_trays": "ဒုတိယရွေး ထပ်ခါး",
                "finished_pcs": "ကုန်ချော အရေအတွက်",
                "byproduct_bark_ks": "ပေါက်ဖတ် ရောင်းရငွေ (Ks)",
                "byproduct_dust_bags_out": "ရောင်းပြီး အမှုန့် (အိတ်)",
                "byproduct_waste_segment_bags_out": "ရောင်းပြီး အလွှာအပိုင်း (အိတ်)",
            },
            "inventory_snapshot": {
                "log_stock_mt": "ထင်းစတော့ (MT)",
                "saw_stock_tray": "ခုတ်စတော့ (ထပ်ခါး)",
                "dip_stock_tray": "ဆေးစိမ်စတော့ (ထပ်ခါး)",
                "sorting_stock_tray": "မီးဖိုဝင်ရန်စတော့ (ထပ်ခါး)",
                "kiln_done_stock_tray": "မီးဖိုပြီးစတော့ (ထပ်ခါး)",
                "dust_bag_stock": "အမှုန့်စတော့ (အိတ်)",
                "bark_stock_m3": "ပေါက်ဖတ်စတော့ (m3)",
                "waste_segment_bag_stock": "အလွှာအပိုင်းစတော့ (အိတ်)",
                "finished_product_count": "ကုန်ချောစုစုပေါင်း",
                "finished_product_m3": "ကုန်ချောပမာဏ (m3)",
            },
            "breakdown": {
                "log_entries": "ထင်းဝင်စာရင်း",
                "saw_records": "ခုတ်မှတ်တမ်း",
                "dip_records": "ဆေးစိမ်မှတ်တမ်း",
                "sort_records": "ရွေးချယ်မှတ်တမ်း",
                "tray_batches": "ထပ်ခါး batch",
                "product_batches": "ကုန်ချော batch",
                "byproduct_records": "ဘေးထွက်မှတ်တမ်း",
            },
            "kiln_status": {
                "A": "မီးဖို A",
                "B": "မီးဖို B",
                "C": "မီးဖို C",
                "D": "မီးဖို D",
            },
            "yield_loss": {
                "saw_to_dip_output_rate_pct": "ခုတ်->ဆေးစိမ် ထွက်ရှိနှုန်း",
                "saw_to_dip_loss_rate_pct": "ခုတ်->ဆေးစိမ် ဆုံးရှုံးနှုန်း",
                "dip_to_sort_output_rate_pct": "ဆေးစိမ်->ရွေးချယ် ထွက်ရှိနှုန်း",
                "dip_to_sort_loss_rate_pct": "ဆေးစိမ်->ရွေးချယ် ဆုံးရှုံးနှုန်း",
                "sort_to_kiln_output_rate_pct": "ရွေးချယ်->မီးဖို ထွက်ရှိနှုန်း",
                "sort_to_kiln_loss_rate_pct": "ရွေးချယ်->မီးဖို ဆုံးရှုံးနှုန်း",
                "secondary_to_finish_output_rate_pct": "ဒုတိယရွေး->ကုန်ချော ထွက်ရှိနှုန်း",
                "secondary_to_finish_loss_rate_pct": "ဒုတိယရွေး->ကုန်ချော ဆုံးရှုံးနှုန်း",
                "finished_m3_per_log_mt": "ကုန်ချော m3 / ခုတ် MT",
            },
            "note": "kiln_unload_trays ကို kiln unload logs မှတွက်ပြီး secondary_trays ကို second_sort_records မှတွက်သည်။",
        }
    return {
        "summary": {
            "log_in_mt": "原木入库 (MT)",
            "saw_log_consumed_mt": "锯解消耗原木 (MT)",
            "saw_output_trays": "锯解产出锯托",
            "dip_cans": "药浸罐次",
            "dip_trays": "药浸托数",
            "sort_trays": "拣选托数",
            "kiln_load_trays": "入窑托数",
            "kiln_unload_trays": "出窑托数",
            "secondary_trays": "二选托数",
            "finished_pcs": "成品件数",
            "byproduct_bark_ks": "销售树皮 (Ks)",
            "byproduct_dust_bags_out": "销售木渣 (袋)",
            "byproduct_waste_segment_bags_out": "销售废木段 (袋)",
        },
        "inventory_snapshot": {
            "log_stock_mt": "原木库存 (MT)",
            "saw_stock_tray": "锯解库存 (托)",
            "dip_stock_tray": "药浸库存 (托)",
            "sorting_stock_tray": "待入窑库存 (托)",
            "kiln_done_stock_tray": "窑完成库存 (托)",
            "dust_bag_stock": "木渣库存 (袋)",
            "bark_stock_m3": "树皮库存 (m3)",
            "waste_segment_bag_stock": "废木段库存 (袋)",
            "finished_product_count": "成品总件数",
            "finished_product_m3": "成品总体积 (m3)",
        },
        "breakdown": {
            "log_entries": "原木入库记录",
            "saw_records": "锯解记录",
            "dip_records": "药浸记录",
            "sort_records": "拣选记录",
            "tray_batches": "窑托批次",
            "product_batches": "成品批次",
            "byproduct_records": "副产品记录",
        },
        "kiln_status": {
            "A": "A窑",
            "B": "B窑",
            "C": "C窑",
            "D": "D窑",
        },
        "yield_loss": {
            "saw_to_dip_output_rate_pct": "锯解->药浸 产出比",
            "saw_to_dip_loss_rate_pct": "锯解->药浸 损耗率",
            "dip_to_sort_output_rate_pct": "药浸->拣选 产出比",
            "dip_to_sort_loss_rate_pct": "药浸->拣选 损耗率",
            "sort_to_kiln_output_rate_pct": "拣选->入窑 产出比",
            "sort_to_kiln_loss_rate_pct": "拣选->入窑 损耗率",
            "secondary_to_finish_output_rate_pct": "二选->成品 产出比",
            "secondary_to_finish_loss_rate_pct": "二选->成品 损耗率",
            "finished_m3_per_log_mt": "成品体积 / 锯解原木",
        },
        "note": "出窑托数按出窑动作日志汇总；二选托数按二次拣选记录汇总。",
    }


def _safe_int(value, default=0) -> int:
    try:
        if value in (None, ""):
            return int(default)
        return int(float(value))
    except Exception:
        return int(default)


def _safe_float(value, default=0.0) -> float:
    try:
        if value in (None, ""):
            return float(default)
        return float(value)
    except Exception:
        return float(default)


def _ratio(numerator: float, denominator: float) -> float:
    den = _safe_float(denominator, 0.0)
    if den <= 0:
        return 0.0
    return _safe_float(numerator, 0.0) / den


def _daily_product_id_prefix(day_obj: date) -> str:
    return day_obj.strftime("%m%d-")


def _calc_one_piece_volume_from_spec(spec_text: str) -> float:
    text = str(spec_text or "").strip().lower().replace(" ", "")
    parts = [p for p in text.split("x") if p]
    if len(parts) != 3:
        return 0.0
    try:
        d, w, l = float(parts[0]), float(parts[1]), float(parts[2])
        if d <= 0 or w <= 0 or l <= 0:
            return 0.0
        return (d * w * l) / 1_000_000_000.0
    except Exception:
        return 0.0


def _derive_finished_from_daily_product_ids(session, day_obj: date) -> tuple[int, float]:
    """
    业务规则：一个成品编号=一件。
    日报成品件数优先按当天编号（MMDD-前缀）条数统计，避免历史误录件数影响日报。
    """
    prefix = _daily_product_id_prefix(day_obj)
    rows = (
        session.query(InventoryProduct.product_id, InventoryProduct.volume)
        .filter(InventoryProduct.product_id.like(f"{prefix}%"))
        .all()
    )
    if not rows:
        return 0, 0.0
    pcs = len(rows)
    m3 = 0.0
    for _, volume in rows:
        m3 += _safe_float(volume, 0.0)
    return pcs, m3


def _format_report_kiln_status(info: dict, lang_pack: dict, lang: str) -> str:
    if not isinstance(info, dict):
        return ""
    status = str(info.get("status", "") or "")
    status_display = str(info.get("status_display", "") or status or "")
    total = _safe_int(info.get("total_trays"), 0)
    remaining = _safe_int(info.get("remaining_trays"), 0)

    # 规则：烘干中只显示时间；其他状态显示托数。
    if status == "drying":
        elapsed = _safe_int(info.get("elapsed_hours"), 0)
        left = _safe_int(info.get("remaining_hours"), 0)
        tpl = str(lang_pack.get("drying_progress", "") or "")
        if "{elapsed}" in tpl and "{remaining}" in tpl:
            return f"{status_display} {tpl.format(elapsed=elapsed, remaining=left)}"
        if lang == "en":
            return f"{status_display} elapsed {elapsed}h remaining {left}h"
        if lang == "my":
            return f"{status_display} ကုန်လွန် {elapsed} နာရီ ကျန် {left} နာရီ"
        return f"{status_display} 已烘干{elapsed}小时 剩余{left}小时"

    total_label = str(lang_pack.get("total_trays", "总托数") or "总托数")
    remain_label = str(lang_pack.get("remaining_trays", "剩余") or "剩余")
    tray_unit = str(lang_pack.get("trays", "托") or "托")
    return f"{status_display} {total_label}{total} {remain_label}{remaining}{tray_unit}"


def _normalize_day(day_text: str | None) -> date:
    raw = str(day_text or "").strip()
    if not raw:
        return datetime.now().date()
    try:
        return datetime.strptime(raw, "%Y-%m-%d").date()
    except Exception:
        return datetime.now().date()


def _fetch_day_rows(session, model, day_str: str, time_field: str = "created_at"):
    col = getattr(model, time_field)
    return session.query(model).filter(col.like(f"{day_str}%")).all()


def _sum_daily_kiln_unload_trays_from_audit(session, day_str: str) -> int:
    rows = (
        session.query(AdminAuditLog.detail)
        .filter(AdminAuditLog.action == "kiln_action")
        .filter(AdminAuditLog.created_at.like(f"{day_str}%"))
        .filter(AdminAuditLog.detail.like("%action=unload%"))
        .all()
    )
    total = 0
    for row in rows:
        detail = str(getattr(row, "detail", "") or "")
        m = re.search(r"(?:^|,)count=(\d+)(?:,|$)", detail)
        if m:
            total += _safe_int(m.group(1), 0)
    return max(0, total)


def _sum_daily_secondary_sort_trays_from_audit(session, day_str: str) -> int:
    rows = (
        session.query(AdminAuditLog.detail)
        .filter(AdminAuditLog.action == "submit_secondary_sort")
        .filter(AdminAuditLog.created_at.like(f"{day_str}%"))
        .all()
    )
    total = 0
    for row in rows:
        detail = str(getattr(row, "detail", "") or "")
        m = re.search(r"(?:^|,)trays=(\d+)(?:,|$)", detail)
        if m:
            total += _safe_int(m.group(1), 0)
    return max(0, total)


def _daily_rolled_back_tray_batches_from_audit(session, day_str: str) -> set[str]:
    """
    识别当日被“回流待入窑”的入窑批次（manual_restore），用于日报排除失效入窑量。
    示例：rollback ... moved batch D202604020001 back to pending ...
    """
    rows = (
        session.query(AdminAuditLog.detail)
        .filter(AdminAuditLog.action == "manual_restore")
        .filter(AdminAuditLog.created_at.like(f"{day_str}%"))
        .filter(AdminAuditLog.detail.like("%moved batch%back to pending%"))
        .all()
    )
    out: set[str] = set()
    for row in rows:
        detail = str(getattr(row, "detail", "") or "")
        m = re.search(r"moved\s+batch\s+([A-Za-z][0-9]{8,})\s+back\s+to\s+pending", detail, re.I)
        if not m:
            continue
        out.add(str(m.group(1) or "").strip().upper())
    return out


def build_daily_report(day_text: str | None = None, lang: str = "zh") -> dict:
    day_obj = _normalize_day(day_text)
    day_str = day_obj.strftime("%Y-%m-%d")

    session = Session()
    try:
        log_rows = _fetch_day_rows(session, LogEntry, day_str)
        saw_rows = _fetch_day_rows(session, SawRecord, day_str)
        dip_rows = _fetch_day_rows(session, DipRecord, day_str)
        sort_rows = _fetch_day_rows(session, SortRecord, day_str)
        tray_rows = _fetch_day_rows(session, TrayBatch, day_str)
        product_rows = _fetch_day_rows(session, ProductBatch, day_str)
        byproduct_rows = _fetch_day_rows(session, ByproductRecord, day_str)
        second_sort_rows = _fetch_day_rows(session, FlowSecondSortRecord, day_str, time_field="time")
        kiln_unload_trays = _sum_daily_kiln_unload_trays_from_audit(session, day_str)
        secondary_trays_from_audit = _sum_daily_secondary_sort_trays_from_audit(session, day_str)
        rolled_back_tray_batches = _daily_rolled_back_tray_batches_from_audit(session, day_str)
        id_finished_pcs, id_finished_m3 = _derive_finished_from_daily_product_ids(session, day_obj)
    finally:
        session.close()

    if rolled_back_tray_batches:
        tray_rows = [
            r for r in tray_rows
            if str(getattr(r, "batch_number", "") or "").strip().upper() not in rolled_back_tray_batches
        ]

    log_in_mt = sum(_safe_float(r.log_amount) for r in log_rows)
    saw_log_consumed_mt = sum(_safe_float(r.saw_mt) for r in saw_rows)
    saw_output_trays = sum(_safe_int(r.saw_trays) for r in saw_rows)
    dip_cans = sum(_safe_int(r.dip_cans) for r in dip_rows)
    dip_trays = sum(_safe_int(r.dip_trays) for r in dip_rows)
    sort_trays = sum(_safe_int(r.sort_trays) for r in sort_rows)
    kiln_load_trays = sum(_safe_int(r.tray_count) for r in tray_rows)
    # 业务口径：成品件数按“当日成品编号条数”统计（一个编号=一件）。
    # 兼容：若当日编号无法推导（例如历史非日期编号），再回退批次汇总。
    finished_pcs = id_finished_pcs if id_finished_pcs > 0 else sum(_safe_int(r.product_count) for r in product_rows)
    finished_volume_m3 = id_finished_m3 if id_finished_m3 > 0 else sum(_safe_float(r.total_volume) for r in product_rows)

    secondary_trays = max(
        sum(_safe_int(r.trays) for r in second_sort_rows),
        _safe_int(secondary_trays_from_audit, 0),
    )

    sale_rows = [r for r in byproduct_rows if _safe_int(r.dust_bags_in, 0) == 0]
    byproduct_bark_ks = sum(_safe_float(r.bark_sale_amount) for r in sale_rows)
    byproduct_waste_segment_bags_out = sum(
        int(round(_safe_float(r.dust_sale_amount) / float(WASTE_SEGMENT_PRICE_PER_BAG_KS)))
        for r in sale_rows
    )
    byproduct_dust_bags_out = sum(
        max(0, _safe_int(r.dust_bags_out) - int(round(_safe_float(r.dust_sale_amount) / float(WASTE_SEGMENT_PRICE_PER_BAG_KS))))
        for r in sale_rows
    )

    stock = get_stock_data(lang=lang)
    labels = _report_labels(lang)
    snapshot = {
        "log_stock_mt": round(_safe_float(stock.get("log_stock")), 4),
        "saw_stock_tray": _safe_int(stock.get("saw_stock")),
        "dip_stock_tray": _safe_int(stock.get("dip_stock")),
        "sorting_stock_tray": _safe_int(stock.get("sorting_stock")),
        "kiln_done_stock_tray": _safe_int(stock.get("kiln_done_stock")),
        "dust_bag_stock": _safe_int(stock.get("dust_bag_stock")),
        "bark_stock_m3": round(_safe_float(stock.get("bark_stock_m3")), 3),
        "waste_segment_bag_stock": _safe_int(stock.get("waste_segment_bag_stock")),
        "finished_product_count": _safe_int(stock.get("product_count")),
        "finished_product_m3": round(_safe_float(stock.get("product_m3")), 3),
    }

    lang_pack = LANGUAGES.get(lang, LANGUAGES["zh"])
    summary_order = [
        "log_in_mt",
        "saw_log_consumed_mt",
        "saw_output_trays",
        "dip_cans",
        "dip_trays",
        "sort_trays",
        "kiln_load_trays",
        "kiln_unload_trays",
        "secondary_trays",
        "finished_pcs",
        "byproduct_bark_ks",
        "byproduct_dust_bags_out",
        "byproduct_waste_segment_bags_out",
    ]
    inventory_order = [
        "log_stock_mt",
        "saw_stock_tray",
        "dip_stock_tray",
        "sorting_stock_tray",
        "kiln_done_stock_tray",
        "finished_product_count",
        "finished_product_m3",
        "bark_stock_m3",
        "dust_bag_stock",
        "waste_segment_bag_stock",
    ]
    breakdown_order = [
        "log_entries",
        "saw_records",
        "dip_records",
        "sort_records",
        "tray_batches",
        "product_batches",
        "byproduct_records",
    ]
    yield_loss_enabled = str(os.getenv("AIF_ENABLE_YIELD_LOSS", "0") or "0").strip().lower() in ("1", "true", "yes", "on")
    yield_loss_order = [
        "saw_to_dip_output_rate_pct",
        "saw_to_dip_loss_rate_pct",
        "dip_to_sort_output_rate_pct",
        "dip_to_sort_loss_rate_pct",
        "sort_to_kiln_output_rate_pct",
        "sort_to_kiln_loss_rate_pct",
        "secondary_to_finish_output_rate_pct",
        "secondary_to_finish_loss_rate_pct",
        "finished_m3_per_log_mt",
    ]
    kiln_order = ["A", "B", "C", "D"]
    kiln_status = {}
    kiln_status_detail = {}
    kiln_map = stock.get("kiln_status", {}) if isinstance(stock.get("kiln_status"), dict) else {}
    for kid in kiln_order:
        info = kiln_map.get(kid, {}) if isinstance(kiln_map.get(kid), dict) else {}
        kiln_status[kid] = _format_report_kiln_status(info, lang_pack, lang)
        kiln_status_detail[kid] = {
            "status": str(info.get("status", "") or ""),
            "status_display": str(info.get("status_display", "") or ""),
            "progress": str(info.get("progress", "") or ""),
        }

    saw_to_dip_output = _ratio(dip_trays, saw_output_trays)
    dip_to_sort_output = _ratio(sort_trays, dip_trays)
    sort_to_kiln_output = _ratio(kiln_load_trays, sort_trays)
    secondary_to_finish_output = _ratio(finished_pcs, secondary_trays)
    yield_loss = {
        "saw_to_dip_output_rate_pct": round(saw_to_dip_output * 100, 2),
        "saw_to_dip_loss_rate_pct": round(max(0.0, 1.0 - saw_to_dip_output) * 100, 2),
        "dip_to_sort_output_rate_pct": round(dip_to_sort_output * 100, 2),
        "dip_to_sort_loss_rate_pct": round(max(0.0, 1.0 - dip_to_sort_output) * 100, 2),
        "sort_to_kiln_output_rate_pct": round(sort_to_kiln_output * 100, 2),
        "sort_to_kiln_loss_rate_pct": round(max(0.0, 1.0 - sort_to_kiln_output) * 100, 2),
        "secondary_to_finish_output_rate_pct": round(secondary_to_finish_output * 100, 2),
        "secondary_to_finish_loss_rate_pct": round(max(0.0, 1.0 - secondary_to_finish_output) * 100, 2),
        "finished_m3_per_log_mt": round(_ratio(finished_volume_m3, saw_log_consumed_mt), 4),
    }
    return {
        "date": day_str,
        "range": {
            "start": f"{day_str}T00:00:00",
            "end": f"{day_str}T23:59:59",
        },
        "summary": {
            "log_in_mt": round(log_in_mt, 4),
            "saw_log_consumed_mt": round(saw_log_consumed_mt, 4),
            "saw_output_trays": saw_output_trays,
            "dip_cans": dip_cans,
            "dip_trays": dip_trays,
            "sort_trays": sort_trays,
            "kiln_load_trays": kiln_load_trays,
            "kiln_unload_trays": kiln_unload_trays,
            "secondary_trays": secondary_trays,
            "finished_pcs": finished_pcs,
            "byproduct_bark_ks": round(byproduct_bark_ks, 2),
            "byproduct_dust_bags_out": byproduct_dust_bags_out,
            "byproduct_waste_segment_bags_out": byproduct_waste_segment_bags_out,
        },
        "inventory_snapshot": snapshot,
        "yield_loss": yield_loss if yield_loss_enabled else {},
        "show_yield_loss": bool(yield_loss_enabled),
        "kiln_status": kiln_status,
        "kiln_status_detail": kiln_status_detail,
        "factory_intelligence": stock.get("factory_intelligence", {}) if isinstance(stock.get("factory_intelligence"), dict) else {},
        "ai_deep_monitor": stock.get("ai_deep_monitor", {}) if isinstance(stock.get("ai_deep_monitor"), dict) else {},
        "breakdown": {
            "log_entries": [
                {
                    "truck_number": r.truck_number,
                    "driver_name": r.driver_name,
                    "log_amount": _safe_float(r.log_amount),
                    "created_at": r.created_at,
                    "created_by": r.created_by,
                }
                for r in log_rows
            ],
            "saw_records": [
                {
                    "saw_mt": _safe_float(r.saw_mt),
                    "saw_trays": _safe_int(r.saw_trays),
                    "bark_sales_amount": _safe_float(r.bark_sales_amount),
                    "dust_sales_amount": _safe_float(r.dust_sales_amount),
                    "created_at": r.created_at,
                    "created_by": r.created_by,
                }
                for r in saw_rows
            ],
            "dip_records": [
                {
                    "dip_cans": _safe_int(r.dip_cans),
                    "dip_trays": _safe_int(r.dip_trays),
                    "dip_chemicals": _safe_float(r.dip_chemicals),
                    "created_at": r.created_at,
                    "created_by": r.created_by,
                }
                for r in dip_rows
            ],
            "sort_records": [
                {
                    "sort_trays": _safe_int(r.sort_trays),
                    "sorted_kiln_trays": r.sorted_kiln_trays,
                    "created_at": r.created_at,
                    "created_by": r.created_by,
                }
                for r in sort_rows
            ],
            "tray_batches": [
                {
                    "batch_number": r.batch_number,
                    "kiln_id": r.kiln_id,
                    "tray_count": _safe_int(r.tray_count),
                    "total_volume": _safe_float(r.total_volume),
                    "created_at": r.created_at,
                    "created_by": r.created_by,
                }
                for r in tray_rows
            ],
            "product_batches": [
                {
                    "batch_number": r.batch_number,
                    "product_count": _safe_int(r.product_count),
                    "total_volume": _safe_float(r.total_volume),
                    "created_at": r.created_at,
                    "created_by": r.created_by,
                }
                for r in product_rows
            ],
            "byproduct_records": [
                {
                    "bark_sale_amount": _safe_float(r.bark_sale_amount),
                    "dust_bags_in": _safe_int(r.dust_bags_in),
                    "dust_bags_out": _safe_int(r.dust_bags_out),
                    "dust_sale_amount": _safe_float(r.dust_sale_amount),
                    "created_at": r.created_at,
                    "created_by": r.created_by,
                }
                for r in byproduct_rows
            ],
        },
        "display_labels": labels,
        "display_order": {
            "summary": summary_order,
            "inventory_snapshot": inventory_order,
            "yield_loss": yield_loss_order if yield_loss_enabled else [],
            "kiln_status": kiln_order,
            "breakdown": breakdown_order,
        },
        "meta": {
            "note": lang_pack.get("report_note_second_sort", labels["note"]),
        },
    }
