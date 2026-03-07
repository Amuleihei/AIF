import importlib
import pkgutil
from pathlib import Path


MODULE_DIR = Path(__file__).parent / "modules"


def discover_modules():
    loaded = []

    for pkg in MODULE_DIR.iterdir():
        if not pkg.is_dir():
            continue

        try:
            importlib.import_module(f"modules.{pkg.name}")
            loaded.append(pkg.name)
        except Exception:
            pass

    return loaded


def start_core():
    print("🏭 AIF Core Online")

    mods = discover_modules()

    if mods:
        print("已加载模块：")
        for m in mods:
            print(f" - {m}")
    else:
        print("⚠️ 未加载任何模块")