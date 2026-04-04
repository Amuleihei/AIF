import logging
import os
import sys
import time
from datetime import datetime
from urllib import error as urllib_error
from urllib import request as urllib_request

# =====================================================
# 路径初始化
# =====================================================

BASE = os.path.dirname(os.path.dirname(__file__))
sys.path.append(BASE)

# =====================================================
# Telegram
# =====================================================

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    MenuButtonWebApp,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    Update,
    WebAppInfo,
)
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
from telegram.request import HTTPXRequest

from tg_bot.config import get_bot_token, get_miniapp_url

# =====================================================
# 权限系统
# =====================================================

from modules.auth.auth_engine import (
    auth_command,
    get_admin_ids,
    get_role,
    has_permission,
    load as load_auth_users,
    set_user_role,
)

# =====================================================
# 🌏 多语言模块
# =====================================================

from modules.i18n.translate_engine import translate_from_cn, translate_to_cn
from modules.i18n.shortcut_engine import shortcut_to_cn
from web.models import Session, TgSetting, TgPendingUser
from web.services.entry_reminder_service import get_daily_missing_entry_status
from web.services.daily_once_link_service import issue_daily_once_token, build_daily_once_link
from web.services.tg_login_token_service import issue_tg_login_token, build_tg_login_link
from modules.report.report_engine import handle_report
from modules.report.daily_report_engine import handle_daily_report
from modules.report.system_report import handle_system_report
from modules.report.reconcile_engine import handle_reconcile
from modules.system.system_engine import handle_system

# =====================================================
# 日志系统
# =====================================================

LOG_FILE = os.path.join(BASE, "logs/tg_bot.log")
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
TG_SYSTEM_KEY = "tg_system_cfg"
TG_PENDING_KEY = "tg_pending_users"
TG_ENTRY_REMINDER_LAST_DAY_KEY = "entry_reminder_last_sent_day"
TG_DAILY_ONCE_LAST_DAY_KEY = "daily_once_report_last_sent_day"
TG_CF_TUNNEL_STATE_KEY = "cf_tunnel_state"
TG_CF_TUNNEL_LAST_CHANGE_KEY = "cf_tunnel_last_change_at"

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)

# 避免第三方库把 Telegram 请求 URL（含 token）写进日志
for noisy in ("httpx", "httpcore", "telegram", "telegram.ext"):
    logging.getLogger(noisy).setLevel(logging.WARNING)

# =====================================================
# 指令权限级别
# =====================================================

def required_level(text: str) -> int:

    admin_cmds = [
        "清空",
        "开始挖矿",
        "停止挖矿",
        "系统重启",
        "全厂停产",
        "全厂加班",
    ]

    if (text or "").strip().startswith(("强制", "force", "Force")):
        return 2

    for cmd in admin_cmds:
        if text.startswith(cmd):
            return 2

    return 1


BOSS_TEXT_TO_CMD = {
    "工厂状态": "工厂状态",
    "库存概况": "库存概况",
    "生产概况": "工厂状态",
    "窑概况": "窑概况",
    "窑状况": "窑概况",
}


def boss_menu_keyboard(lang: str | None = None) -> ReplyKeyboardMarkup:
    lang = lang or get_default_lang()
    rows = [
        [ui_label("工厂状态", lang), ui_label("库存概况", lang)],
        [ui_label("窑概况", lang)],
    ]
    if _workspace_base_url():
        rows.append([f"🌐 {ui_label('工作台', lang)}"])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


def boss_home_text() -> str:
    return "📊 老板菜单\n工厂状态 / 库存概况 / 窑概况"


def is_boss_menu_command(text: str) -> bool:
    t = text.strip()
    return t in ("查询菜单", "老板菜单")


def is_exit_boss_mode_command(text: str) -> bool:
    t = text.strip()
    return t in ("退出老板菜单", "退出老板模式", "退出菜单")


def is_general_menu_command(text: str) -> bool:
    t = text.strip()
    return t in ("菜单", "录入菜单", "管理员菜单", "မီနူး")


LANG_BTN_MY = "မြန်မာ"
LANG_BTN_EN = "English"

ZH_TO_MY = {
    "菜单": "မီနူး",
    "老板菜单": "သူဌေးမီနူး",
    "今日总览": "ယနေ့အကျဉ်းချုပ်",
    "工厂状态": "စက်ရုံအခြေအနေ",
    "库存概况": "စတော့အကျဉ်းချုပ်",
    "生产概况": "ထုတ်လုပ်မှုအကျဉ်းချုပ်",
    "窑概况": "မီးဖိုအကျဉ်းချုပ်",
    "财务概况": "ငွေကြေးအကျဉ်းချုပ်",
    "财务明细": "ငွေကြေးအသေးစိတ်",
    "系统状态": "စနစ်အခြေအနေ",
    "日报": "နေ့စဉ်အစီရင်ခံစာ",
    "员工添加": "ဝန်ထမ်းထည့်",
    "员工删除": "ဝန်ထမ်းဖျက်",
    "添加员工": "ဝန်ထမ်းထည့်",
    "删除员工": "ဝန်ထမ်းဖျက်",
    "员工列表": "ဝန်ထမ်းစာရင်း",
    "考勤": "တက်ရောက်မှု",
    "工资试算": "လစာတွက်ချက်",
    "HR帮助": "HR အကူအညီ",
    "用户列表": "အသုံးပြုသူစာရင်း",
    "打印日报": "နေ့စဉ်စာရင်းပုံနှိပ်",
    "打印台账": "ထုတ်လုပ်မှုစာရင်းပုံနှိပ်",
    "打印机列表": "ပရင်တာစာရင်း",
    "开始挖矿": "မိုင်းစတင်",
    "停止挖矿": "မိုင်းရပ်",
    "切换语言": "ဘာသာပြောင်း",
    "导出Excel": "Excel ထုတ်ယူ",
    "工作台": "လုပ်ငန်းခွင်",
}
MY_TO_ZH = {v: k for k, v in ZH_TO_MY.items()}

ZH_TO_EN = {
    "菜单": "menu",
    "老板菜单": "boss menu",
    "今日总览": "today overview",
    "工厂状态": "factory status",
    "库存概况": "stock overview",
    "生产概况": "production overview",
    "窑概况": "kiln overview",
    "财务概况": "finance overview",
    "财务明细": "finance details",
    "系统状态": "system status",
    "日报": "daily report",
    "员工添加": "add employee",
    "员工删除": "delete employee",
    "添加员工": "add employee",
    "删除员工": "delete employee",
    "员工列表": "employee list",
    "考勤": "attendance",
    "工资试算": "payroll estimation",
    "HR帮助": "hr help",
    "用户列表": "users",
    "打印日报": "print daily report",
    "打印台账": "print ledger",
    "打印机列表": "printers",
    "开始挖矿": "start mining",
    "停止挖矿": "stop mining",
    "切换语言": "language",
    "导出Excel": "export excel",
    "工作台": "workspace",
}
EN_TO_ZH = {v: k for k, v in ZH_TO_EN.items()}
# Backward-compatible aliases for old UI inputs.
EN_TO_ZH.update({
    "add user": "员工添加",
    "delete user": "员工删除",
})

