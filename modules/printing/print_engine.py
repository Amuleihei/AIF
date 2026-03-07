import json
import shutil
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path


CONFIG_FILE = Path.home() / "AIF/data/system/printer.json"


def _load_cfg() -> dict:
    if not CONFIG_FILE.exists():
        return {"default_printer": ""}
    try:
        d = json.load(open(CONFIG_FILE, "r", encoding="utf-8"))
        if not isinstance(d, dict):
            return {"default_printer": ""}
        d.setdefault("default_printer", "")
        return d
    except Exception:
        return {"default_printer": ""}


def _save_cfg(cfg: dict) -> None:
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)


def _has_lp() -> bool:
    return shutil.which("lp") is not None


def _has_lpr() -> bool:
    return shutil.which("lpr") is not None


def _has_print_cmd() -> bool:
    return _has_lp() or _has_lpr()


def _run(cmd: list[str]) -> tuple[bool, str]:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, check=False)
        out = (p.stdout or "").strip()
        err = (p.stderr or "").strip()
        if p.returncode != 0:
            msg = err or out or f"return code {p.returncode}"
            return False, msg
        return True, out
    except Exception as e:
        return False, str(e)


def _printer_list() -> tuple[list[str], str | None]:
    ok, out = _run(["lpstat", "-p"])
    if not ok:
        return [], None

    printers: list[str] = []
    for line in out.splitlines():
        # printer HP_LaserJet is idle. ...
        parts = line.split()
        if len(parts) >= 2 and parts[0] == "printer":
            printers.append(parts[1])

    ok_d, out_d = _run(["lpstat", "-d"])
    default = None
    if ok_d and ":" in out_d:
        default = out_d.split(":", 1)[1].strip()

    return printers, default


def _resolve_printer() -> str | None:
    cfg = _load_cfg()
    if cfg.get("default_printer"):
        return cfg["default_printer"]

    _, default = _printer_list()
    return default


def _print_text(text: str, title: str, printer: str | None = None, copies: int = 1) -> tuple[bool, str]:
    if not _has_print_cmd():
        return False, "系统未安装打印命令（lp/lpr），请先安装/启用 CUPS"

    target = printer or _resolve_printer()
    if not target:
        return False, "未设置默认打印机，请先执行：设置打印机 打印机名称"

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write(text)
        path = f.name

    if _has_lp():
        cmd = ["lp", "-d", target, "-n", str(max(1, copies)), "-t", title, path]
    else:
        # lpr 在多数系统可用；不支持标题参数时忽略
        cmd = ["lpr", "-P", target, path]
    ok, msg = _run(cmd)
    if not ok:
        return False, f"打印失败: {msg}"

    return True, f"🖨️ 已发送到打印机 {target}（{stamp}）"


def _print_daily_report() -> tuple[bool, str]:
    try:
        from modules.report.daily_report_engine import daily_report
        content = daily_report()
    except Exception as e:
        return False, f"日报生成失败: {e}"
    return _print_text(content, "AIF-日报")


def _print_today_ledger() -> tuple[bool, str]:
    try:
        from modules.ledger.production_ledger_engine import handle_ledger
        content = handle_ledger("今日台账")
        if not content:
            content = "今日台账为空"
    except Exception as e:
        return False, f"台账生成失败: {e}"
    return _print_text(content, "AIF-今日台账")


def handle_print(text: str):
    t = text.strip()

    disabled_cmds = (
        "打印机",
        "打印机列表",
        "printer",
        "printers",
        "设置打印机",
        "默认打印机",
        "当前打印机",
        "打印测试",
        "测试打印",
        "打印日报",
        "打印今日报告",
        "打印台账",
        "打印今日台账",
    )
    if t in disabled_cmds or t.startswith("设置打印机 "):
        return "⛔ 打印功能已取消"

    if t in ("打印机", "打印机列表", "printer", "printers"):
        if not (_has_lp() or shutil.which("lpstat")):
            return "❌ 本机未检测到打印系统命令（lp/lpstat）"

        cfg = _load_cfg()
        configured = cfg.get("default_printer", "")
        printers, system_default = _printer_list()

        lines = ["🖨️ 打印机列表"]
        lines.append(f"系统默认: {system_default or '未设置'}")
        lines.append(f"AIF默认: {configured or '未设置'}")

        if not printers:
            lines.append("未发现可用打印机")
            lines.append("提示: 先在系统添加打印机，再执行 设置打印机 名称")
            return "\n".join(lines)

        lines.append("可用:")
        for p in printers:
            lines.append(f"- {p}")
        return "\n".join(lines)

    if t.startswith("设置打印机 "):
        name = t.replace("设置打印机", "", 1).strip()
        if not name:
            return "❌ 格式: 设置打印机 打印机名称"
        cfg = _load_cfg()
        cfg["default_printer"] = name
        _save_cfg(cfg)
        return f"✅ 默认打印机已设置: {name}"

    if t in ("默认打印机", "当前打印机"):
        cfg = _load_cfg()
        val = cfg.get("default_printer", "") or _resolve_printer() or "未设置"
        return f"🖨️ 当前默认打印机: {val}"

    if t in ("打印测试", "测试打印"):
        sample = (
            "AIF 打印测试\n"
            f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            "状态: OK\n"
        )
        ok, msg = _print_text(sample, "AIF-打印测试")
        return msg if ok else f"❌ {msg}"

    if t in ("打印日报", "打印今日报告"):
        ok, msg = _print_daily_report()
        return msg if ok else f"❌ {msg}"

    if t in ("打印台账", "打印今日台账"):
        ok, msg = _print_today_ledger()
        return msg if ok else f"❌ {msg}"

    return None
