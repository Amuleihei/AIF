import os
import time
import psutil


START_TIME = time.time()


def get_status():

    uptime = int(time.time() - START_TIME)

    return (
        "🖥 系统状态\n"
        f"CPU: {psutil.cpu_percent()}%\n"
        f"内存: {psutil.virtual_memory().percent}%\n"
        f"磁盘: {psutil.disk_usage('/').percent}%\n"
        f"运行: {uptime}s"
    )