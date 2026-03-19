from web.data_store import get_kilns_data, get_shipping_data
from web.models import Session, TgSetting
from modules.auth.auth_engine import load as load_auth_users


DEFAULT = {
    "lang_policy": {"default": "my", "by_user": {}},
    "backup": {"enabled": True, "schedule": "daily", "keep": 7},
    "entry_rule": {"allow_negative": False, "amount_decimals": 2, "quantity_decimals": 3, "expense_note_required": False},
    "audit": {"enabled": True},
}


def _merge_dict(base: dict, current: dict) -> dict:
    merged = {}
    for key, value in base.items():
        cur = current.get(key)
        if isinstance(value, dict) and isinstance(cur, dict):
            merged[key] = _merge_dict(value, cur)
        else:
            merged[key] = cur if cur is not None else value
    return merged


def _load():
    session = Session()
    try:
        current = {
            "lang_policy": {"default": "my", "by_user": {}},
            "backup": {},
            "entry_rule": {},
            "audit": {},
        }
        rows = session.query(TgSetting).all()
        for row in rows:
            key = str(row.key or "")
            value = str(row.value or "")
            if key == "lang_default":
                current["lang_policy"]["default"] = value or "my"
            elif key.startswith("lang_user:"):
                uid = key.split(":", 1)[1].strip()
                if uid:
                    current["lang_policy"]["by_user"][uid] = value or "my"
            elif key == "backup_enabled":
                current["backup"]["enabled"] = value == "1"
            elif key == "backup_schedule":
                current["backup"]["schedule"] = value or "daily"
            elif key == "backup_keep":
                try:
                    current["backup"]["keep"] = int(value)
                except Exception:
                    pass
            elif key == "entry_allow_negative":
                current["entry_rule"]["allow_negative"] = value == "1"
            elif key == "entry_amount_decimals":
                try:
                    current["entry_rule"]["amount_decimals"] = int(value)
                except Exception:
                    pass
            elif key == "entry_quantity_decimals":
                try:
                    current["entry_rule"]["quantity_decimals"] = int(value)
                except Exception:
                    pass
            elif key == "entry_expense_note_required":
                current["entry_rule"]["expense_note_required"] = value == "1"
            elif key == "audit_enabled":
                current["audit"]["enabled"] = value == "1"
        return _merge_dict(DEFAULT, current)
    except Exception:
        return DEFAULT.copy()
    finally:
        session.close()


def _save(data: dict):
    merged = _merge_dict(DEFAULT, data if isinstance(data, dict) else {})
    session = Session()
    try:
        keep_keys = {"lang_default"}
        lang_default = str(merged.get("lang_policy", {}).get("default", "my") or "my")
        row = session.query(TgSetting).filter_by(key="lang_default").first()
        if not row:
            session.add(TgSetting(key="lang_default", value=lang_default))
        else:
            row.value = lang_default

        by_user = merged.get("lang_policy", {}).get("by_user", {})
        if isinstance(by_user, dict):
            for uid, lang in by_user.items():
                uid_str = str(uid).strip()
                if not uid_str:
                    continue
                key = f"lang_user:{uid_str}"
                keep_keys.add(key)
                ur = session.query(TgSetting).filter_by(key=key).first()
                if not ur:
                    session.add(TgSetting(key=key, value=str(lang or "my")))
                else:
                    ur.value = str(lang or "my")

        scalar_map = {
            "backup_enabled": "1" if merged["backup"].get("enabled") else "0",
            "backup_schedule": str(merged["backup"].get("schedule", "daily") or "daily"),
            "backup_keep": str(int(merged["backup"].get("keep", 7) or 7)),
            "entry_allow_negative": "1" if merged["entry_rule"].get("allow_negative") else "0",
            "entry_amount_decimals": str(int(merged["entry_rule"].get("amount_decimals", 2) or 2)),
            "entry_quantity_decimals": str(int(merged["entry_rule"].get("quantity_decimals", 3) or 3)),
            "entry_expense_note_required": "1" if merged["entry_rule"].get("expense_note_required") else "0",
            "audit_enabled": "1" if merged["audit"].get("enabled") else "0",
        }
        for key, value in scalar_map.items():
            keep_keys.add(key)
            sr = session.query(TgSetting).filter_by(key=key).first()
            if not sr:
                session.add(TgSetting(key=key, value=value))
            else:
                sr.value = value

        for row in session.query(TgSetting).all():
            key = str(row.key or "")
            if (key.startswith("lang_user:") or key in scalar_map or key == "lang_default") and key not in keep_keys:
                session.delete(row)
        session.commit()
    finally:
        session.close()


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


def handle_system(text: str):
    t = text.strip()
    d = _load()
    parts = t.split()

    if t in ("系统状态", "系统健康", "状态"):
        users = load_auth_users().get("users", {})
        kilns = get_kilns_data()
        shipping = get_shipping_data().get("shipments", [])
        running = 0
        for kid in ("A", "B", "C", "D"):
            k = kilns.get(kid, {}) if isinstance(kilns, dict) else {}
            if str(k.get("status", "") or "") in ("loading", "drying", "unloading"):
                running += 1
        return (
            "🟢 系统状态\n"
            f"默认语言: {d['lang_policy'].get('default', 'zh')}\n"
            f"用户数: {len(users) if isinstance(users, dict) else 0}\n"
            f"运行中窑: {running}\n"
            f"发货单: {len(shipping) if isinstance(shipping, list) else 0}"
        )

    if t in ("系统设置", "设置总览"):
        return (
            "⚙️ 系统设置\n"
            f"语言默认: {d['lang_policy'].get('default', 'my')}\n"
            f"备份: {'开' if d['backup'].get('enabled') else '关'} / 频率 {d['backup'].get('schedule')} / 保留 {d['backup'].get('keep')} 份\n"
            f"录入规则: 负数{'允许' if d['entry_rule'].get('allow_negative') else '不允许'} | 金额小数{d['entry_rule'].get('amount_decimals')}位 | 数量小数{d['entry_rule'].get('quantity_decimals')}位\n"
            f"审计: {'开' if d['audit'].get('enabled') else '关'}"
        )

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
        return f"🧷 备份设置\n开关: {'开' if b.get('enabled') else '关'}\n频率: {b.get('schedule')}\n保留: {b.get('keep')} 份"

    if len(parts) >= 3 and parts[0] == "设置备份" and parts[1] in ("开关", "状态"):
        v = _bool_cn(parts[2])
        if v is None:
            return "❌ 用法: 设置备份 开关 开|关"
        d["backup"]["enabled"] = v
        _save(d)
        return f"✅ 备份已{'开启' if v else '关闭'}"

    if len(parts) >= 2 and parts[0] == "设置备份":
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
        return f"✅ 备份保留已设置: {keep} 份"

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
            return "❌ 用法: 设置录入规则 小数 金额|数量 位数"
        if digits < 0:
            return "❌ 位数不能小于0"
        if target == "金额":
            d["entry_rule"]["amount_decimals"] = digits
        elif target == "数量":
            d["entry_rule"]["quantity_decimals"] = digits
        else:
            return "❌ 仅支持: 金额/数量"
        _save(d)
        return f"✅ {target}小数位已设置: {digits}"

    return None
