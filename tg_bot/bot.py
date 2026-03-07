import logging
import os
import sys
import json
import time
from pathlib import Path

# =====================================================
# 路径初始化
# =====================================================

BASE = os.path.dirname(os.path.dirname(__file__))
sys.path.append(BASE)

# =====================================================
# Telegram
# =====================================================

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
from telegram.request import HTTPXRequest

from tg_bot.config import get_bot_token

# =====================================================
# 权限系统
# =====================================================

from modules.auth.auth_engine import (
    auth_command,
    get_admin_ids,
    get_role,
    has_permission,
    set_user_role,
)

# =====================================================
# 🌏 多语言模块
# =====================================================

from modules.i18n.translate_engine import translate_from_cn, translate_to_cn

# =====================================================
# AIF 主调度系统
# =====================================================

from aif import dispatch, load_modules

# =====================================================
# 日志系统
# =====================================================

LOG_FILE = os.path.join(BASE, "logs/tg_bot.log")
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
SYSTEM_CFG_FILE = Path.home() / "AIF/data/system/system.json"
PENDING_USERS_FILE = Path.home() / "AIF/data/system/pending_users.json"

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
    "今日总览": "今日汇总",
    "今日汇总": "今日汇总",
    "工厂状态": "工厂状态",
    "库存概况": "库存概况",
    "生产概况": "生产概况",
    "窑概况": "窑概况",
    "财务概况": "财务概况",
    "财务状况": "财务概况",
    "财务明细": "财务明细",
    "系统状态": "系统状态",
    "日报": "日报",
}


def boss_menu_keyboard(lang: str | None = None) -> ReplyKeyboardMarkup:
    lang = lang or get_default_lang()
    rows = [
        [ui_label("今日总览", lang), ui_label("工厂状态", lang)],
        [ui_label("库存概况", lang), ui_label("生产概况", lang)],
        [ui_label("窑概况", lang)],
        [ui_label("系统状态", lang), ui_label("日报", lang)],
    ]
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


def boss_home_text() -> str:
    return "📊 老板查询菜单\n请直接点击按钮查看数据。"


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
    "上锯录入": "လွှမှတ်တမ်း",
    "药浸录入": "ဆေးစိမ်မှတ်တမ်း",
    "分拣录入": "ရွေးချယ်မှတ်တမ်း",
    "入窑录入": "မီးဖိုထည့်မှတ်တမ်း",
    "点火录入": "မီးဖွင့်မှတ်တမ်း",
    "出窑录入": "မီးဖိုထုတ်မှတ်တမ်း",
    "二次拣选录入": "ဒုတိယရွေးမှတ်တမ်း",
    "成品发货录入": "ကုန်ချောပို့မှတ်တမ်း",
    "成品入库录入": "ကုန်ချောထည့်မှတ်တမ်း",
    "收入录入": "ဝင်ငွေမှတ်တမ်း",
    "支出录入": "အသုံးစရိတ်မှတ်တမ်း",
    "原木入库录入": "သစ်ဝင်မှတ်တမ်း",
    "员工添加": "ဝန်ထမ်းထည့်",
    "员工删除": "ဝန်ထမ်းဖျက်",
    "用户列表": "အသုံးပြုသူစာရင်း",
    "打印日报": "နေ့စဉ်စာရင်းပုံနှိပ်",
    "打印台账": "ထုတ်လုပ်မှုစာရင်းပုံနှိပ်",
    "打印机列表": "ပရင်တာစာရင်း",
    "开始挖矿": "မိုင်းစတင်",
    "停止挖矿": "မိုင်းရပ်",
    "切换语言": "ဘာသာပြောင်း",
    "导出Excel": "Excel ထုတ်ယူ",
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
    "上锯录入": "saw entry",
    "药浸录入": "dip entry",
    "分拣录入": "sorting entry",
    "入窑录入": "kiln load entry",
    "点火录入": "kiln fire entry",
    "出窑录入": "kiln unload entry",
    "二次拣选录入": "2nd sorting entry",
    "成品发货录入": "shipping entry",
    "成品入库录入": "product in entry",
    "收入录入": "income entry",
    "支出录入": "expense entry",
    "原木入库录入": "log in entry",
    "员工添加": "add user",
    "员工删除": "delete user",
    "用户列表": "users",
    "打印日报": "print daily report",
    "打印台账": "print ledger",
    "打印机列表": "printers",
    "开始挖矿": "start mining",
    "停止挖矿": "stop mining",
    "切换语言": "language",
    "导出Excel": "export excel",
}
EN_TO_ZH = {v: k for k, v in ZH_TO_EN.items()}

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
    if not SYSTEM_CFG_FILE.exists():
        return {}
    try:
        return json.load(open(SYSTEM_CFG_FILE, "r", encoding="utf-8"))
    except Exception:
        return {}


