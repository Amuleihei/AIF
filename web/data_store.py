import json
from datetime import datetime, timedelta

from web.models import (
    Session,
    SystemConfig,
    InventoryRaw,
    InventoryProduct,
    InventoryWip,
    FlowMetric,
    FlowSelectedTray,
    FlowSelectedTrayDetail,
    FlowKilnDoneTray,
    FlowSawMachineTotal,
    FlowSawMachineDaily,
    FlowSecondSortRecord,
    KilnState,
    KilnTray,
    ShippingOrder,
    ShippingOrderItem,
    TgSetting,
)

MIGRATION_KEY = "migration_v2_done"
FLOW_KEY = "flow_data"
KILN_KEY = "kilns"
INVENTORY_KEY = "inventory_data"
SHIPPING_KEY = "shipping_data"

FLOW_DEFAULTS = {
    "saw_tray_pool": 0,
    "dip_tray_pool": 0,
    "selected_tray_pool": 0,
    "selected_loose_pcs": 0,
    "kiln_done_tray_pool": 0,
    "dip_chem_bag_total": 0,
    "dip_chem_bag_pool": 19.0,
    "dip_additive_kg_pool": 0.0,
    "bark_tray_total": 0,
    "dust_bag_total": 0,
    "dust_bag_pool": 0,
    "waste_segment_bag_pool": 0,
    "bark_stock_m3": 0.0,
    "second_sort_ok_m3": 0.0,
    "second_sort_ab_m3": 0.0,
    "second_sort_bc_m3": 0.0,
    "second_sort_loss_m3": 0.0,
}

FLOW_INT_KEYS = {
    "saw_tray_pool",
    "dip_tray_pool",
    "selected_tray_pool",
    "selected_loose_pcs",
    "kiln_done_tray_pool",
    "dip_chem_bag_total",
    "bark_tray_total",
    "dust_bag_total",
    "dust_bag_pool",
    "waste_segment_bag_pool",
}

FLOW_FLOAT_KEYS = {
    "dip_chem_bag_pool",
    "dip_additive_kg_pool",
    "bark_stock_m3",
    "second_sort_ok_m3",
    "second_sort_ab_m3",
    "second_sort_bc_m3",
    "second_sort_loss_m3",
}

KILN_IDS = ("A", "B", "C", "D")


def _to_int(v, default=0):
    try:
        if v in (None, ""):
            return int(default)
        return int(float(v))
    except Exception:
        return int(default)


def _to_float(v, default=0.0):
    try:
        if v in (None, ""):
            return float(default)
        return float(v)
    except Exception:
        return float(default)


def _parse_iso_dt(raw):
    text = str(raw or "").strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except Exception:
        return None


def _normalize_shipping_record(item: dict):
    if not isinstance(item, dict):
        return item, False

    changed = False
    status = str(item.get("status", "") or "").strip()
    now = datetime.now()

    legacy_map = {
        "待发货": "去仰光途中",
        "运输中": "去仰光途中",
        "已签收": "仰光仓已到",
    }
    if status in legacy_map:
        item["status"] = legacy_map[status]
        status = item["status"]
        changed = True

    if not status:
        item["status"] = "去仰光途中"
        status = item["status"]
        changed = True

    departure_at = _parse_iso_dt(item.get("departure_at")) or _parse_iso_dt(item.get("created_at"))
    eta_hours = item.get("eta_hours_to_yangon", 36)
    try:
        eta_hours = max(1, int(float(eta_hours)))
    except Exception:
        eta_hours = 36
    item["eta_hours_to_yangon"] = eta_hours

    if status in {"待发车", "去仰光途中"} and departure_at:
        if departure_at <= now and status == "待发车":
            item["status"] = "去仰光途中"
            status = item["status"]
            changed = True
        if departure_at + timedelta(hours=eta_hours) <= now and status == "去仰光途中":
            item["status"] = "仰光仓已到"
            if not item.get("yangon_arrived_at"):
                item["yangon_arrived_at"] = now.isoformat()
            changed = True

    return item, changed


def _legacy_get_cfg_json(session, key: str, default=None):
    cfg = session.query(SystemConfig).filter_by(key=key).first()
    if not cfg:
        return {} if default is None else default
    try:
        data = json.loads(cfg.value or "{}")
        return data if isinstance(data, dict) else ({} if default is None else default)
    except Exception:
        return {} if default is None else default


def _get_metric(session, key: str, default: str = ""):
    row = session.query(FlowMetric).filter_by(key=key).first()
    if not row:
        return default
    return str(row.value or "")


def _set_metric(session, key: str, value):
    row = session.query(FlowMetric).filter_by(key=key).first()
    if not row:
        row = FlowMetric(key=key, value="")
        session.add(row)
    row.value = str(value if value is not None else "")


def _delete_metric(session, key: str):
    row = session.query(FlowMetric).filter_by(key=key).first()
    if row:
        session.delete(row)


