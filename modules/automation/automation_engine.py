def handle_automation(text):

    if text == "自动模式 开":
        return "⚙️ 自动模式已开启"

    if text == "自动模式 关":
        return "⚙️ 自动模式已关闭"

    return None