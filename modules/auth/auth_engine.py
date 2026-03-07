import json
from pathlib import Path

DATA_FILE = Path.home() / "AIF/data/auth/users.json"


# =====================================================
# 默认数据
# =====================================================

def default_data():
    return {"users": {}}


# =====================================================
# 读写
# =====================================================

def load():

    if not DATA_FILE.exists():
        d = default_data()
        save(d)
        return d

    try:
        return json.load(open(DATA_FILE))
    except:
        d = default_data()
        save(d)
        return d


def save(d):

    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)

    with open(DATA_FILE, "w") as f:
        json.dump(d, f, indent=2, ensure_ascii=False)


# =====================================================
# 角色等级
# =====================================================

ROLE_LEVEL = {
    "管理员": 2,
    "老板": 2,
    "财务": 1,
    "操作员": 1
}

ROLE_ALIASES = {
    # Burmese aliases (case-insensitive handled by caller)
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


# =====================================================
# 添加用户
# =====================================================

def add_user(parts):

    try:
        uid = parts[1]
        role = normalize_role(parts[2])
    except:
        return "❌ 格式: 添加用户 ID 角色"

    if role not in ROLE_LEVEL:
        return "❌ 无效角色"

    d = load()
    d["users"][uid] = role
    save(d)

    return f"👤 用户 {uid} → {role}"


# =====================================================
# 直接设置用户角色
# =====================================================

def set_user_role(uid: str, role: str):

    role = normalize_role(role)
    if role not in ROLE_LEVEL:
        return "❌ 无效角色"

    d = load()
    d["users"][uid] = role
    save(d)

    return f"👤 用户 {uid} → {role}"


# =====================================================
# 删除用户
# =====================================================

def delete_user(parts):

    try:
        uid = parts[1]
    except:
        return "❌ 格式: 删除用户 ID"

    d = load()

    if uid not in d["users"]:
        return "❌ 用户不存在"

    old_role = d["users"].pop(uid)
    save(d)

    return f"🗑️ 已删除用户 {uid}（{old_role}）"


# =====================================================
# 获取角色
# =====================================================

def get_role(uid):

    d = load()
    return d["users"].get(uid)


# =====================================================
# 权限检查
# =====================================================

def has_permission(uid, required_level):

    role = get_role(uid)

    if not role:
        return False

    return ROLE_LEVEL[role] >= required_level


# =====================================================
# 用户列表
# =====================================================

def list_users():

    d = load()

    if not d["users"]:
        return "👥 无用户"

    lines = ["👥 用户列表"]

    for uid, role in d["users"].items():
        lines.append(f"{uid}: {role}")

    return "\n".join(lines)


# =====================================================
# 管理员列表
# =====================================================

def get_admin_ids():
    d = load()
    ids = []
    for uid, role in d.get("users", {}).items():
        if role == "管理员":
            ids.append(uid)
    return ids


# =====================================================
# ⭐ 用户管理入口（不叫 handle_）
# =====================================================

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
