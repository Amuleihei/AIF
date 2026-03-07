import asyncio

from tg_bot.config import get_bot_chat_id, get_bot_token
from modules.report.daily_report_engine import daily_report


async def main():
    try:
        from telegram import Bot
    except Exception as e:
        raise RuntimeError("缺少 telegram 依赖，请安装 python-telegram-bot") from e

    print("▶ 开始发送日报")

    text = daily_report()

    print("日报内容：")
    print(text)

    bot = Bot(token=get_bot_token())

    await bot.send_message(
        chat_id=get_bot_chat_id(),
        text=text
    )

    print("✅ 发送成功")


if __name__ == "__main__":
    asyncio.run(main())

def send_report():
    asyncio.run(main())
