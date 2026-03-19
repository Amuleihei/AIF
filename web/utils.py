from flask import request, session as flask_session
from flask_login import current_user
import time
from datetime import datetime
from pathlib import Path
from .i18n import LANGUAGES  # 中文注释：从 i18n 聚合入口读取翻译
from .data_store import get_log_stock_total, get_product_stats, get_flow_data, get_kilns_data, save_flow_data, save_kilns_data, get_shipping_data
from .models import Session, User, TgSetting
from .services.alert_settings_service import get_alert_settings
from .services.alert_center_service import evaluate_inventory_alerts, get_alert_center_payload
from .services.period_report_service import ensure_period_reports_generated, get_period_report_links
from .observability import count_recent_web_errors

BARK_PRICE_PER_M3_KS = 31765.0
MIGRATION_KEY = "migration_v2_done"


def _build_inventory_alerts(lang: str, stock: dict) -> list[dict]:
    cfg = get_alert_settings()
    return evaluate_inventory_alerts(stock=stock, threshold_cfg=cfg)


def _fmt_dt(ts: float | None) -> str:
    if not ts:
        return "-"
    try:
        return datetime.fromtimestamp(float(ts)).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return "-"


def get_system_health_snapshot() -> dict:
    """系统健康快照：用于首页和健康接口。"""
    root = Path(__file__).resolve().parent.parent
    db_path = root / "unified.db"
    backup_dir = root / "backups" / "db"

    db_exists = db_path.exists()
    db_size_mb = round((db_path.stat().st_size / 1024 / 1024), 2) if db_exists else 0.0

    latest_backup = None
    if backup_dir.exists():
        cands = [p for p in backup_dir.glob("unified.db.*.sqlite") if p.is_file()]
        if cands:
            latest_backup = max(cands, key=lambda p: p.stat().st_mtime)
    backup_time = latest_backup.stat().st_mtime if latest_backup else None
    web_errors_24h = count_recent_web_errors(root, hours=24)

    migrated = False
    user_total = 0
    weak_password_user_count = 0
    session = Session()
    try:
        marker = session.query(TgSetting).filter_by(key=MIGRATION_KEY).first()
        migrated = bool(marker and str(marker.value or "").strip() == "1")
        users = session.query(User).all()
        user_total = len(users)
        weak_password_user_count = sum(1 for u in users if not User._is_password_hash(u.password))
    except Exception:
        pass
    finally:
        session.close()

    issues = []
    if not db_exists:
        issues.append("数据库文件缺失")
    if not migrated:
        issues.append("迁移标记未完成")
    if latest_backup is None:
        issues.append("未找到数据库备份")
    if weak_password_user_count > 0:
        issues.append(f"检测到 {weak_password_user_count} 个历史明文密码用户")
    if web_errors_24h > 20:
        issues.append(f"最近24小时 Web 错误 {web_errors_24h} 次")

    status = "healthy" if not issues else "warning"
    return {
        "status": status,
        "db_exists": db_exists,
        "db_size_mb": db_size_mb,
        "migration_done": migrated,
        "user_total": user_total,
        "weak_password_user_count": weak_password_user_count,
        "latest_backup_file": str(latest_backup.name) if latest_backup else "",
        "latest_backup_at": _fmt_dt(backup_time),
        "web_errors_24h": web_errors_24h,
        "issues": issues,
    }

def get_lang():
    """获取当前语言（优先级：URL参数 > 会话记忆 > 角色默认）"""
    lang_from_query = str(request.args.get("lang", "") or "").strip()
    if lang_from_query in LANGUAGES:
        flask_session["lang"] = lang_from_query
        return lang_from_query

    lang_from_session = str(flask_session.get("lang", "") or "").strip()
    if lang_from_session in LANGUAGES:
        return lang_from_session

    # 中文注释：未显式选择语言时，管理员默认中文，其他角色默认英文。
    try:
        if getattr(current_user, "is_authenticated", False):
            role = str(getattr(current_user, "role", "") or "").strip().lower()
            return "zh" if role == "admin" else "en"
    except Exception:
        pass
    return "zh"

def get_stock_data_with_lang():
    """获取带语言参数的库存数据"""
    lang = get_lang()
    if lang not in LANGUAGES:
        lang = 'zh'
    return get_stock_data(lang)

