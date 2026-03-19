import hashlib
import hmac
import json
import os
import time
from datetime import datetime
from urllib import request as urllib_request
from urllib.parse import parse_qsl

from flask import request, render_template_string, jsonify, redirect, url_for, flash
from flask_login import login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash

from web.forms import LoginForm
from tg_bot.config import get_bot_token
from web.models import User, Session, TgUserRole, AdminAuditLog, LoginSecurity, LoginTrustedIp
from web.i18n import LANGUAGES
from web.utils import get_lang
from web.templates import LOGIN_TEMPLATE
from web.templates_admin import (
    ADMIN_USERS_TEMPLATE,
    ADMIN_DASHBOARD_TEMPLATE,
    ADMIN_AUDIT_TEMPLATE,
    ADMIN_ALERT_SETTINGS_TEMPLATE,
    ADMIN_ALERT_CENTER_TEMPLATE,
    ADMIN_HR_SETTINGS_TEMPLATE,
    ADMIN_HR_EMPLOYEES_TEMPLATE,
)
from modules.hr.hr_engine import (
    add_hr_attendance_from_admin,
    apply_hr_attendance_batch_from_admin,
    add_hr_employee_from_admin,
    get_hr_admin_payload,
    get_hr_employees_payload,
    save_hr_admin_settings,
    update_hr_employee_from_admin,
)
from web.services.alert_settings_service import get_alert_settings, save_alert_settings
from web.services.alert_center_service import (
    append_threshold_version,
    get_alert_center_payload,
    save_alert_engine_config,
    set_alert_silence,
    update_alert_event,
)
from web.services.period_report_service import get_period_report_links


def _verify_tg_init_data(init_data: str, bot_token: str, max_age_seconds: int = 6 * 3600) -> dict | None:
    text = str(init_data or "").strip()
    if not text or not bot_token:
        return None

    pairs = dict(parse_qsl(text, keep_blank_values=True))
    received_hash = pairs.pop("hash", "")
    if not received_hash:
        return None

    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(pairs.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode("utf-8"), hashlib.sha256).digest()
    calc_hash = hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(calc_hash, received_hash):
        return None

    try:
        auth_date = int(pairs.get("auth_date", "0"))
    except Exception:
        return None
    now = int(time.time())
    if auth_date <= 0 or abs(now - auth_date) > max_age_seconds:
        return None

    try:
        user = json.loads(pairs.get("user", "{}"))
    except Exception:
        return None
    return user if isinstance(user, dict) else None


def _get_or_create_web_user_for_role(session, role: str, tg_uid: str):
    role_key = "admin" if role == "管理员" else "boss"
    user = session.query(User).filter_by(role=role_key).order_by(User.id.asc()).first()
    if user:
        return user

    username = f"{role_key}_{tg_uid}"
    user = User(username=username, role=role_key, password=generate_password_hash(f"tg-{tg_uid}-{role_key}"))
    session.add(user)
    session.commit()
    return user