def _encode_spec_summary(summary: dict) -> str:
    if not isinstance(summary, dict):
        return ""
    parts = []
    for k, v in summary.items():
        spec = str(k or "").strip()
        if not spec:
            continue
        parts.append(f"{spec}:{_to_int(v, 0)}")
    return "|".join(parts)


def _decode_spec_summary(raw: str) -> dict:
    text = str(raw or "").strip()
    if not text:
        return {}
    out = {}
    for token in text.split("|"):
        token = token.strip()
        if not token or ":" not in token:
            continue
        spec, cnt = token.rsplit(":", 1)
        spec = spec.strip()
        if not spec:
            continue
        out[spec] = _to_int(cnt, 0)
    return out


def _encode_tray_specs(specs: list[dict]) -> str:
    if not isinstance(specs, list):
        return ""
    parts = []
    for item in specs:
        if not isinstance(item, dict):
            continue
        spec = str(item.get("spec", "") or "").strip()
        qty = _to_int(item.get("qty"), 0)
        if not spec:
            continue
        parts.append(f"{spec}x{qty}" if qty > 0 else spec)
    return "+".join(parts)


def _decode_tray_specs(spec_text: str) -> list[dict]:
    text = str(spec_text or "").strip()
    if not text:
        return []
    out = []
    for token in text.split("+"):
        t = token.strip()
        if not t:
            continue
        parts = [p for p in t.split("x") if p != ""]
        if len(parts) >= 2 and parts[-1].isdigit():
            spec = "x".join(parts[:-1]).strip()
            qty = _to_int(parts[-1], 1)
        else:
            spec = t
            qty = 1
        if spec:
            out.append({"spec": spec, "qty": max(1, qty)})
    return out


