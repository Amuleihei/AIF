from datetime import datetime

from web.models import AdminAuditLog, Session, SortRecord


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
    session = Session()
    try:
        sort_rows = (
            session.query(SortRecord.sort_trays)
            .filter(SortRecord.created_at.like(f"{day_str}%"))
            .all()
        )
        sort_trays_total = sum(int(getattr(row, "sort_trays", 0) or 0) for row in sort_rows)

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

        missing_sort = load_count > 0 and sort_trays_total <= 0
        missing_secondary_sort = secondary_products_count > 0 and secondary_sort_count <= 0

        return {
            "day": day_str,
            "counts": {
                "sort_trays_total": int(sort_trays_total),
                "kiln_load_count": int(load_count),
                "secondary_products_count": int(secondary_products_count),
                "secondary_sort_count": int(secondary_sort_count),
            },
            "missing_sort": bool(missing_sort),
            "missing_secondary_sort": bool(missing_secondary_sort),
            "has_missing": bool(missing_sort or missing_secondary_sort),
        }
    finally:
        session.close()

