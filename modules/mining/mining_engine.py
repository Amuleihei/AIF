import os
import subprocess
from pathlib import Path

BASE = Path.home() / "AIF"

PID_FILE = BASE / "logs/xmrig.pid"
XMRIG_BIN = BASE / "xmrig/xmrig"


def pid():
    if PID_FILE.exists():
        return int(PID_FILE.read_text())
    return None


def handle_mining(text):

    # ================= 状态 =================
    if text == "挖矿状态":
        p = pid()
        if p:
            return f"🟢 挖矿中 (PID {p})"
        return "🔴 未运行"

    # ================= 启动 =================
    if text == "开始挖矿":

        if pid():
            return "⚠️ 已在运行"

        if not XMRIG_BIN.exists():
            return "❌ 未找到 xmrig 程序"

        proc = subprocess.Popen(
            [str(XMRIG_BIN)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        PID_FILE.parent.mkdir(parents=True, exist_ok=True)
        PID_FILE.write_text(str(proc.pid))

        return f"🚀 已启动 (PID {proc.pid})"

    # ================= 停止 =================
    if text == "停止挖矿":

        p = pid()

        if not p:
            return "⚠️ 未运行"

        try:
            os.kill(p, 9)
        except:
            pass

        PID_FILE.unlink(missing_ok=True)

        return "⛔ 已停止"

    return None