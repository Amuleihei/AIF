def handle_ai(text):

    if text == "AI状态":
        return "🧠 AI 在线"

    if text.startswith("AI "):
        return f"🤖 AI处理: {text[3:]}"

    return None