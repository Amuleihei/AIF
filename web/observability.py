import logging
from collections import deque
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler
from pathlib import Path
import re


def configure_web_logging(base_dir: Path) -> Path:
    log_dir = Path(base_dir) / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "web_app.log"

    root = logging.getLogger()
    root.setLevel(logging.INFO)

    # 避免重复挂载 handler（例如热重启场景）
    for h in list(root.handlers):
        if isinstance(h, RotatingFileHandler) and getattr(h, "baseFilename", "").endswith(str(log_file)):
            return log_file

    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")

    fh = RotatingFileHandler(log_file, maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8")
    fh.setLevel(logging.INFO)
    fh.setFormatter(fmt)
    root.addHandler(fh)

    sh = logging.StreamHandler()
    sh.setLevel(logging.INFO)
    sh.setFormatter(fmt)
    root.addHandler(sh)
    return log_file


def count_recent_web_errors(base_dir: Path, hours: int = 24, max_lines: int = 8000) -> int:
    log_file = Path(base_dir) / "logs" / "web_app.log"
    if not log_file.exists():
        return 0

    try:
        with log_file.open("r", encoding="utf-8", errors="ignore") as f:
            lines = deque(f, maxlen=max_lines)
    except Exception:
        return 0

    since = datetime.now() - timedelta(hours=max(1, int(hours or 24)))
    # 中文注释：按“请求级别错误”统计，避免同一次异常被 traceback 重复计数。
    err_seen = set()
    count = 0
    path_re = re.compile(r"path=([^ ]+)")
    status_re = re.compile(r"status=(\d{3})")
    for line in lines:
        if " ERROR " not in line and " CRITICAL " not in line and " status=5" not in line:
            continue
        # 日志时间格式: 2026-03-16 08:12:33,123
        ts = line[:23]
        try:
            dt = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S,%f")
        except Exception:
            continue
        if dt < since:
            continue

        # 1) 统一入口异常日志（每次异常 1 条）
        if " aif.web http_exception " in line:
            path_match = path_re.search(line)
            path = path_match.group(1) if path_match else "-"
            key = ("http_exception", dt.strftime("%Y-%m-%d %H:%M:%S"), path)
            if key not in err_seen:
                err_seen.add(key)
                count += 1
            continue

        # 2) 仅有 5xx 但无异常行的兜底统计
        if " aif.web http_request " in line:
            status_match = status_re.search(line)
            status = int(status_match.group(1)) if status_match else 0
            if status >= 500:
                path_match = path_re.search(line)
                path = path_match.group(1) if path_match else "-"
                key = ("http_5xx", dt.strftime("%Y-%m-%d %H:%M:%S"), path)
                if key not in err_seen:
                    err_seen.add(key)
                    count += 1
            continue

        # 3) 前端上报 JS 错误
        if "CLIENT_JS_ERROR" in line:
            key = ("client_js_error", dt.strftime("%Y-%m-%d %H:%M:%S"), line.strip())
            if key not in err_seen:
                err_seen.add(key)
                count += 1
    return count
