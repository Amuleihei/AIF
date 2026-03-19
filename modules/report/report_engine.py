from web.utils import get_stock_data


# =====================================================
# 💰 财务概况
# =====================================================

def finance_report():
    return "💰 财务概况\n⛔ 财务功能已暂时关闭（系统维护中）"


# =====================================================
# 🏭 生产概况
# =====================================================

def production_report():
    try:
        s = get_stock_data("zh")
        return (
            "🏭 生产概况\n"
            f"原木库存: {float(s.get('log_stock', 0.0)):.4f} MT\n"
            f"当前锯解库存: {int(s.get('saw_stock', 0) or 0)} 托\n"
            f"当前药浸库存: {int(s.get('dip_stock', 0) or 0)} 托\n"
            f"待入窑库存: {int(s.get('sorting_stock', 0) or 0)} 窑托\n"
            f"窑完成库存: {int(s.get('kiln_done_stock', 0) or 0)} 窑托\n"
            f"成品库存: {int(s.get('product_count', 0) or 0)} 件（{float(s.get('product_m3', 0.0)):.2f} m³）\n"
            f"当前树皮库存: {float(s.get('bark_stock_m3', 0.0)):.2f} 立方\n"
            f"当前木渣库存: {int(s.get('dust_bag_stock', 0) or 0)} 袋"
        )
    except Exception:
        return "🏭 生产概况\n暂无记录"


# =====================================================
# 📦 库存概况（ERP三层）
# =====================================================

def inventory_report():
    try:
        from modules.report.inventory_view import build_inventory_overview
        return build_inventory_overview("📦 库存概况")
    except Exception:
        return "📦 库存概况\n❌ 生成失败"


# =====================================================
# 🔥 窑状态
# =====================================================

def kiln_report():
    from modules.kiln.kiln_view import build_kiln_overview
    return build_kiln_overview(title="🔥 窑概况", include_footer=True, footer_style="two_lines")


# =====================================================
# 📊 工厂总览（管理层）
# =====================================================

def factory_report():

    parts = [
        "📊 AIF 工厂总览",
        finance_report(),
        inventory_report(),
        production_report(),
        kiln_report(),
    ]

    return "\n\n".join(parts)


# =====================================================
# 🧠 ⭐ 工厂驾驶舱（老板用）
# =====================================================

def dashboard():
    s = get_stock_data("zh")
    lines = [
        "🏭 工厂状态",
        f"原木库存: {float(s.get('log_stock', 0.0)):.4f} MT",
        f"当前锯解库存: {int(s.get('saw_stock', 0) or 0)} 托",
        f"当前药浸库存: {int(s.get('dip_stock', 0) or 0)} 托",
        f"待入窑库存: {int(s.get('sorting_stock', 0) or 0)} 窑托",
        f"窑完成库存: {int(s.get('kiln_done_stock', 0) or 0)} 窑托",
        f"成品库存: {int(s.get('product_count', 0) or 0)} 件（{float(s.get('product_m3', 0.0)):.2f} m³）",
        f"当前树皮库存: {float(s.get('bark_stock_m3', 0.0)):.2f} 立方",
        f"当前木渣库存: {int(s.get('dust_bag_stock', 0) or 0)} 袋",
        "",
        "🔥 窑状态",
    ]
    running = 0
    for kid in ("A", "B", "C", "D"):
        info = s.get("kiln_status", {}).get(kid, {}) if isinstance(s.get("kiln_status", {}), dict) else {}
        status_display = str(info.get("status_display", "空") or "空")
        progress = str(info.get("progress", "") or "")
        if str(info.get("status", "") or "") in ("loading", "drying", "unloading"):
            running += 1
        line = f"{kid} 窑: {status_display}"
        if progress:
            line += f" - {progress}"
        lines.append(line)
    lines.extend(["", f"运行中: {running} 窑"])
    return "\n".join(lines)


# =====================================================
# TG入口
# =====================================================

def handle_report(text):

    # -------- 老板驾驶舱 --------

    if text in ("工厂状态", "今日汇总", "驾驶舱", "工厂概况"):
        return dashboard()

    # -------- 管理报表 --------

    if text in ("总览", "工厂总览", "系统总览"):
        return factory_report()

    if text in ("财务概况", "财务报告"):
        return finance_report()

    if text in ("生产概况", "生产报告", "生产状况"):
        return production_report()

    if text in ("库存概况", "库存报告", "库存状况"):
        return inventory_report()

    if text in ("窑概况", "窑报告", "窑状况"):
        return kiln_report()

    return None