I18N_TEXT = {
    "admin_new_user_title": {
        "zh": "🆕 有新用户关注",
        "my": "🆕 အသုံးပြုသူအသစ် ဝင်ရောက်လာပါသည်",
        "en": "🆕 New user subscribed",
    },
    "admin_user_id": {
        "zh": "用户ID",
        "my": "အသုံးပြုသူ ID",
        "en": "User ID",
    },
    "admin_username": {
        "zh": "用户名",
        "my": "အသုံးပြုသူအမည်",
        "en": "Username",
    },
    "start_waiting_role": {
        "zh": "👋 欢迎使用，请等待管理员分配角色权限。",
        "my": "👋 ကြိုဆိုပါတယ်၊ အက်မင်က အခန်းကဏ္ဍခွင့်ပြုချက်ပေးသည်ကို စောင့်ပါ။",
        "en": "👋 Welcome. Please wait for an admin to assign your role.",
    },
    "start_logged_in": {
        "zh": "✅ 已登录，发送“菜单”查看功能。",
        "my": "✅ ဝင်ရောက်ပြီးပါပြီ၊ \"မီနူး\" ပို့ပြီး လုပ်ဆောင်ချက်များကိုကြည့်ပါ။",
        "en": "✅ Logged in. Send \"menu\" to view available features.",
    },
    "no_permission_wait_admin": {
        "zh": "⛔ 尚未开通权限，请等待管理员设置角色。",
        "my": "⛔ သင့်ခွင့်ပြုချက် မဖွင့်ရသေးပါ၊ အက်မင်က role သတ်မှတ်သည်ကို စောင့်ပါ။",
        "en": "⛔ Access not enabled yet. Please wait for an admin to set your role.",
    },
    "role_opened": {
        "zh": "✅ 你的权限已开通：{role}\n发送“菜单”查看可用功能。",
        "my": "✅ သင့်ခွင့်ပြုချက် ဖွင့်ပြီးပါပြီ: {role}\n\"မီနူး\" ပို့ပြီး အသုံးပြုနိုင်သောလုပ်ဆောင်ချက်များကို ကြည့်ပါ။",
        "en": "✅ Your access has been enabled: {role}\nSend \"menu\" to view available features.",
    },
}

def effective_lang(role: str | None, uid: str | None) -> str:
    return get_user_lang(uid)


def normalize_lang(lang: str | None) -> str:
    t = str(lang or "").strip().lower()
    if t in ("zh", "cn", "chinese", "中文"):
        return "zh"
    if t in ("my", "mm", "burmese", "မြန်မာ", "缅语"):
        return "my"
    if t in ("en", "english", "英文"):
        return "en"
    return "zh"


def tr_text(key: str, lang: str | None = None, **kwargs) -> str:
    table = I18N_TEXT.get(key, {})
    code = normalize_lang(lang or get_default_lang())
    text = table.get(code) or table.get("zh") or key
    if kwargs:
        try:
            return text.format(**kwargs)
        except Exception:
            return text
    return text


def _load_system_cfg() -> dict:
    session = Session()
    try:
        default_lang = "zh"
        by_user = {}
        for row in session.query(TgSetting).all():
            key = str(row.key or "")
            value = str(row.value or "")
            if key == "lang_default":
                default_lang = normalize_lang(value)
            elif key.startswith("lang_user:"):
                uid = key.split(":", 1)[1].strip()
                if uid:
                    by_user[uid] = normalize_lang(value)
        return {"lang_policy": {"default": default_lang, "by_user": by_user}}
    except Exception:
        return {}
    finally:
        session.close()


def _save_system_cfg(cfg: dict) -> None:
    if not isinstance(cfg, dict):
        cfg = {}
    lang_policy = cfg.get("lang_policy", {}) if isinstance(cfg.get("lang_policy"), dict) else {}
    default_lang = normalize_lang(lang_policy.get("default", "zh"))
    by_user = lang_policy.get("by_user", {}) if isinstance(lang_policy.get("by_user"), dict) else {}

    session = Session()
    try:
        keep_keys = {"lang_default"}
        row = session.query(TgSetting).filter_by(key="lang_default").first()
        if not row:
            row = TgSetting(key="lang_default", value=default_lang)
            session.add(row)
        else:
            row.value = default_lang

        for uid, lang in by_user.items():
            uid_str = str(uid).strip()
            if not uid_str:
                continue
            k = f"lang_user:{uid_str}"
            keep_keys.add(k)
            ur = session.query(TgSetting).filter_by(key=k).first()
            if not ur:
                ur = TgSetting(key=k, value=normalize_lang(lang))
                session.add(ur)
            else:
                ur.value = normalize_lang(lang)

        rows = session.query(TgSetting).all()
        for r in rows:
            k = str(r.key or "")
            if k.startswith("lang_user:") and k not in keep_keys:
                session.delete(r)
        session.commit()
    finally:
        session.close()


def _load_pending_users() -> dict:
    session = Session()
    try:
        pending = {}
        rows = session.query(TgPendingUser).all()
        for row in rows:
            uid = str(row.user_id or "").strip()
            if not uid:
                continue
            pending[uid] = {
                "username": str(row.username or ""),
                "time": int(row.created_at or 0),
            }
        return {"pending": pending}
    except Exception:
        return {"pending": {}}
    finally:
        session.close()


def _save_pending_users(d: dict) -> None:
    pending = d.get("pending", {}) if isinstance(d, dict) and isinstance(d.get("pending"), dict) else {}
    session = Session()
    try:
        session.query(TgPendingUser).delete()
        for uid, item in pending.items():
            if not isinstance(item, dict):
                item = {}
            uid_str = str(uid).strip()
            if not uid_str:
                continue
            session.add(
                TgPendingUser(
                    user_id=uid_str,
                    username=str(item.get("username", "") or ""),
                    created_at=int(item.get("time", int(time.time())) or int(time.time())),
                )
            )
        session.commit()
    finally:
        session.close()


def _get_tg_setting_value(key: str, default: str = "") -> str:
    session = Session()
    try:
        row = session.query(TgSetting).filter_by(key=str(key)).first()
        if not row:
            return str(default or "")
        return str(row.value or "")
    except Exception:
        return str(default or "")
    finally:
        session.close()


