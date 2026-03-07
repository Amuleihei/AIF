def handle_global(text):

    if text == "全厂停产":
        return "⛔ 全厂停产指令已下达"

    if text == "全厂加班":
        return "🔥 加班模式启动"

    if text == "系统状态":
        return "🟢 全系统运行正常"

    return None