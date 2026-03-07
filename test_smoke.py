#!/usr/bin/env python3
"""
Lightweight smoke tests for AIF command routing.
Runs non-destructive checks against dispatch() and reports pass/fail.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import aif
from modules.i18n.translate_engine import translate_from_cn


Predicate = Callable[[str], bool]


@dataclass(frozen=True)
class SmokeCase:
    name: str
    command: str
    check: Predicate
    hint: str


def contains(*parts: str) -> Predicate:
    def _check(text: str) -> bool:
        return all(p in text for p in parts)

    return _check


CASES: list[SmokeCase] = [
    SmokeCase(
        name="CEO report",
        command="公司状况",
        check=contains("CEO报告", "日产能"),
        hint="应返回 CEO 报告，而不是模块异常",
    ),
    SmokeCase(
        name="Factory advice",
        command="工厂建议",
        check=contains("🧠"),
        hint="应返回自动建议文本",
    ),
    SmokeCase(
        name="Stage inventory routing",
        command="工序库存",
        check=contains("各工序库存"),
        hint="不应被翻译层改写成“库存”",
    ),
    SmokeCase(
        name="Flow inventory routing",
        command="流程库存",
        check=contains("各工序库存"),
        hint="不应被 inventory 模块抢占",
    ),
    SmokeCase(
        name="Warehouse inventory",
        command="库存",
        check=contains("库存状态"),
        hint="应命中 inventory_engine 的库存输出",
    ),
    SmokeCase(
        name="Product stock (EN) routing",
        command="product stock",
        check=contains("成品库存"),
        hint="英文 product stock 应映射到 成品库存",
    ),
    SmokeCase(
        name="Kiln unload details",
        command="A窑出窑详情",
        check=contains("出窑详情", "A窑"),
        hint="出窑详情应为查询命令，不应直接出窑",
    ),
    SmokeCase(
        name="Second sort (ss) reference",
        command="ss",
        check=contains("二次拣选", "待二拣"),
        hint="ss 不应改数据，应输出待二拣参考",
    ),
    SmokeCase(
        name="Tray export (EN)",
        command="export kiln load A 10 30",
        check=contains("待入窑导出", "A窑入窑"),
        hint="英文导出应路由到 待入窑导出",
    ),
    SmokeCase(
        name="Inventory overview WIP unit",
        command="库存概况",
        check=contains(
            "在制详情：",
            "已锯解：",
            "（锯解托）",
            "待入窑：",
            "（入窑托）",
            "待二分：",
        ),
        hint="库存概况应区分锯解托/入窑托两个口径（容量不同）",
    ),
    SmokeCase(
        name="Ledger input validation",
        command="锯解 abc",
        check=contains("数值错误"),
        hint="非法数字应返回可读错误，不应抛异常",
    ),
    SmokeCase(
        name="Finance details routing",
        command="财务明细 3",
        check=lambda text: "财务功能已暂时关闭" in text,
        hint="财务关闭后，财务明细应返回关闭提示",
    ),
    SmokeCase(
        name="SCM list",
        command="采购列表",
        check=lambda text: ("采购列表" in text) or ("无采购记录" in text),
        hint="应命中 SCM 查询分支",
    ),
    SmokeCase(
        name="Order list",
        command="订单列表",
        check=lambda text: ("订单列表" in text) or ("无订单" in text),
        hint="应命中正式订单模块",
    ),
    SmokeCase(
        name="Forecast order list",
        command="预测订单列表",
        check=lambda text: ("无预测订单" in text) or bool(text.strip()),
        hint="应命中预测订单模块",
    ),
    SmokeCase(
        name="Daily report units",
        command="日报",
        check=lambda text: ("日报暂未生产" in text) or all(
            k in text
            for k in (
                "📦 库存明细",
                "原木库存：",
                "MT",
                "在制详情：",
                "（锯解托）",
                "（入窑托）",
                "入窑:",
                "出窑:",
                "托",
                "总额:",
            )
        ),
        hint="日报中原料/在制/待二拣应为 MT/托，入窑/出窑应为 托，并包含财务总额",
    ),
    SmokeCase(
        name="Multiline dispatch",
        command="工序库存\n工序库存",
        check=lambda text: text.count("各工序库存") >= 2,
        hint="多行批量录入应逐行分发执行",
    ),
    SmokeCase(
        name="Reconcile report",
        command="对账",
        check=contains("对账", "现状", "今日台账"),
        hint="对账应输出状态与今日台账对比",
    ),
]


def main() -> int:
    # i18n sanity checks (avoid CN words leaking into EN/MM UI)
    sample = "🧪 药浸完成 1 罐（4 托，药剂 1 袋）"
    en = translate_from_cn(sample, lang="en")
    my = translate_from_cn(sample, lang="my")
    assert "药剂" not in en and "Chemical" in en, f"EN translation unexpected: {en}"
    assert "药剂" not in my and "ဆေး" in my, f"MY translation unexpected: {my}"
    assert "罐" not in en and "tank" in en, f"EN translation unexpected: {en}"
    assert "罐" not in my and "ကန်" in my, f"MY translation unexpected: {my}"

    kiln_overview = "🔥 窑总览\nA窑：出窑中 (26托)\nB窑：烘干中 剩71h (55托)\n\n运行: 3窑\n总托: 141托"
    kiln_en = translate_from_cn(kiln_overview, lang="en")
    assert all(x not in kiln_en for x in ("窑", "托", "剩")), f"EN translation unexpected: {kiln_en}"
    assert "Kiln A" in kiln_en and "Unloading" in kiln_en and "remaining" in kiln_en, f"EN translation unexpected: {kiln_en}"

    # admin force command typo tolerance
    from modules.admin.admin_force_engine import normalize_force_payload
    assert normalize_force_payload("出窑待二捡 297托") == "出窑待二拣 297托", "Force typo '二捡' should normalize"
    assert normalize_force_payload("待二拣 297托") == "出窑待二拣 297托", "Force alias '待二拣' should normalize"

    print(f"Loaded handlers: {len(aif.HANDLERS)}")
    print("-" * 60)

    failed = 0

    for idx, case in enumerate(CASES, 1):
        result = aif.dispatch(case.command)
        ok = case.check(result)

        status = "PASS" if ok else "FAIL"
        print(f"[{idx:02d}] {status} - {case.name}")
        print(f"  cmd: {case.command}")
        print(f"  out: {result}")

        if not ok:
            failed += 1
            print(f"  why: {case.hint}")

        print("-" * 60)

    if failed:
        print(f"Smoke test failed: {failed}/{len(CASES)} case(s) failed.")
        return 1

    print(f"Smoke test passed: {len(CASES)}/{len(CASES)} case(s) passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