def _set_tg_setting_value(key: str, value: str) -> None:
    session = Session()
    try:
        row = session.query(TgSetting).filter_by(key=str(key)).first()
        if not row:
            row = TgSetting(key=str(key), value=str(value or ""))
            session.add(row)
        else:
            row.value = str(value or "")
        session.commit()
    except Exception:
        session.rollback()
    finally:
        session.close()


def _entry_reminder_target_uids() -> list[str]:
    users = load_auth_users().get("users", {})
    targets = []
    for uid, role in users.items():
        r = str(role or "").strip()
        if r in ("财务", "操作员"):
            targets.append(str(uid))
    # 兜底：若统计/财务组没人，避免提醒丢失，发给管理员。
    if not targets:
        targets = [str(uid) for uid in get_admin_ids()]
    return targets


def _entry_reminder_text_for_uid(uid: str, status: dict) -> str:
    lang = get_user_lang(uid)
    missing_sort = bool(status.get("missing_sort"))
    missing_secondary = bool(status.get("missing_secondary_sort"))
    day = str(status.get("day", "") or datetime.now().strftime("%Y-%m-%d"))
    items_zh = []
    if missing_sort:
        items_zh.append("今日已入窑但未录入拣选消耗")
    if missing_secondary:
        items_zh.append("今日已入成品但未录入二选消耗")

    if lang == "my":
        title = f"⏰ {day} မှတ်တမ်း ဖြည့်ရန် သတိပေး"
        body = []
        if missing_sort:
            body.append("• ယနေ့ မီးဖိုထည့်ပြီးသော်လည်း ရွေးချယ်သုံးစွဲမှု မဖြည့်ရသေးပါ")
        if missing_secondary:
            body.append("• ယနေ့ ကုန်ချောထည့်ပြီးသော်လည်း ဒုတိယရွေးသုံးစွဲမှု မဖြည့်ရသေးပါ")
        tail = "ကျေးဇူးပြု၍ Web တွင် ယနေ့အချက်အလက်ကို ဖြည့်ပေးပါ။"
        return "\n".join([title] + body + [tail])
    if lang == "en":
        title = f"⏰ {day} Data Entry Reminder"
        body = []
        if missing_sort:
            body.append("• Kiln load exists but sorting consumption is missing")
        if missing_secondary:
            body.append("• Product inbound exists but secondary-sort consumption is missing")
        tail = "Please complete today's entries in Web."
        return "\n".join([title] + body + [tail])

    title = f"⏰ {day} 录入提醒"
    body = [f"• {item}" for item in items_zh]
    tail = "请在 Web 端补齐今日数据。"
    return "\n".join([title] + body + [tail])


async def scheduled_entry_reminder(context: ContextTypes.DEFAULT_TYPE):
    try:
        now = datetime.now()
        if now.hour < 18:
            return
        day = now.strftime("%Y-%m-%d")
        if _get_tg_setting_value(TG_ENTRY_REMINDER_LAST_DAY_KEY, "") == day:
            return

        status = get_daily_missing_entry_status(day)
        if not bool(status.get("has_missing")):
            return

        target_uids = _entry_reminder_target_uids()
        sent_ok = False
        for uid in target_uids:
            try:
                await context.bot.send_message(chat_id=str(uid), text=_entry_reminder_text_for_uid(str(uid), status))
                sent_ok = True
            except Exception:
                logging.exception(f"entry reminder send failed: {uid}")

        if sent_ok:
            _set_tg_setting_value(TG_ENTRY_REMINDER_LAST_DAY_KEY, day)
    except Exception:
        logging.exception("scheduled_entry_reminder failed")


def _daily_once_target_uids() -> list[str]:
    out = [str(uid) for uid in get_admin_ids()]
    return [x for x in out if str(x).strip()]


def _daily_once_web_base_url() -> str:
    env_url = str(os.getenv("AIF_WEB_BASE_URL", "") or "").strip()
    if env_url:
        return env_url.rstrip("/")
    cfg_url = str(_get_tg_setting_value("web_base_url", "") or "").strip()
    return cfg_url.rstrip("/") if cfg_url else ""


def _workspace_base_url() -> str:
    raw = str(os.getenv("AIF_WEB_BASE_URL", "") or "").strip()
    if not raw:
        raw = str(get_miniapp_url() or "").strip()
    if not raw:
        raw = str(_get_tg_setting_value("web_base_url", "") or "").strip()
    raw = raw.rstrip("/")
    if raw.endswith("/tg/mini"):
        raw = raw[:-8]
    return raw.rstrip("/")


def _workspace_menu_url() -> str:
    base = _workspace_base_url()
    if not base:
        return ""
    return f"{base}/tg/mini"


def _workspace_login_url_for_uid(uid: str) -> str:
    base = _workspace_base_url()
    uid_text = str(uid or "").strip()
    if not base or not uid_text:
        return ""
    try:
        token = issue_tg_login_token(uid_text, ttl_seconds=3600)
        return build_tg_login_link(base, token)
    except Exception:
        logging.exception("issue_tg_login_token failed uid=%s", uid_text)
        return ""


def _daily_once_text_for_uid(uid: str, day: str, link: str) -> str:
    lang = get_user_lang(uid)
    if lang == "my":
        return "\n".join(
            [
                f"📘 {day} နေ့စဉ်အစီရင်ခံစာ (တစ်ကြိမ်သုံးလင့်ခ်)",
                "⚠️ ဤလင့်ခ်သည် တစ်ကြိမ်သာအသုံးပြုနိုင်ပြီး ဒုတိယအကြိမ်ဝင်ရန် Login လိုအပ်ပါသည်။",
                link,
            ]
        )
    if lang == "en":
        return "\n".join(
            [
                f"📘 Daily Report {day} (One-time Link)",
                "⚠️ This link can be opened once only. Second access requires login.",
                link,
            ]
        )
    return "\n".join(
        [
            f"📘 {day} 日报（一次性链接）",
            "⚠️ 此链接为一次性链接，二次访问需登录。",
            link,
        ]
    )


