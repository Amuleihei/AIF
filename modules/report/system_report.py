from modules.report.daily_report_engine import daily_report


def handle_system_report(text):
    if text in ("日报", "今日日报", "工厂日报"):
        return daily_report()
    return None
