import time
import traceback
from datetime import datetime

from send_daily_report import send_report


SEND_HOUR = 8      # 早上8点发送
CHECK_INTERVAL = 60   # 每分钟检查一次


def main():

    print("📊 日报服务启动")

    last_sent_day = None

    while True:

        try:
            now = datetime.now()

            # 每天只发一次
            if (
                now.hour == SEND_HOUR
                and now.minute == 0
                and last_sent_day != now.date()
            ):

                print("▶ 发送日报")
                send_report()

                last_sent_day = now.date()

            time.sleep(CHECK_INTERVAL)

        except Exception:
            print("❌ 日报服务异常")
            traceback.print_exc()
            time.sleep(60)


if __name__ == "__main__":
    main()