async def scheduled_daily_once_report_link(context: ContextTypes.DEFAULT_TYPE):
    try:
        now = datetime.now()
        if now.hour < 18 or (now.hour == 18 and now.minute < 30):
            return
        day = now.strftime("%Y-%m-%d")
        if _get_tg_setting_value(TG_DAILY_ONCE_LAST_DAY_KEY, "") == day:
            return

        base_url = _daily_once_web_base_url()
        if not base_url:
            logging.warning("daily_once_report skipped: empty AIF_WEB_BASE_URL/web_base_url")
            return

        sent_ok = False
        for uid in _daily_once_target_uids():
            try:
                token = issue_daily_once_token(uid, day)
                link = build_daily_once_link(base_url, token, lang=get_user_lang(uid))
                if not link:
                    continue
                await context.bot.send_message(chat_id=str(uid), text=_daily_once_text_for_uid(str(uid), day, link))
                sent_ok = True
            except Exception:
                logging.exception(f"daily_once_report send failed: {uid}")

        if sent_ok:
            _set_tg_setting_value(TG_DAILY_ONCE_LAST_DAY_KEY, day)
    except Exception:
        logging.exception("scheduled_daily_once_report_link failed")


def _cloudflared_ha_connections() -> tuple[bool, int, str]:
    url = "http://127.0.0.1:20241/metrics"
    try:
        with urllib_request.urlopen(url, timeout=3) as resp:
            payload = resp.read().decode("utf-8", errors="ignore")
    except urllib_error.URLError as e:
        return False, 0, f"metrics_unreachable:{e.reason}"
    except Exception as e:
        return False, 0, f"metrics_unreachable:{e}"

    for line in payload.splitlines():
        if line.startswith("cloudflared_tunnel_ha_connections "):
            raw = line.split(" ", 1)[1].strip()
            try:
                n = int(float(raw))
            except Exception:
                return False, 0, f"metric_parse_error:{raw}"
            if n >= 1:
                return True, n, "ok"
            return False, n, "zero_connections"
    return False, 0, "metric_missing"


def _cf_tunnel_alert_text(uid: str, is_recovery: bool, detail: str, ha_connections: int) -> str:
    lang = get_user_lang(uid)
    now_txt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if is_recovery:
        if lang == "my":
            return (
                "✅ Cloudflare Tunnel ပြန်လည်ချိတ်ဆက်ပြီးပါပြီ\n"
                f"အချိန်: {now_txt}\n"
                f"HA Connections: {ha_connections}\n"
                "ပြင်ပဝင်ရောက်မှု ပြန်လည်အသုံးပြုနိုင်ပါပြီ။"
            )
        if lang == "en":
            return (
                "✅ Cloudflare Tunnel recovered\n"
                f"Time: {now_txt}\n"
                f"HA Connections: {ha_connections}\n"
                "External access is available again."
            )
        return (
            "✅ Cloudflare Tunnel 已恢复\n"
            f"时间: {now_txt}\n"
            f"HA连接数: {ha_connections}\n"
            "外网访问已恢复。"
        )

    if lang == "my":
        return (
            "⚠️ Cloudflare Tunnel ပြတ်တောက်သတိပေး\n"
            f"အချိန်: {now_txt}\n"
            f"အကြောင်းရင်း: {detail}\n"
            f"HA Connections: {ha_connections}\n"
            "ပြင်ပ URL ဝင်မရနိုင်ခြေရှိပါသည်။"
        )
    if lang == "en":
        return (
            "⚠️ Cloudflare Tunnel outage alert\n"
            f"Time: {now_txt}\n"
            f"Reason: {detail}\n"
            f"HA Connections: {ha_connections}\n"
            "The public URL may be unreachable."
        )
    return (
        "⚠️ Cloudflare Tunnel 断连预警\n"
        f"时间: {now_txt}\n"
        f"原因: {detail}\n"
        f"HA连接数: {ha_connections}\n"
        "外网地址可能无法访问。"
    )


async def scheduled_cloudflared_tunnel_watch(context: ContextTypes.DEFAULT_TYPE):
    try:
        is_up, ha_connections, detail = _cloudflared_ha_connections()
        prev = _get_tg_setting_value(TG_CF_TUNNEL_STATE_KEY, "unknown").strip().lower()
        now_txt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if is_up:
            if prev == "down":
                for uid in _daily_once_target_uids():
                    try:
                        await context.bot.send_message(
                            chat_id=str(uid),
                            text=_cf_tunnel_alert_text(str(uid), True, detail, ha_connections),
                        )
                    except Exception:
                        logging.exception(f"cf_tunnel_recovery send failed: {uid}")
            _set_tg_setting_value(TG_CF_TUNNEL_STATE_KEY, "up")
            _set_tg_setting_value(TG_CF_TUNNEL_LAST_CHANGE_KEY, now_txt)
            return

        if prev != "down":
            for uid in _daily_once_target_uids():
                try:
                    await context.bot.send_message(
                        chat_id=str(uid),
                        text=_cf_tunnel_alert_text(str(uid), False, detail, ha_connections),
                    )
                except Exception:
                    logging.exception(f"cf_tunnel_down send failed: {uid}")
            _set_tg_setting_value(TG_CF_TUNNEL_LAST_CHANGE_KEY, now_txt)
        _set_tg_setting_value(TG_CF_TUNNEL_STATE_KEY, "down")
    except Exception:
        logging.exception("scheduled_cloudflared_tunnel_watch failed")


def _mark_pending(uid: str, username: str) -> bool:
    d = _load_pending_users()
    pending = d.get("pending", {})
    if uid in pending:
        return False
    pending[uid] = {
        "username": username,
        "time": int(time.time()),
    }
    d["pending"] = pending
    _save_pending_users(d)
    return True


def _clear_pending(uid: str) -> None:
    d = _load_pending_users()
    pending = d.get("pending", {})
    if uid in pending:
        pending.pop(uid, None)
        d["pending"] = pending
        _save_pending_users(d)


def _role_set_keyboard(target_uid: str):
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("管理员", callback_data=f"setrole:{target_uid}:管理员"),
        InlineKeyboardButton("老板", callback_data=f"setrole:{target_uid}:老板"),
    ]])


async def _notify_admin_new_user(update: Update, context: ContextTypes.DEFAULT_TYPE, uid: str):
    username = ""
    if update.effective_user:
        username = update.effective_user.username or ""

    first_time = _mark_pending(uid, username)
    if not first_time:
        return

    admins = get_admin_ids()
    if not admins:
        return

    sys_lang = get_default_lang()
    msg = f"{tr_text('admin_new_user_title', sys_lang)}\n{tr_text('admin_user_id', sys_lang)}: {uid}"
    if username:
        msg += f"\n{tr_text('admin_username', sys_lang)}: @{username}"
    for admin_id in admins:
        try:
            await context.bot.send_message(
                chat_id=admin_id,
                text=msg,
                reply_markup=_role_set_keyboard(uid),
            )
        except Exception:
            logging.exception(f"notify admin failed: {admin_id}")


def get_default_lang() -> str:
    cfg = _load_system_cfg()
    return normalize_lang(cfg.get("lang_policy", {}).get("default", "zh"))