def _save_system_cfg(cfg: dict) -> None:
    SYSTEM_CFG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(SYSTEM_CFG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)


def _load_pending_users() -> dict:
    if not PENDING_USERS_FILE.exists():
        return {"pending": {}}
    try:
        d = json.load(open(PENDING_USERS_FILE, "r", encoding="utf-8"))
        if not isinstance(d, dict):
            return {"pending": {}}
        d.setdefault("pending", {})
        return d
    except Exception:
        return {"pending": {}}


def _save_pending_users(d: dict) -> None:
    PENDING_USERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(PENDING_USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=2, ensure_ascii=False)


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
        InlineKeyboardButton("老板", callback_data=f"setrole:{target_uid}:老板"),
        InlineKeyboardButton("财务", callback_data=f"setrole:{target_uid}:财务"),
        InlineKeyboardButton("操作员", callback_data=f"setrole:{target_uid}:操作员"),
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
    return t


def operator_menu_keyboard(lang: str) -> ReplyKeyboardMarkup:
    rows = [
        [ui_label("上锯录入", lang), ui_label("药浸录入", lang), ui_label("分拣录入", lang)],
        [ui_label("入窑录入", lang), ui_label("点火录入", lang), ui_label("出窑录入", lang)],
        [ui_label("二次拣选录入", lang), ui_label("成品发货录入", lang), ui_label("成品入库录入", lang)],
        [ui_label("原木入库录入", lang)],
        [ui_label("员工添加", lang), ui_label("员工删除", lang), ui_label("用户列表", lang)],
        [ui_label("工厂状态", lang), ui_label("库存概况", lang), ui_label("生产概况", lang)],
        [ui_label("窑概况", lang), ui_label("日报", lang)],
        [LANG_BTN_MY, LANG_BTN_EN],
        [ui_label("菜单", lang)],
    ]
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


def finance_menu_keyboard(lang: str) -> ReplyKeyboardMarkup:
    rows = [
        [ui_label("上锯录入", lang), ui_label("药浸录入", lang), ui_label("分拣录入", lang)],
        [ui_label("入窑录入", lang), ui_label("点火录入", lang), ui_label("出窑录入", lang)],
        [ui_label("二次拣选录入", lang), ui_label("成品发货录入", lang), ui_label("成品入库录入", lang)],
        [ui_label("原木入库录入", lang)],
        [ui_label("员工添加", lang), ui_label("员工删除", lang), ui_label("用户列表", lang)],
        [ui_label("工厂状态", lang), ui_label("库存概况", lang), ui_label("生产概况", lang)],
        [ui_label("窑概况", lang), ui_label("日报", lang)],
        [LANG_BTN_MY, LANG_BTN_EN],
        [ui_label("菜单", lang)],
    ]
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


def admin_menu_keyboard(lang: str) -> ReplyKeyboardMarkup:
    rows = [
        [ui_label("上锯录入", lang), ui_label("药浸录入", lang), ui_label("分拣录入", lang)],
        [ui_label("入窑录入", lang), ui_label("点火录入", lang), ui_label("出窑录入", lang)],
        [ui_label("二次拣选录入", lang), ui_label("成品发货录入", lang), ui_label("成品入库录入", lang)],
        [ui_label("原木入库录入", lang)],
        [ui_label("员工添加", lang), ui_label("员工删除", lang), ui_label("用户列表", lang)],
        [ui_label("开始挖矿", lang), ui_label("停止挖矿", lang), ui_label("系统状态", lang)],
        [ui_label("工厂状态", lang), ui_label("库存概况", lang), ui_label("生产概况", lang)],
        [ui_label("窑概况", lang), ui_label("日报", lang)],
        [ui_label("切换语言", lang), ui_label("老板菜单", lang)],
        [ui_label("菜单", lang)],
    ]
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
            return "📋 ငွေကြေးမှတ်တမ်းမီနူး အသင့်ဖြစ်ပါပြီ"
        if lang == "en":
            return "📋 Finance entry menu loaded"
        return "📋 财务录入菜单已加载"
    if role == "操作员":
        if lang == "my":
            return "📋 အော်ပရေတာမှတ်တမ်းမီနူး အသင့်ဖြစ်ပါပြီ"
        if lang == "en":
            return "📋 Operator entry menu loaded"
        return "📋 操作员录入菜单已加载"
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