def _sync_flow_payload_into_tables(session, flow: dict):
    data = dict(FLOW_DEFAULTS)
    if isinstance(flow, dict):
        data.update(flow)

    selected_trays = data.get("selected_trays", {})
    if not isinstance(selected_trays, dict):
        selected_trays = {}
    selected_details_raw = data.get("selected_tray_details", [])
    selected_details_provided = isinstance(data, dict) and ("selected_tray_details" in data)
    selected_details = selected_details_raw if isinstance(selected_details_raw, list) else []

    detail_ids = []
    for item in selected_details:
        if not isinstance(item, dict):
            continue
        tray_id = str(item.get("id", "") or "").strip()
        if tray_id:
            detail_ids.append(tray_id)
    detail_id_set = set(detail_ids)
    tray_id_set = {str(k).strip() for k in selected_trays.keys() if str(k).strip()}

    # 显式传入 selected_tray_details（即使为空）时，以其为唯一来源，避免残留旧明细。
    if selected_details_provided:
        data["selected_tray_pool"] = len(detail_ids)
        rebuilt = {}
        for item in selected_details:
            if not isinstance(item, dict):
                continue
            tray_id = str(item.get("id", "") or "").strip()
            if not tray_id:
                continue
            specs = item.get("specs", []) if isinstance(item.get("specs"), list) else _decode_tray_specs(item.get("spec", ""))
            first = specs[0] if specs else {}
            rebuilt[tray_id] = {
                "id": tray_id,
                "length_mm": 0,
                "width_mm": 0,
                "thick_mm": 0,
                "pcs": _to_int(first.get("qty"), 1),
                "spec": str(first.get("spec", "") or ""),
                "full_spec": str(first.get("spec", "") or ""),
            }
        selected_trays = rebuilt
    # 兼容历史：仅提交 selected_trays 的旧请求，继续自动重建。
    elif detail_id_set:
        data["selected_tray_pool"] = len(detail_ids)
        if (not selected_trays) or (tray_id_set != detail_id_set):
            rebuilt = {}
            for item in selected_details:
                if not isinstance(item, dict):
                    continue
                tray_id = str(item.get("id", "") or "").strip()
                if not tray_id:
                    continue
                specs = item.get("specs", []) if isinstance(item.get("specs"), list) else _decode_tray_specs(item.get("spec", ""))
                first = specs[0] if specs else {}
                rebuilt[tray_id] = {
                    "id": tray_id,
                    "length_mm": 0,
                    "width_mm": 0,
                    "thick_mm": 0,
                    "pcs": _to_int(first.get("qty"), 1),
                    "spec": str(first.get("spec", "") or ""),
                    "full_spec": str(first.get("spec", "") or ""),
                }
            selected_trays = rebuilt
    else:
        if selected_trays:
            data["selected_tray_pool"] = len(selected_trays)
        else:
            data["selected_tray_pool"] = _to_int(data.get("selected_tray_pool"), 0)

    for key in FLOW_DEFAULTS:
        if key in FLOW_INT_KEYS:
            _set_metric(session, key, _to_int(data.get(key), FLOW_DEFAULTS[key]))
        elif key in FLOW_FLOAT_KEYS:
            _set_metric(session, key, _to_float(data.get(key), FLOW_DEFAULTS[key]))
        else:
            _set_metric(session, key, data.get(key))

    session.query(FlowSelectedTray).delete()
    if isinstance(selected_trays, dict):
        for idx, (tray_id, item) in enumerate(selected_trays.items(), start=1):
            if not isinstance(item, dict):
                continue
            session.add(
                FlowSelectedTray(
                    tray_id=str(tray_id),
                    length_mm=_to_int(item.get("length_mm"), 0),
                    width_mm=_to_int(item.get("width_mm"), 0),
                    thick_mm=_to_int(item.get("thick_mm"), 0),
                    pcs=_to_int(item.get("pcs"), 0),
                    spec=str(item.get("spec", "") or ""),
                    full_spec=str(item.get("full_spec", "") or ""),
                    seq=idx,
                )
            )

    session.query(FlowSelectedTrayDetail).delete()
    derived_details = []
    if isinstance(selected_trays, dict):
        for tray_id, item in selected_trays.items():
            if not isinstance(item, dict):
                continue
            full_spec = str(item.get("full_spec", "") or item.get("spec", "") or "").strip()
            pcs = _to_int(item.get("pcs"), 0)
            specs = [{"spec": full_spec, "qty": pcs if pcs > 0 else 1}] if full_spec else []
            derived_details.append({"id": str(tray_id), "specs": specs, "count": 1})

    if derived_details and not selected_details:
        detail_ids = {
            str(item.get("id", "")).strip()
            for item in selected_details
            if isinstance(item, dict) and str(item.get("id", "")).strip()
        }
        tray_ids = {str(item.get("id", "")).strip() for item in derived_details if str(item.get("id", "")).strip()}
        if (not selected_details) or (detail_ids != tray_ids):
            selected_details = derived_details

    if isinstance(selected_details, list):
        for idx, item in enumerate(selected_details, start=1):
            if not isinstance(item, dict):
                continue
            tray_id = str(item.get("id", "") or "").strip()
            if not tray_id:
                continue
            specs = item.get("specs", []) if isinstance(item.get("specs"), list) else []
            spec_text = _encode_tray_specs(specs)
            if not spec_text:
                spec_text = str(item.get("spec", "") or "").strip()
            session.add(
                FlowSelectedTrayDetail(
                    tray_id=tray_id,
                    spec=spec_text,
                    count=_to_int(item.get("count"), 0),
                    volume=_to_float(item.get("volume"), 0.0),
                    batch_number=str(item.get("batch_number", "") or ""),
                    seq=idx,
                )
            )

    session.query(FlowKilnDoneTray).delete()
    kiln_done_trays = data.get("kiln_done_trays", [])
    if isinstance(kiln_done_trays, list):
        for idx, item in enumerate(kiln_done_trays, start=1):
            if not isinstance(item, dict):
                continue
            session.add(
                FlowKilnDoneTray(
                    tray_id=str(item.get("id", "") or ""),
                    spec=str(item.get("spec", "") or ""),
                    seq=idx,
                )
            )

    session.query(FlowSawMachineTotal).delete()
    saw_totals = data.get("saw_machine_totals", {})
    if isinstance(saw_totals, dict):
        for machine_no, rec in saw_totals.items():
            if not isinstance(rec, dict):
                continue
            session.add(
                FlowSawMachineTotal(
                    machine_no=_to_int(machine_no, 0),
                    mt=_to_float(rec.get("mt"), 0.0),
                    tray=_to_int(rec.get("tray"), 0),
                )
            )

    session.query(FlowSawMachineDaily).delete()
    saw_daily = data.get("saw_machine_daily", {})
    if isinstance(saw_daily, dict):
        for day, day_map in saw_daily.items():
            if not isinstance(day_map, dict):
                continue
            for machine_no, rec in day_map.items():
                if not isinstance(rec, dict):
                    continue
                session.add(
                    FlowSawMachineDaily(
                        day=str(day or ""),
                        machine_no=_to_int(machine_no, 0),
                        mt=_to_float(rec.get("mt"), 0.0),
                        tray=_to_int(rec.get("tray"), 0),
                        bark=_to_int(rec.get("bark"), 0),
                        dust=_to_int(rec.get("dust"), 0),
                    )
                )

    session.query(FlowSecondSortRecord).delete()
    second_sort_records = data.get("second_sort_records", [])
    if isinstance(second_sort_records, list):
        for rec in second_sort_records:
            if not isinstance(rec, dict):
                continue
            session.add(
                FlowSecondSortRecord(
                    time=str(rec.get("time", "") or ""),
                    trays=_to_int(rec.get("trays"), 0),
                    ok_m3=_to_float(rec.get("ok_m3"), 0.0),
                    ab_m3=_to_float(rec.get("ab_m3"), 0.0),
                    bc_m3=_to_float(rec.get("bc_m3"), 0.0),
                    loss_m3=_to_float(rec.get("loss_m3"), 0.0),
                    spec_summary=_encode_spec_summary(rec.get("spec_summary", {})),
                )
            )