def get_user_lang(uid: str | None) -> str:
    cfg = _load_system_cfg()
    policy = cfg.get("lang_policy", {})
    if uid:
        u = (policy.get("by_user", {}) or {}).get(uid)
        if u:
            return normalize_lang(u)
    return normalize_lang(policy.get("default", "zh"))


def set_default_lang(lang: str) -> None:
    cfg = _load_system_cfg()
    policy = cfg.get("lang_policy", {})
    policy["default"] = normalize_lang(lang)
    cfg["lang_policy"] = policy
    _save_system_cfg(cfg)


def set_user_lang(uid: str, lang: str) -> None:
    if not uid:
        return
    cfg = _load_system_cfg()
    policy = cfg.get("lang_policy", {})
    by_user = policy.get("by_user", {}) or {}
    by_user[str(uid)] = normalize_lang(lang)
    policy["by_user"] = by_user
    cfg["lang_policy"] = policy
    _save_system_cfg(cfg)


def toggle_default_lang() -> str:
    cur = get_default_lang()
    if cur == "zh":
        nxt = "my"
    elif cur == "my":
        nxt = "en"
    else:
        nxt = "zh"
    set_default_lang(nxt)
    return nxt


def ui_label(text: str, lang: str) -> str:
    t = str(lang).lower()
    if t == "my":
        return ZH_TO_MY.get(text, text)
    if t == "en":
        return ZH_TO_EN.get(text, text)
    return text


def normalize_ui_text(text: str) -> str:
    t = text.strip()
    if t.startswith("🌐"):
        t = t.lstrip("🌐").strip()
    if t in MY_TO_ZH:
        return MY_TO_ZH[t]
    if t in EN_TO_ZH:
        return EN_TO_ZH[t]
    if t in ("EN", "English", "英文"):
        return "__set_lang_en__"
    if t in ("MM", "Myanmar", "Burmese", "缅语", LANG_BTN_MY):
        return "__set_lang_my__"
    if t == "မီနူး":
        return "菜单"
    if t == "သူဌေးမီနူး":
        return "老板菜单"
    if t in ("workspace", "လုပ်ငန်းခွင်"):
        return "工作台"
    return t


def operator_menu_keyboard(lang: str) -> ReplyKeyboardMarkup:
    rows = [
        [ui_label("用户列表", lang)],
        [ui_label("工厂状态", lang), ui_label("库存概况", lang)],
        [ui_label("窑概况", lang), ui_label("日报", lang)],
        [LANG_BTN_MY, LANG_BTN_EN],
        [ui_label("菜单", lang)],
    ]
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


def finance_menu_keyboard(lang: str) -> ReplyKeyboardMarkup:
    rows = [
        [ui_label("用户列表", lang)],
        [ui_label("工厂状态", lang), ui_label("库存概况", lang)],
        [ui_label("窑概况", lang), ui_label("日报", lang)],
        [LANG_BTN_MY, LANG_BTN_EN],
        [ui_label("菜单", lang)],
    ]
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


def admin_menu_keyboard(lang: str) -> ReplyKeyboardMarkup:
    rows = [
        [ui_label("用户列表", lang), ui_label("系统状态", lang)],
        [ui_label("工厂状态", lang), ui_label("库存概况", lang)],
        [ui_label("窑概况", lang), ui_label("日报", lang)],
        [ui_label("菜单", lang)],
    ]
    if _workspace_base_url():
        rows.append([f"🌐 {ui_label('工作台', lang)}"])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


def keyboard_for_role(role: str, uid: str | None, admin_boss_mode: bool = False) -> ReplyKeyboardMarkup | None:
    lang = effective_lang(role, uid)
    if role == "老板" or admin_boss_mode:
        return boss_menu_keyboard(get_default_lang())
    if role == "财务":
        return finance_menu_keyboard(lang)
    if role == "操作员":
        return operator_menu_keyboard(lang)
    if role == "管理员":
        return admin_menu_keyboard(get_default_lang())
    return None


def role_menu_tip(role: str, uid: str | None) -> str:
    lang = effective_lang(role, uid)
    if role == "财务":
        if lang == "my":
            return "📋 ငွေကြေး စုံစမ်းမေးမြန်း မီနူး အသင့်ဖြစ်ပါပြီ"
        if lang == "en":
            return "📋 Finance query menu loaded"
        return "📋 财务查询菜单已加载"
    if role == "操作员":
        if lang == "my":
            return "📋 အော်ပရေတာ စုံစမ်းမေးမြန်း မီနူး အသင့်ဖြစ်ပါပြီ"
        if lang == "en":
            return "📋 Operator query menu loaded"
        return "📋 操作员查询菜单已加载"
    if role == "管理员":
        if lang == "my":
            return "📋 အက်မင်မီနူး အသင့်ဖြစ်ပါပြီ"
        if lang == "en":
            return "📋 Admin menu loaded"
        return "📋 管理员菜单已加载"
    if lang == "my":
        return "📋 မီနူး အသင့်ဖြစ်ပါပြီ"
    if lang == "en":
        return "📋 Menu loaded"
    return "📋 菜单已加载"


BUTTON_COMMANDS = {
    "工厂状态": "工厂状态",
    "库存概况": "库存概况",
    "库存状况": "库存概况",
    "生产概况": "生产概况",
    "生产状况": "生产概况",
    "窑概况": "窑概况",
    "窑状况": "窑概况",
    "财务概况": "财务概况",
    "财务状况": "财务概况",
    "财务明细": "财务明细",
    "系统状态": "系统状态",
    "日报": "日报",
    "用户列表": "用户列表",
    "开始挖矿": "开始挖矿",
    "停止挖矿": "停止挖矿",
}


def is_print_command(text: str) -> bool:
    t = text.strip()
    finance_print_cmds = (
        "打印机",
        "打印机列表",
        "设置打印机",
        "默认打印机",
        "当前打印机",
        "打印测试",
        "测试打印",
        "打印日报",
        "打印今日报告",
        "打印台账",
        "打印今日台账",
        "ပရင်တာစာရင်း",
        "ပရင်တာသတ်မှတ်",
        "ပုံနှိပ်စမ်း",
        "နေ့စဉ်အစီရင်ခံစာပုံနှိပ်",
        "နေ့စဉ်ထုတ်လုပ်မှုစာရင်းပုံနှိပ်",
    )
    return t.startswith(finance_print_cmds)