ENTRY_TEMPLATES = {
    "上锯录入": "🪚 上锯模板\n上锯 缅吨 托数 树皮托 木渣袋 [锯号]\n例: 上锯 3.2 12 2 5 锯号3",
    "药浸录入": "🧪 药浸模板\n药浸 罐次 [托数] [药剂袋数]\n例: 药浸 2 8 1",
    "分拣录入": "🧰 分拣模板\n分拣 编号 规格 根数 [托数]\n例: 分拣 250301-01 84x21 297 1",
    "入窑录入": "🔥 入窑模板\nA窑入窑 编号1 编号2 ...\n例: A窑入窑 250301-01 250301-02",
    "点火录入": "🔥 点火模板\nA窑点火\n例: A窑点火",
    "出窑录入": "🚚 出窑模板\nA窑出窑\n例: A窑出窑",
    "二次拣选录入": "📦 二次拣选模板\n二次拣选 编号 规格 等级 根数 体积 [托数]\n例: 二次拣选 250301-01 84x21 AB 297 0.82 1",
    "成品发货录入": "🚚 发货模板\n成品发货 编号/区间\n例: 成品发货 022-030 076",
    "成品入库录入": "📦 成品入库模板\n成品入库 编号 规格 等级 根数 体积 [托数]\n例: 成品入库 022 970x81x21 AB 517 0.853 1",
    "原木入库录入": "🪵 原木入库模板\n原木入库 数量\n例: 原木入库 12.5",
    "收入录入": "💰 收入模板\n收入 金额 备注\n例: 收入 250000 货款SO240301",
    "支出录入": "💸 支出模板\n支出 金额 备注\n例: 支出 35000 柴油装载机",
    "员工添加": "👤 员工添加模板\n添加用户 TelegramID 角色\n例: 添加用户 5687758092 操作员",
    "员工删除": "🗑️ 员工删除模板\n删除用户 TelegramID\n例: 删除用户 5687758092",
}

ENTRY_TEMPLATES_MY = {
    "上锯录入": "🪚 လွှ မှတ်တမ်း ပုံစံ\nလွှ MT ထုပ်အရေအတွက် သစ်ခေါက်ထုပ် သစ်မှုန့်အိတ် [လွှနံပါတ်]\nဥပမာ: လွှ 3.2 12 2 5 လွှနံပါတ်3",
    "药浸录入": "🧪 ဆေးစိမ် မှတ်တမ်း ပုံစံ\nဆေးစိမ် ဂဏန်း [ထုပ်အရေအတွက်] [ဆေးအိတ်]\nဥပမာ: ဆေးစိမ် 2 8 1",
    "分拣录入": "🧰 ရွေးချယ် မှတ်တမ်း ပုံစံ\nရွေးချယ် အမှတ် အရွယ်အစား အရေအတွက် [ထုပ်]\nဥပမာ: ရွေးချယ် 250301-01 84x21 297 1",
    "入窑录入": "🔥 မီးဖိုထည့် မှတ်တမ်း ပုံစံ\nAမီးဖိုထည့် အမှတ်1 အမှတ်2 ...\nဥပမာ: Aမီးဖိုထည့် 250301-01 250301-02",
    "点火录入": "🔥 မီးဖွင့် မှတ်တမ်း ပုံစံ\nAမီးဖိုမီးဖွင့်\nဥပမာ: Aမီးဖိုမီးဖွင့်",
    "出窑录入": "🚚 မီးဖိုထုတ် မှတ်တမ်း ပုံစံ\nAမီးဖိုထုတ်\nဥပမာ: Aမီးဖိုထုတ်",
    "二次拣选录入": "📦 ဒုတိယရွေး (ss)\n- နေ့စဉ်ကြည့်ရန်: ss\n- ဖြည့်တင်း(ထုတ်ပြီးစ) တော့အရေအတွက်သာ လျော့: ss 10托\n- ကုန်ချောထည့် (待二拣 လျော့): pi code spec grade pcs volume [trays]",
    "成品发货录入": "🚚 ကုန်ချောပို့ မှတ်တမ်း ပုံစံ\nကုန်ချောပို့ အမှတ်/အပိုင်းအခြား\nဥပမာ: ကုန်ချောပို့ 022-030 076",
    "成品入库录入": "📦 ကုန်ချောထည့် မှတ်တမ်း ပုံစံ\nကုန်ချောထည့် အမှတ် အရွယ်အစား အဆင့် အရေအတွက် ပမာဏ [ထုပ်]\nဥပမာ: ကုန်ချောထည့် 022 970x81x21 AB 517 0.853 1",
    "原木入库录入": "🪵 သစ်ဝင် မှတ်တမ်း ပုံစံ\nသစ်ဝင် ပမာဏ\nဥပမာ: သစ်ဝင် 12.5",
    "收入录入": "💰 ဝင်ငွေ မှတ်တမ်း ပုံစံ\nဝင်ငွေ ပမာဏ မှတ်ချက်\nဥပမာ: ဝင်ငွေ 250000 SO240301",
    "支出录入": "💸 အသုံးစရိတ် မှတ်တမ်း ပုံစံ\nအသုံးစရိတ် ပမာဏ မှတ်ချက်\nဥပမာ: အသုံးစရိတ် 35000 ဒီဇယ်",
    "员工添加": "👤 အသုံးပြုသူထည့် ပုံစံ\nဝန်ထမ်းထည့် TelegramID အခန်းကဏ္ဍ\nဥပမာ: ဝန်ထမ်းထည့် 5687758092 အော်ပရေတာ",
    "员工删除": "🗑️ အသုံးပြုသူဖျက် ပုံစံ\nဝန်ထမ်းဖျက် TelegramID\nဥပမာ: ဝန်ထမ်းဖျက် 5687758092",
}