def _build_flow_from_tables(session):
    out = dict(FLOW_DEFAULTS)
    metric_rows = session.query(FlowMetric).all()
    for row in metric_rows:
        k = str(row.key or "")
        v = row.value
        if k in FLOW_INT_KEYS:
            out[k] = _to_int(v, FLOW_DEFAULTS.get(k, 0))
        elif k in FLOW_FLOAT_KEYS:
            out[k] = _to_float(v, FLOW_DEFAULTS.get(k, 0.0))
        elif k:
            out[k] = v

    selected_map = {}
    for row in session.query(FlowSelectedTray).order_by(FlowSelectedTray.seq.asc(), FlowSelectedTray.tray_id.asc()).all():
        selected_map[row.tray_id] = {
            "id": row.tray_id,
            "length_mm": _to_int(row.length_mm, 0),
            "width_mm": _to_int(row.width_mm, 0),
            "thick_mm": _to_int(row.thick_mm, 0),
            "pcs": _to_int(row.pcs, 0),
            "spec": str(row.spec or ""),
            "full_spec": str(row.full_spec or ""),
        }
    out["selected_trays"] = selected_map

    selected_details = []
    for row in session.query(FlowSelectedTrayDetail).order_by(FlowSelectedTrayDetail.seq.asc(), FlowSelectedTrayDetail.tray_id.asc()).all():
        specs = _decode_tray_specs(str(row.spec or ""))
        selected_details.append(
            {
                "id": row.tray_id,
                "spec": str(row.spec or ""),
                "specs": specs,
                "count": _to_int(row.count, 0),
                "volume": _to_float(row.volume, 0.0),
                "batch_number": str(row.batch_number or ""),
            }
        )
    if selected_details:
        out["selected_tray_details"] = selected_details

    kiln_done_trays = []
    for row in session.query(FlowKilnDoneTray).order_by(FlowKilnDoneTray.seq.asc(), FlowKilnDoneTray.id.asc()).all():
        kiln_done_trays.append({"id": str(row.tray_id or "") or None, "spec": str(row.spec or "") or "?"})
    if kiln_done_trays:
        out["kiln_done_trays"] = kiln_done_trays

    saw_totals = {}
    for row in session.query(FlowSawMachineTotal).all():
        saw_totals[str(_to_int(row.machine_no, 0))] = {
            "mt": _to_float(row.mt, 0.0),
            "tray": _to_int(row.tray, 0),
        }
    out["saw_machine_totals"] = saw_totals

    saw_daily = {}
    for row in session.query(FlowSawMachineDaily).all():
        day = str(row.day or "")
        if not day:
            continue
        day_map = saw_daily.setdefault(day, {})
        day_map[str(_to_int(row.machine_no, 0))] = {
            "mt": _to_float(row.mt, 0.0),
            "tray": _to_int(row.tray, 0),
            "bark": _to_int(row.bark, 0),
            "dust": _to_int(row.dust, 0),
        }
    out["saw_machine_daily"] = saw_daily

    second_sort = []
    for row in session.query(FlowSecondSortRecord).order_by(FlowSecondSortRecord.id.asc()).all():
        second_sort.append(
            {
                "time": str(row.time or ""),
                "trays": _to_int(row.trays, 0),
                "ok_m3": _to_float(row.ok_m3, 0.0),
                "ab_m3": _to_float(row.ab_m3, 0.0),
                "bc_m3": _to_float(row.bc_m3, 0.0),
                "loss_m3": _to_float(row.loss_m3, 0.0),
                "spec_summary": _decode_spec_summary(row.spec_summary),
            }
        )
    out["second_sort_records"] = second_sort

    out["selected_tray_pool"] = len(selected_map)
    if kiln_done_trays:
        out["kiln_done_tray_pool"] = len(kiln_done_trays)
    else:
        out["kiln_done_tray_pool"] = _to_int(out.get("kiln_done_tray_pool"), 0)

    return out