def get_stock_data(lang='zh'):
    """获取库存数据"""
    # 自动生成周报/月报（到点后首次访问触发）
    try:
        ensure_period_reports_generated()
    except Exception:
        pass

    log_stock = float(get_log_stock_total())
    product_count, product_m3 = get_product_stats()

    # 锯解库存
    saw_stock = 0
    dip_stock = 0
    dip_chem_bag_stock = 0.0
    dip_additive_kg_stock = 0.0
    sorting_stock = 0
    kiln_done_stock = 0
    dust_bag_stock = 0
    waste_segment_bag_stock = 0
    bark_stock_m3 = 0.0
    shipping_summary = {'去仰光途中': 0, '仰光仓已到': 0, '已从仰光出港': 0, '异常': 0}
    overview_radar_labels = ["原木保障", "前段均衡", "中段流速", "积压健康", "成品健康"]
    overview_radar = {
        "current": [0, 0, 0, 0, 0],
        "day": [0, 0, 0, 0, 0],
        "week": [0, 0, 0, 0, 0],
        "month": [0, 0, 0, 0, 0],
    }

    flow = get_flow_data()
    saw_stock = flow.get('saw_tray_pool', 0)
    dip_stock = flow.get('dip_tray_pool', 0)
    dip_chem_bag_stock = float(flow.get('dip_chem_bag_pool', flow.get('dip_chem_bag_total', 19.0)))
    dip_additive_kg_stock = float(flow.get('dip_additive_kg_pool', 0.0))
    sorting_stock = flow.get('selected_tray_pool', 0)
    kiln_done_stock = flow.get('kiln_done_tray_pool', 0)
    dust_bag_stock = flow.get('dust_bag_pool', 0)
    waste_segment_bag_stock = flow.get('waste_segment_bag_pool', 0)
    bark_stock_m3 = flow.get('bark_stock_m3', 0.0)
    bark_stock_ks = float(bark_stock_m3) * BARK_PRICE_PER_M3_KS

    shipping = get_shipping_data()
    for item in shipping.get('shipments', []) if isinstance(shipping.get('shipments'), list) else []:
        if not isinstance(item, dict):
            continue
        status = str(item.get('status', '待发货') or '待发货')
        if status == '待发车':
            shipping_summary['去仰光途中'] = shipping_summary.get('去仰光途中', 0) + 1
        elif status in shipping_summary:
            shipping_summary[status] = shipping_summary.get(status, 0) + 1

    # 窑状态
    kiln_status = {}
    kilns = get_kilns_data()
    kilns_changed = False
    for kiln_id in ['A', 'B', 'C', 'D']:
        if kiln_id in kilns:
            kiln_data = kilns[kiln_id]
            status = kiln_data.get('status', 'empty')
            # 兼容旧状态名，统一展示/存储为 ready（完成待出）
            if status == 'ready_unload':
                status = 'ready'
                kiln_data['status'] = 'ready'
                kilns_changed = True
            status_display = {
                'empty': LANGUAGES[lang]['empty'],
                'loading': LANGUAGES[lang]['loading'],
                'drying': LANGUAGES[lang]['drying'],
                'unloading': LANGUAGES[lang]['unloading'],
                'ready': LANGUAGES[lang]['ready'],
                'completed': LANGUAGES[lang]['completed']
            }.get(status, status)

            progress = ""
            elapsed_hours = 0
            remaining_hours = 0
            total_trays = 0
            remaining_trays = 0
            trays_list = kiln_data.get('trays', [])
            trays_in_kiln = sum(int(tray.get('count', 0) or 0) for tray in trays_list) if isinstance(trays_list, list) else 0
            # 中文注释：管理员在后台修正的总托/已出托，视为权威值，优先用于全局展示。
            stored_total_trays = int(kiln_data.get('unloading_total_trays', 0) or 0)
            unloaded_trays = int(kiln_data.get('unloaded_count', 0) or 0)
            total_trays = stored_total_trays if stored_total_trays > 0 else trays_in_kiln
            remaining_trays = max(0, total_trays - unloaded_trays)
            if status == 'drying' and ('dry_start' in kiln_data or 'start' in kiln_data):
                start_time = kiln_data.get('dry_start') or kiln_data.get('start')
                if isinstance(start_time, str):
                    # 如果是字符串格式的时间，需要转换
                    try:
                        from datetime import datetime
                        start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                        elapsed = int(time.time()) - int(start_dt.timestamp())
                    except:
                        elapsed = 0
                else:
                    elapsed = int(time.time()) - start_time
                # 满120小时自动流转为“完成待出”
                if elapsed >= 120 * 3600:
                    status = 'ready'
                    kiln_data['status'] = 'ready'
                    kilns_changed = True
                remaining = max(0, 120 * 3600 - elapsed)  # 120小时
                elapsed_hours = elapsed // 3600
                remaining_hours = remaining // 3600
                progress = LANGUAGES[lang]['drying_progress'].format(
                    elapsed=elapsed_hours, remaining=remaining_hours
                )
                status_display = {
                    'empty': LANGUAGES[lang]['empty'],
                    'loading': LANGUAGES[lang]['loading'],
                    'drying': LANGUAGES[lang]['drying'],
                    'unloading': LANGUAGES[lang]['unloading'],
                    'ready': LANGUAGES[lang]['ready'],
                    'completed': LANGUAGES[lang]['completed']
                }.get(status, status)
            # 主页与日报口径统一：烘干中仅显示时间；其余状态显示托数。
            if status != 'drying' and total_trays > 0:
                tray_progress = f"{LANGUAGES[lang]['total_trays']}{total_trays} {LANGUAGES[lang]['remaining_trays']}{remaining_trays}{LANGUAGES[lang]['trays']}"
                progress = tray_progress

            kiln_status[kiln_id] = {
                'status': status,
                'status_display': status_display,
                'progress': progress,
                'elapsed_hours': elapsed_hours,
                'remaining_hours': remaining_hours,
                'total_trays': total_trays,
                'remaining_trays': remaining_trays,
                'in_kiln_trays': trays_in_kiln,
                'remaining_kiln_trays': remaining_trays,
            }
        else:
            kiln_status[kiln_id] = {
                'status': 'empty',
                'status_display': LANGUAGES[lang]['empty'],
                'progress': '',
                'elapsed_hours': 0,
                'remaining_hours': 0,
                'total_trays': 0,
                'remaining_trays': 0,
                'in_kiln_trays': 0,
                'remaining_kiln_trays': 0,
            }

    if kilns_changed:
        save_kilns_data(kilns)

    try:
        alert_payload = get_alert_center_payload(limit_recent=20)
        efficiency = alert_payload.get("efficiency", {}) if isinstance(alert_payload, dict) else {}
        labels = efficiency.get("radar_labels", []) if isinstance(efficiency, dict) else []
        radar = efficiency.get("radar", {}) if isinstance(efficiency, dict) else {}
        def _radar_vals(key: str) -> list[float]:
            vals = radar.get(key, []) if isinstance(radar, dict) else []
            if not isinstance(vals, list) or len(vals) < 5:
                return [0.0, 0.0, 0.0, 0.0, 0.0]
            return [max(0.0, min(100.0, float(x or 0))) for x in vals[:5]]
        if isinstance(labels, list) and len(labels) >= 5:
            overview_radar_labels = [str(x) for x in labels[:5]]
        overview_radar = {
            "current": _radar_vals("current"),
            "day": _radar_vals("day"),
            "week": _radar_vals("week"),
            "month": _radar_vals("month"),
        }
    except Exception:
        pass

    stock_payload = {
        'log_stock': log_stock,
        'saw_stock': saw_stock,
        'dip_stock': dip_stock,
        'dip_chem_bag_stock': dip_chem_bag_stock,
        'dip_additive_kg_stock': dip_additive_kg_stock,
        'sorting_stock': sorting_stock,
        'kiln_done_stock': kiln_done_stock,
        'dust_bag_stock': dust_bag_stock,
        'waste_segment_bag_stock': waste_segment_bag_stock,
        'bark_stock_m3': bark_stock_m3,
        'bark_stock_ks': bark_stock_ks,
        'product_count': product_count,
        'product_m3': product_m3,
        'shipping_summary': shipping_summary,
        'overview_radar_labels': overview_radar_labels,
        'overview_radar': overview_radar,
        'kiln_status': kiln_status,
        'system_health': get_system_health_snapshot(),
        'lang': lang,
        'texts': LANGUAGES[lang],
        'period_reports': get_period_report_links(),
    }
    stock_payload['alerts'] = _build_inventory_alerts(lang, stock_payload)
    return stock_payload