ENTRY_TEMPLATES_EN = {
    "上锯录入": "🪚 Saw template\nsw MT trays [bark_trays] [dust_bags] [saw#]\nExample: sw 3.2 12 2 5 saw#3",
    "药浸录入": "🧪 Dip template\ndp tanks [trays] [chem_bags]\nExample: dp 2 8 1",
    "分拣录入": "🧰 Sorting template\nst code spec pcs [trays]\nExample: st 250301-01 84x21 297 1",
    "入窑录入": "🔥 Kiln load template\nkiln A load code1 code2 ...\nExample: kiln A load 250301-01 250301-02",
    "点火录入": "🔥 Kiln fire template\nkiln A fire\nExample: kiln A fire",
    "出窑录入": "🚚 Kiln unload template\nkiln A unload\nExample: kiln A unload",
    "二次拣选录入": "📦 2nd sort (ss)\n- Daily reference: ss\n- Backfill (deduct trays only): ss 10 tray\n- Product-in (deduct kiln-done): pi code spec grade pcs volume [trays]",
    "成品发货录入": "🚚 Shipping template\npo codes/ranges\nExample: po 022-030 076",
    "成品入库录入": "📦 Product-in template\npi code spec grade pcs volume [trays]\nExample: pi 022 970x81x21 AB 517 0.853 1",
    "原木入库录入": "🪵 Log-in template\nri amount\nExample: ri 12.5",
    "收入录入": "💰 Income template\ninc amount note\nExample: inc 250000 SO240301",
    "支出录入": "💸 Expense template\nexp amount note\nExample: exp 35000 diesel",
    "员工添加": "👤 Add-user template\nadduser TelegramID role\nExample: adduser 5687758092 operator",
    "员工删除": "🗑️ Delete-user template\ndeluser TelegramID\nExample: deluser 5687758092",
}


BUTTON_COMMANDS = {
    "工厂状态": "工厂状态",
    "库存概况": "库存概况",
    "生产概况": "生产概况",
    "窑概况": "窑概况",
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
        "设置日薪",
        "设置计件",
        "计件 ",
        "添加员工",
        "签到 ",
        "签退 ",
        "评分 ",
        "产量记录 ",
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

    if role == "老板":
        await update.message.reply_text(localize_output(boss_home_text(), role, uid), reply_markup=boss_menu_keyboard(get_default_lang()))
        return

    await update.message.reply_text(
        tr_text("start_logged_in", effective_lang(role, uid)),
        reply_markup=keyboard_for_role(role, uid),
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

        # =================================================
        # 权限检查
        # =================================================

        role = get_role(uid)
        if not role:
            await _notify_admin_new_user(update, context, uid)
            await update.message.reply_text(tr_text("no_permission_wait_admin"))
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
                result = dispatch(cmd) or "⚠️ 未识别指令"
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

        # 录入按钮 -> 模板提示（不直接写库）
        if text in ENTRY_TEMPLATES:
            lang = effective_lang(role, uid)
            tmpl = ENTRY_TEMPLATES[text]
            if lang == "my":
                tmpl = ENTRY_TEMPLATES_MY.get(text, tmpl)
            elif lang == "en":
                tmpl = ENTRY_TEMPLATES_EN.get(text, tmpl)
            await update.message.reply_text(
                tmpl,
                reply_markup=keyboard_for_role(role, uid, admin_boss_mode),
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

        result = dispatch(text)

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
    load_modules()
    token = get_bot_token()

    # 这里必须做“自恢复”循环：现场网络波动/Telegram 连接超时会导致 run_polling 抛异常退出。
    # 若不自恢复，TG 端表现为“无回复”（进程已死）。
    while True:
        try:
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
                .build()
            )

            app.add_handler(CommandHandler("start", handle_start))
            app.add_handler(CallbackQueryHandler(handle_set_role_callback, pattern=r"^setrole:"))
            app.add_handler(CallbackQueryHandler(handle_export_callback, pattern=r"^export:"))

            app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))
            app.add_error_handler(on_error)

            print("🔐 AIF Industrial Secure Bot Running...", flush=True)

            # 网络波动时持续重试（bootstrap_retries=-1），但某些异常仍会冒泡；外层循环兜底重启
            app.run_polling(drop_pending_updates=True, bootstrap_retries=-1)
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
