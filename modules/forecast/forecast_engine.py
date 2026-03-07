def handle_forecast(text):

    if text == "生产预测":

        return (
            "📊 生产预测\n"
            "未来7天产能稳定\n"
            "建议保持当前节奏"
        )

    if text == "订单预测":

        return "📦 预计订单增长 12%"

    return None