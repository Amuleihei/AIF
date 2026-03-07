import os
import importlib
from pathlib import Path

# =====================================================
# 🌐 多语言 + 简写系统
# =====================================================

from modules.i18n.translate_engine import translate_to_cn
from modules.i18n.shortcut_engine import shortcut_to_cn


BASE = Path(__file__).parent
MODULE_DIR = BASE / "modules"

# =====================================================
# 自动加载所有 handle_* 函数
# =====================================================

HANDLERS = []


def load_modules():

    HANDLERS.clear()  # 防止重复加载

    for root, dirs, files in os.walk(MODULE_DIR):
        dirs.sort()

        for f in sorted(files):

            if not (
                f.endswith("_engine.py")
                or f in ("global_command.py", "factory_brain.py")
            ):
                continue

            full_path = Path(root) / f

            rel = full_path.relative_to(BASE).with_suffix("")
            module_name = ".".join(rel.parts)

            try:
                mod = importlib.import_module(module_name)

                for attr in dir(mod):

                    if attr.startswith("handle_"):
                        fn = getattr(mod, attr)

                        if callable(fn):
                            HANDLERS.append(fn)

            except Exception as e:
                print("⚠️ 模块加载失败:", module_name, e)


# =====================================================
# 🧠 主分发器（AIF核心）
# =====================================================

def dispatch(text: str) -> str:

    if not text:
        return "⚠️ 空指令"

    # -------------------------------------------------
    # ⭐ 支持多行批量录入（TG 粘贴：一行一条）
    # -------------------------------------------------
    if "\n" in text:
        results = []
        for line in text.splitlines():
            line = (line or "").strip()
            if not line:
                continue
            r = dispatch(line)
            results.append(r or "⚠️ 未识别指令")
        return "\n\n".join(results) if results else "⚠️ 空指令"

    # -------------------------------------------------
    # ⭐ 第一步：简写转换（最快）
    # -------------------------------------------------
    text = shortcut_to_cn(text)

    # -------------------------------------------------
    # ⭐ 第二步：多语言转换
    # -------------------------------------------------
    text = translate_to_cn(text)

    # -------------------------------------------------
    # ⭐ 第三步：分发到各模块
    # -------------------------------------------------
    errors = []

    for h in HANDLERS:

        try:
            r = h(text)

            if r:
                return r

        except Exception as e:
            errors.append(f"{h.__module__}: {e}")
            continue

    if errors:
        return "❌ 模块异常:\n" + "\n".join(errors[:3])

    return "⚠️ 未识别指令"


# =====================================================
# 系统启动（仅调试）
# =====================================================

def start_system():

    if not HANDLERS:
        load_modules()

    print("🏭 AIF Core Online")
    print("已加载模块:")

    for h in HANDLERS:
        print(" -", h.__module__)


# =====================================================
# ⭐ 导入时自动初始化
# =====================================================

load_modules()


# =====================================================
# 单独运行调试
# =====================================================

if __name__ == "__main__":
    start_system()
