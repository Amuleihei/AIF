import json
import re
from pathlib import Path
from datetime import datetime

DATA_FILE = Path.home() / "AIF/data/finance/finance.json"
CURRENCY = "KS"
FINANCE_DISABLED = True  # 临时关闭财务功能（防止现场误操作/系统风险）


# =====================================================
# 默认数据（工业版）
# =====================================================

def default_data():
    return {
        "accounts": {
            "cash": 0.0,
            "bank": 0.0
        },
        "records": []
    }


# =====================================================
# 数据升级（关键）
# =====================================================

def upgrade(d):

    # 老版本没有 accounts
    if "accounts" not in d:

        bal = d.get("balance", 0.0)

        d["accounts"] = {
            "cash": bal,
            "bank": 0.0
        }

    if "records" not in d:
        d["records"] = []

    return d


# =====================================================
# 读写
# =====================================================

def load():

    if not DATA_FILE.exists():
        d = default_data()
        save(d)
        return d

    try:
        d = json.load(open(DATA_FILE))
        return upgrade(d)
    except:
        d = default_data()
        save(d)
        return d


def save(d):

    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)

    with open(DATA_FILE, "w") as f:
        json.dump(d, f, indent=2, ensure_ascii=False)


# =====================================================
# 记录工具
# =====================================================

def add_record(d, typ, amount, account, note=""):

    d["records"].append({
        "time": datetime.now().isoformat(),
        "type": typ,
        "amount": amount,
        "account": account,
        "note": note
    })


# =====================================================
# 收入
# =====================================================

def income(d, amount, note, account="cash"):

    d["accounts"].setdefault(account, 0.0)

    d["accounts"][account] += amount

    add_record(d, "income", amount, account, note)

    return f"💰 收入 {amount:.2f} {CURRENCY} → {account}"


# =====================================================
# 支出
# =====================================================

def expense(d, amount, note, account="cash"):

    d["accounts"].setdefault(account, 0.0)

    if d["accounts"][account] < amount:
        return "❌ 余额不足"

    d["accounts"][account] -= amount

    add_record(d, "expense", amount, account, note)

    return f"💸 支出 {amount:.2f} {CURRENCY} ← {account}"


# =====================================================
# 转账
# =====================================================

def transfer(d, amount, src, dst):

    d["accounts"].setdefault(src, 0.0)
    d["accounts"].setdefault(dst, 0.0)

    if d["accounts"][src] < amount:
        return "❌ 源账户余额不足"

    d["accounts"][src] -= amount
    d["accounts"][dst] += amount

    add_record(d, "transfer", amount, f"{src}->{dst}")

    return f"🔁 转账 {amount:.2f} {CURRENCY} {src} → {dst}"


# =====================================================
# 今日统计
# =====================================================

def today_report(d):

    today = datetime.now().date()

    inc = 0.0
    exp = 0.0

    for r in d["records"]:
        t = datetime.fromisoformat(r["time"]).date()

        if t == today:
            if r["type"] == "income":
                inc += r["amount"]
            elif r["type"] == "expense":
                exp += r["amount"]

    return (
        "📊 今日财务\n"
        f"收入: {inc:.2f} {CURRENCY}\n"
        f"支出: {exp:.2f} {CURRENCY}\n"
        f"净额: {inc-exp:.2f} {CURRENCY}\n"
        f"总额: {inc+exp:.2f} {CURRENCY}"
    )

def _parse_date(s: str):
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except Exception:
        return None


