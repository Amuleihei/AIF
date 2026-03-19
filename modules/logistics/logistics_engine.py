from web.data_store import get_shipping_data


def _status_rank(status: str) -> int:
    order = {
        "待发车": 0,
        "去仰光途中": 1,
        "仰光仓已到": 2,
        "已从仰光出港": 3,
        "中国港口已到": 4,
        "异常": 5,
    }
    return order.get(str(status or "").strip(), 99)


def _format_time(raw: str) -> str:
    text = str(raw or "").strip()
    if not text:
        return "-"
    return text.replace("T", " ")[:16]


def handle_logistics(text):
    cmd = (text or "").strip()
    if cmd not in ("物流状态", "在途", "发货列表", "物流"):
        return None

    data = get_shipping_data()
    shipments = data.get("shipments", []) if isinstance(data.get("shipments"), list) else []
    if not shipments:
        return "📦 暂无发货记录"

    summary = {"去仰光途中": 0, "仰光仓已到": 0, "已从仰光出港": 0, "异常": 0}
    rows = []
    for item in shipments:
        if not isinstance(item, dict):
            continue
        status = str(item.get("status", "") or "")
        if status == "待发车":
            summary["去仰光途中"] += 1
        elif status in summary:
            summary[status] += 1
        rows.append(item)

    rows.sort(key=lambda x: (_status_rank(x.get("status", "")), str(x.get("shipment_no", ""))))

    lines = [
        "🚚 物流状态",
        f"去仰光途中: {summary['去仰光途中']} 单",
        f"仰光仓已到: {summary['仰光仓已到']} 单",
        f"已从仰光出港: {summary['已从仰光出港']} 单",
        f"异常: {summary['异常']} 单",
        "",
        "最近发货:",
    ]

    for item in rows[:12]:
        shipment_no = str(item.get("shipment_no", "") or "-")
        customer = str(item.get("customer", "") or "-")
        status = str(item.get("status", "") or "-")
        vehicle = str(item.get("vehicle_no", "") or "-")
        departure = _format_time(item.get("departure_at", ""))
        lines.append(f"{shipment_no} | {customer} | {status} | 车牌:{vehicle} | 发车:{departure}")

    if len(rows) > 12:
        lines.append(f"\n其余 {len(rows) - 12} 单未展开")

    return "\n".join(lines)
