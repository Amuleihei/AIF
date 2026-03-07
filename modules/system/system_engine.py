import json
import shutil
from datetime import datetime
from pathlib import Path


DATA_DIR = Path.home() / "AIF/data"
SYSTEM_FILE = DATA_DIR / "system/system.json"
BACKUP_DIR = Path.home() / "AIF/backups"
TG_LOG = Path.home() / "AIF/logs/tg_bot.log"


DEFAULT = {
    "lang_policy": {
        "default": "my",
        "by_user": {},
    },
    "backup": {
        "enabled": True,
        "schedule": "daily",
        "keep": 7,
    },
    "entry_rule": {
        "allow_negative": False,
        "amount_decimals": 2,
        "quantity_decimals": 3,
        "expense_note_required": False,
    },
    "audit": {
        "enabled": True,
    },
}


def _load():
    if not SYSTEM_FILE.exists():
        _save(DEFAULT.copy())
        return DEFAULT.copy()
    try:
        d = json.load(open(SYSTEM_FILE, "r", encoding="utf-8"))
        if not isinstance(d, dict):
            d = {}
    except Exception:
        d = {}

    merged = DEFAULT.copy()
    for k, v in DEFAULT.items():
        cur = d.get(k, {})
        if isinstance(v, dict) and isinstance(cur, dict):
            m = v.copy()
            m.update(cur)
            merged[k] = m
        else:
            merged[k] = cur if cur is not None else v
    _save(merged)
    return merged


def _save(d):
    SYSTEM_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(SYSTEM_FILE, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=2, ensure_ascii=False)


def _bool_cn(v: str):
    t = v.strip().lower()
    if t in ("开", "开启", "on", "true", "1", "是", "yes"):
        return True
    if t in ("关", "关闭", "off", "false", "0", "否", "no"):
        return False
    return None


def _lang_norm(v: str):
    t = v.strip().lower()
    if t in ("中文", "zh", "cn", "chinese"):
        return "zh"
    if t in ("缅语", "缅文", "my", "mm", "burmese"):
        return "my"
    if t in ("英文", "en", "english"):
        return "en"
    return None


def _settings_report(d):
    return (
        "⚙️ 系统设置\n"
        f"语言默认: {d['lang_policy'].get('default', 'my')}\n"
        f"备份: {'开' if d['backup'].get('enabled') else '关'} / 频率 {d['backup'].get('schedule')} / 保留 {d['backup'].get('keep')} 份\n"
        f"录入规则: 负数{'允许' if d['entry_rule'].get('allow_negative') else '不允许'} | 金额小数{d['entry_rule'].get('amount_decimals')}位 | 数量小数{d['entry_rule'].get('quantity_decimals')}位\n"
        f"审计: {'开' if d['audit'].get('enabled') else '关'}\n"
        "打印: 已取消"
    )


def _backup_now():
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dst = BACKUP_DIR / f"data_{stamp}"
    shutil.copytree(DATA_DIR, dst)
    return dst


def _prune_backups(keep: int):
    if not BACKUP_DIR.exists():
        return
    dirs = sorted([p for p in BACKUP_DIR.iterdir() if p.is_dir() and p.name.startswith("data_")])
    extra = len(dirs) - max(1, keep)
    for p in dirs[:max(0, extra)]:
        shutil.rmtree(p, ignore_errors=True)


def _audit_recent(n: int):
    if not TG_LOG.exists():
        return "🧾 审计记录为空"
    try:
        lines = open(TG_LOG, "r", encoding="utf-8", errors="ignore").read().splitlines()
    except Exception:
        return "❌ 审计读取失败"
    rows = [x for x in lines if "MSG from " in x]
    if not rows:
        return "🧾 审计记录为空"
    pick = rows[-max(1, n):]
    return "🧾 最近操作\n" + "\n".join(pick)


