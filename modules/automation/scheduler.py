import threading
import time


_running = False


def loop():

    while _running:

        # 可在这里加入自动逻辑
        time.sleep(60)


def start():

    global _running

    if _running:
        return "⚠️ 自动系统已运行"

    _running = True
    threading.Thread(target=loop, daemon=True).start()

    return "⚙️ 自动系统启动"


def stop():

    global _running

    if not _running:
        return "⚠️ 未运行"

    _running = False

    return "⛔ 自动系统停止"