def is_data_entry_command(text: str) -> bool:
    """
    录入/变更类命令识别（用于老板只读权限控制）
    """
    t = text.strip()
    if not t:
        return False

    # 先做一次输入归一化，确保缅文也能命中中文规则
    norm = translate_to_cn(t).strip()

    # 典型录入命令（生产/库存/台账/业务）
    write_prefixes = (
        "原木入库",
        "成品入库",
        "成品发货",
        "投料",
        "完工",
        "上锯",
        "药浸",
        "分拣",
        "拣选",
        "二次拣选",
        "树皮 ",
        "木渣 ",
        "采购 ",
        "添加供应商",
        "到货 ",
        "新订单",
        "订单状态 ",
        "添加设备",
        "故障 ",
        "修复 ",
        "保养 ",
        "停机 ",
        "启动 ",
        "新增预测订单",
        "发货 ",
        "新增班组",
        "分配 ",
        "收入 ",
        "支出 ",
        "设置打印机 ",
    )
    if norm.startswith(write_prefixes):
        return True

    # 窑动作命令（入窑/点火/出窑）也属于数据变更
    if ("窑入窑" in norm) or ("窑点火" in norm) or ("窑出窑" in norm):
        return True
    if ("မီးဖို" in t) and (("ထည့်" in t) or ("မီးဖွင့်" in t) or ("ထုတ်" in t)):
        return True

    return False


# =====================================================
# 👁️ 操作员界面过滤
# =====================================================

def filter_for_operator(text: str) -> str:
    # 操作员/财务同权后不再做财务字段屏蔽
    return text


# =====================================================
# 🌏 输出语言处理
# =====================================================

def localize_output(text: str, role: str, uid: str | None = None) -> str:
    """
    根据角色决定是否翻译
    """

    lang = effective_lang(role, uid)
    if lang == "zh":
        return text
    return translate_from_cn(text, lang=lang)


def localize_template(text: str, role: str, uid: str | None) -> str:
    lang = effective_lang(role, uid)
    if lang == "zh":
        return text
    return translate_from_cn(text, lang=lang)


def query_dispatch(text: str) -> str:
    t = shortcut_to_cn(text or "")
    t = translate_to_cn(t or "")
    t = (t or "").strip()
    if not t:
        return "⚠️ 未识别指令"

    auth_result = auth_command(t)
    if auth_result:
        return auth_result

    for fn in (handle_report, handle_daily_report, handle_system_report, handle_system, handle_reconcile):
        try:
            r = fn(t)
            if r:
                return r
        except Exception:
            logging.exception(f"query handler failed: {getattr(fn, '__name__', 'unknown')}")
    return "⚠️ 未识别指令"


LAST_EXPORT_CACHE: dict[str, dict] = {}


def _export_label(role: str, uid: str) -> str:
    lang = effective_lang(role, uid)
    if lang == "my":
        return "Excel ထုတ်ယူ"
    if lang == "en":
        return "Export Excel"
    return "导出Excel"


def _make_export_keyboard(role: str, uid: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(_export_label(role, uid), callback_data=f"export:{uid}")]]
    )


def _split_table_line(line: str) -> list[str]:
    import re
    s = (line or "").strip()
    if not s:
        return []
    if "|" in s and s.count("|") >= 2:
        return [c.strip() for c in s.split("|") if c.strip()]
    if "\t" in s:
        return [c.strip() for c in s.split("\t") if c.strip()]
    parts = [p.strip() for p in re.split(r"\s{2,}", s) if p.strip()]
    return parts if len(parts) >= 2 else [s]


def _write_export_file(text: str, title: str) -> tuple[str, str]:
    """
    Returns (path, filename).
    Prefer xlsx if openpyxl exists; fallback to csv.
    """
    import csv
    import tempfile
    import time as _time

    stamp = _time.strftime("%Y%m%d_%H%M%S")
    safe_title = "".join(ch for ch in (title or "export") if ch.isalnum() or ch in ("-", "_"))[:32] or "export"

    lines = [ln.rstrip("\n") for ln in (text or "").splitlines() if ln.strip()]
    rows = [_split_table_line(ln) for ln in lines]
    rows = [r for r in rows if r]

    try:
        from openpyxl import Workbook  # type: ignore

        wb = Workbook()
        ws = wb.active
        ws.title = "data"
        for r in rows:
            ws.append(r)
        fd, path = tempfile.mkstemp(suffix=".xlsx")
        os.close(fd)
        wb.save(path)
        return path, f"{safe_title}_{stamp}.xlsx"
    except Exception:
        fd, path = tempfile.mkstemp(suffix=".csv")
        os.close(fd)
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            for r in rows:
                w.writerow(r)
        return path, f"{safe_title}_{stamp}.csv"


async def handle_export_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return

    await query.answer()
    data = (query.data or "").strip()
    parts = data.split(":", 1)
    if len(parts) != 2:
        return
    uid = parts[1].strip()
    cached = LAST_EXPORT_CACHE.get(uid)
    if not cached:
        await query.answer("No export data", show_alert=True)
        return

    text = str(cached.get("text") or "")
    title = str(cached.get("title") or "export")
    path, filename = _write_export_file(text, title)
    try:
        with open(path, "rb") as f:
            await context.bot.send_document(chat_id=uid, document=f, filename=filename)
    finally:
        try:
            os.unlink(path)
        except Exception:
            pass


async def on_error(update: object, context: ContextTypes.DEFAULT_TYPE):
    logging.exception("TG global error", exc_info=context.error)


async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    uid = str(update.effective_user.id) if update.effective_user else ""
    role = get_role(uid) if uid else None

    if not role:
        await _notify_admin_new_user(update, context, uid)
        await update.message.reply_text(tr_text("start_waiting_role", get_default_lang()))
        return

    if role not in ("管理员", "老板"):
        await update.message.reply_text("⛔ TG 端仅开放给管理员/老板，请联系管理员调整角色。")
        return

    if role == "老板":
        await update.message.reply_text(localize_output(boss_home_text(), role, uid), reply_markup=boss_menu_keyboard(get_default_lang()))

        login_url = _workspace_login_url_for_uid(uid)
        if login_url:
            inline_kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("🌐 打开工作台", url=login_url)]
            ])
            await update.message.reply_text(
                "🌐 已启用工作台，点击可直接登录并打开 Web 页面。",
                reply_markup=inline_kb
            )
        return

    await update.message.reply_text(
        tr_text("start_logged_in", effective_lang(role, uid)),
        reply_markup=keyboard_for_role(role, uid),
    )
    login_url = _workspace_login_url_for_uid(uid)
    if login_url:
        inline_kb = InlineKeyboardMarkup([[InlineKeyboardButton("🌐 打开工作台", url=login_url)]])
        await update.message.reply_text(
            "🌐 已启用工作台，点击可直接登录并打开 Web 页面。",
            reply_markup=inline_kb,
        )


