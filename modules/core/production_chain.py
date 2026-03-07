from modules.production.process_flow_engine import load as load_flow
from modules.production.process_flow_engine import save as save_flow
from modules.finance.finance_engine import load as load_finance
from modules.finance.finance_engine import save as save_finance


# =====================================================
# 工序转移 + 联动
# =====================================================

def transfer(src, dst, v):

    flow = load_flow()

    if src not in flow or dst not in flow:
        return "❌ 工序不存在"

    if flow[src] < v:
        return "❌ 数量不足"

    flow[src] -= v
    flow[dst] += v

    save_flow(flow)

    return f"🔄 {src} → {dst} {v}"


# =====================================================
# 出货联动
# =====================================================

def ship(v, price):

    flow = load_flow()

    if flow["包装完成"] < v:
        return "❌ 成品不足"

    flow["包装完成"] -= v
    save_flow(flow)

    fin = load_finance()
    fin.setdefault("accounts", {})
    fin["accounts"]["cash"] = fin["accounts"].get("cash", 0.0) + v * price
    save_finance(fin)

    return (
        f"🚚 出货 {v}\n"
        f"收入 {v * price:.2f}"
    )
