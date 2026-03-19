import json

from web.models import Session, SystemConfig, TgSetting, TgUserRole

AUTH_USERS_KEY = "auth_users"
AUTH_MIGRATION_KEY = "auth_users_migrated_v2"


def default_data():
    return {"users": {}}


ROLE_LEVEL = {
    "管理员": 2,
    "老板": 2,
    "财务": 1,
    "操作员": 1,
}

ROLE_ALIASES = {
    "အက်မင်": "管理员",
    "admin": "管理员",
    "သူဌေး": "老板",
    "boss": "老板",
    "ငွေကြေး": "财务",
    "finance": "财务",
    "အော်ပရေတာ": "操作员",
    "operator": "操作员",
}


def normalize_role(role: str) -> str:
    t = (role or "").strip()
    if t in ROLE_LEVEL:
        return t
    low = t.lower()
    return ROLE_ALIASES.get(low) or ROLE_ALIASES.get(t) or t


def _legacy_users_from_system_config(session) -> dict:
    cfg = session.query(SystemConfig).filter_by(key=AUTH_USERS_KEY).first()
    if not cfg:
        return {}
    try:
        data = json.loads(cfg.value or "{}")
        users = data.get("users", {}) if isinstance(data, dict) else {}
        return users if isinstance(users, dict) else {}
    except Exception:
        return {}


def _ensure_migrated(session):
    migrated = session.query(TgSetting).filter_by(key=AUTH_MIGRATION_KEY).first()
    if migrated and str(migrated.value or "").strip() == "1":
        return

    if session.query(TgUserRole).count() == 0:
        old_users = _legacy_users_from_system_config(session)
        for uid, role in old_users.items():
            uid_str = str(uid).strip()
            role_norm = normalize_role(str(role or ""))
            if uid_str and role_norm in ROLE_LEVEL:
                session.add(TgUserRole(user_id=uid_str, role=role_norm))

    old = session.query(SystemConfig).filter_by(key=AUTH_USERS_KEY).first()
    if old:
        session.delete(old)

    if not migrated:
        migrated = TgSetting(key=AUTH_MIGRATION_KEY, value="1")
        session.add(migrated)
    else:
        migrated.value = "1"


def load():
    session = Session()
    try:
        _ensure_migrated(session)
        session.commit()
        users = {}
        for row in session.query(TgUserRole).all():
            uid = str(row.user_id or "").strip()
            role = normalize_role(str(row.role or ""))
            if uid and role in ROLE_LEVEL:
                users[uid] = role
        return {"users": users}
    except Exception:
        session.rollback()
        return default_data()
    finally:
        session.close()


def save(d):
    if not isinstance(d, dict):
        d = default_data()
    users = d.get("users", {})
    if not isinstance(users, dict):
        users = {}

    session = Session()
    try:
        _ensure_migrated(session)
        session.query(TgUserRole).delete()
        for uid, role in users.items():
            uid_str = str(uid).strip()
            role_norm = normalize_role(str(role or ""))
            if not uid_str or role_norm not in ROLE_LEVEL:
                continue
            session.add(TgUserRole(user_id=uid_str, role=role_norm))
        session.commit()
    finally:
        session.close()


def add_user(parts):
    try:
        uid = parts[1]
        role = normalize_role(parts[2])
    except Exception:
        return "❌ 格式: 添加用户 ID 角色"

    if role not in ROLE_LEVEL:
        return "❌ 无效角色"

    d = load()
    d["users"][uid] = role
    save(d)
    return f"👤 用户 {uid} → {role}"


def set_user_role(uid: str, role: str):
    role = normalize_role(role)
    if role not in ROLE_LEVEL:
        return "❌ 无效角色"

    d = load()
    d["users"][uid] = role
    save(d)
    return f"👤 用户 {uid} → {role}"


def delete_user(parts):
    try:
        uid = parts[1]
    except Exception:
        return "❌ 格式: 删除用户 ID"

    d = load()
    if uid not in d["users"]:
        return "❌ 用户不存在"

    old_role = d["users"].pop(uid)
    save(d)
    return f"🗑️ 已删除用户 {uid}（{old_role}）"


def get_role(uid):
    d = load()
    return d["users"].get(uid)


def has_permission(uid, required_level):
    role = get_role(uid)
    if not role:
        return False
    return ROLE_LEVEL[role] >= required_level


def list_users():
    d = load()
    if not d["users"]:
        return "👥 无用户"

    lines = ["👥 用户列表"]
    for uid, role in d["users"].items():
        lines.append(f"{uid}: {role}")
    lines.append("\n删除命令: 删除用户 ID")
    return "\n".join(lines)


def get_admin_ids():
    d = load()
    ids = []
    for uid, role in d.get("users", {}).items():
        if role == "管理员":
            ids.append(uid)
    return ids


def auth_command(text):
    parts = text.split()
    if not parts:
        return None

    if parts[0] == "添加用户":
        return add_user(parts)
    if parts[0] == "删除用户":
        return delete_user(parts)
    if text in ("用户", "用户列表"):
        return list_users()
    return None