async def handle_set_role_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return

    await query.answer()
    data = (query.data or "").strip()
    # setrole:<uid>:<role>
    parts = data.split(":", 2)
    if len(parts) != 3 or parts[0] != "setrole":
        return

    operator_uid = str(query.from_user.id)
    operator_role = get_role(operator_uid)
    if operator_role != "管理员":
        await query.answer("仅管理员可操作", show_alert=True)
        return

    target_uid, role = parts[1], parts[2]
    if role not in ("管理员", "老板"):
        await query.answer("仅支持设置为 管理员/老板", show_alert=True)
        return
    result = set_user_role(target_uid, role)
    _clear_pending(target_uid)

    await query.edit_message_text(f"✅ 已设置\n{result}")

    try:
        await context.bot.send_message(
            chat_id=target_uid,
            text=tr_text("role_opened", role=role),
        )
    except Exception:
        logging.exception(f"notify new user role failed: {target_uid}")


# =====================================================
# 主消息入口
# =====================================================

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):

    try:

        # ---------- 基础校验 ----------
        if not update.message or not update.message.text:
            return

        if update.effective_user and update.effective_user.is_bot:
            return

        raw_text = update.message.text.strip()
        text = normalize_ui_text(raw_text)
        uid = str(update.effective_user.id)

        logging.info(f"MSG from {uid}: {raw_text}")

        # =================================================
        # 获取 ID（无需权限）
        # =================================================

        if text.lower() in ("我的id", "id"):
            await update.message.reply_text(uid)
            return

        if text == "工作台":
            url = _workspace_login_url_for_uid(uid)
            if url:
                inline_kb = InlineKeyboardMarkup([[InlineKeyboardButton("🌐 打开工作台", url=url)]])
                await update.message.reply_text(
                    "🌐 点击下方按钮直接登录并打开 Web 工作台页面。",
                    reply_markup=inline_kb,
                )
            else:
                await update.message.reply_text("⛔ 尚未配置 Web 地址（AIF_WEB_BASE_URL）")
            return

        # =================================================
        # 权限检查
        # =================================================

        role = get_role(uid)
        if not role:
            await _notify_admin_new_user(update, context, uid)
            await update.message.reply_text(tr_text("no_permission_wait_admin"))
            return

        if role not in ("管理员", "老板"):
            await update.message.reply_text("⛔ TG 端当前仅开放给管理员/老板。")
            return

        if role == "管理员" and is_exit_boss_mode_command(text):
            context.user_data["boss_mode"] = False
            await update.message.reply_text("✅ 已退出老板菜单测试模式")
            return

        admin_boss_mode = (role == "管理员") and bool(context.user_data.get("boss_mode"))

        # 管理员在“老板菜单测试模式”下也允许执行强制命令（否则会被老板菜单分支吞掉）
        if admin_boss_mode and text.strip().startswith("强制"):
            context.user_data["boss_mode"] = False
            admin_boss_mode = False

        if role == "管理员" and text.strip() in ("管理员菜单",):
            context.user_data["boss_mode"] = False
            await update.message.reply_text(
                role_menu_tip(role, uid),
                reply_markup=admin_menu_keyboard(get_default_lang()),
            )
            return

        if role == "管理员" and text.strip() == "切换语言":
            nxt = toggle_default_lang()
            if nxt == "zh":
                msg = "✅ 语言已切换为 中文"
            elif nxt == "my":
                msg = "✅ ဘာသာကို မြန်မာလို ပြောင်းပြီးပါပြီ"
            else:
                msg = "✅ Language switched to English"
            await update.message.reply_text(msg, reply_markup=admin_menu_keyboard(nxt))
            return

        # 操作员/财务：用按钮切换个人语言（不改系统默认）
        if text in ("__set_lang_my__", "__set_lang_en__"):
            if text == "__set_lang_my__":
                set_user_lang(uid, "my")
                msg = "✅ ဘာသာကို မြန်မာလို ပြောင်းပြီးပါပြီ"
            else:
                set_user_lang(uid, "en")
                msg = "✅ Language switched to English"
            await update.message.reply_text(
                msg,
                reply_markup=keyboard_for_role(role, uid, admin_boss_mode),
            )
            return

        # 非老板模式下，主动拉起角色菜单
        if (not admin_boss_mode) and role in ("操作员", "财务", "管理员") and is_general_menu_command(text):
            await update.message.reply_text(
                role_menu_tip(role, uid),
                reply_markup=keyboard_for_role(role, uid, admin_boss_mode),
            )
            return

        # 老板端菜单模式
        if role == "老板" or admin_boss_mode:
            norm = translate_to_cn(text).strip()
            cmd = BOSS_TEXT_TO_CMD.get(text) or BOSS_TEXT_TO_CMD.get(norm)
            if cmd:
                result = query_dispatch(cmd) or "⚠️ 未识别指令"
                if result.startswith(("❌", "⛔", "⚠️")):
                    result = "⛔ 老板端仅支持查询，请点击菜单按钮。"
                await update.message.reply_text(localize_output(result, role, uid), reply_markup=boss_menu_keyboard(get_default_lang()))
                return

            await update.message.reply_text("✅ 已切换老板菜单模式", reply_markup=ReplyKeyboardRemove())
            await update.message.reply_text(localize_output(boss_home_text(), role, uid), reply_markup=boss_menu_keyboard(get_default_lang()))
            return

        # 管理员可通过“老板菜单”进入老板视图做验收
        if role == "管理员" and is_boss_menu_command(text):
            context.user_data["boss_mode"] = True
            await update.message.reply_text(
                "✅ 已切换老板菜单模式",
                reply_markup=ReplyKeyboardRemove(),
            )
            await update.message.reply_text(
                localize_output(boss_home_text(), role, uid),
                reply_markup=boss_menu_keyboard(get_default_lang()),
            )
            return

        # 查询/执行按钮 -> 真实命令
        mapped = BUTTON_COMMANDS.get(text)
        if mapped:
            text = mapped

        # =================================================
        # 用户管理命令（优先）
        # =================================================

        auth_text = translate_to_cn(text).strip()
        if auth_text.startswith(("添加用户", "删除用户", "开始挖矿", "停止挖矿", "系统重启", "全厂停产", "全厂加班")):
            lang = effective_lang(role, uid)
            if lang == "my":
                msg = "⛔ TG မှာ ပြင်ဆင်/လုပ်ဆောင်မှု အမိန့်များ ဖယ်ရှားပြီးပါပြီ။ စုံစမ်းခြင်းသာရနိုင်သည်။"
            elif lang == "en":
                msg = "⛔ TG mutating/action commands have been removed. Query-only mode is enabled."
            else:
                msg = "⛔ TG端已移除变更/执行命令，仅保留查询。"
            await update.message.reply_text(msg, reply_markup=keyboard_for_role(role, uid, admin_boss_mode))
            return
        r = auth_command(auth_text)
        if r:
            r = localize_output(r, role, uid)
            if role in ("操作员", "财务") and auth_text in ("用户", "用户列表"):
                LAST_EXPORT_CACHE[uid] = {"text": r, "title": text, "time": int(time.time())}
                await update.message.reply_text(r, reply_markup=_make_export_keyboard(role, uid))
            else:
                await update.message.reply_text(r, reply_markup=keyboard_for_role(role, uid, admin_boss_mode))
            return

        level = required_level(text)

        if not has_permission(uid, level):
            if role == "老板":
                await update.message.reply_text("⛔ 老板这里暂不支出闲聊哦~")
            else:
                if effective_lang(role, uid) == "my":
                    await update.message.reply_text("⛔ ခွင့်ပြုချက်မရှိ")
                else:
                    await update.message.reply_text("⛔ 权限不足")
            return

        # TG 端已移除所有录入能力：仅保留查询
        if is_data_entry_command(text):
            lang = effective_lang(role, uid)
            if lang == "my":
                msg = "⛔ TG မှာ မှတ်တမ်းဖြည့်သွင်းမှုအားလုံး ဖယ်ရှားပြီးပါပြီ။ Web မှသာ ဖြည့်နိုင်ပါသည်။"
            elif lang == "en":
                msg = "⛔ All TG data-entry features have been removed. Please use Web for data input."
            else:
                msg = "⛔ TG端所有录入功能已删除，请只在Web端录入。"
            await update.message.reply_text(msg, reply_markup=keyboard_for_role(role, uid, admin_boss_mode))
            return

        # =================================================
        # AIF 主系统
        # =================================================

        # 打印功能已取消（不再提供 UI / 命令）
        if is_print_command(text):
            if effective_lang(role, uid) == "my":
                await update.message.reply_text(
                    "⛔ ပုံနှိပ်မှုကို ပိတ်ထားပြီးပါပြီ",
                    reply_markup=keyboard_for_role(role, uid, admin_boss_mode),
                )
            else:
                await update.message.reply_text(
                    "⛔ 打印功能已取消",
                    reply_markup=keyboard_for_role(role, uid, admin_boss_mode),
                )
            return

        result = query_dispatch(text)

        if not result:
            result = "⚠️ 未识别指令"

        # 老板的异常/参数错误/未识别提示统一话术
        if role == "老板" and (
            result.startswith("❌")
            or result.startswith("⛔")
            or result.startswith("⚠️")
        ):
            result = "⛔ 老板这里暂不支出闲聊哦~"

        # =================================================
        # 👁️ 根据角色过滤显示
        # =================================================

        if role in ("操作员", "财务"):
            result = filter_for_operator(result)

        # =================================================
        # 🌏 输出翻译
        # =================================================

        result = localize_output(result, role, uid)

        if role == "老板":
            await update.message.reply_text(result, reply_markup=boss_menu_keyboard())
        else:
            if role in ("操作员", "财务") and (not is_data_entry_command(text)):
                LAST_EXPORT_CACHE[uid] = {"text": result, "title": text, "time": int(time.time())}
                await update.message.reply_text(result, reply_markup=_make_export_keyboard(role, uid))
            else:
                await update.message.reply_text(result, reply_markup=keyboard_for_role(role, uid, admin_boss_mode))

    except Exception:

        logging.exception("TG handle error")

        try:
            await update.message.reply_text("❌ 系统错误，请联系管理员")
        except Exception:
            # 网络波动时 reply_text 也可能超时；避免二次异常导致 handler 彻底崩掉
            logging.exception("TG reply_text failed in exception handler")