def _sync_kilns_payload_into_tables(session, kilns: dict):
    data = kilns if isinstance(kilns, dict) else {}

    session.query(KilnTray).delete()
    state_map = {row.kiln_id: row for row in session.query(KilnState).all()}
    seen = set()

    for kiln_id, item in data.items():
        kid = str(kiln_id or "").strip().upper()
        if not kid:
            continue
        seen.add(kid)
        if not isinstance(item, dict):
            item = {}

        state = state_map.get(kid)
        if not state:
            state = KilnState(kiln_id=kid)
            session.add(state)

        state.status = str(item.get("status", "empty") or "empty")
        state.start = str(item.get("start", "") or "")
        state.dry_start = str(item.get("dry_start", "") or "")
        state.completed_time = str(item.get("completed_time", "") or "")
        state.last_volume = _to_float(item.get("last_volume"), 0.0)
        state.unloaded_count = _to_int(item.get("unloaded_count"), 0)
        state.unloading_total_trays = _to_int(item.get("unloading_total_trays"), 0)
        state.unloading_out_trays = _to_int(item.get("unloading_out_trays"), 0)
        state.unloading_out_applied = _to_int(item.get("unloading_out_applied"), 0)
        state.last_trays = _to_int(item.get("last_trays"), 0)
        state.manual_elapsed_hours = _to_int(item.get("manual_elapsed_hours"), 0)
        state.manual_remaining_hours = _to_int(item.get("manual_remaining_hours"), 0)

        trays = item.get("trays", [])
        if isinstance(trays, list):
            for idx, tray in enumerate(trays, start=1):
                if not isinstance(tray, dict):
                    continue
                session.add(
                    KilnTray(
                        kiln_id=kid,
                        tray_id=str(tray.get("id", "") or ""),
                        spec=str(tray.get("spec", "") or ""),
                        count=_to_int(tray.get("count"), 0),
                        volume=_to_float(tray.get("volume"), 0.0),
                        batch_number=str(tray.get("batch_number", "") or ""),
                        seq=idx,
                    )
                )

    for kid in KILN_IDS:
        if kid not in seen:
            state = state_map.get(kid)
            if not state:
                session.add(KilnState(kiln_id=kid, status="empty"))


def _build_kilns_from_tables(session):
    out = {}
    tray_map = {}
    for row in session.query(KilnTray).order_by(KilnTray.kiln_id.asc(), KilnTray.seq.asc(), KilnTray.id.asc()).all():
        tray_map.setdefault(row.kiln_id, []).append(
            {
                "id": str(row.tray_id or ""),
                "spec": str(row.spec or ""),
                "count": _to_int(row.count, 0),
                "volume": _to_float(row.volume, 0.0),
                "batch_number": str(row.batch_number or ""),
            }
        )

    state_rows = {row.kiln_id: row for row in session.query(KilnState).all()}
    for kid in KILN_IDS:
        st = state_rows.get(kid)
        if not st:
            out[kid] = {"trays": [], "status": "empty", "start": None, "completed_time": None, "last_volume": 0.0}
            continue
        out[kid] = {
            "trays": tray_map.get(kid, []),
            "status": str(st.status or "empty"),
            "start": str(st.start or "") or None,
            "dry_start": _to_int(st.dry_start, None) if str(st.dry_start or "").isdigit() else (str(st.dry_start or "") or None),
            "completed_time": str(st.completed_time or "") or None,
            "last_volume": _to_float(st.last_volume, 0.0),
            "unloaded_count": _to_int(st.unloaded_count, 0),
            "unloading_total_trays": _to_int(st.unloading_total_trays, 0),
            "unloading_out_trays": _to_int(st.unloading_out_trays, 0),
            "unloading_out_applied": _to_int(st.unloading_out_applied, 0),
            "last_trays": _to_int(st.last_trays, 0),
            "manual_elapsed_hours": _to_int(st.manual_elapsed_hours, 0),
            "manual_remaining_hours": _to_int(st.manual_remaining_hours, 0),
        }
    return out


def _sync_shipping_payload_into_tables(session, data: dict):
    payload = data if isinstance(data, dict) else {"shipments": [], "meta": {}}
    shipments = payload.get("shipments", [])
    meta = payload.get("meta", {})
    if not isinstance(shipments, list):
        shipments = []
    if not isinstance(meta, dict):
        meta = {}

    session.query(ShippingOrderItem).delete()
    session.query(ShippingOrder).delete()

    for item in shipments:
        if not isinstance(item, dict):
            continue
        normalized, _ = _normalize_shipping_record(dict(item))
        shipment_no = str(normalized.get("shipment_no", "") or "").strip()
        if not shipment_no:
            continue
        row = ShippingOrder(
            shipment_no=shipment_no,
            customer=str(normalized.get("customer", "") or ""),
            destination=str(normalized.get("destination", "") or ""),
            vehicle_no=str(normalized.get("vehicle_no", "") or ""),
            driver_name=str(normalized.get("driver_name", "") or ""),
            tracking_no=str(normalized.get("tracking_no", "") or ""),
            departure_at=str(normalized.get("departure_at", "") or ""),
            eta_hours_to_yangon=_to_int(normalized.get("eta_hours_to_yangon"), 36),
            yangon_arrived_at=str(normalized.get("yangon_arrived_at", "") or ""),
            yangon_departed_at=str(normalized.get("yangon_departed_at", "") or ""),
            china_port_arrived_at=str(normalized.get("china_port_arrived_at", "") or ""),
            status=str(normalized.get("status", "去仰光途中") or "去仰光途中"),
            remark=str(normalized.get("remark", "") or ""),
            created_at=str(normalized.get("created_at", "") or ""),
            updated_at=str(normalized.get("updated_at", "") or ""),
        )
        session.add(row)
        products = normalized.get("products", [])
        if isinstance(products, list):
            for idx, p in enumerate(products, start=1):
                if not isinstance(p, dict):
                    continue
                session.add(
                    ShippingOrderItem(
                        shipment_no=shipment_no,
                        product_id=str(p.get("product_id", "") or ""),
                        spec=str(p.get("spec", "") or ""),
                        grade=str(p.get("grade", "") or ""),
                        pcs=_to_int(p.get("pcs"), 0),
                        volume=_to_float(p.get("volume"), 0.0),
                        status=str(p.get("status", "运输中") or "运输中"),
                        seq=idx,
                    )
                )

    _set_metric(session, "shipping_last_date", str(meta.get("last_date", "") or ""))
    _set_metric(session, "shipping_last_seq", _to_int(meta.get("last_seq"), 0))