def register_auth_admin_routes(app, translate):
    """注册认证与管理员路由。"""

    lan_prefix = str(os.getenv("AIF_LAN_EXEMPT_PREFIX", "192.168.1.") or "192.168.1.").strip()
    notify_new_external_login = str(os.getenv("AIF_NOTIFY_NEW_EXTERNAL_LOGIN", "1") or "1").strip().lower() in ("1", "true", "yes", "on")

    def _client_ip() -> str:
        xff = (request.headers.get("X-Forwarded-For") or "").strip()
        if xff:
            return xff.split(",")[0].strip()
        return str(request.remote_addr or "").strip()

    def _is_lan_ip(ip: str) -> bool:
        return bool(ip) and ip.startswith(lan_prefix)

    def _notify_admin_external_login(username: str, ip: str, user_agent: str) -> None:
        if not notify_new_external_login:
            return
        if not ip or _is_lan_ip(ip):
            return
        try:
            token = get_bot_token()
        except Exception:
            return

        session = Session()
        try:
            admin_ids = {
                str(r.user_id).strip()
                for r in session.query(TgUserRole).filter_by(role="管理员").all()
                if str(r.user_id or "").strip()
            }
        finally:
            session.close()
        fallback_chat = str(os.getenv("BOT_CHAT_ID", "") or "").strip()
        if fallback_chat:
            admin_ids.add(fallback_chat)
        if not admin_ids:
            return

        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ua = str(user_agent or "").strip()
        if len(ua) > 140:
            ua = ua[:140] + "..."
        text = (
            "AIF 外网登录提醒\n"
            f"用户: {username}\n"
            f"IP: {ip}\n"
            f"时间: {ts}\n"
            f"设备: {ua or '-'}"
        )
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        headers = {"Content-Type": "application/json"}
        for cid in admin_ids:
            try:
                req = urllib_request.Request(
                    url,
                    data=json.dumps({"chat_id": cid, "text": text}).encode("utf-8"),
                    headers=headers,
                    method="POST",
                )
                urllib_request.urlopen(req, timeout=5).read()
            except Exception:
                continue

    def _audit(action: str, target: str = "", detail: str = "", operator: str | None = None):
        session = None
        try:
            session = Session()
            op = str((operator if operator is not None else getattr(current_user, "username", "")) or "")
            row = AdminAuditLog(
                operator=op,
                action=str(action or ""),
                target=str(target or ""),
                detail=str(detail or ""),
            )
            session.add(row)
            session.commit()
            session.close()
        except Exception:
            try:
                if session is not None:
                    session.close()
            except Exception:
                pass

    def _can_access_hr_employees() -> bool:
        role = str(getattr(current_user, "role", "") or "").strip().lower()
        return bool(current_user.has_permission("admin") or role in ("finance", "stats"))

    def _localize_hr_option(value: str, kind: str, lang: str) -> str:
        raw = str(value or "").strip()
        if not raw:
            return ""
        key = raw.lower()

        alias_map = {
            "team": {
                "办公室": "office",
                "office": "office",
                "office team": "office",
                "锯工组": "saw_team",
                "saw team": "saw_team",
                "sawing team": "saw_team",
                "药浸&烘干组": "dip_kiln_team",
                "dip & kiln team": "dip_kiln_team",
                "dip and kiln team": "dip_kiln_team",
                "采购组": "procurement_team",
                "procurement team": "procurement_team",
                "设备保障": "maintenance_team",
                "maintenance": "maintenance_team",
                "安保组": "security_team",
                "security team": "security_team",
                "窑工组": "kiln_team",
                "kiln team": "kiln_team",
                "拣选组": "sorting_team",
                "sorting team": "sorting_team",
                "物流组": "logistics_team",
                "logistics team": "logistics_team",
                "未分组": "unassigned_team",
                "unassigned": "unassigned_team",
            },
            "position": {
                "财务": "finance",
                "finance": "finance",
                "统计": "statistics",
                "stats": "statistics",
                "statistics": "statistics",
                "经理": "manager",
                "manager": "manager",
                "锯工": "sawyer",
                "sawyer": "sawyer",
                "窑工": "kiln_operator",
                "kiln operator": "kiln_operator",
                "拣选": "sorter",
                "sorter": "sorter",
                "发货员": "shipper",
                "shipper": "shipper",
                "仓管": "warehouse_keeper",
                "warehouse keeper": "warehouse_keeper",
                "副锯工": "assistant_sawyer",
                "assistant sawyer": "assistant_sawyer",
                "锯工qc": "saw_qc",
                "saw qc": "saw_qc",
                "药浸烘干控制(同岗)": "dip_kiln_controller",
                "dip kiln controller": "dip_kiln_controller",
                "锅炉工": "boiler_operator",
                "boiler operator": "boiler_operator",
                "拣选qc": "sorting_qc",
                "sorting qc": "sorting_qc",
                "拣选员": "sorting_worker",
                "sorting worker": "sorting_worker",
                "二选修正人员": "secondary_sort_rework",
                "secondary sort rework": "secondary_sort_rework",
                "采购兼司机": "buyer_driver",
                "buyer driver": "buyer_driver",
                "电工": "electrician",
                "electrician": "electrician",
                "叉车司机": "forklift_driver",
                "forklift driver": "forklift_driver",
                "保安": "security_guard",
                "security guard": "security_guard",
                "未设置": "unset_position",
                "unassigned position": "unset_position",
            },
            "salary_type": {
                "日薪": "daily",
                "daily": "daily",
                "月薪": "monthly",
                "monthly": "monthly",
                "计件": "piecework",
                "piecework": "piecework",
                "hourly": "hourly",
                "时薪": "hourly",
                "小时工": "hourly",
            },
        }
        labels = {
            "team": {
                "office": {"zh": "办公室", "en": "Office", "my": "ရုံးအဖွဲ့"},
                "saw_team": {"zh": "锯工组", "en": "Saw Team", "my": "လွှအသင်း"},
                "dip_kiln_team": {"zh": "药浸&烘干组", "en": "Dip & Kiln Team", "my": "ဆေးစိမ်နှင့် အိုးဖိုအဖွဲ့"},
                "procurement_team": {"zh": "采购组", "en": "Procurement Team", "my": "ဝယ်ယူရေးအဖွဲ့"},
                "maintenance_team": {"zh": "设备保障", "en": "Maintenance", "my": "စက်ပစ္စည်းထိန်းသိမ်းရေး"},
                "security_team": {"zh": "安保组", "en": "Security Team", "my": "လုံခြုံရေးအဖွဲ့"},
                "kiln_team": {"zh": "窑工组", "en": "Kiln Team", "my": "အိုးဖိုအသင်း"},
                "sorting_team": {"zh": "拣选组", "en": "Sorting Team", "my": "ရွေးချယ်အသင်း"},
                "logistics_team": {"zh": "物流组", "en": "Logistics Team", "my": "ပို့ဆောင်ရေးအသင်း"},
                "unassigned_team": {"zh": "未分组", "en": "Unassigned", "my": "မသတ်မှတ်ထားသောအဖွဲ့"},
            },
            "position": {
                "finance": {"zh": "财务", "en": "Finance", "my": "ဘဏ္ဍာရေး"},
                "statistics": {"zh": "统计", "en": "Statistics", "my": "စာရင်းအင်း"},
                "manager": {"zh": "经理", "en": "Manager", "my": "မန်နေဂျာ"},
                "sawyer": {"zh": "锯工", "en": "Sawyer", "my": "လွှလုပ်သား"},
                "kiln_operator": {"zh": "窑工", "en": "Kiln Operator", "my": "အိုးဖိုလုပ်သား"},
                "sorter": {"zh": "拣选", "en": "Sorter", "my": "ရွေးချယ်လုပ်သား"},
                "shipper": {"zh": "发货员", "en": "Shipper", "my": "ပို့ဆောင်ရေးဝန်ထမ်း"},
                "warehouse_keeper": {"zh": "仓管", "en": "Warehouse Keeper", "my": "ဂိုဒေါင်ထိန်း"},
                "assistant_sawyer": {"zh": "副锯工", "en": "Assistant Sawyer", "my": "လွှအကူလုပ်သား"},
                "saw_qc": {"zh": "锯工QC", "en": "Saw QC", "my": "လွှ QC"},
                "dip_kiln_controller": {"zh": "药浸烘干控制(同岗)", "en": "Dip & Kiln Controller", "my": "ဆေးစိမ်နှင့် အိုးဖို ထိန်းချုပ်သူ"},
                "boiler_operator": {"zh": "锅炉工", "en": "Boiler Operator", "my": "ဘွိုင်လာလုပ်သား"},
                "sorting_qc": {"zh": "拣选QC", "en": "Sorting QC", "my": "ရွေးချယ် QC"},
                "sorting_worker": {"zh": "拣选员", "en": "Sorting Worker", "my": "ရွေးချယ်လုပ်သား"},
                "secondary_sort_rework": {"zh": "二选修正人员", "en": "Secondary Sort Rework", "my": "ဒုတိယရွေး ပြန်ပြင်ဝန်ထမ်း"},
                "buyer_driver": {"zh": "采购兼司机", "en": "Buyer & Driver", "my": "ဝယ်ယူရေးနှင့် ယာဉ်မောင်း"},
                "electrician": {"zh": "电工", "en": "Electrician", "my": "လျှပ်စစ်ဝန်ထမ်း"},
                "forklift_driver": {"zh": "叉车司机", "en": "Forklift Driver", "my": "ဖော့ကလစ်ယာဉ်မောင်း"},
                "security_guard": {"zh": "保安", "en": "Security Guard", "my": "လုံခြုံရေးဝန်ထမ်း"},
                "unset_position": {"zh": "未设置", "en": "Unassigned Position", "my": "မသတ်မှတ်ထားသောရာထူး"},
            },
            "salary_type": {
                "daily": {"zh": "日薪", "en": "Daily Wage", "my": "နေ့စားလစာ"},
                "monthly": {"zh": "月薪", "en": "Monthly Salary", "my": "လစာ (လစဉ်)"},
                "piecework": {"zh": "计件", "en": "Piece Rate", "my": "အပိုင်းလိုက်လစာ"},
                "hourly": {"zh": "时薪", "en": "Hourly Wage", "my": "နာရီလိုက်လစာ"},
            },
        }
        canonical = alias_map.get(kind, {}).get(key) or alias_map.get(kind, {}).get(raw)
        if not canonical:
            return raw
        return labels.get(kind, {}).get(canonical, {}).get(lang, raw)

    def _attach_hr_choice_labels(data: dict, lang: str) -> dict:
        payload = dict(data or {})
        team_options = payload.get("team_options", []) if isinstance(payload.get("team_options"), list) else []
        position_options = payload.get("position_options", []) if isinstance(payload.get("position_options"), list) else []
        salary_type_options = payload.get("salary_type_options", []) if isinstance(payload.get("salary_type_options"), list) else []
        team_choices = [{"value": str(v or ""), "label": _localize_hr_option(str(v or ""), "team", lang)} for v in team_options]
        position_choices = [
            {"value": str(v or ""), "label": _localize_hr_option(str(v or ""), "position", lang)} for v in position_options
        ]
        salary_type_choices = [
            {"value": str(v or ""), "label": _localize_hr_option(str(v or ""), "salary_type", lang)}
            for v in salary_type_options
        ]
        payload["team_choices"] = team_choices
        payload["position_choices"] = position_choices
        payload["salary_type_choices"] = salary_type_choices
        payload["team_label_map"] = {str(x.get("value", "") or ""): str(x.get("label", "") or "") for x in team_choices}
        payload["position_label_map"] = {str(x.get("value", "") or ""): str(x.get("label", "") or "") for x in position_choices}
        payload["salary_type_label_map"] = {
            str(x.get("value", "") or ""): str(x.get("label", "") or "") for x in salary_type_choices
        }
        return payload

    @app.route("/admin/users")
    @login_required
    def admin_users():
        if not current_user.has_permission("admin"):
            flash(translate("no_admin_perm"), "error")
            return redirect(url_for("index"))

        lang = get_lang()
        texts = LANGUAGES[lang]

        session = Session()
        users = session.query(User).all()
        sec_rows = session.query(LoginSecurity).all()
        trusted_ip_rows = session.query(LoginTrustedIp).all()
        session.close()
        now_ts = int(time.time())
        sec_map = {str(r.username): r for r in sec_rows}
        trusted_ip_count_map = {}
        for row in trusted_ip_rows:
            uname = str(row.username or "").strip()
            if not uname:
                continue
            trusted_ip_count_map[uname] = int(trusted_ip_count_map.get(uname, 0)) + 1

        return render_template_string(
            ADMIN_USERS_TEMPLATE,
            users=users,
            sec_map=sec_map,
            trusted_ip_count_map=trusted_ip_count_map,
            now_ts=now_ts,
            texts=texts,
            lang=lang,
            current_user=current_user,
        )

    @app.route("/admin/audit")
    @login_required
    def admin_audit_logs():
        if not current_user.has_permission("admin"):
            flash(translate("no_admin_perm"), "error")
            return redirect(url_for("index"))

        lang = get_lang()
        texts = LANGUAGES[lang]
        operator = (request.args.get("operator") or "").strip()
        action = (request.args.get("action") or "").strip()
        keyword = (request.args.get("keyword") or "").strip()
        try:
            page = max(1, int((request.args.get("page") or "1").strip() or "1"))
        except Exception:
            page = 1
        per_page = 100
        session = Session()
        q = session.query(AdminAuditLog)
        if operator:
            q = q.filter(AdminAuditLog.operator.like(f"%{operator}%"))
        if action:
            q = q.filter(AdminAuditLog.action.like(f"%{action}%"))
        if keyword:
            q = q.filter(
                (AdminAuditLog.target.like(f"%{keyword}%"))
                | (AdminAuditLog.detail.like(f"%{keyword}%"))
            )
        total = int(q.count() or 0)
        total_pages = max(1, (total + per_page - 1) // per_page)
        if page > total_pages:
            page = total_pages
        offset = (page - 1) * per_page
        logs = q.order_by(AdminAuditLog.id.desc()).offset(offset).limit(per_page).all()
        session.close()
        return render_template_string(
            ADMIN_AUDIT_TEMPLATE,
            logs=logs,
            filters={"operator": operator, "action": action, "keyword": keyword},
            pager={
                "page": page,
                "per_page": per_page,
                "total": total,
                "total_pages": total_pages,
                "has_prev": page > 1,
                "has_next": page < total_pages,
                "prev_page": page - 1 if page > 1 else 1,
                "next_page": page + 1 if page < total_pages else total_pages,
            },
            texts=texts,
            lang=lang,
            current_user=current_user,
        )

    @app.route("/admin")
    @login_required
    def admin_root():
        return redirect(url_for("admin_dashboard"))

    @app.route("/admin/dashboard")
    @login_required
    def admin_dashboard():
        if not current_user.has_permission("admin"):
            flash(translate("no_admin_perm"), "error")
            return redirect(url_for("index"))

        lang = get_lang()
        session = Session()
        try:
            user_total = int(session.query(User).count() or 0)
        finally:
            session.close()
        center = get_alert_center_payload()
        links = get_period_report_links()
        stats = {
            "user_total": user_total,
            "active_alerts": len(center.get("active") or []),
            "weekly_generated": bool(((links.get("weekly") or {}).get("generated"))),
            "monthly_generated": bool(((links.get("monthly") or {}).get("generated"))),
            "weekly_key": str(((links.get("weekly") or {}).get("key")) or ""),
            "monthly_key": str(((links.get("monthly") or {}).get("key")) or ""),
            "weekly_url": str(((links.get("weekly") or {}).get("url")) or ""),
            "monthly_url": str(((links.get("monthly") or {}).get("url")) or ""),
        }
        return render_template_string(ADMIN_DASHBOARD_TEMPLATE, stats=stats, lang=lang, texts=LANGUAGES.get(lang, LANGUAGES["zh"]))

    @app.route("/admin/alerts", methods=["GET", "POST"])
    @login_required
    def admin_alert_settings():
        if not current_user.has_permission("admin"):
            flash(translate("no_admin_perm"), "error")
            return redirect(url_for("index"))

        result_msg = ""
        if request.method == "POST":
            payload = {
                "log_stock_mt_min": request.form.get("log_stock_mt_min"),
                "sorting_stock_tray_min": request.form.get("sorting_stock_tray_min"),
                "kiln_done_stock_tray_max": request.form.get("kiln_done_stock_tray_max"),
                "product_shippable_tray_min": request.form.get("product_shippable_tray_min"),
            }
            saved = save_alert_settings(payload)
            append_threshold_version(saved, operator=str(getattr(current_user, "username", "") or ""))
            _audit(
                "update_alert_thresholds",
                target="inventory_alerts",
                detail=(
                    f"log_min={saved.get('log_stock_mt_min')},"
                    f"sorting_min={saved.get('sorting_stock_tray_min')},"
                    f"kiln_done_max={saved.get('kiln_done_stock_tray_max')},"
                    f"product_shippable_tray_min={saved.get('product_shippable_tray_min')}"
                ),
            )
            result_msg = "✅ 预警值已保存并生效"

        settings = get_alert_settings()
        return render_template_string(
            ADMIN_ALERT_SETTINGS_TEMPLATE,
            settings=settings,
            result_msg=result_msg,
        )

    @app.route("/admin/alert-center", methods=["GET", "POST"])
    @login_required
    def admin_alert_center():
        if not current_user.has_permission("admin"):
            flash(translate("no_admin_perm"), "error")
            return redirect(url_for("index"))

        result_msg = ""
        if request.method == "POST":
            form_type = str(request.form.get("form_type", "") or "").strip()
            if form_type == "engine_cfg":
                saved = save_alert_engine_config(
                    {
                        "dedup_seconds": request.form.get("dedup_seconds"),
                        "product_ready_threshold": request.form.get("product_ready_threshold"),
                        "product_full_threshold": request.form.get("product_full_threshold"),
                        "product_burst_threshold": request.form.get("product_burst_threshold"),
                        "enable_bottleneck_mode": request.form.get("enable_bottleneck_mode"),
                        "bottleneck_kiln_done_threshold": request.form.get("bottleneck_kiln_done_threshold"),
                        "bottleneck_relax_weight_pct": request.form.get("bottleneck_relax_weight_pct"),
                        "improve_bonus_2day": request.form.get("improve_bonus_2day"),
                        "improve_bonus_3day": request.form.get("improve_bonus_3day"),
                        "smooth_day_window_points": request.form.get("smooth_day_window_points"),
                        "smooth_week_window_points": request.form.get("smooth_week_window_points"),
                        "weight_raw_security": request.form.get("weight_raw_security"),
                        "weight_front_balance": request.form.get("weight_front_balance"),
                        "weight_middle_flow": request.form.get("weight_middle_flow"),
                        "weight_backlog_health": request.form.get("weight_backlog_health"),
                        "weight_product_health": request.form.get("weight_product_health"),
                    }
                )
                _audit(
                    "update_alert_engine_cfg",
                    target="alert_engine",
                    detail=(
                        f"dedup={saved.get('dedup_seconds')},"
                        f"ready={saved.get('product_ready_threshold')},"
                        f"full={saved.get('product_full_threshold')},"
                        f"burst={saved.get('product_burst_threshold')},"
                        f"bottleneck={saved.get('enable_bottleneck_mode')},"
                        f"relax={saved.get('bottleneck_relax_weight_pct')},"
                        f"bonus2={saved.get('improve_bonus_2day')},"
                        f"bonus3={saved.get('improve_bonus_3day')}"
                    ),
                )
                result_msg = "✅ 预警引擎参数已保存"
            elif form_type == "silence":
                try:
                    minutes = int(float(request.form.get("silence_minutes", "0") or 0))
                except Exception:
                    minutes = 0
                until_ts = set_alert_silence(minutes, operator=str(getattr(current_user, "username", "") or ""))
                _audit("set_alert_silence", target="alert_engine", detail=f"minutes={minutes},until={until_ts}")
                result_msg = "✅ 通知静默已更新"

        data = get_alert_center_payload()
        return render_template_string(ADMIN_ALERT_CENTER_TEMPLATE, data=data, result_msg=result_msg)

    @app.route("/admin/alert-center/action", methods=["POST"])
    @login_required
    def admin_alert_center_action():
        if not current_user.has_permission("admin"):
            return jsonify({"ok": False, "error": translate("no_admin_perm")}), 403

        alert_id = str(request.form.get("alert_id", "") or "").strip()
        action = str(request.form.get("action", "") or "").strip().lower()
        owner = str(request.form.get("owner", "") or "").strip()
        note = str(request.form.get("note", "") or "").strip()

        ok, msg = update_alert_event(
            event_id=alert_id,
            action=action,
            operator=str(getattr(current_user, "username", "") or ""),
            owner=owner,
            note=note,
        )
        if not ok:
            return redirect(url_for("admin_alert_center", result="0"))

        _audit("alert_event_action", target=alert_id, detail=f"action={action},owner={owner},note={note}")
        return redirect(url_for("admin_alert_center", result="1"))

    @app.route("/admin/hr-settings", methods=["GET", "POST"])
    @login_required
    def admin_hr_settings():
        if not current_user.has_permission("admin"):
            flash(translate("no_admin_perm"), "error")
            return redirect(url_for("index"))

        lang = get_lang()
        texts = LANGUAGES.get(lang, LANGUAGES["zh"])
        result_msg = ""
        error_msg = ""
        data = get_hr_admin_payload()
        if request.method == "POST":
            teams_json = request.form.get("teams_json", "")
            salary_types_json = request.form.get("salary_types_json", "")
            notes_text = request.form.get("notes_text", "")
            teams_text = request.form.get("teams_text", "")
            salary_types_text = request.form.get("salary_types_text", "")
            team_names = request.form.getlist("team_name")
            team_positions = request.form.getlist("team_positions")
            salary_types_list = request.form.getlist("salary_type")
            salary_cycles = request.form.getlist("salary_cycle")
            salary_descs = request.form.getlist("salary_desc")
            overtime_multipliers = request.form.getlist("ot_multiplier_option")
            default_overtime_multiplier = request.form.get("ot_default_multiplier", "")
            ok, msg, payload = save_hr_admin_settings(
                teams_json=teams_json,
                salary_types_json=salary_types_json,
                notes_text=notes_text,
                teams_text=teams_text,
                salary_types_text=salary_types_text,
                team_names=team_names,
                team_positions=team_positions,
                salary_types_list=salary_types_list,
                salary_cycles=salary_cycles,
                salary_descs=salary_descs,
                overtime_multipliers=overtime_multipliers,
                default_overtime_multiplier=default_overtime_multiplier,
            )
            data = payload
            if ok:
                result_msg = msg
                org_data = (data.get("org", {}) or {}) if isinstance(data, dict) else {}
                attendance_cfg = (org_data.get("attendance", {}) or {}) if isinstance(org_data, dict) else {}
                _audit(
                    "update_hr_settings",
                    target="hr_org",
                    detail=(
                        f"teams={len(org_data.get('teams', []))},"
                        f"salary_types={len(org_data.get('salary_types', {}))},"
                        f"ot_multipliers={len(attendance_cfg.get('overtime_multipliers', []))}"
                    ),
                )
            else:
                error_msg = msg
        return render_template_string(
            ADMIN_HR_SETTINGS_TEMPLATE,
            data=data,
            result_msg=result_msg,
            error_msg=error_msg,
            lang=lang,
            texts=texts,
        )

    @app.route("/admin/hr-employees", methods=["GET", "POST"])
    @login_required
    def admin_hr_employees():
        if not _can_access_hr_employees():
            flash(translate("no_perm"), "error")
            return redirect(url_for("index"))

        lang = get_lang()
        texts = LANGUAGES.get(lang, LANGUAGES["zh"])
        result_msg = ""
        error_msg = ""
        data = _attach_hr_choice_labels(get_hr_employees_payload(), lang)
        if request.method == "POST":
            form_action = str(request.form.get("form_action", "add") or "add").strip()
            if form_action == "edit":
                ok, msg, payload = update_hr_employee_from_admin(
                    original_name=request.form.get("original_name", ""),
                    team=request.form.get("team", ""),
                    position=request.form.get("position", ""),
                    salary_type=request.form.get("salary_type", ""),
                    salary_value=request.form.get("salary_value", ""),
                    join_date=request.form.get("join_date", ""),
                    status=request.form.get("status", ""),
                )
            elif form_action == "attendance":
                ok, msg, payload = add_hr_attendance_from_admin(
                    name=request.form.get("attendance_name", ""),
                    regular_hours=request.form.get("regular_hours", ""),
                    overtime_hours=request.form.get("overtime_hours", ""),
                    overtime_multiplier=request.form.get("overtime_multiplier", ""),
                    day=request.form.get("attendance_date", ""),
                )
            elif form_action == "attendance_batch":
                names_json = str(request.form.get("attendance_batch_names_json", "") or "").strip()
                selected_names = []
                if names_json:
                    try:
                        parsed = json.loads(names_json)
                        if isinstance(parsed, list):
                            selected_names = [str(x or "").strip() for x in parsed if str(x or "").strip()]
                    except Exception:
                        selected_names = []
                ok, msg, payload = apply_hr_attendance_batch_from_admin(
                    names=selected_names,
                    action=request.form.get("attendance_batch_action", ""),
                    day=request.form.get("attendance_date", ""),
                    overtime_hours=request.form.get("attendance_ot_hours", ""),
                    overtime_multiplier=request.form.get("attendance_ot_multiplier", ""),
                    special_hours=request.form.get("attendance_special_hours", ""),
                )
            else:
                ok, msg, payload = add_hr_employee_from_admin(
                    name=request.form.get("name", ""),
                    team=request.form.get("team", ""),
                    position=request.form.get("position", ""),
                    salary_type=request.form.get("salary_type", ""),
                    salary_value=request.form.get("salary_value", ""),
                    join_date=request.form.get("join_date", ""),
                )
            data = _attach_hr_choice_labels(payload, lang)
            if ok:
                result_msg = msg
                if form_action == "edit":
                    _audit(
                        "update_hr_employee",
                        target=str(request.form.get("original_name", "") or ""),
                        detail=(
                            f"team={request.form.get('team','')},"
                            f"position={request.form.get('position','')},"
                            f"salary_type={request.form.get('salary_type','')},"
                            f"status={request.form.get('status','')}"
                        ),
                    )
                elif form_action == "attendance":
                    _audit(
                        "add_hr_attendance",
                        target=str(request.form.get("attendance_name", "") or ""),
                        detail=(
                            f"date={request.form.get('attendance_date','')},"
                            f"regular_hours={request.form.get('regular_hours','')},"
                            f"overtime_hours={request.form.get('overtime_hours','')},"
                            f"overtime_multiplier={request.form.get('overtime_multiplier','')}"
                        ),
                    )
                elif form_action == "attendance_batch":
                    _audit(
                        "add_hr_attendance_batch",
                        target=str(request.form.get("attendance_date", "") or ""),
                        detail=(
                            f"action={request.form.get('attendance_batch_action','')},"
                            f"selected={request.form.get('attendance_batch_names_json','')},"
                            f"ot_hours={request.form.get('attendance_ot_hours','')},"
                            f"ot_multiplier={request.form.get('attendance_ot_multiplier','')},"
                            f"special_hours={request.form.get('attendance_special_hours','')}"
                        ),
                    )
                else:
                    _audit(
                        "add_hr_employee",
                        target=str(request.form.get("name", "") or ""),
                        detail=(
                            f"team={request.form.get('team','')},"
                            f"position={request.form.get('position','')},"
                            f"salary_type={request.form.get('salary_type','')}"
                        ),
                    )
            else:
                error_msg = msg
        return render_template_string(
            ADMIN_HR_EMPLOYEES_TEMPLATE,
            data=data,
            result_msg=result_msg,
            error_msg=error_msg,
            lang=lang,
            texts=texts,
            can_manage_hr_settings=bool(current_user.has_permission("admin")),
            hr_back_url=url_for("admin_root") if current_user.has_permission("admin") else url_for("index"),
        )

    @app.route("/admin/add_user", methods=["POST"])
    @login_required
    def add_user():
        if not current_user.has_permission("admin"):
            return jsonify({"error": translate("no_perm")}), 403

        username = request.form.get("username")
        password = request.form.get("password")
        role = request.form.get("role")

        if not all([username, password, role]):
            return jsonify({"error": translate("all_fields_required")}), 400
        if len(password) < 8:
            return jsonify({"error": "密码长度至少 8 位"}), 400

        session = Session()
        existing_user = session.query(User).filter_by(username=username).first()
        if existing_user:
            session.close()
            return jsonify({"error": translate("username_exists")}), 400

        new_user = User(username=username, role=role)
        new_user.set_password(password)
        session.add(new_user)
        session.commit()
        _audit("add_user", target=username, detail=f"role={role}")
        session.close()
        return jsonify({"success": True})

    @app.route("/admin/delete_user/<int:user_id>", methods=["POST"])
    @login_required
    def delete_user(user_id):
        if not current_user.has_permission("admin"):
            return jsonify({"error": translate("no_perm")}), 403
        if user_id == current_user.id:
            return jsonify({"error": translate("cannot_delete_self")}), 400

        session = Session()
        user = session.query(User).get(user_id)
        target_name = str(user.username) if user else f"id={user_id}"
        if user:
            session.delete(user)
            session.commit()
            _audit("delete_user", target=target_name, detail="deleted")
        session.close()
        return jsonify({"success": True})

    @app.route("/admin/reset_password/<int:user_id>", methods=["POST"])
    @login_required
    def reset_user_password(user_id):
        if not current_user.has_permission("admin"):
            return jsonify({"error": translate("no_perm")}), 403

        password = (request.form.get("password") or "").strip()
        if len(password) < 8:
            return jsonify({"error": "密码长度至少 8 位"}), 400

        session = Session()
        user = session.query(User).get(user_id)
        if not user:
            session.close()
            return jsonify({"error": "用户不存在"}), 404

        user.set_password(password)
        session.commit()
        _audit("reset_password", target=str(user.username), detail="password changed")
        session.close()
        return jsonify({"success": True})

    @app.route("/admin/unlock_user/<int:user_id>", methods=["POST"])
    @login_required
    def unlock_user(user_id):
        if not current_user.has_permission("admin"):
            return jsonify({"error": translate("no_perm")}), 403

        session = Session()
        user = session.query(User).get(user_id)
        if not user:
            session.close()
            return jsonify({"error": "用户不存在"}), 404

        sec = session.query(LoginSecurity).filter_by(username=user.username).first()
        if sec:
            sec.failed_count = 0
            sec.locked_until_ts = 0
            sec.last_fail_ts = 0
            session.commit()
        session.close()
        _audit("unlock_user", target=str(user.username), detail="manual unlock")
        return jsonify({"success": True})

    @app.route("/admin/clear_trusted_ips/<int:user_id>", methods=["POST"])
    @login_required
    def clear_trusted_ips(user_id):
        if not current_user.has_permission("admin"):
            return jsonify({"error": translate("no_perm")}), 403

        session = Session()
        user = session.query(User).get(user_id)
        if not user:
            session.close()
            return jsonify({"error": "用户不存在"}), 404

        rows = session.query(LoginTrustedIp).filter_by(username=user.username).all()
        cleared = len(rows)
        for row in rows:
            session.delete(row)
        session.commit()
        session.close()
        _audit("clear_trusted_ips", target=str(user.username), detail=f"count={cleared}")
        return jsonify({"success": True, "cleared": cleared})

    @app.route("/login", methods=["GET", "POST"])
    def login():
        lang = get_lang()
        texts = LANGUAGES[lang]
        if current_user.is_authenticated:
            return redirect(url_for("index"))

        form = LoginForm()
        if form.validate_on_submit():
            session = Session()
            username = (form.username.data or "").strip()
            client_ip = _client_ip()
            user_agent = str(request.headers.get("User-Agent", "") or "").strip()
            user = session.query(User).filter_by(username=username).first()
            sec = session.query(LoginSecurity).filter_by(username=username).first()
            now_ts = int(time.time())
            is_new_external_ip = False
            if sec and int(sec.locked_until_ts or 0) > now_ts:
                remain_min = max(1, int((int(sec.locked_until_ts) - now_ts + 59) // 60))
                flash(f"账号已临时锁定，请 {remain_min} 分钟后重试", "error")
                session.close()
                return render_template_string(LOGIN_TEMPLATE, form=form, texts=texts, lang=lang)
            ok = bool(user and user.verify_password(form.password.data))
            # 兼容旧明文口令：登录成功后自动升级为哈希。
            if ok and user and not User._is_password_hash(user.password):
                user.set_password(form.password.data)
                session.commit()
            if ok:
                if sec:
                    sec.failed_count = 0
                    sec.locked_until_ts = 0
                    sec.last_fail_ts = 0
                if user and client_ip and (not _is_lan_ip(client_ip)):
                    ip_row = session.query(LoginTrustedIp).filter_by(username=user.username, ip=client_ip).first()
                    if ip_row:
                        ip_row.last_seen_ts = now_ts
                        ip_row.last_user_agent = user_agent[:300]
                    else:
                        is_new_external_ip = True
                        session.add(
                            LoginTrustedIp(
                                username=user.username,
                                ip=client_ip,
                                first_seen_ts=now_ts,
                                last_seen_ts=now_ts,
                                last_user_agent=user_agent[:300],
                            )
                        )
                session.commit()
            else:
                if not sec:
                    sec = LoginSecurity(username=username, failed_count=0, locked_until_ts=0, last_fail_ts=0)
                    session.add(sec)
                sec.failed_count = int(sec.failed_count or 0) + 1
                sec.last_fail_ts = now_ts
                # 连续 5 次失败，锁定 15 分钟。
                if sec.failed_count >= 5:
                    sec.locked_until_ts = now_ts + 15 * 60
                    sec.failed_count = 0
                    flash("密码错误次数过多，账号已锁定 15 分钟", "error")
                session.commit()
            if ok and user:
                login_user(user)
                session.close()
                if is_new_external_ip:
                    _audit(
                        "external_new_ip_login",
                        target=str(user.username),
                        detail=f"ip={client_ip}",
                        operator=str(user.username),
                    )
                    _notify_admin_external_login(str(user.username), client_ip, user_agent)
                return redirect(url_for("index"))
            session.close()
            flash(texts["invalid_credentials"], "error")

        return render_template_string(LOGIN_TEMPLATE, form=form, texts=texts, lang=lang)

    @app.route("/logout")
    @login_required
    def logout():
        logout_user()
        return redirect(url_for("login"))

    @app.route("/tg/mini")
    def tg_mini():
        # 中文注释：MiniApp 启动页，前端 JS 读取 initData 并换取 Web 会话。
        bot_username = os.getenv("BOT_USERNAME", "").strip().lstrip("@")
        tg_reopen_url = f"https://t.me/{bot_username}?startapp=home" if bot_username else ""
        return render_template_string(
            """
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>AIF MiniApp</title>
  <script src="https://telegram.org/js/telegram-web-app.js"></script>
  <style>
    body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #f5f7fb; color: #1f2937; }
    .card { max-width: 520px; margin: 32px auto; padding: 20px; border-radius: 10px; background: #fff; box-shadow: 0 8px 24px rgba(0,0,0,0.08); }
    .muted { color: #6b7280; font-size: 14px; }
    .actions { margin-top: 14px; display: none; }
    .btn { display: inline-block; padding: 10px 14px; border-radius: 8px; background: #0ea5e9; color: #fff; text-decoration: none; font-size: 14px; border: none; cursor: pointer; }
  </style>
</head>
<body>
  <div class="card">
    <h3 style="margin-top:0;">AIF MiniApp 登录中...</h3>
    <p id="msg" class="muted">正在验证 Telegram 身份，请稍候。</p>
    <div id="actions" class="actions">
      <button id="open-tg-btn" class="btn" type="button">回到 Telegram 机器人</button>
    </div>
  </div>
  <script>
    function openBotChat(url) {
      const tg = window.Telegram && window.Telegram.WebApp ? window.Telegram.WebApp : null;
      try {
        if (tg && typeof tg.openTelegramLink === "function") {
          tg.openTelegramLink(url);
          return;
        }
      } catch (e) {}
      window.location.href = url;
    }

    (async function () {
      try {
        const tg = window.Telegram && window.Telegram.WebApp ? window.Telegram.WebApp : null;
        if (!tg) throw new Error("未检测到 Telegram WebApp 环境");
        tg.ready();
        if (tg.expand) tg.expand();
        const initData = tg.initData || "";
        if (!initData) {
          const msg = "Telegram initData 为空，请从机器人按钮进入";
          document.getElementById("msg").textContent = msg;
          const reopenUrl = "{{ tg_reopen_url }}";
          if (reopenUrl) {
            document.getElementById("open-tg-btn").onclick = function () { openBotChat(reopenUrl); };
            document.getElementById("actions").style.display = "block";
          }
          return;
        }
        const res = await fetch("/tg/auth", {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify({ init_data: initData })
        });
        const data = await res.json();
        if (!res.ok || !data.ok) throw new Error(data.error || "登录失败");
        window.location.replace("/");
      } catch (e) {
        document.getElementById("msg").textContent = e.message || String(e);
      }
    })();
  </script>
</body>
</html>
            """
            ,
            tg_reopen_url=tg_reopen_url,
        )

    @app.route("/tg/auth", methods=["POST"])
    def tg_auth():
        payload = request.get_json(silent=True) or {}
        init_data = str(payload.get("init_data", "") or "").strip()
        try:
            bot_token = get_bot_token()
        except Exception:
            return jsonify({"ok": False, "error": "BOT_TOKEN 未配置"}), 500

        user = _verify_tg_init_data(init_data, bot_token)
        if not user:
            return jsonify({"ok": False, "error": "Telegram 验签失败或数据过期"}), 401

        uid = str(user.get("id", "") or "").strip()
        if not uid:
            return jsonify({"ok": False, "error": "缺少 Telegram 用户ID"}), 400

        session = Session()
        try:
            role_row = session.query(TgUserRole).filter_by(user_id=uid).first()
            role = str(role_row.role or "") if role_row else ""
            if role not in ("管理员", "老板"):
                return jsonify({"ok": False, "error": "仅管理员/老板可访问 MiniApp"}), 403

            web_user = _get_or_create_web_user_for_role(session, role, uid)
            login_user(web_user)
            return jsonify({"ok": True, "role": role, "username": web_user.username})
        finally:
            session.close()