def update_flow_data(updates):
    """更新流程数据"""
    flow = get_flow_data()
    flow.update(updates)
    save_flow_data(flow)

def update_kiln_status(kiln_id, status, trays=None):
    """更新窑状态"""
    kilns = get_kilns_data()

    if kiln_id not in kilns:
        kilns[kiln_id] = {}

    kiln = kilns[kiln_id]
    kiln['status'] = status
    if trays is not None:
        kiln['trays'] = trays
    kiln.pop('manual_elapsed_hours', None)
    kiln.pop('manual_remaining_hours', None)

    if status == 'drying':
        current_time = int(time.time())
        kiln['dry_start'] = current_time
        # 同时设置start字段以兼容现有数据
        from datetime import datetime
        kiln['start'] = datetime.fromtimestamp(current_time).isoformat()
    elif status == 'unloading':
        trays_in_kiln = kiln.get('trays', [])
        tray_total = sum(_to_int(t.get('count'), 0) for t in trays_in_kiln) if isinstance(trays_in_kiln, list) else 0
        if tray_total > 0:
            kiln['unloading_total_trays'] = tray_total
        kiln['unloaded_count'] = max(0, _to_int(kiln.get('unloaded_count'), 0))
    elif status in ('empty', 'loading', 'completed'):
        kiln['dry_start'] = None
        kiln['start'] = None
        if status == 'empty':
            kiln['trays'] = []
        if status != 'completed':
            kiln['unloaded_count'] = 0
            kiln['unloading_total_trays'] = 0

    save_kilns_data(kilns)