def detail_report(d, day=None, limit: int = 30):

    recs = d.get("records", []) if isinstance(d.get("records"), list) else []
    limit = max(1, min(int(limit or 30), 200))

    filtered = []
    for r in recs:
        if not isinstance(r, dict):
            continue
        t = r.get("time")
        if not t:
            continue
        try:
            dt = datetime.fromisoformat(t)
        except Exception:
            continue
        if day is not None and dt.date() != day:
            continue
        filtered.append((dt, r))

    filtered.sort(key=lambda x: x[0], reverse=True)
    filtered = filtered[:limit]

    title = "💰 财务明细"
    if day is not None:
        title += f" {day.isoformat()}"

    if not filtered:
        return f"{title}\n暂无记录"

    inc = 0.0
    exp = 0.0
    transfer = 0.0

    lines = [title]
    for dt, r in filtered:
        typ = r.get("type")
        amount = float(r.get("amount", 0) or 0)
        account = str(r.get("account", "") or "")
        note = str(r.get("note", "") or "").strip()

        if typ == "income":
            sign = "+"
            inc += amount
            typ_label = "收入"
        elif typ == "expense":
            sign = "-"
            exp += amount
            typ_label = "支出"
        elif typ == "transfer":
            sign = ""
            transfer += amount
            typ_label = "转账"
        else:
            sign = ""
            typ_label = str(typ or "记录")

        time_s = dt.strftime("%m-%d %H:%M")
        main = f"{time_s} {typ_label} {sign}{amount:.0f}{CURRENCY} {account}".strip()
        if note:
            main += f" | {note}"
        lines.append(main)

    lines.append("")
    lines.append("📊 小计")
    lines.append(f"收入: {inc:.2f} {CURRENCY}")
    lines.append(f"支出: {exp:.2f} {CURRENCY}")
    lines.append(f"净额: {inc-exp:.2f} {CURRENCY}")
    if transfer:
        lines.append(f"转账: {transfer:.2f} {CURRENCY}")

    return "\n".join(lines)


# =====================================================
# 余额
# =====================================================

def balance(d):

    lines = ["🏦 账户余额"]

    for k, v in d["accounts"].items():
        lines.append(f"{k}: {v:.2f} {CURRENCY}")

    return "\n".join(lines)


# =====================================================
# TG入口
# =====================================================

def handle_finance(text):

    d = load()

    parts = text.split()

    if not parts:
        return None

    if FINANCE_DISABLED:
        t = (text or "").strip()
        if (
            t.startswith(("收入", "支出", "转账"))
            or t in ("今日财务", "今日收入", "今日统计", "余额", "财务状态")
            or t.startswith(("财务明细", "财务流水", "财务记录"))
        ):
            return "⛔ 财务功能已暂时关闭（系统维护中）"

    # ---------- 收入 ----------
    if parts[0] == "收入":
        try:
            amount = float(parts[1])
            note = " ".join(parts[2:])
        except:
            return "❌ 格式: 收入 金额 备注"

        r = income(d, amount, note)
        save(d)
        return r

    # ---------- 支出 ----------
    if parts[0] == "支出":
        try:
            amount = float(parts[1])
            note = " ".join(parts[2:])
        except:
            return "❌ 格式: 支出 金额 备注"

        r = expense(d, amount, note)
        save(d)
        return r

    # ---------- 转账 ----------
    if parts[0] == "转账":
        try:
            amount = float(parts[1])
            src = parts[2]
            dst = parts[3]
        except:
            return "❌ 格式: 转账 金额 源账户 目标账户"

        r = transfer(d, amount, src, dst)
        save(d)
        return r

    # ---------- 今日财务 ----------
    if text in ("今日财务", "今日收入", "今日统计"):
        return today_report(d)

    # ---------- 财务明细 ----------
    if text.startswith(("财务明细", "财务流水", "财务记录")):
        parts = text.split()
        day = None
        limit = 30

        idx = 1
        if len(parts) >= 2:
            p = parts[1].strip()
            if p in ("今日", "今天"):
                day = datetime.now().date()
                idx = 2
            elif re.fullmatch(r"\d{4}-\d{2}-\d{2}", p or ""):
                day = _parse_date(p)
                idx = 2
            elif re.fullmatch(r"\d{1,3}", p or ""):
                limit = int(p)
                idx = 2

        if len(parts) > idx and re.fullmatch(r"\d{1,3}", parts[idx] or ""):
            limit = int(parts[idx])

        return detail_report(d, day=day, limit=limit)

    # ---------- 余额 ----------
    if text in ("余额", "财务状态"):
        return balance(d)

    return None
