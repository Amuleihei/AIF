import re
from dataclasses import dataclass
from typing import List, Tuple

DEFAULT_THICKNESS = "22"


@dataclass
class TraySpec:
    spec: str
    qty: int


@dataclass
class ParsedTrayGroup:
    base_id: str
    multiplier: int
    specs: List[TraySpec]


def _split_segments(raw: str) -> List[str]:
    text = (raw or "").replace("，", ",").replace("；", ",").replace(";", ",")
    return [seg.strip() for seg in text.split(",") if seg.strip()]


def _split_base_and_payload(segment: str) -> Tuple[str, str]:
    parts = segment.strip().split(maxsplit=1)
    if not parts:
        raise ValueError("empty tray segment")
    if len(parts) == 1:
        raise ValueError(f"缺少内容: {segment}")
    return parts[0], parts[1].strip()


def _parse_spec_token(token: str) -> TraySpec:
    txt = token.strip().lower().replace(" ", "")
    values = [v for v in txt.split("x") if v]
    if len(values) == 4:
        w, h, t, qty = values
    elif len(values) == 3:
        w, h, qty = values
        t = DEFAULT_THICKNESS
    else:
        raise ValueError(f"规格格式错误: {token}")

    if not (w.isdigit() and h.isdigit() and t.isdigit() and qty.isdigit()):
        raise ValueError(f"规格数字错误: {token}")

    return TraySpec(spec=f"{int(w)}x{int(h)}x{int(t)}", qty=int(qty))


def _parse_payload(payload: str) -> Tuple[int, List[TraySpec]]:
    match = re.match(r"^(.*?)(?:\s+(\d+))?$", payload.strip())
    if not match:
        raise ValueError(f"格式错误: {payload}")

    spec_part = (match.group(1) or "").strip()
    multiplier = int(match.group(2) or "1")
    if multiplier <= 0:
        raise ValueError(f"托数量必须大于0: {payload}")

    if spec_part.isdigit():
        multiplier = int(spec_part)
        if multiplier <= 0:
            raise ValueError(f"托数量必须大于0: {payload}")
        return multiplier, []

    specs: List[TraySpec] = []
    for token in spec_part.split("+"):
        token = token.strip()
        if not token:
            continue
        specs.append(_parse_spec_token(token))

    if not specs:
        raise ValueError(f"未识别到规格或数量: {payload}")

    return multiplier, specs


def _expand_ids(base_id: str, multiplier: int) -> List[str]:
    if multiplier == 1:
        return [base_id]

    m = re.match(r"^(.*?)(\d+)$", base_id)
    if not m:
        raise ValueError(f"编号无法自动递增: {base_id}")

    prefix, num = m.group(1), m.group(2)
    width = len(num)
    start = int(num)
    return [f"{prefix}{str(start + i).zfill(width)}" for i in range(multiplier)]


def parse_sorted_kiln_trays(raw: str) -> List[ParsedTrayGroup]:
    groups: List[ParsedTrayGroup] = []
    for segment in _split_segments(raw):
        base_id, payload = _split_base_and_payload(segment)
        multiplier, specs = _parse_payload(payload)
        groups.append(ParsedTrayGroup(base_id=base_id, multiplier=multiplier, specs=specs))
    return groups


def flatten_to_tray_items(groups: List[ParsedTrayGroup]) -> List[dict]:
    items: List[dict] = []
    for group in groups:
        ids = _expand_ids(group.base_id, group.multiplier)
        specs = [{"spec": s.spec, "qty": s.qty} for s in group.specs]
        for tray_id in ids:
            items.append({"id": tray_id, "specs": specs, "count": 1})
    return items


def count_total_trays(groups: List[ParsedTrayGroup]) -> int:
    return sum(g.multiplier for g in groups)


def summarize_specs(specs: List[dict]) -> str:
    if not specs:
        return ""
    return "+".join(f"{s.get('spec', '')}x{s.get('qty', 0)}" for s in specs)