def _build_shipping_from_tables(session):
    meta = {
        "last_date": _get_metric(session, "shipping_last_date", ""),
        "last_seq": _to_int(_get_metric(session, "shipping_last_seq", "0"), 0),
    }

    item_rows = session.query(ShippingOrderItem).order_by(ShippingOrderItem.shipment_no.asc(), ShippingOrderItem.seq.asc(), ShippingOrderItem.id.asc()).all()
    item_map = {}
    for row in item_rows:
        item_map.setdefault(row.shipment_no, []).append(
            {
                "product_id": str(row.product_id or ""),
                "spec": str(row.spec or ""),
                "grade": str(row.grade or ""),
                "pcs": _to_int(row.pcs, 0),
                "volume": _to_float(row.volume, 0.0),
                "status": str(row.status or "运输中"),
            }
        )

    shipments = []
    for row in session.query(ShippingOrder).order_by(ShippingOrder.created_at.asc(), ShippingOrder.shipment_no.asc()).all():
        item = {
            "shipment_no": str(row.shipment_no or ""),
            "customer": str(row.customer or ""),
            "destination": str(row.destination or ""),
            "vehicle_no": str(row.vehicle_no or ""),
            "driver_name": str(row.driver_name or ""),
            "tracking_no": str(row.tracking_no or ""),
            "departure_at": str(row.departure_at or ""),
            "eta_hours_to_yangon": _to_int(row.eta_hours_to_yangon, 36),
            "yangon_arrived_at": str(row.yangon_arrived_at or ""),
            "yangon_departed_at": str(row.yangon_departed_at or ""),
            "china_port_arrived_at": str(row.china_port_arrived_at or ""),
            "status": str(row.status or "去仰光途中"),
            "remark": str(row.remark or ""),
            "created_at": str(row.created_at or ""),
            "updated_at": str(row.updated_at or ""),
            "products": item_map.get(row.shipment_no, []),
        }
        item, changed = _normalize_shipping_record(item)
        if changed:
            row.status = str(item.get("status", row.status) or row.status)
            row.yangon_arrived_at = str(item.get("yangon_arrived_at", row.yangon_arrived_at) or row.yangon_arrived_at)
            row.updated_at = datetime.now().isoformat()
        shipments.append(item)
    return {"shipments": shipments, "meta": meta}


def _refresh_inventory_summary_from_rows(session):
    rows = session.query(InventoryProduct).filter_by(status="库存").all()
    count = len(rows)
    m3 = 0.0
    for row in rows:
        m3 += _to_float(row.volume, 0.0)
    return count, m3


def _sync_inventory_payload_into_tables(session, data: dict):
    payload = data if isinstance(data, dict) else {}

    raw = payload.get("raw", {}) if isinstance(payload.get("raw"), dict) else {}
    raw_total = 0.0
    for material, volume in raw.items():
        vol = max(0.0, _to_float(volume, 0.0))
        raw_total += vol
        row = session.query(InventoryRaw).filter_by(material=str(material)).first()
        if not row:
            row = InventoryRaw(material=str(material), volume=0.0)
            session.add(row)
        row.volume = vol
    if "原木" not in raw:
        row = session.query(InventoryRaw).filter_by(material="原木").first()
        if not row:
            row = InventoryRaw(material="原木", volume=0.0)
            session.add(row)
        row.volume = max(0.0, raw_total)

    wip = payload.get("wip", {}) if isinstance(payload.get("wip"), dict) else {}
    if wip:
        session.query(InventoryWip).delete()
        for batch_number, item in wip.items():
            if not isinstance(item, dict):
                continue
            session.add(
                InventoryWip(
                    batch_number=str(batch_number),
                    kiln_id=str(item.get("kiln_id", "") or ""),
                    tray_count=_to_int(item.get("tray_count"), 0),
                    total_volume=_to_float(item.get("total_volume"), 0.0),
                    status=str(item.get("status", "active") or "active"),
                    created_at=str(item.get("created_at", "") or ""),
                    created_by=str(item.get("created_by", "") or ""),
                )
            )

    has_product_key = isinstance(payload, dict) and ("product" in payload)
    prod_map = payload.get("product", {}) if isinstance(payload.get("product"), dict) else {}
    existing = {r.product_id: r for r in session.query(InventoryProduct).all()}
    should_sync_products = has_product_key and (bool(prod_map) or not existing)
    if should_sync_products:
        for pid, item in prod_map.items():
            if not isinstance(item, dict):
                continue
            row = existing.get(str(pid))
            if not row:
                row = InventoryProduct(product_id=str(pid))
                session.add(row)
            row.spec = str(item.get("spec", "") or "")
            row.grade = str(item.get("grade", "") or "")
            row.pcs = _to_int(item.get("pcs"), 0)
            row.volume = _to_float(item.get("volume"), 0.0)
            row.status = str(item.get("status", "库存") or "库存")
        for pid, row in existing.items():
            if pid not in prod_map:
                session.delete(row)