# =====================================================
# 启动
# =====================================================

def run_bot():
    token = get_bot_token()
    menu_web_url = _workspace_menu_url()

    # 这里必须做“自恢复”循环：现场网络波动/Telegram 连接超时会导致 run_polling 抛异常退出。
    # 若不自恢复，TG 端表现为“无回复”（进程已死）。
    while True:
        try:
            async def _post_init(application):
                if not menu_web_url:
                    return
                try:
                    await application.bot.set_chat_menu_button(
                        menu_button=MenuButtonWebApp(
                            text="工作台",
                            web_app=WebAppInfo(url=menu_web_url),
                        )
                    )
                    logging.info("set_chat_menu_button ok url=%s", menu_web_url)
                except Exception:
                    logging.exception("set_chat_menu_button failed")

            # Increase timeouts for field networks (ConnectTimeout/TimedOut were common).
            # Use separate request objects: long-polling needs longer read timeout.
            proxy = os.getenv("BOT_PROXY") or os.getenv("HTTPS_PROXY") or os.getenv("HTTP_PROXY")
            req = HTTPXRequest(connect_timeout=20.0, read_timeout=20.0, write_timeout=20.0, pool_timeout=10.0, proxy=proxy)
            get_updates_req = HTTPXRequest(connect_timeout=20.0, read_timeout=90.0, write_timeout=20.0, pool_timeout=10.0, proxy=proxy)

            app = (
                ApplicationBuilder()
                .token(token)
                .request(req)
                .get_updates_request(get_updates_req)
                .post_init(_post_init)
                .build()
            )

            app.add_handler(CommandHandler("start", handle_start))
            app.add_handler(CallbackQueryHandler(handle_set_role_callback, pattern=r"^setrole:"))
            app.add_handler(CallbackQueryHandler(handle_export_callback, pattern=r"^export:"))

            app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))
            app.add_error_handler(on_error)
            if app.job_queue:
                app.job_queue.run_repeating(
                    scheduled_entry_reminder,
                    interval=300,
                    first=30,
                    name="daily_missing_entry_reminder",
                )
                app.job_queue.run_repeating(
                    scheduled_daily_once_report_link,
                    interval=60,
                    first=35,
                    name="daily_once_report_link",
                )
                app.job_queue.run_repeating(
                    scheduled_cloudflared_tunnel_watch,
                    interval=60,
                    first=20,
                    name="cloudflared_tunnel_watch",
                )

            print("🔐 AIF Industrial Secure Bot Running...", flush=True)

            # 网络波动时持续重试（bootstrap_retries=-1），但某些异常仍会冒泡；外层循环兜底重启
            app.run_polling(
                drop_pending_updates=True,
                bootstrap_retries=-1,
                close_loop=False,
            )
        except KeyboardInterrupt:
            raise
        except BaseException:
            logging.exception("TG run_polling crashed, restarting in 5s")
            time.sleep(5)


# =====================================================
# 启动入口
# =====================================================

if __name__ == "__main__":
    run_bot()
