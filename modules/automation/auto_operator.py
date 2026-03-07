import threading
import time

from .factory_brain import decision


_running = False


def loop():

    while _running:

        msg = decision()
        print("AUTO:", msg)

        time.sleep(300)  # 5分钟一次


def start():

    global _running

    if _running:
        return "⚠️ 已运行"

    _running = True
    threading.Thread(target=loop, daemon=True).start()

    return "⚙️ 自动运营启动"


def stop():

    global _running

    _running = False

    return "⛔ 自动运营停止"


# TG入口
def handle_auto(text):

    if text == "自动运营 开":
        return start()

    if text == "自动运营 关":
        return stop()

    return None