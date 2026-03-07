import json
from pathlib import Path
from datetime import datetime, timedelta

DATA = Path.home() / "AIF/data"

INV_FILE = DATA / "inventory/inventory.json"
FIN_FILE = DATA / "finance/finance.json"
KILN_FILE = DATA / "kiln/kilns.json"
LEDGER_FILE = DATA / "ledger/production_ledger.json"


# =====================================================
# 工具
# =====================================================

def load(p):
    if not p.exists():
        return {}
    try:
        return json.load(open(p))
    except:
        return {}


def today():
    return datetime.now().strftime("%Y-%m-%d")


# =====================================================
# 原料 + 在制 + 成品库存
# =====================================================

def inventory_part():
    # 与「库存概况」统一口径（同一渲染器，避免菜单/日报不一致）
    try:
        from modules.report.inventory_view import build_inventory_overview
        return build_inventory_overview("📦 库存明细")
    except Exception:
        return "📦 库存明细\n❌ 生成失败"


# =====================================================
# 今日生产（来自台账）
# =====================================================

def production_part():

    d = load(LEDGER_FILE)
    day = today()

    if day not in d:
        return "🏭 今日生产\n暂无记录"

    r = d[day]

    saw_mt = r.get("saw_mt", 0)
    saw_tray = r.get("saw_tray", 0)
    kiln_out_m3 = r.get("kiln_out_m3", 0)
    product = r.get("product_m3", r.get("pack_m3", 0))
    pack_pkg = r.get("pack_pkg", 0)
    pack_pcs = r.get("pack_pcs", 0)
    kiln_in_tray = r.get("kiln_tray", 0)
    kiln_out_tray = r.get("kiln_out_tray", 0)
    ab_m3 = r.get("ab_m3", 0)
    bc_m3 = r.get("bc_m3", 0)

    # 日报：入窑/出窑统一用“托”
    kiln_in_text = f"{kiln_in_tray} 托"
    kiln_out_text = f"{kiln_out_tray} 托"

    # 产出效率（避免用 m³ 做百分比导致夸张比率）
    efficiency = ""
    if kiln_out_tray and kiln_out_m3:
        try:
            efficiency = f"\n出窑均产: {float(kiln_out_m3)/int(kiln_out_tray):.3f} m³/托"
        except Exception:
            efficiency = ""

    ratio = ""
    total_grade = ab_m3 + bc_m3
    if total_grade > 0:
        ratio = f"\nAB/BC占比：{ab_m3/total_grade*100:.1f}% / {bc_m3/total_grade*100:.1f}%"

    dip_line = ""
    if (r.get("dip_tank", 0) > 0) or (r.get("dip_tray", 0) > 0):
        dip_line = f"药浸: {r.get('dip_tank',0)}罐 {r.get('dip_tray',0)}托 药剂:{r.get('dip_bag',0)}袋\n"

    return (
        "🏭 今日生产\n"
        f"上锯投入: {float(saw_mt):.4f} MT\n"
        f"上锯产出: {saw_tray} 托\n"
        f"{dip_line}"
        f"入窑: {kiln_in_text}\n"
        f"出窑: {kiln_out_text}\n"
        f"成品: {product:.1f} m³ ({pack_pkg}件)"
        f"{efficiency}{ratio}"
    )


# =====================================================
# 窑状态（四窑工业版）
# =====================================================

def kiln_part():
    from modules.kiln.kiln_view import build_kiln_overview

    # Keep daily report kiln section aligned with “窑总览” menu output.
    return build_kiln_overview(title="🔥 窑总览", include_footer=True, footer_style="two_lines")


# =====================================================
# 财务
# =====================================================

def finance_part():
    # 临时关闭财务：日报中保留段落占位，避免报表结构变化导致现场误解
    return "💰 今日财务\n⛔ 财务功能已暂时关闭（系统维护中）\n总额: 0.00 KS"


# =====================================================
# ⭐ 终极日报
# =====================================================

def daily_report():

    day = today()

    # 若今日无任何生产台账记录，则返回一句话（避免“点日报没反应”的观感）
    ledger = load(LEDGER_FILE)
    r = ledger.get(day) if isinstance(ledger, dict) else None
    if not isinstance(r, dict):
        return f"📊 {day} 日报暂未生产"
    key_fields = (
        "saw_mt", "saw_tray",
        "dip_tank", "dip_tray",
        "select_tray",
        "kiln_tray", "kiln_out_tray",
        "pack_pcs", "pack_m3", "product_m3",
    )
    if all((r.get(k) in (0, 0.0, False, None)) for k in key_fields):
        return f"📊 {day} 日报暂未生产"

    parts = [
        f"📊 AIF 生产日报 {day}",
        inventory_part(),
        production_part(),
        kiln_part(),
        finance_part(),
    ]

    return "\n\n".join(parts)


# =====================================================
# TG入口
# =====================================================

def handle_daily_report(text):

    if text in ("日报", "今日报告", "生产日报", "工厂日报"):
        return daily_report()

    return None