def handle_system(text: str):
    t = text.strip()
    d = _load()
    parts = t.split()

    if t in ("系统设置", "设置总览"):
        return _settings_report(d)

    if t in ("语言设置", "查看语言"):
        user_count = len(d["lang_policy"].get("by_user", {}))
        return (
            "🌏 语言设置\n"
            f"默认: {d['lang_policy'].get('default', 'my')}\n"
            f"用户覆盖: {user_count} 个\n"
            "用法: 设置语言 默认 缅语|英文|中文 | 设置语言 用户ID 缅语|英文|中文"
        )

    if len(parts) >= 3 and parts[0] == "设置语言":
        target = parts[1]
        lang = _lang_norm(parts[2])
        if not lang:
            return "❌ 语言仅支持: 中文/缅语/英文"
        if target == "默认":
            d["lang_policy"]["default"] = lang
            _save(d)
            return f"✅ 默认语言已设置: {lang}"
        d["lang_policy"].setdefault("by_user", {})[target] = lang
        _save(d)
        return f"✅ 用户 {target} 语言已设置: {lang}"

    if t in ("备份设置",):
        b = d["backup"]
        return (
            "🧷 备份设置\n"
            f"开关: {'开' if b.get('enabled') else '关'}\n"
            f"频率: {b.get('schedule')}\n"
            f"保留: {b.get('keep')} 份"
        )

    if len(parts) >= 3 and parts[0] == "设置备份" and parts[1] in ("开关", "状态"):
        v = _bool_cn(parts[2])
        if v is None:
            return "❌ 用法: 设置备份 开关 开|关"
        d["backup"]["enabled"] = v
        _save(d)
        return f"✅ 备份已{'开启' if v else '关闭'}"

    if len(parts) >= 2 and parts[0] == "设置备份":
        # 兼容：设置备份 开 / 设置备份 关
        v = _bool_cn(parts[1])
        if v is not None:
            d["backup"]["enabled"] = v
            _save(d)
            return f"✅ 备份已{'开启' if v else '关闭'}"

    if len(parts) >= 3 and parts[0] == "设置备份频率":
        freq = parts[1].lower()
        if freq not in ("daily", "hourly", "weekly"):
            return "❌ 频率仅支持: hourly/daily/weekly"
        d["backup"]["schedule"] = freq
        _save(d)
        return f"✅ 备份频率已设置: {freq}"

    if len(parts) >= 2 and parts[0] == "设置备份保留":
        try:
            keep = int(parts[1])
        except Exception:
            return "❌ 用法: 设置备份保留 份数"
        if keep <= 0:
            return "❌ 份数必须大于0"
        d["backup"]["keep"] = keep
        _save(d)
        _prune_backups(keep)
        return f"✅ 备份保留已设置: {keep} 份"

    if t in ("立即备份", "执行备份"):
        dst = _backup_now()
        _prune_backups(int(d["backup"].get("keep", 7)))
        return f"✅ 备份完成: {dst}"

    if t in ("录入规则", "查看录入规则"):
        r = d["entry_rule"]
        return (
            "🧮 录入规则\n"
            f"允许负数: {'开' if r.get('allow_negative') else '关'}\n"
            f"金额小数: {r.get('amount_decimals')}\n"
            f"数量小数: {r.get('quantity_decimals')}\n"
            f"支出备注必填: {'开' if r.get('expense_note_required') else '关'}"
        )

    if len(parts) >= 4 and parts[0] == "设置录入规则" and parts[1] == "小数":
        target = parts[2]
        try:
            digits = int(parts[3])
        except Exception:
            return "❌ 小数位必须是数字"
        if digits < 0 or digits > 6:
            return "❌ 小数位范围: 0-6"
        if target == "金额":
            d["entry_rule"]["amount_decimals"] = digits
        elif target == "数量":
            d["entry_rule"]["quantity_decimals"] = digits
        else:
            return "❌ 仅支持: 金额/数量"
        _save(d)
        return f"✅ {target}小数位已设置: {digits}"

    if len(parts) >= 3 and parts[0] == "设置录入规则" and parts[1] == "允许负数":
        v = _bool_cn(parts[2])
        if v is None:
            return "❌ 用法: 设置录入规则 允许负数 开|关"
        d["entry_rule"]["allow_negative"] = v
        _save(d)
        return f"✅ 允许负数已{'开启' if v else '关闭'}"

    if len(parts) >= 3 and parts[0] == "设置录入规则" and parts[1] == "支出备注必填":
        v = _bool_cn(parts[2])
        if v is None:
            return "❌ 用法: 设置录入规则 支出备注必填 开|关"
        d["entry_rule"]["expense_note_required"] = v
        _save(d)
        return f"✅ 支出备注必填已{'开启' if v else '关闭'}"

    if t in ("审计设置",):
        return f"🧾 审计设置\n状态: {'开' if d['audit'].get('enabled') else '关'}"

    if len(parts) >= 2 and parts[0] == "审计开关":
        v = _bool_cn(parts[1])
        if v is None:
            return "❌ 用法: 审计开关 开|关"
        d["audit"]["enabled"] = v
        _save(d)
        return f"✅ 审计已{'开启' if v else '关闭'}"

    if parts and parts[0] == "审计":
        n = 20
        if len(parts) >= 3 and parts[1] in ("最近", "last"):
            try:
                n = int(parts[2])
            except Exception:
                return "❌ 用法: 审计 最近 条数"
        if not d["audit"].get("enabled"):
            return "⛔ 审计已关闭"
        return _audit_recent(n)

    if t in ("导出数据",):
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out = BACKUP_DIR / f"export_{stamp}"
        zip_path = shutil.make_archive(str(out), "zip", str(DATA_DIR))
        return f"✅ 数据导出完成: {zip_path}"

    return None