def _migrate_from_legacy_json_once(session):
    marker = session.query(TgSetting).filter_by(key=MIGRATION_KEY).first()
    already_done = bool(marker and str(marker.value or "").strip() == "1")

    if not already_done:
        flow_empty = session.query(FlowMetric).count() == 0 and session.query(FlowSelectedTray).count() == 0
        kiln_empty = session.query(KilnState).count() == 0 and session.query(KilnTray).count() == 0
        shipping_empty = session.query(ShippingOrder).count() == 0 and session.query(ShippingOrderItem).count() == 0

        if flow_empty:
            flow = _legacy_get_cfg_json(session, FLOW_KEY, {})
            if isinstance(flow, dict) and flow:
                _sync_flow_payload_into_tables(session, flow)

        if kiln_empty:
            kilns = _legacy_get_cfg_json(session, KILN_KEY, {})
            if isinstance(kilns, dict) and kilns:
                _sync_kilns_payload_into_tables(session, kilns)

        if shipping_empty:
            shipping = _legacy_get_cfg_json(session, SHIPPING_KEY, {"shipments": [], "meta": {}})
            if isinstance(shipping, dict):
                _sync_shipping_payload_into_tables(session, shipping)

        inventory = _legacy_get_cfg_json(session, INVENTORY_KEY, {"raw": {}, "wip": {}, "product": {}, "meta": {}})
        if isinstance(inventory, dict) and (inventory.get("raw") or inventory.get("product")):
            _sync_inventory_payload_into_tables(session, inventory)

    old_keys = (
        FLOW_KEY,
        KILN_KEY,
        INVENTORY_KEY,
        SHIPPING_KEY,
        "inventory_summary",
        "tg_system_cfg",
        "tg_pending_users",
        "lang_policy",
        "backup",
        "entry_rule",
        "audit",
        "flow",
        "db_migration_v1",
    )
    for old_key in old_keys:
        row = session.query(SystemConfig).filter_by(key=old_key).first()
        if row:
            session.delete(row)

    if not marker:
        marker = TgSetting(key=MIGRATION_KEY, value="1")
        session.add(marker)
    else:
        marker.value = "1"


def ensure_migrated():
    session = Session()
    try:
        _migrate_from_legacy_json_once(session)
        for kid in KILN_IDS:
            if not session.query(KilnState).filter_by(kiln_id=kid).first():
                session.add(KilnState(kiln_id=kid, status="empty"))
        session.commit()
    finally:
        session.close()


def get_flow_data():
    ensure_migrated()
    session = Session()
    try:
        return _build_flow_from_tables(session)
    finally:
        session.close()


def save_flow_data(flow: dict):
    ensure_migrated()
    session = Session()
    try:
        current = _build_flow_from_tables(session)
        if isinstance(flow, dict):
            current.update(flow)
        _sync_flow_payload_into_tables(session, current)
        session.commit()
    finally:
        session.close()


def get_inventory_data():
    ensure_migrated()
    session = Session()
    try:
        raw = {}
        for row in session.query(InventoryRaw).all():
            raw[str(row.material)] = _to_float(row.volume, 0.0)

        wip = {}
        for row in session.query(InventoryWip).all():
            wip[str(row.batch_number)] = {
                "kiln_id": str(row.kiln_id or ""),
                "tray_count": _to_int(row.tray_count, 0),
                "total_volume": _to_float(row.total_volume, 0.0),
                "status": str(row.status or "active"),
                "created_at": str(row.created_at or ""),
                "created_by": str(row.created_by or ""),
            }

        product = {}
        for row in session.query(InventoryProduct).all():
            product[str(row.product_id)] = {
                "spec": str(row.spec or ""),
                "grade": str(row.grade or ""),
                "pcs": _to_int(row.pcs, 0),
                "volume": _to_float(row.volume, 0.0),
                "status": str(row.status or "库存"),
            }
        return {"raw": raw, "wip": wip, "product": product, "meta": {}}
    finally:
        session.close()


