from datetime import datetime
import re

from web.models import (
    AdminAuditLog,
    DipRecord,
    FlowSelectedTrayDetail,
    LogEntry,
    SawRecord,
    Session,
    SortRecord,
)


def _day_prefix(day: str | None = None) -> str:
    if day:
        return str(day)
    return datetime.now().strftime("%Y-%m-%d")


def get_daily_missing_entry_status(day: str | None = None) -> dict:
    """
    口径说明：
    - 拣选消耗缺失：当日已发生“入窑”动作，但当日未提交拣选消耗。
    - 二选消耗缺失：当日已提交“二选成品入库”，但当日未提交“今日二选托数”。
    """
    day_str = _day_prefix(day)
    day_mmdd = ""
    try:
        day_mmdd = datetime.strptime(day_str, "%Y-%m-%d").strftime("%m%d")
    except Exception:
        day_mmdd = datetime.now().strftime("%m%d")
    session = Session()
    try:
        log_entry_count = (
            session.query(LogEntry.id)
            .filter(LogEntry.created_at.like(f"{day_str}%"))
            .count()
        )
        saw_count = (
            session.query(SawRecord.id)
            .filter(SawRecord.created_at.like(f"{day_str}%"))
            .count()
        )
        dip_count = (
            session.query(DipRecord.id)
            .filter(DipRecord.created_at.like(f"{day_str}%"))
            .count()
        )
        sort_rows = (
            session.query(SortRecord.sort_trays)
            .filter(SortRecord.created_at.like(f"{day_str}%"))
            .all()
        )
        sort_trays_total = sum(int(getattr(row, "sort_trays", 0) or 0) for row in sort_rows)
        sort_consumption_count = (
            session.query(SortRecord.id)
            .filter(SortRecord.created_at.like(f"{day_str}%"))
            .count()
        )
        # 中文注释：拣选窑托录入没有独立日报表，按“托号含当天MMDD前缀”近似识别当日拣选录入。
        sort_stage_count = (
            session.query(FlowSelectedTrayDetail.tray_id)
            .filter(FlowSelectedTrayDetail.tray_id.like(f"{day_mmdd}-%"))
            .count()
        )

        load_count = (
            session.query(AdminAuditLog.id)
            .filter(AdminAuditLog.action == "kiln_action")
            .filter(AdminAuditLog.created_at.like(f"{day_str}%"))
            .filter(AdminAuditLog.detail.like("%action=load%"))
            .count()
        )
        secondary_products_count = (
            session.query(AdminAuditLog.id)
            .filter(AdminAuditLog.action == "submit_secondary_products")
            .filter(AdminAuditLog.created_at.like(f"{day_str}%"))
            .count()
        )
        secondary_sort_count = (
            session.query(AdminAuditLog.id)
            .filter(AdminAuditLog.action == "submit_secondary_sort")
            .filter(AdminAuditLog.created_at.like(f"{day_str}%"))
            .count()
        )
        secondary_sort_rows = (
            session.query(AdminAuditLog.detail)
            .filter(AdminAuditLog.action == "submit_secondary_sort")
            .filter(AdminAuditLog.created_at.like(f"{day_str}%"))
            .all()
        )
        secondary_waste_segment_total = 0
        for row in secondary_sort_rows:
            detail = str(getattr(row, "detail", "") or "")
            m = re.search(r"(?:^|,)waste_segment_in=(\d+)(?:,|$)", detail)
            if m:
                secondary_waste_segment_total += int(m.group(1) or 0)

        missing_sort = load_count > 0 and sort_trays_total <= 0
        missing_secondary_sort = secondary_products_count > 0 and secondary_sort_count <= 0
        entries = [
            {"key": "log_entry", "required": False, "completed": log_entry_count > 0},
            {"key": "saw", "required": True, "completed": saw_count > 0},
            {"key": "dip", "required": True, "completed": dip_count > 0},
            {"key": "sort_stage", "required": True, "completed": sort_stage_count > 0},
            {"key": "sort_consumption", "required": True, "completed": sort_consumption_count > 0 and sort_trays_total > 0},
            {"key": "secondary_sort", "required": True, "completed": secondary_sort_count > 0},
            {"key": "secondary_waste_segment", "required": False, "completed": secondary_waste_segment_total > 0},
            {"key": "secondary_products", "required": True, "completed": secondary_products_count > 0},
        ]
        all_required_done = all(bool(e["completed"]) for e in entries if bool(e["required"]))

        return {
            "day": day_str,
            "counts": {
                "log_entry_count": int(log_entry_count),
                "saw_count": int(saw_count),
                "dip_count": int(dip_count),
                "sort_stage_count": int(sort_stage_count),
                "sort_consumption_count": int(sort_consumption_count),
                "sort_trays_total": int(sort_trays_total),
                "kiln_load_count": int(load_count),
                "secondary_products_count": int(secondary_products_count),
                "secondary_sort_count": int(secondary_sort_count),
                "secondary_waste_segment_total": int(secondary_waste_segment_total),
            },
            "entries": entries,
            "all_required_done": bool(all_required_done),
            "missing_sort": bool(missing_sort),
            "missing_secondary_sort": bool(missing_secondary_sort),
            "has_missing": bool((not all_required_done) or missing_sort or missing_secondary_sort),
        }
    finally:
        session.close()