def save_inventory_data(data: dict):
    ensure_migrated()
    session = Session()
    try:
        _sync_inventory_payload_into_tables(session, data if isinstance(data, dict) else {})
        session.commit()
    finally:
        session.close()


def get_kilns_data():
    ensure_migrated()
    session = Session()
    try:
        return _build_kilns_from_tables(session)
    finally:
        session.close()


def save_kilns_data(kilns: dict):
    ensure_migrated()
    session = Session()
    try:
        _sync_kilns_payload_into_tables(session, kilns if isinstance(kilns, dict) else {})
        session.commit()
    finally:
        session.close()


def get_shipping_data():
    ensure_migrated()
    session = Session()
    try:
        data = _build_shipping_from_tables(session)
        session.commit()
        return data
    finally:
        session.close()


def save_shipping_data(data: dict):
    ensure_migrated()
    session = Session()
    try:
        _sync_shipping_payload_into_tables(session, data if isinstance(data, dict) else {"shipments": [], "meta": {}})
        session.commit()
    finally:
        session.close()


def get_log_stock_total():
    ensure_migrated()
    session = Session()
    try:
        rows = session.query(InventoryRaw).all()
        total = 0.0
        for r in rows:
            total += _to_float(r.volume, 0.0)
        return total
    finally:
        session.close()


def set_log_stock_total(value: float):
    ensure_migrated()
    session = Session()
    try:
        row = session.query(InventoryRaw).filter_by(material="原木").first()
        if not row:
            row = InventoryRaw(material="原木", volume=0.0)
            session.add(row)
        row.volume = max(0.0, float(value))
        session.commit()
    finally:
        session.close()


def add_log_stock(delta: float):
    current = get_log_stock_total()
    set_log_stock_total(current + float(delta))


def get_product_stats():
    ensure_migrated()
    session = Session()
    try:
        rows = session.query(InventoryProduct).filter_by(status="库存").all()
        count = len(rows)
        m3 = 0.0
        for row in rows:
            m3 += _to_float(row.volume, 0.0)
        return count, m3
    finally:
        session.close()


def upsert_inventory_product(product_id: str, spec: str, grade: str, pcs: int, volume: float, status: str = "库存"):
    ensure_migrated()
    session = Session()
    try:
        row = session.query(InventoryProduct).filter_by(product_id=str(product_id)).first()
        if not row:
            row = InventoryProduct(product_id=str(product_id))
            session.add(row)
        row.spec = str(spec or "")
        row.grade = str(grade or "")
        row.pcs = int(pcs or 0)
        row.volume = float(volume or 0.0)
        row.status = str(status or "库存")
        session.commit()
    finally:
        session.close()


def list_inventory_products(status: str = "库存"):
    ensure_migrated()
    session = Session()
    try:
        query = session.query(InventoryProduct)
        if status is not None:
            query = query.filter_by(status=status)
        rows = query.all()
        out = []
        for r in rows:
            out.append(
                {
                    "product_id": r.product_id,
                    "spec": r.spec or "",
                    "grade": r.grade or "",
                    "pcs": int(r.pcs or 0),
                    "volume": float(r.volume or 0.0),
                    "status": r.status or "库存",
                }
            )
        return out
    finally:
        session.close()


def get_inventory_products_by_ids(product_ids: list[str]):
    ensure_migrated()
    ids = [str(pid) for pid in (product_ids or []) if str(pid).strip()]
    if not ids:
        return []
    session = Session()
    try:
        rows = session.query(InventoryProduct).filter(InventoryProduct.product_id.in_(ids)).all()
        out = []
        for r in rows:
            out.append(
                {
                    "product_id": r.product_id,
                    "spec": r.spec or "",
                    "grade": r.grade or "",
                    "pcs": int(r.pcs or 0),
                    "volume": float(r.volume or 0.0),
                    "status": r.status or "库存",
                }
            )
        return out
    finally:
        session.close()


def update_inventory_product_status(product_ids: list[str], status: str):
    ensure_migrated()
    ids = [str(pid) for pid in (product_ids or []) if str(pid).strip()]
    if not ids:
        return 0
    session = Session()
    try:
        rows = session.query(InventoryProduct).filter(InventoryProduct.product_id.in_(ids)).all()
        for row in rows:
            row.status = str(status or row.status or "库存")
        session.commit()
        return len(rows)
    finally:
        session.close()


def delete_inventory_product(product_id: str):
    ensure_migrated()
    session = Session()
    try:
        row = session.query(InventoryProduct).filter_by(product_id=str(product_id)).first()
        if row:
            session.delete(row)
            session.commit()
            return True
        return False
    finally:
        session.close()
