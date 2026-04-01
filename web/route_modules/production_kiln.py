# 生产流转与窑相关路由（从 routes.py 拆分）
import json
import logging
import re

from web.route_support import (
    AdminAuditLog,
    BARK_PRICE_PER_M3_KS,
    WASTE_SEGMENT_PRICE_PER_BAG_KS,
    ByproductRecord,
    DipRecord,
    LogEntryDetail,
    LogEntryMeta,
    LogEntrySettlement,
    LogPricingProfile,
    LogPricingRule,
    LogConsumption,
    LogEntry,
    ProductBatch,
    SawRecord,
    SawMachineLogDetail,
    SawMachineRecord,
    Session,
    SortRecord,
    TrayBatch,
    current_user,
    datetime,
    dispatch,
    flash,
    flatten_to_tray_items,
    generate_product_batch_number,
    generate_tray_batch_number,
    get_lang,
    get_stock_data_with_lang,
    jsonify,
    login_required,
    pd,
    parse_sorted_kiln_trays,
    redirect,
    request,
    send_file,
    summarize_specs,
    time,
    update_flow_data,
    update_kiln_status,
    upsert_inventory_product,
    url_for,
    _infer_spec_and_volume,
    _lang_code,
    _load_kilns_data,
    _parse_id_list,
    _parse_kiln_trays_input,
    _read_flow_data,
    _register_secondary_rule,
    _save_flow_data,
    _save_kilns_data,
    audit_admin_action,
    _secondary_rule_map,
    _t,
    _to_float,
    _to_int,
    sync_raw_inventory,
)
from io import BytesIO
from web.services.alert_settings_service import get_alert_settings

LOG_PRICE_RULE_DEFS = [
    {"key": "15_17", "label": "15-17", "min": 15.0, "max": 17.0, "is_max_open": 0, "default_price": 90000.0},
    {"key": "15_18", "label": "15-18", "min": 15.0, "max": 18.0, "is_max_open": 0, "default_price": 90000.0},
    {"key": "18_24", "label": "18-24", "min": 18.0, "max": 24.0, "is_max_open": 0, "default_price": 320000.0},
    {"key": "19_24", "label": "19-24", "min": 19.0, "max": 24.0, "is_max_open": 0, "default_price": 320000.0},
    {"key": "25_plus_430", "label": "25+", "min": 25.0, "max": 0.0, "is_max_open": 1, "default_price": 430000.0},
    {"key": "25_plus_450", "label": "25+", "min": 25.0, "max": 0.0, "is_max_open": 1, "default_price": 450000.0},
]
LOG_PRICE_RULE_DEF_MAP = {item["key"]: item for item in LOG_PRICE_RULE_DEFS}
KILN_MAX_TRAYS_DEFAULT = 70


def _get_kiln_max_trays() -> int:
    try:
        cfg = get_alert_settings()
        val = _to_int((cfg or {}).get("kiln_max_trays"), KILN_MAX_TRAYS_DEFAULT)
        return max(1, val)
    except Exception:
        return KILN_MAX_TRAYS_DEFAULT


def _parse_secondary_sort_input(raw: str):
    """
    二选输入兼容：
    - 编号模式：A001,A002
    - 数字模式：17 / 17托 / 17tray
    - 混合模式：A001,A002,3  => 共5托
    返回：({id1,id2...}, total_trays)
    """
    text = str(raw or "").strip()
    if not text:
        return set(), 0
    normalized = (
        text.replace("，", ",")
        .replace("；", ",")
        .replace(";", ",")
        .replace("\n", ",")
    )
    tokens = [t.strip() for t in normalized.split(",") if t.strip()]
    id_set = set()
    total = 0
    for token in tokens:
        m = re.fullmatch(r"(\d+)\s*(?:托|tray|trays)?", token, re.I)
        if m:
            total += _to_int(m.group(1), 0)
            continue
        norm_id = str(token).strip().upper()
        if not norm_id:
            continue
        id_set.add(norm_id)
        total += 1
    return id_set, total


def _calc_saw_log_mt(size_mm: int, length_ft: int, quantity: int) -> float:
    if size_mm <= 0 or quantity <= 0 or length_ft <= 0:
        return 0.0
    return float(size_mm) * float(size_mm) * float(length_ft) * float(quantity) / 115200.0


def _normalize_saw_machine_payload(raw_payload):
    payload = raw_payload
    if isinstance(raw_payload, str):
        text = raw_payload.strip()
        if not text:
            return []
        payload = json.loads(text)
    if not isinstance(payload, list):
        raise ValueError("invalid saw machine payload")

    normalized = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        machine_no = _to_int(item.get("machine_no"), 0)
        if machine_no < 1 or machine_no > 6:
            continue
        log_details = []
        for detail in item.get("log_details", []) if isinstance(item.get("log_details"), list) else []:
            if not isinstance(detail, dict):
                continue
            size_mm = _to_int(detail.get("size_mm"), 0)
            length_ft = _to_int(detail.get("length_ft"), 3)
            quantity = _to_int(detail.get("quantity"), 0)
            if size_mm <= 0 or quantity <= 0 or length_ft not in (3, 4):
                continue
            log_details.append(
                {
                    "size_mm": size_mm,
                    "length_ft": length_ft,
                    "quantity": quantity,
                    "consumed_mt": round(_calc_saw_log_mt(size_mm, length_ft, quantity), 4),
                }
            )
        saw_mt_input = _to_float(item.get("saw_mt"), 0.0)
        saw_mt = round(sum(d["consumed_mt"] for d in log_details), 4) if log_details else round(saw_mt_input, 4)
        normalized.append(
            {
                "machine_no": machine_no,
                "saw_mt": saw_mt,
                "saw_trays": _to_int(item.get("saw_trays"), 0),
                "bark_m3": round(_to_float(item.get("bark_m3"), 0.0), 4),
                "dust_bags": _to_int(item.get("dust_bags"), 0),
                "log_details": log_details,
            }
        )

    normalized.sort(key=lambda rec: rec["machine_no"])
    return normalized


def _normalize_log_entry_details(raw_payload):
    payload = raw_payload
    if isinstance(raw_payload, str):
        text = raw_payload.strip()
        if not text:
            return []
        payload = json.loads(text)
    if not isinstance(payload, list):
        return []

    details = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        size_mm = _to_int(item.get("size_mm"), 0)
        length_ft = _to_int(item.get("length_ft"), 3)
        quantity = _to_int(item.get("quantity"), 0)
        if size_mm <= 0 or quantity <= 0 or length_ft not in (3, 4):
            continue
        details.append(
            {
                "size_mm": size_mm,
                "length_ft": length_ft,
                "quantity": quantity,
                "consumed_mt": round(_calc_saw_log_mt(size_mm, length_ft, quantity), 4),
            }
        )
    return details


def _default_log_price_rules():
    # 中文注释：默认全部可见，但未启用；价格按你给的区间基准值填充。
    return [
        {
            "key": item["key"],
            "label": item["label"],
            "min_size": item["min"],
            "max_size": item["max"],
            "is_max_open": int(item["is_max_open"]),
            "enabled": 0,
            "price_per_mt": float(item["default_price"]),
        }
        for item in LOG_PRICE_RULE_DEFS
    ]


def _normalize_log_price_rules(raw_payload):
    payload = raw_payload
    if isinstance(raw_payload, str):
        text = raw_payload.strip()
        if not text:
            return _default_log_price_rules()
        payload = json.loads(text)
    if not isinstance(payload, list):
        return _default_log_price_rules()

    merged = {item["key"]: dict(item) for item in _default_log_price_rules()}
    for item in payload:
        if not isinstance(item, dict):
            continue
        key = str(item.get("key", "") or "").strip()
        if key not in merged:
            continue
        merged[key]["enabled"] = 1 if _to_int(item.get("enabled"), 0) == 1 else 0
        price = _to_float(item.get("price_per_mt"), merged[key]["price_per_mt"])
        merged[key]["price_per_mt"] = max(0.0, float(price))
    return [merged[item["key"]] for item in LOG_PRICE_RULE_DEFS]


def _in_rule_range(size_val: float, rule: dict) -> bool:
    lo = _to_float(rule.get("min_size"), 0.0)
    hi = _to_float(rule.get("max_size"), 0.0)
    if _to_int(rule.get("is_max_open"), 0) == 1:
        return size_val >= lo
    return lo <= size_val <= hi


def _pick_log_rule_for_size(size_val: float, enabled_rules: list):
    for rule in enabled_rules:
        if _in_rule_range(size_val, rule):
            return rule
    return None


def _build_log_settlement(details: list, rules: list):
    enabled_rules = [
        r for r in rules
        if _to_int(r.get("enabled"), 0) == 1 and _to_float(r.get("price_per_mt"), 0.0) > 0
    ]
    # 中文注释：按固定顺序匹配，避免每次汇总顺序变化导致结果跳动。
    key_order = [item["key"] for item in LOG_PRICE_RULE_DEFS]
    enabled_rules.sort(key=lambda r: key_order.index(str(r.get("key", ""))) if str(r.get("key", "")) in key_order else 999)

    aggregates = {}
    unmatched_mt = 0.0
    for detail in details:
        size_val = _to_float(detail.get("size_mm"), 0.0)
        mt = _to_float(detail.get("consumed_mt"), 0.0)
        if mt <= 0:
            continue
        matched = _pick_log_rule_for_size(size_val, enabled_rules)
        if not matched:
            unmatched_mt += mt
            continue
        key = str(matched.get("key", "") or "")
        row = aggregates.get(key, {"rule_key": key, "rule_label": str(matched.get("label", "") or ""), "price_per_mt": _to_float(matched.get("price_per_mt"), 0.0), "mt": 0.0})
        row["mt"] = round(_to_float(row.get("mt"), 0.0) + mt, 4)
        aggregates[key] = row

    results = []
    total_amount = 0.0
    for key in key_order:
        row = aggregates.get(key)
        if not row:
            continue
        price = _to_float(row.get("price_per_mt"), 0.0)
        amount = round(_to_float(row.get("mt"), 0.0) * price, 2)
        total_amount += amount
        row["amount_ks"] = amount
        results.append(row)
    return results, round(unmatched_mt, 4), round(total_amount, 2)


def _upsert_log_pricing_profile(session, driver_name: str, truck_number: str, rules: list, updated_by: str):
    if not driver_name:
        return
    profile = (
        session.query(LogPricingProfile)
        .filter_by(driver_name=driver_name, truck_number=truck_number)
        .first()
    )
    if profile is None:
        profile = LogPricingProfile(driver_name=driver_name, truck_number=truck_number, updated_by=updated_by)
        session.add(profile)
        session.flush()
    else:
        profile.updated_at = datetime.now().isoformat()
        profile.updated_by = updated_by

    existing = session.query(LogPricingRule).filter_by(profile_id=int(profile.id)).all()
    existing_map = {str(row.rule_key): row for row in existing}
    for rule in rules:
        key = str(rule.get("key", "") or "")
        if not key:
            continue
        row = existing_map.get(key)
        if row is None:
            row = LogPricingRule(profile_id=int(profile.id), rule_key=key)
            session.add(row)
        row.rule_label = str(rule.get("label", "") or LOG_PRICE_RULE_DEF_MAP.get(key, {}).get("label", ""))
        row.min_size = _to_float(rule.get("min_size"), _to_float(LOG_PRICE_RULE_DEF_MAP.get(key, {}).get("min"), 0.0))
        row.max_size = _to_float(rule.get("max_size"), _to_float(LOG_PRICE_RULE_DEF_MAP.get(key, {}).get("max"), 0.0))
        row.is_max_open = 1 if _to_int(rule.get("is_max_open"), 0) == 1 else 0
        row.price_per_mt = round(max(0.0, _to_float(rule.get("price_per_mt"), 0.0)), 4)
        row.enabled = 1 if _to_int(rule.get("enabled"), 0) == 1 else 0
        row.updated_at = datetime.now().isoformat()


def _load_log_pricing_profile(session, driver_name: str, truck_number: str):
    q = session.query(LogPricingProfile).filter_by(driver_name=driver_name)
    profile = None
    if truck_number:
        profile = q.filter_by(truck_number=truck_number).first()
    if profile is None:
        profile = q.order_by(LogPricingProfile.updated_at.desc()).first()
    if profile is None:
        return None, _default_log_price_rules()
    rows = session.query(LogPricingRule).filter_by(profile_id=int(profile.id)).all()
    row_map = {str(r.rule_key): r for r in rows}
    rules = []
    for item in LOG_PRICE_RULE_DEFS:
        key = item["key"]
        row = row_map.get(key)
        if row is None:
            rules.append(
                {
                    "key": key,
                    "label": item["label"],
                    "min_size": item["min"],
                    "max_size": item["max"],
                    "is_max_open": int(item["is_max_open"]),
                    "enabled": 0,
                    "price_per_mt": float(item["default_price"]),
                }
            )
            continue
        rules.append(
            {
                "key": key,
                "label": str(row.rule_label or item["label"]),
                "min_size": _to_float(row.min_size, item["min"]),
                "max_size": _to_float(row.max_size, item["max"]),
                "is_max_open": 1 if _to_int(row.is_max_open, 0) == 1 else 0,
                "enabled": 1 if _to_int(row.enabled, 0) == 1 else 0,
                "price_per_mt": _to_float(row.price_per_mt, item["default_price"]),
            }
        )
    return profile, rules


def _persist_saw_machine_stats(records):
    if not records:
        return
    flow = _read_flow_data()
    day_key = datetime.now().strftime("%Y-%m-%d")
    totals = flow.get("saw_machine_totals", {})
    if not isinstance(totals, dict):
        totals = {}
    daily = flow.get("saw_machine_daily", {})
    if not isinstance(daily, dict):
        daily = {}
    day_map = daily.get(day_key, {})
    if not isinstance(day_map, dict):
        day_map = {}

    for rec in records:
        machine_key = str(_to_int(rec.get("machine_no"), 0))
        if not machine_key or machine_key == "0":
            continue
        total_row = totals.get(machine_key, {}) if isinstance(totals.get(machine_key), dict) else {}
        day_row = day_map.get(machine_key, {}) if isinstance(day_map.get(machine_key), dict) else {}
        totals[machine_key] = {
            "mt": round(_to_float(total_row.get("mt"), 0.0) + _to_float(rec.get("saw_mt"), 0.0), 4),
            "tray": _to_int(total_row.get("tray"), 0) + _to_int(rec.get("saw_trays"), 0),
        }
        day_map[machine_key] = {
            "mt": round(_to_float(day_row.get("mt"), 0.0) + _to_float(rec.get("saw_mt"), 0.0), 4),
            "tray": _to_int(day_row.get("tray"), 0) + _to_int(rec.get("saw_trays"), 0),
            "bark": _to_int(day_row.get("bark"), 0) + int(round(_to_float(rec.get("bark_m3"), 0.0))),
            "dust": _to_int(day_row.get("dust"), 0) + _to_int(rec.get("dust_bags"), 0),
        }

    daily[day_key] = day_map
    flow["saw_machine_totals"] = totals
    flow["saw_machine_daily"] = daily
    _save_flow_data(flow)


def register_production_kiln_routes(app, logger=None):
    if logger is None:
        logger = logging.getLogger(__name__)

    # 中文注释：模块内保留原有重定向行为，避免改动业务返回格式
    def _redirect_index_result(message: str, error: bool = False):
        return redirect(
            url_for(
                "index",
                result=str(message or ""),
                error="1" if error else "0",
                lang=get_lang(),
            ),
            code=303,
        )

    def _today_prefix() -> str:
        return datetime.now().strftime("%Y-%m-%d")

    def _today_sorted_trays() -> int:
        session = Session()
        try:
            rows = (
                session.query(SortRecord.sort_trays)
                .filter(SortRecord.created_at.like(f"{_today_prefix()}%"))
                .all()
            )
            return sum(_to_int(getattr(row, "sort_trays", 0), 0) for row in rows)
        finally:
            session.close()

    @app.route("/submit_log_entry", methods=["POST"])
    @login_required
    def submit_log_entry():
        try:
            truck_number = request.form.get("truck_number", "").strip()
            driver_name = request.form.get("driver_name", "").strip()
            log_amount = _to_float(request.form.get("log_amount", 0), 0.0)
            size_range = str(request.form.get("log_size_range", "") or "").strip()
            price_per_mt = _to_float(request.form.get("log_price_per_mt", 0), 0.0)
            log_details = _normalize_log_entry_details(request.form.get("log_details_payload", ""))
            log_price_rules = _normalize_log_price_rules(request.form.get("log_price_rules_payload", ""))
            if log_details:
                log_amount = round(sum(_to_float(item.get("consumed_mt"), 0.0) for item in log_details), 4)
            if not all([truck_number, driver_name, log_amount > 0]):
                return _redirect_index_result(f"❌ {_t('fill_required')}", error=True)

            session = Session()
            # 防重复：15秒内同用户+同车牌+同司机+同数量，判定为刷新导致的重复提交
            latest = (
                session.query(LogEntry)
                .filter_by(created_by=current_user.username)
                .order_by(LogEntry.id.desc())
                .first()
            )
            if latest:
                try:
                    latest_dt = datetime.fromisoformat(latest.created_at)
                    if (
                        latest.truck_number == truck_number
                        and latest.driver_name == driver_name
                        and abs(float(latest.log_amount or 0) - float(log_amount)) < 1e-9
                        and (datetime.now() - latest_dt).total_seconds() <= 15
                    ):
                        session.close()
                        return _redirect_index_result(f"⚠️ {_t('duplicate_log_entry_blocked')}", error=False)
                except Exception:
                    pass
            # 中文注释：再做一层全局防重，避免不同账号在短时间内重复录入同一车次。
            epsilon = 1e-6
            recent_global_same = (
                session.query(LogEntry)
                .filter(LogEntry.truck_number == truck_number)
                .filter(LogEntry.driver_name == driver_name)
                .filter(LogEntry.log_amount >= float(log_amount) - epsilon)
                .filter(LogEntry.log_amount <= float(log_amount) + epsilon)
                .order_by(LogEntry.id.desc())
                .first()
            )
            if recent_global_same:
                try:
                    recent_dt = datetime.fromisoformat(str(recent_global_same.created_at or ""))
                    if (datetime.now() - recent_dt).total_seconds() <= 90:
                        session.close()
                        return _redirect_index_result(f"⚠️ {_t('duplicate_log_entry_blocked')}", error=False)
                except Exception:
                    pass

            log_entry = LogEntry(
                truck_number=truck_number,
                driver_name=driver_name,
                log_amount=log_amount,
                created_by=current_user.username,
            )
            session.add(log_entry)
            session.flush()
            if size_range or price_per_mt > 0:
                session.add(
                    LogEntryMeta(
                        log_entry_id=int(log_entry.id),
                        size_range=size_range,
                        price_per_mt=round(price_per_mt, 4),
                        created_by=current_user.username,
                    )
                )
            for detail in log_details:
                session.add(
                    LogEntryDetail(
                        log_entry_id=int(log_entry.id),
                        size_mm=_to_int(detail.get("size_mm"), 0),
                        length_ft=_to_int(detail.get("length_ft"), 3),
                        quantity=_to_int(detail.get("quantity"), 0),
                        consumed_mt=round(_to_float(detail.get("consumed_mt"), 0.0), 4),
                        created_by=current_user.username,
                    )
                )
            settlement_rows, unmatched_mt, total_amount_ks = _build_log_settlement(log_details, log_price_rules)
            for row in settlement_rows:
                session.add(
                    LogEntrySettlement(
                        log_entry_id=int(log_entry.id),
                        driver_name=driver_name,
                        truck_number=truck_number,
                        rule_key=str(row.get("rule_key", "") or ""),
                        rule_label=str(row.get("rule_label", "") or ""),
                        price_per_mt=round(_to_float(row.get("price_per_mt"), 0.0), 4),
                        mt=round(_to_float(row.get("mt"), 0.0), 4),
                        amount_ks=round(_to_float(row.get("amount_ks"), 0.0), 2),
                        created_by=current_user.username,
                    )
                )
            _upsert_log_pricing_profile(
                session=session,
                driver_name=driver_name,
                truck_number=truck_number,
                rules=log_price_rules,
                updated_by=current_user.username,
            )
            session.commit()
            session.close()
            sync_raw_inventory(log_amount)
            audit_admin_action(
                "submit_log_entry",
                target=f"log_entry:{truck_number}",
                detail=(
                    f"driver={driver_name},mt={log_amount:.4f},"
                    f"details={len(log_details)},settlements={len(settlement_rows)},"
                    f"amount_ks={total_amount_ks:.2f},unmatched_mt={unmatched_mt:.4f}"
                ),
            )

            lc = _lang_code()
            if lc == "en":
                result = f"Log entry saved: truck {truck_number}, driver {driver_name}, {log_amount:.4f} MT"
            elif lc == "my":
                result = f"ထင်းဝင်စာရင်း အောင်မြင်: ကား {truck_number}, ယာဉ်မောင်း {driver_name}, {log_amount:.4f} MT"
            else:
                extra = ""
                if total_amount_ks > 0:
                    extra = f"，计价合计 {total_amount_ks:.2f}Ks"
                if unmatched_mt > 0:
                    extra += f"，未匹配区间 {unmatched_mt:.4f}MT"
                result = f"原木入库成功：车牌{truck_number}, 司机{driver_name}, {log_amount:.4f}MT{extra}"
            return _redirect_index_result(result, error=False)
        except Exception as e:
            return _redirect_index_result(f"❌ {_t('log_entry_fail')}: {str(e)}", error=True)

    @app.route("/api/log_driver_profile", methods=["GET"])
    @login_required
    def api_log_driver_profile():
        driver_name = str(request.args.get("driver_name", "") or "").strip()
        truck_number = str(request.args.get("truck_number", "") or "").strip()
        if not driver_name:
            return jsonify({"found": False, "driver_name": "", "truck_number": "", "rules": _default_log_price_rules()})
        session = Session()
        try:
            profile, rules = _load_log_pricing_profile(session, driver_name, truck_number)
            if not profile:
                return jsonify(
                    {
                        "found": False,
                        "driver_name": driver_name,
                        "truck_number": truck_number,
                        "rules": rules,
                    }
                )
            return jsonify(
                {
                    "found": True,
                    "driver_name": str(profile.driver_name or ""),
                    "truck_number": str(profile.truck_number or ""),
                    "rules": rules,
                }
            )
        finally:
            session.close()

    @app.route("/api/log_entry_settlements", methods=["GET"])
    @login_required
    def api_log_entry_settlements():
        driver_name = str(request.args.get("driver_name", "") or "").strip()
        truck_number = str(request.args.get("truck_number", "") or "").strip()
        limit = max(1, min(100, _to_int(request.args.get("limit"), 20)))
        session = Session()
        try:
            q = session.query(LogEntrySettlement)
            if driver_name:
                q = q.filter_by(driver_name=driver_name)
            if truck_number:
                q = q.filter_by(truck_number=truck_number)
            rows = q.order_by(LogEntrySettlement.id.desc()).limit(limit).all()
            result = [
                {
                    "log_entry_id": _to_int(r.log_entry_id, 0),
                    "driver_name": str(r.driver_name or ""),
                    "truck_number": str(r.truck_number or ""),
                    "rule_key": str(r.rule_key or ""),
                    "rule_label": str(r.rule_label or ""),
                    "price_per_mt": round(_to_float(r.price_per_mt, 0.0), 4),
                    "mt": round(_to_float(r.mt, 0.0), 4),
                    "amount_ks": round(_to_float(r.amount_ks, 0.0), 2),
                    "created_at": str(r.created_at or ""),
                }
                for r in rows
            ]
            return jsonify({"rows": result})
        finally:
            session.close()

    @app.route("/api/log_entries", methods=["GET"])
    @login_required
    def api_log_entries():
        limit = max(1, min(1000, _to_int(request.args.get("limit"), 300)))
        driver_name_filter = str(request.args.get("driver_name", "") or "").strip()
        truck_number_filter = str(request.args.get("truck_number", "") or "").strip()
        date_filter = str(request.args.get("date", "") or "").strip()
        session = Session()
        try:
            q = session.query(LogEntry)
            if driver_name_filter:
                q = q.filter(LogEntry.driver_name == driver_name_filter)
            if truck_number_filter:
                q = q.filter(LogEntry.truck_number == truck_number_filter)
            if date_filter:
                q = q.filter(LogEntry.created_at.like(f"{date_filter}%"))
            rows = q.order_by(LogEntry.id.desc()).limit(limit).all()
            result = []
            total_mt = 0.0
            for row in rows:
                mt = round(_to_float(row.log_amount, 0.0), 4)
                total_mt += mt
                result.append(
                    {
                        "id": _to_int(row.id, 0),
                        "created_at": str(row.created_at or "").replace("T", " ")[:16],
                        "driver_name": str(row.driver_name or ""),
                        "truck_number": str(row.truck_number or ""),
                        "log_amount": mt,
                    }
                )
            return jsonify({"rows": result, "total_mt": round(total_mt, 4)})
        finally:
            session.close()

    @app.route("/api/log_entries/<int:log_entry_id>", methods=["DELETE"])
    @login_required
    def delete_log_entry(log_entry_id: int):
        if not current_user.has_permission("admin"):
            return jsonify({"error": _t("no_admin_perm")}), 403
        if log_entry_id <= 0:
            return jsonify({"error": _t("adjust_invalid_value")}), 400

        session = Session()
        try:
            entry = session.query(LogEntry).filter(LogEntry.id == int(log_entry_id)).first()
            if not entry:
                return jsonify({"error": "not found"}), 404

            mt = round(_to_float(entry.log_amount, 0.0), 4)
            session.query(LogEntryMeta).filter(LogEntryMeta.log_entry_id == int(log_entry_id)).delete(synchronize_session=False)
            session.query(LogEntryDetail).filter(LogEntryDetail.log_entry_id == int(log_entry_id)).delete(synchronize_session=False)
            session.query(LogEntrySettlement).filter(LogEntrySettlement.log_entry_id == int(log_entry_id)).delete(synchronize_session=False)
            session.delete(entry)
            session.commit()

            # 中文注释：删除入库记录时同步回退原木库存，确保首页与库存口径一致。
            if mt > 0:
                sync_raw_inventory(-mt)
            return jsonify({"ok": True, "deleted_id": int(log_entry_id), "rollback_mt": mt})
        except Exception as e:
            session.rollback()
            return jsonify({"error": str(e)}), 500
        finally:
            session.close()

    @app.route("/export/log_entries_detail", methods=["GET"])
    @login_required
    def export_log_entries_detail():
        log_entry_id = _to_int(request.args.get("log_entry_id"), 0)
        driver_name_filter = str(request.args.get("driver_name", "") or "").strip()
        date_filter = str(request.args.get("date", "") or "").strip()
        session = Session()
        try:
            q = session.query(LogEntry)
            if log_entry_id > 0:
                q = q.filter(LogEntry.id == log_entry_id)
            else:
                if driver_name_filter:
                    q = q.filter(LogEntry.driver_name == driver_name_filter)
                if date_filter:
                    q = q.filter(LogEntry.created_at.like(f"{date_filter}%"))
            entries = q.order_by(LogEntry.id.desc()).all()
            details = session.query(LogEntryDetail).order_by(LogEntryDetail.id.asc()).all()
            detail_map = {}
            for d in details:
                eid = _to_int(d.log_entry_id, 0)
                if eid <= 0:
                    continue
                detail_map.setdefault(eid, []).append(d)

            summary_rows = []
            detail_rows = []
            summary_mt_total = 0.0
            detail_mt_total = 0.0
            detail_qty_total = 0
            for e in entries:
                eid = _to_int(e.id, 0)
                mt = round(_to_float(e.log_amount, 0.0), 4)
                summary_mt_total += mt
                created_at = str(e.created_at or "").replace("T", " ")[:19]
                summary_rows.append(
                    {
                        "日期": created_at,
                        "司机": str(e.driver_name or ""),
                        "车号": str(e.truck_number or ""),
                        "MT": mt,
                    }
                )
                for d in detail_map.get(eid, []):
                    d_mt = round(_to_float(d.consumed_mt, 0.0), 4)
                    qty = _to_int(d.quantity, 0)
                    detail_mt_total += d_mt
                    detail_qty_total += qty
                    detail_rows.append(
                        {
                            "日期": created_at,
                            "司机": str(e.driver_name or ""),
                            "车号": str(e.truck_number or ""),
                            "尺寸": _to_int(d.size_mm, 0),
                            "长度": _to_int(d.length_ft, 0),
                            "数量": qty,
                            "MT": d_mt,
                        }
                    )

            if not summary_rows:
                summary_rows.append({"日期": "", "司机": "", "车号": "", "MT": 0.0})
            if not detail_rows:
                detail_rows.append({"日期": "", "司机": "", "车号": "", "尺寸": 0, "长度": 0, "数量": 0, "MT": 0.0})

            summary_rows.append({"日期": "合计", "司机": "", "车号": "", "MT": round(summary_mt_total, 4)})
            detail_rows.append(
                {
                    "日期": "合计",
                    "司机": "",
                    "车号": "",
                    "尺寸": "",
                    "长度": "",
                    "数量": detail_qty_total,
                    "MT": round(detail_mt_total, 4),
                }
            )

            output = BytesIO()
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                pd.DataFrame(summary_rows).to_excel(writer, index=False, sheet_name="已入库汇总")
                pd.DataFrame(detail_rows).to_excel(writer, index=False, sheet_name="尺寸明细")
            output.seek(0)
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filters = []
            if log_entry_id > 0:
                filters.append(f"trip_{log_entry_id}")
            if driver_name_filter:
                filters.append(f"driver_{driver_name_filter}")
            if date_filter:
                filters.append(f"date_{date_filter}")
            suffix = "_" + "_".join(filters) if filters else ""
            return send_file(
                output,
                as_attachment=True,
                download_name=f"log_entries_detail{suffix}_{stamp}.xlsx",
                mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        finally:
            session.close()

    @app.route("/submit_saw", methods=["POST"])
    @login_required
    def submit_saw():
        try:
            saw_machine_records = []
            raw_machine_payload = request.form.get("saw_machine_payload", "")
            if str(raw_machine_payload or "").strip():
                saw_machine_records = _normalize_saw_machine_payload(raw_machine_payload)

            saw_tm = _to_float(request.form.get("saw_tm"), 0.0)
            saw_trays = _to_int(request.form.get("saw_trays"), 0)
            bark_m3 = _to_float(request.form.get("bark_m3"), 0.0)
            dust_bags = _to_int(request.form.get("dust_bags"), 0)
            if saw_machine_records:
                saw_tm = round(sum(_to_float(item.get("saw_mt"), 0.0) for item in saw_machine_records), 4)
                saw_trays = sum(_to_int(item.get("saw_trays"), 0) for item in saw_machine_records)
                bark_m3 = round(sum(_to_float(item.get("bark_m3"), 0.0) for item in saw_machine_records), 4)
                dust_bags = sum(_to_int(item.get("dust_bags"), 0) for item in saw_machine_records)

            stock_data = get_stock_data_with_lang()
            if saw_tm <= 0 or saw_trays < 0 or bark_m3 < 0 or dust_bags < 0:
                return _redirect_index_result(f"❌ {_t('fill_required')}", error=True)
            if stock_data["log_stock"] < saw_tm:
                return _redirect_index_result(f"❌ {_t('log_stock_insufficient')}", error=True)

            session = Session()
            consumption = LogConsumption(
                consumed_amount=saw_tm,
                operation_type="saw",
                created_by=current_user.username,
            )
            session.add(consumption)
            saw_record_row = SawRecord(
                saw_mt=saw_tm,
                saw_trays=saw_trays,
                bark_sales_amount=bark_m3,
                dust_sales_amount=float(dust_bags),
                created_by=current_user.username,
            )
            session.add(saw_record_row)
            session.add(
                ByproductRecord(
                    bark_sale_amount=bark_m3,
                    dust_bags_in=dust_bags,
                    dust_bags_out=0,
                    dust_sale_amount=0.0,
                    created_by=current_user.username,
                )
            )
            session.flush()
            saw_record_id = int(saw_record_row.id) if saw_record_row and saw_record_row.id else None
            if saw_machine_records:
                for machine in saw_machine_records:
                    machine_row = SawMachineRecord(
                        saw_record_id=saw_record_id,
                        machine_no=_to_int(machine.get("machine_no"), 0),
                        saw_mt=_to_float(machine.get("saw_mt"), 0.0),
                        saw_trays=_to_int(machine.get("saw_trays"), 0),
                        bark_m3=_to_float(machine.get("bark_m3"), 0.0),
                        dust_bags=_to_int(machine.get("dust_bags"), 0),
                        created_by=current_user.username,
                    )
                    session.add(machine_row)
                    session.flush()
                    for detail in machine.get("log_details", []):
                        session.add(
                            SawMachineLogDetail(
                                machine_record_id=machine_row.id,
                                saw_record_id=saw_record_id,
                                machine_no=_to_int(machine.get("machine_no"), 0),
                                size_mm=_to_int(detail.get("size_mm"), 0),
                                length_ft=_to_int(detail.get("length_ft"), 3),
                                quantity=_to_int(detail.get("quantity"), 0),
                                consumed_mt=_to_float(detail.get("consumed_mt"), 0.0),
                                created_by=current_user.username,
                            )
                        )
            session.commit()
            session.close()
            sync_raw_inventory(-saw_tm)

            update_flow_data(
                {
                    "saw_tray_pool": stock_data["saw_stock"] + saw_trays,
                    "dust_bag_pool": stock_data.get("dust_bag_stock", 0) + dust_bags,
                    "bark_stock_ks_pool": float(stock_data.get("bark_stock_ks", 0.0)) + float(bark_m3) * float(BARK_PRICE_PER_M3_KS),
                    "bark_stock_m3": (float(stock_data.get("bark_stock_ks", 0.0)) + float(bark_m3) * float(BARK_PRICE_PER_M3_KS)) / float(BARK_PRICE_PER_M3_KS),
                }
            )
            _persist_saw_machine_stats(saw_machine_records)
            audit_admin_action(
                "submit_saw",
                target="saw_record",
                detail=(
                    f"mt={saw_tm:.4f},trays={saw_trays},bark_m3={bark_m3:.4f},"
                    f"dust_bags={dust_bags},machines={len(saw_machine_records)}"
                ),
            )

            lc = _lang_code()
            if lc == "en":
                result = f"Sawing saved: consumed {saw_tm:.4f} MT logs, output {saw_trays} trays, bark {bark_m3:.2f} m³, dust {dust_bags} bags"
            elif lc == "my":
                result = f"ခုတ်လုပ်မှု အောင်မြင်: ထင်း {saw_tm:.4f} MT သုံး, ထုတ်ကုန် {saw_trays} ထပ်ခါး, ပေါက်ဖတ် {bark_m3:.2f} m³, အမှုန့် {dust_bags} အိတ်"
            else:
                result = f"锯解提交成功：消耗{saw_tm:.4f}MT原木，产出{saw_trays}锯托，产生树皮{bark_m3:.2f}立方，产生木渣{dust_bags}袋"
            return _redirect_index_result(result, error=False)
        except Exception as e:
            return _redirect_index_result(f"❌ {_t('saw_submit_fail')}: {str(e)}", error=True)

    @app.route("/submit_byproduct_sale", methods=["POST"])
    @login_required
    def submit_byproduct_sale():
        try:
            sell_dust_bags = _to_int(request.form.get("sell_dust_bags"), 0)
            sell_bark_ks = _to_float(request.form.get("sell_bark_ks"), 0.0)
            sell_waste_segment_bags = _to_int(request.form.get("sell_waste_segment_bags"), 0)
            stock_data = get_stock_data_with_lang()

            if sell_dust_bags < 0 or sell_bark_ks < 0 or sell_waste_segment_bags < 0:
                return _redirect_index_result(f"❌ {_t('fill_required')}", error=True)
            current_bark_ks = float(stock_data.get("bark_stock_ks", 0.0))
            sell_bark_m3 = sell_bark_ks / BARK_PRICE_PER_M3_KS
            if stock_data.get("dust_bag_stock", 0) < sell_dust_bags:
                return _redirect_index_result(f"❌ {_t('dust_stock_insufficient')}", error=True)
            if current_bark_ks < sell_bark_ks:
                return _redirect_index_result(f"❌ {_t('bark_stock_insufficient')}", error=True)
            if stock_data.get("waste_segment_bag_stock", 0) < sell_waste_segment_bags:
                return _redirect_index_result(f"❌ {_t('waste_segment_stock_insufficient')}", error=True)

            session = Session()
            session.add(
                ByproductRecord(
                    bark_sale_amount=sell_bark_ks,
                    dust_bags_in=0,
                    dust_bags_out=sell_dust_bags + sell_waste_segment_bags,
                    dust_sale_amount=float(sell_waste_segment_bags * WASTE_SEGMENT_PRICE_PER_BAG_KS),
                    created_by=current_user.username,
                )
            )
            session.commit()
            session.close()

            new_bark_ks = current_bark_ks - sell_bark_ks
            update_flow_data(
                {
                    "dust_bag_pool": stock_data.get("dust_bag_stock", 0) - sell_dust_bags,
                    "bark_stock_ks_pool": new_bark_ks,
                    "bark_stock_m3": new_bark_ks / float(BARK_PRICE_PER_M3_KS),
                    "waste_segment_bag_pool": stock_data.get("waste_segment_bag_stock", 0) - sell_waste_segment_bags,
                }
            )
            audit_admin_action(
                "submit_byproduct_sale",
                target="byproduct_sale",
                detail=(
                    f"dust_out={sell_dust_bags},bark_ks={sell_bark_ks:.2f},"
                    f"bark_m3={sell_bark_m3:.4f},waste_segment_out={sell_waste_segment_bags}"
                ),
            )

            lc = _lang_code()
            if lc == "en":
                result = (
                    f"Byproduct sale saved: sawdust {sell_dust_bags} bags, bark {sell_bark_ks:.0f} Ks "
                    f"({sell_bark_m3:.2f} m³), waste segment {sell_waste_segment_bags} bags"
                )
            elif lc == "my":
                result = (
                    f"ဘေးထွက်ရောင်းချမှု အောင်မြင်: အမှုန့် {sell_dust_bags} အိတ်, ပေါက်ဖတ် {sell_bark_ks:.0f} Ks "
                    f"({sell_bark_m3:.2f} m³), အလွှာအပိုင်း {sell_waste_segment_bags} အိတ်"
                )
            else:
                result = (
                    f"副产品销售提交成功：销售木渣{sell_dust_bags}袋，销售树皮{sell_bark_ks:.0f}Ks"
                    f"（折算{sell_bark_m3:.2f}立方），销售废木段{sell_waste_segment_bags}袋"
                )

            return _redirect_index_result(result, error=False)
        except Exception as e:
            return _redirect_index_result(f"❌ {_t('sys_error')}: {str(e)}", error=True)

    @app.route("/admin/adjust_bark_sale", methods=["POST"])
    @login_required
    def admin_adjust_bark_sale():
        if not current_user.has_permission("admin"):
            return _redirect_index_result(f"❌ {_t('no_admin_perm')}", error=True)
        try:
            bark_sale_delta_ks = _to_float(request.form.get("bark_sale_delta_ks"), 0.0)
            if abs(bark_sale_delta_ks) <= 0:
                return _redirect_index_result(f"❌ {_t('fill_required')}", error=True)

            stock_data = get_stock_data_with_lang()
            bark_stock_ks = float(stock_data.get("bark_stock_ks", 0.0))
            delta_m3 = float(bark_sale_delta_ks) / float(BARK_PRICE_PER_M3_KS)
            new_bark_stock_ks = bark_stock_ks - bark_sale_delta_ks
            if new_bark_stock_ks < 0:
                return _redirect_index_result(f"❌ {_t('bark_stock_insufficient')}", error=True)

            session = Session()
            session.add(
                ByproductRecord(
                    bark_sale_amount=bark_sale_delta_ks,
                    dust_bags_in=0,
                    dust_bags_out=0,
                    dust_sale_amount=0.0,
                    created_by=current_user.username,
                )
            )
            session.commit()
            session.close()

            update_flow_data(
                {
                    "bark_stock_ks_pool": new_bark_stock_ks,
                    "bark_stock_m3": new_bark_stock_ks / float(BARK_PRICE_PER_M3_KS),
                }
            )
            audit_admin_action(
                "adjust_bark_sale",
                target="byproduct_sale",
                detail=f"delta_ks={bark_sale_delta_ks:.2f},delta_m3={delta_m3:.4f}",
            )

            if bark_sale_delta_ks >= 0:
                return _redirect_index_result(f"✅ 已补记树皮销售 {bark_sale_delta_ks:.0f}Ks", error=False)
            return _redirect_index_result(f"✅ 已冲减树皮销售 {abs(bark_sale_delta_ks):.0f}Ks", error=False)
        except Exception as e:
            return _redirect_index_result(f"❌ {_t('sys_error')}: {str(e)}", error=True)

    @app.route("/submit_dip", methods=["POST"])
    @login_required
    def submit_dip():
        try:
            dip_cans = _to_int(request.form.get("dip_cans"), 0)
            dip_trays = _to_int(request.form.get("dip_trays"), 0)
            dip_chemicals = _to_float(request.form.get("dip_chemicals"), 0.0)
            dip_additive_used = _to_float(request.form.get("dip_additive_used"), 0.0)
            dip_chem_inbound = _to_float(request.form.get("dip_chem_inbound"), 0.0)
            dip_additive_inbound = _to_float(request.form.get("dip_additive_inbound"), 0.0)

            stock_data = get_stock_data_with_lang()
            if dip_chemicals < 0 or dip_additive_used < 0 or dip_chem_inbound < 0 or dip_additive_inbound < 0:
                return _redirect_index_result(f"❌ {_t('fill_required')}", error=True)
            # 业务规则：药浸 6 项（罐次/锯托/药品添加/添加剂消耗/药品入库/添加剂入库）任意一项 > 0 即可提交。
            if not any(
                [
                    dip_cans > 0,
                    dip_trays > 0,
                    dip_chemicals > 0,
                    dip_additive_used > 0,
                    dip_chem_inbound > 0,
                    dip_additive_inbound > 0,
                ]
            ):
                return _redirect_index_result(f"❌ {_t('fill_required')}", error=True)
            if dip_trays > 0 and stock_data["saw_stock"] < dip_trays:
                return _redirect_index_result(f"❌ {_t('saw_stock_insufficient')}", error=True)
            current_dip_chem = float(stock_data.get("dip_chem_bag_stock", 0.0))
            current_additive_kg = float(stock_data.get("dip_additive_kg_stock", 0.0))
            if (current_dip_chem + dip_chem_inbound) < dip_chemicals:
                return _redirect_index_result(f"❌ {_t('dip_chem_stock_insufficient')}", error=True)
            if (current_additive_kg + dip_additive_inbound) < dip_additive_used:
                return _redirect_index_result(f"❌ {_t('dip_additive_stock_insufficient')}", error=True)

            if dip_cans > 0 or dip_trays > 0 or dip_chemicals > 0:
                session = Session()
                session.add(
                    DipRecord(
                        dip_cans=dip_cans,
                        dip_trays=dip_trays,
                        dip_chemicals=dip_chemicals,
                        created_by=current_user.username,
                    )
                )
                session.commit()
                session.close()

            update_flow_data(
                {
                    "saw_tray_pool": stock_data["saw_stock"] - dip_trays,
                    "dip_tray_pool": stock_data["dip_stock"] + dip_trays,
                    "dip_chem_bag_pool": current_dip_chem + dip_chem_inbound - dip_chemicals,
                    "dip_additive_kg_pool": current_additive_kg + dip_additive_inbound - dip_additive_used,
                }
            )
            audit_admin_action(
                "submit_dip",
                target="dip_record",
                detail=(
                    f"cans={dip_cans},trays={dip_trays},chemicals={dip_chemicals:.4f},"
                    f"additive_used={dip_additive_used:.4f},chem_in={dip_chem_inbound:.4f},"
                    f"additive_in={dip_additive_inbound:.4f}"
                ),
            )

            lc = _lang_code()
            if lc == "en":
                result = (
                    f"Dipping saved: runs {dip_cans}, trays {dip_trays}, chemical used {dip_chemicals:.2f}, "
                    f"additive used {dip_additive_used:.2f} kg, chemical inbound +{dip_chem_inbound:.2f} bags, "
                    f"additive inbound +{dip_additive_inbound:.2f} kg"
                )
            elif lc == "my":
                result = (
                    f"ဆေးစိမ်မှု အောင်မြင်: ကြိမ် {dip_cans}, ထပ်ခါး {dip_trays}, ဆေးအသုံး {dip_chemicals:.2f}, "
                    f"ထည့်ဆေးအသုံး {dip_additive_used:.2f} kg, ဆေးဝင် +{dip_chem_inbound:.2f} အိတ်, "
                    f"ထည့်ဆေးဝင် +{dip_additive_inbound:.2f} kg"
                )
            else:
                result = (
                    f"药浸提交成功：罐次{dip_cans}，锯托{dip_trays}，药品添加{dip_chemicals:.2f}袋，"
                    f"添加剂消耗{dip_additive_used:.2f}公斤，药品入库+{dip_chem_inbound:.2f}袋，"
                    f"添加剂入库+{dip_additive_inbound:.2f}公斤"
                )
            return _redirect_index_result(result, error=False)
        except Exception as e:
            return _redirect_index_result(f"❌ {_t('dip_submit_fail')}: {str(e)}", error=True)

    @app.route("/submit_sort", methods=["GET", "POST"])
    @login_required
    def submit_sort():
        if request.method == "GET":
            flash(_t("sort_submit_fail"), "error")
            return redirect(url_for("index", lang=get_lang()))

        try:
            sort_trays = _to_int(request.form.get("sort_trays"), 0)
            sorted_kiln_trays = request.form.get("sorted_kiln_trays", "").strip()

            stock_data = get_stock_data_with_lang()
            if sort_trays <= 0:
                return _redirect_index_result(f"❌ {_t('fill_required')}", error=True)
            if stock_data["dip_stock"] < sort_trays:
                return _redirect_index_result(f"❌ {_t('dip_stock_insufficient')}", error=True)

            session = Session()
            session.add(
                SortRecord(
                    sort_trays=sort_trays,
                    sorted_kiln_trays=sorted_kiln_trays,
                    created_by=current_user.username,
                )
            )
            session.commit()
            session.close()

            # 业务口径：待入窑明细由“添加窑托弹窗保存”直接落库；
            # submit_sort 仅记录今日拣选并扣减药浸库存，不再改待入窑明细。
            update_flow_data(
                {
                    "dip_tray_pool": stock_data["dip_stock"] - sort_trays,
                }
            )
            audit_admin_action(
                "submit_sort",
                target="sort_record",
                detail=f"sort_trays={sort_trays},raw={sorted_kiln_trays}",
            )

            lc = _lang_code()
            if lc == "en":
                result = f"Sorting saved: consumed {sort_trays} saw trays"
            elif lc == "my":
                result = f"ရွေးချယ်မှု အောင်မြင်: ဆေးစိမ်ထပ်ခါး {sort_trays} သုံး"
            else:
                result = f"拣选提交成功：消耗{sort_trays}锯托"
            return _redirect_index_result(result, error=False)
        except Exception as e:
            return _redirect_index_result(f"❌ {_t('sort_submit_fail')}: {str(e)}", error=True)

    @app.route("/kiln_action", methods=["POST"])
    @login_required
    def kiln_action():
        try:
            kiln_id = request.form.get("kiln_id", "")
            action = request.form.get("action", "")
            trays = request.form.get("trays", "")
            audit_target = ""
            audit_detail = ""

            if action == "start_dry":
                kiln_max_trays = _get_kiln_max_trays()
                confirm_dry = request.form.get("confirm_dry", "0")
                kilns = _load_kilns_data()
                kiln_data = kilns.get(kiln_id, {})
                trays_in_kiln = kiln_data.get("trays", [])
                current_trays = sum(_to_int(t.get("count"), 0) for t in trays_in_kiln) if isinstance(trays_in_kiln, list) else 0
                if current_trays < kiln_max_trays and confirm_dry != "1":
                    return _redirect_index_result(
                        f"❌ {_t('kiln_dry_not_full_confirm_needed').format(current=current_trays, max_trays=kiln_max_trays)}",
                        error=True,
                    )
                update_kiln_status(kiln_id, "drying")
                audit_target = f"kiln_{kiln_id}"
                audit_detail = f"action=start_dry,current_trays={current_trays}"
                lc = _lang_code()
                result = (f"Kiln {kiln_id} drying started" if lc == "en" else
                          f"မီးဖို {kiln_id} အခြောက် စတင်" if lc == "my" else
                          f"窑{kiln_id} 开始烘烤")
            elif action == "complete":
                update_kiln_status(kiln_id, "completed")
                audit_target = f"kiln_{kiln_id}"
                audit_detail = "action=complete"
                lc = _lang_code()
                result = (f"Kiln {kiln_id} completed" if lc == "en" else
                          f"မီးဖို {kiln_id} ပြီးစီး" if lc == "my" else
                          f"窑{kiln_id} 已完成")
            elif action == "start_unload":
                confirm_unload = request.form.get("confirm_unload", "0")
                elapsed_hours = 0
                try:
                    kilns = _load_kilns_data()
                    kiln_data = kilns.get(kiln_id, {})
                    if str(kiln_data.get("status", "") or "") == "unloading":
                        trays = kiln_data.get("trays", [])
                        trays_total = sum(_to_int(t.get("count"), 0) for t in trays) if isinstance(trays, list) else 0
                        stored_total = _to_int(kiln_data.get("unloading_total_trays"), 0)
                        total_trays = stored_total if stored_total > 0 else trays_total
                        unloaded = _to_int(kiln_data.get("unloaded_count"), 0)
                        remaining = max(0, total_trays - unloaded)
                        return _redirect_index_result(f"❌ {_t('kiln_already_unloading').format(remaining=remaining)}", error=True)
                    start_time = kiln_data.get("dry_start") or kiln_data.get("start")
                    if isinstance(start_time, str):
                        try:
                            start_dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
                            elapsed_hours = max(0, int((datetime.now().timestamp() - start_dt.timestamp()) // 3600))
                        except Exception:
                            elapsed_hours = 0
                    elif start_time:
                        elapsed_hours = max(0, int((time.time() - float(start_time)) // 3600))
                except Exception:
                    elapsed_hours = 0

                if elapsed_hours < 100 and confirm_unload != "1":
                    return _redirect_index_result(f"❌ {_t('kiln_unload_confirm_needed')}", error=True)

                if elapsed_hours < 100 and confirm_unload == "1":
                    update_kiln_status(kiln_id, "ready")
                else:
                    update_kiln_status(kiln_id, "unloading")
                audit_target = f"kiln_{kiln_id}"
                audit_detail = f"action=start_unload,elapsed_hours={elapsed_hours},confirm={confirm_unload}"
                lc = _lang_code()
                result = (f"Kiln {kiln_id} ready to unload" if lc == "en" else
                          f"မီးဖို {kiln_id} ထုတ်ရန် အသင့်" if lc == "my" else
                          f"窑{kiln_id} 已完成待出")
            elif action == "load":
                kiln_max_trays = _get_kiln_max_trays()
                confirm_missing_sort = request.form.get("confirm_missing_sort", "0")
                flow_data = _read_flow_data()
                selected_tray_details = flow_data.get("selected_tray_details", [])
                if not isinstance(selected_tray_details, list):
                    selected_tray_details = []
                selected_map = {item.get("id"): item for item in selected_tray_details if isinstance(item, dict) and item.get("id")}
                tray_list, loaded_tray_count = _parse_kiln_trays_input(trays, selected_map, allow_plain_count=False)
                loaded_volume = loaded_tray_count * 0.1

                kilns = _load_kilns_data()
                kiln_data = kilns.get(kiln_id, {})
                existing_trays = kiln_data.get("trays", []) if isinstance(kiln_data.get("trays"), list) else []
                incoming_ids = {item.get("id") for item in tray_list if isinstance(item, dict) and item.get("id")}
                kept_existing = [
                    item for item in existing_trays
                    if isinstance(item, dict) and item.get("id") not in incoming_ids
                ]
                merged_trays = kept_existing + tray_list
                total_tray_count = sum(_to_int(item.get("count"), 0) for item in merged_trays if isinstance(item, dict))
                if total_tray_count > kiln_max_trays:
                    return _redirect_index_result(
                        f"❌ {_t('kiln_capacity_exceeded').format(max_trays=kiln_max_trays)}",
                        error=True,
                    )

                today_sorted = _today_sorted_trays()
                if loaded_tray_count > 0 and today_sorted <= 0 and confirm_missing_sort != "1":
                    return _redirect_index_result(
                        f"❌ {_t('sort_missing_confirm_needed').format(sorted=today_sorted, loaded=loaded_tray_count)}",
                        error=True,
                    )

                stock_data = get_stock_data_with_lang()
                if stock_data["sorting_stock"] < loaded_tray_count:
                    return _redirect_index_result(f"❌ {_t('sorting_stock_insufficient')}", error=True)

                if tray_list:
                    batch_number = generate_tray_batch_number(kiln_id)
                    session = Session()
                    tray_batch = TrayBatch(
                        batch_number=batch_number,
                        kiln_id=kiln_id,
                        tray_count=loaded_tray_count,
                        total_volume=loaded_volume,
                        created_by=current_user.username,
                    )
                    session.add(tray_batch)
                    session.commit()
                    for tray in tray_list:
                        tray["batch_number"] = batch_number
                    session.close()
                else:
                    batch_number = ""

                loaded_ids = {t.get("id") for t in tray_list if t.get("id")}
                remaining_selected_details = [item for item in selected_tray_details if item.get("id") not in loaded_ids]
                update_flow_data(
                    {
                        "selected_tray_pool": stock_data["sorting_stock"] - loaded_tray_count,
                        "selected_tray_details": remaining_selected_details,
                    }
                )
                update_kiln_status(kiln_id, "loading", merged_trays)
                audit_target = f"kiln_{kiln_id}"
                audit_detail = (
                    f"action=load,added={loaded_tray_count},total={total_tray_count},"
                    f"batch={batch_number},confirm_missing_sort={confirm_missing_sort}"
                )
                lc = _lang_code()
                if lc == "en":
                    result = f"Kiln {kiln_id} loaded: batch {batch_number}, +{loaded_tray_count} trays, kiln total {total_tray_count} trays"
                elif lc == "my":
                    result = f"မီးဖို {kiln_id} ထည့်သွင်းပြီး: batch {batch_number}, +{loaded_tray_count} ထပ်ခါး, စုစုပေါင်း {total_tray_count} ထပ်ခါး"
                else:
                    result = f"窑{kiln_id} 入窑成功：批次{batch_number}，新增{loaded_tray_count}托，窑内共{total_tray_count}托"
            elif action == "unload":
                tray_list, unload_count = _parse_kiln_trays_input(trays, {}, allow_plain_count=True)
                kilns = _load_kilns_data()
                if kiln_id in kilns:
                    # 中文注释：若当前为完成待出(ready)，发生出窑动作后自动进入出窑中(unloading)。
                    current_status = str(kilns[kiln_id].get("status", "") or "")
                    if unload_count > 0 and current_status == "ready":
                        kilns[kiln_id]["status"] = "unloading"
                        kilns[kiln_id]["status_changed_at"] = int(time.time())

                    kilns[kiln_id]["unloaded_count"] = kilns[kiln_id].get("unloaded_count", 0) + unload_count
                    trays_total = sum(tray.get("count", 0) for tray in kilns[kiln_id].get("trays", []))
                    stored_total = int(kilns[kiln_id].get("unloading_total_trays", 0) or 0)
                    # 中文注释：管理员修正过总托数时，出窑流程也以该值为准。
                    total_trays = stored_total if stored_total > 0 else trays_total
                    if total_trays < kilns[kiln_id]["unloaded_count"]:
                        total_trays = kilns[kiln_id]["unloaded_count"]
                    kilns[kiln_id]["unloading_total_trays"] = total_trays
                    remaining_after = max(0, total_trays - _to_int(kilns[kiln_id].get("unloaded_count"), 0))
                    if kilns[kiln_id]["unloaded_count"] >= total_trays:
                        prev_status = str(kilns[kiln_id].get("status", "") or "")
                        kilns[kiln_id]["status"] = "completed"
                        if prev_status != "completed":
                            kilns[kiln_id]["status_changed_at"] = int(time.time())
                        elif not kilns[kiln_id].get("status_changed_at"):
                            kilns[kiln_id]["status_changed_at"] = int(time.time())
                    # 中文注释：当出窑完成且当前托数为0时，自动回到空窑状态。
                    if remaining_after <= 0:
                        kilns[kiln_id]["status"] = "empty"
                        kilns[kiln_id]["status_changed_at"] = int(time.time())
                        kilns[kiln_id]["trays"] = []
                        kilns[kiln_id]["unloaded_count"] = 0
                        kilns[kiln_id]["unloading_total_trays"] = 0
                    _save_kilns_data(kilns)

                flow_data = _read_flow_data()
                existing_done = flow_data.get("kiln_done_trays", [])
                if not isinstance(existing_done, list):
                    existing_done = []
                existing_done = list(existing_done)

                appended_done = []
                for item in tray_list:
                    if not isinstance(item, dict):
                        continue
                    cnt = max(1, _to_int(item.get("count"), 1))
                    raw_id = str(item.get("id", "") or "").strip().upper()
                    raw_spec = str(item.get("spec", "") or "").strip()
                    spec = raw_spec or "?"
                    # 中文注释：纯数量出窑（TEMP-*）没有可追踪托号，明细只补数量占位，避免库存与明细口径脱节。
                    base_id = raw_id if raw_id and (not raw_id.startswith("TEMP-")) else ""
                    if base_id and cnt == 1:
                        appended_done.append({"id": base_id, "spec": spec})
                        continue
                    for idx in range(cnt):
                        tray_id = f"{base_id}-{idx + 1}" if base_id and cnt > 1 else None
                        appended_done.append({"id": tray_id, "spec": spec})

                merged_done = existing_done + appended_done
                update_flow_data(
                    {
                        "kiln_done_trays": merged_done,
                        "kiln_done_tray_pool": len(merged_done),
                    }
                )
                audit_target = f"kiln_{kiln_id}"
                audit_detail = f"action=unload,count={unload_count}"
                lc = _lang_code()
                result = (f"Kiln {kiln_id} unloaded: {unload_count} trays" if lc == "en" else
                          f"မီးဖို {kiln_id} ထုတ်ပြီး: {unload_count} ထပ်ခါး" if lc == "my" else
                          f"窑{kiln_id} 出窑成功：{unload_count}托")
            else:
                lc = _lang_code()
                result = (f"Unknown kiln action: {action}" if lc == "en" else
                          f"မသိသော မီးဖိုလုပ်ဆောင်ချက်: {action}" if lc == "my" else
                          f"窑{kiln_id} 操作未知：{action}")

            if action in {"start_dry", "complete", "start_unload", "load", "unload"}:
                audit_admin_action("kiln_action", target=audit_target, detail=audit_detail)
            return _redirect_index_result(result, error=False)
        except Exception as e:
            return _redirect_index_result(f"❌ {_t('kiln_action_fail')}: {str(e)}", error=True)

    @app.route("/submit_secondary_sort", methods=["POST"])
    @login_required
    def submit_secondary_sort():
        try:
            secondary_sort_id_set, secondary_sort_trays = _parse_secondary_sort_input(
                request.form.get("secondary_sort_trays", "")
            )
            waste_segment_bags = _to_int(request.form.get("waste_segment_bags"), 0)

            stock_data = get_stock_data_with_lang()
            if secondary_sort_trays <= 0 and waste_segment_bags <= 0:
                return _redirect_index_result(f"❌ {_t('fill_required')}", error=True)
            if secondary_sort_trays > 0 and stock_data["kiln_done_stock"] < secondary_sort_trays:
                return _redirect_index_result(f"❌ {_t('kiln_done_insufficient')}", error=True)
            if waste_segment_bags < 0:
                return _redirect_index_result(f"❌ {_t('fill_required')}", error=True)

            flow_data = _read_flow_data()
            kiln_done_trays = flow_data.get("kiln_done_trays", [])
            second_sort_records = flow_data.get("second_sort_records", [])
            if not isinstance(second_sort_records, list):
                second_sort_records = []
            second_sort_records = list(second_sort_records)
            if secondary_sort_trays > 0:
                second_sort_records.append(
                    {
                        "time": datetime.now().isoformat(),
                        "trays": secondary_sort_trays,
                        "ok_m3": 0.0,
                        "ab_m3": 0.0,
                        "bc_m3": 0.0,
                        "loss_m3": 0.0,
                        "spec_summary": {},
                    }
                )
            flow_updates = {
                "kiln_done_tray_pool": stock_data["kiln_done_stock"] - secondary_sort_trays,
                "waste_segment_bag_pool": stock_data.get("waste_segment_bag_stock", 0) + waste_segment_bags,
                "second_sort_records": second_sort_records,
            }
            # 若存在托级明细，库存读取会以明细数量为准；二选提交时需同步扣减明细，避免页面库存不变化。
            if isinstance(kiln_done_trays, list) and kiln_done_trays:
                if secondary_sort_id_set:
                    kept = []
                    removed = 0
                    for item in kiln_done_trays:
                        tray_id = str((item or {}).get("id", "") or "").strip().upper()
                        if tray_id and tray_id in secondary_sort_id_set and removed < secondary_sort_trays:
                            removed += 1
                            continue
                        kept.append(item)
                    # 输入ID与库存明细不完全匹配时，按FIFO补扣，保证本次提交托数一致落账。
                    need = max(0, secondary_sort_trays - removed)
                    if need > 0:
                        kept = kept[need:]
                else:
                    kept = kiln_done_trays[secondary_sort_trays:]
                flow_updates["kiln_done_trays"] = kept
                flow_updates["kiln_done_tray_pool"] = len(kept)

            update_flow_data(flow_updates)
            audit_admin_action(
                "submit_secondary_sort",
                target="secondary_sort",
                detail=f"trays={secondary_sort_trays},waste_segment_in={waste_segment_bags}",
            )
            lc = _lang_code()
            if lc == "en":
                result = f"Secondary sort saved: {secondary_sort_trays} kiln trays updated, waste segment +{waste_segment_bags} bags"
            elif lc == "my":
                result = f"ဒုတိယရွေးချယ်မှု သိမ်းပြီး: {secondary_sort_trays} မီးဖိုထပ်ခါး, အလွှာအပိုင်း +{waste_segment_bags} အိတ်"
            else:
                result = f"二选提交成功：今日二选 {secondary_sort_trays} 窑托已更新，废木段入库{waste_segment_bags}袋"
            return _redirect_index_result(result, error=False)
        except Exception as e:
            return _redirect_index_result(f"❌ {_t('secondary_submit_fail')}: {str(e)}", error=True)

    @app.route("/submit_secondary_products", methods=["POST"])
    @login_required
    def submit_secondary_products():
        try:
            confirm_missing_secondary_sort = request.form.get("confirm_missing_secondary_sort", "0")
            day_prefix = _today_prefix()
            session = Session()
            try:
                secondary_sort_count = (
                    session.query(AdminAuditLog.id)
                    .filter(AdminAuditLog.action == "submit_secondary_sort")
                    .filter(AdminAuditLog.created_at.like(f"{day_prefix}%"))
                    .count()
                )
            finally:
                session.close()
            if secondary_sort_count <= 0 and confirm_missing_secondary_sort != "1":
                return _redirect_index_result(
                    f"❌ {_t('secondary_sort_missing_confirm_needed').format(count=secondary_sort_count)}",
                    error=True,
                )

            finished_product_trays = request.form.get("finished_product_trays", "")
            if not finished_product_trays.strip():
                return _redirect_index_result(f"❌ {_t('fill_required')}", error=True)

            total_product_count = 0
            total_volume = 0.0
            for product in finished_product_trays.split(","):
                parts = product.strip().split("#")
                if len(parts) == 3:
                    product_id = parts[0].strip()
                    count = _to_int(parts[1].strip(), 0)
                    grade = parts[2].strip().upper()
                    weight_kg = 0.0
                    if not product_id or count <= 0:
                        raise ValueError("invalid product entry")
                    spec, volume = _infer_spec_and_volume(product_id, count, None)
                    upsert_inventory_product(product_id=product_id, spec=spec, grade=grade, pcs=count, volume=volume, status="库存", weight_kg=weight_kg)
                    # 业务口径：一个编号=一件；count 为每件内根数（pcs）。
                    total_product_count += 1
                    total_volume += volume
                elif len(parts) >= 4:
                    product_id = parts[0].strip()
                    spec = parts[1].strip()
                    count = _to_int(parts[2].strip(), 0)
                    grade = parts[3].strip().upper()
                    weight_kg = _to_float(parts[4].strip(), 0.0) if len(parts) >= 5 else 0.0
                    if not product_id or count <= 0:
                        raise ValueError("invalid product entry")
                    # 用户手输的新规格在此自动加入匹配库（规格-数量）
                    _register_secondary_rule(spec, count)
                    spec, volume = _infer_spec_and_volume(product_id, count, spec)
                    upsert_inventory_product(product_id=product_id, spec=spec, grade=grade, pcs=count, volume=volume, status="库存", weight_kg=weight_kg)
                    # 业务口径：一个编号=一件；count 为每件内根数（pcs）。
                    total_product_count += 1
                    total_volume += volume

            batch_number = generate_product_batch_number()
            session = Session()
            product_batch = ProductBatch(
                batch_number=batch_number,
                product_count=total_product_count,
                total_volume=total_volume,
                created_by=current_user.username,
            )
            session.add(product_batch)
            session.commit()
            session.close()
            audit_admin_action(
                "submit_secondary_products",
                target=batch_number,
                detail=(
                    f"product_count={total_product_count},volume_m3={total_volume:.4f},"
                    f"confirm_missing_secondary_sort={confirm_missing_secondary_sort}"
                ),
            )

            lc = _lang_code()
            if lc == "en":
                result = f"Product inbound saved: batch {batch_number}, {total_product_count} pcs, {total_volume:.4f} m³"
            elif lc == "my":
                result = f"ကုန်ချောသိုလှောင်မှု အောင်မြင်: batch {batch_number}, {total_product_count} ခု, {total_volume:.4f} m³"
            else:
                result = f"成品入库成功：批次{batch_number}，{total_product_count}件，{total_volume:.4f}立方米"
            return _redirect_index_result(result, error=False)
        except Exception as e:
            return _redirect_index_result(f"❌ {_t('products_submit_fail')}: {str(e)}", error=True)

    @app.route("/api/secondary_spec_rules", methods=["GET", "POST"])
    @login_required
    def api_secondary_spec_rules():
        if request.method == "GET":
            session = Session()
            try:
                rules = _secondary_rule_map(session)
                out = {k: sorted(list(v)) for k, v in rules.items() if isinstance(v, list) and v}
                return jsonify({"rules": out})
            finally:
                session.close()

        data = request.get_json(silent=True) or {}
        spec = str(data.get("spec", "") or "").strip()
        pcs = _to_int(data.get("pcs"), 0)
        if not spec or pcs <= 0:
            return jsonify({"error": "invalid spec or pcs"}), 400
        try:
            spec_key = _register_secondary_rule(spec, pcs)
            return jsonify({"success": True, "spec": spec_key, "pcs": pcs})
        except Exception as e:
            return jsonify({"error": str(e)}), 400

    @app.route("/api/command", methods=["POST"])
    @login_required
    def api_command():
        data = request.get_json()
        command = data.get("command", "").strip() if data else ""
        if not command:
            return jsonify({"error": "No command provided"}), 400
        try:
            result = dispatch(command) or _t("unknown_cmd")
            return jsonify({"result": result})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/client_log")
    def api_client_log():
        try:
            logger.error(
                "CLIENT_JS_ERROR msg=%s src=%s line=%s col=%s ua=%s",
                request.args.get("msg", ""),
                request.args.get("src", ""),
                request.args.get("line", ""),
                request.args.get("col", ""),
                request.headers.get("User-Agent", ""),
            )
        except Exception:
            pass
        return ("", 204)

    @app.route("/api/kiln_trays/<kiln_id>", methods=["GET", "POST"])
    @login_required
    def api_kiln_trays(kiln_id):
        if kiln_id not in ["A", "B", "C", "D"]:
            return jsonify({"error": "invalid kiln id"}), 400

        if request.method == "GET":
            kilns = _load_kilns_data()
            kiln = kilns.get(kiln_id, {})
            trays = kiln.get("trays", []) if isinstance(kiln.get("trays"), list) else []
            trays_in_kiln = sum(_to_int(item.get("count"), 0) for item in trays if isinstance(item, dict))
            stored_total = _to_int(kiln.get("unloading_total_trays"), 0)
            unloaded_count = _to_int(kiln.get("unloaded_count"), 0)
            status = str(kiln.get("status", "empty") or "empty")
            # 中文注释：仅在待出/出窑/完成阶段优先使用修正总托；装窑/烘干阶段实时以窑内托数为准。
            if status in {"ready", "unloading", "completed"} and stored_total > 0:
                total_trays = stored_total
            else:
                total_trays = trays_in_kiln
            remaining_trays = max(0, total_trays - unloaded_count)
            return jsonify(
                {
                    "kiln_id": kiln_id,
                    "status": status,
                    "trays": trays,
                    "total_trays": total_trays,
                    "remaining_trays": remaining_trays,
                    "in_kiln_trays": trays_in_kiln,
                    "unloaded_count": unloaded_count,
                }
            )

        role = str(getattr(current_user, "role", "") or "").strip().lower()
        if not (current_user.has_permission("admin") or role in {"stats", "statistics", "finance", "统计"}):
            return jsonify({"error": _t("no_admin_perm")}), 403

        data = request.get_json(silent=True) or {}
        trays = data.get("trays", [])
        if not isinstance(trays, list):
            return jsonify({"error": "invalid trays payload"}), 400

        normalized = []
        total = 0
        for item in trays:
            if not isinstance(item, dict):
                continue
            tray_id = str(item.get("id", "")).strip()
            spec = str(item.get("spec", "")).strip()
            count = _to_int(item.get("count"), 0)
            if not tray_id or count <= 0:
                continue
            total += count
            normalized.append(
                {
                    "id": tray_id,
                    "spec": spec,
                    "count": count,
                    "volume": float(count) * 0.1,
                    "batch_number": str(item.get("batch_number", "")),
                }
            )

        kiln_max_trays = _get_kiln_max_trays()
        if total > kiln_max_trays:
            return jsonify({"error": _t("kiln_capacity_exceeded").format(max_trays=kiln_max_trays)}), 400

        kilns = _load_kilns_data()
        kiln = kilns.get(kiln_id, {})
        old_status = str(kiln.get("status", "empty") or "empty")
        old_trays = kiln.get("trays", []) if isinstance(kiln.get("trays"), list) else []
        returned_to_pending = 0

        # 中文注释：装窑中手动删除窑内托盘时，删除量自动回流到“待入窑”池，避免托盘凭空丢失。
        if old_status == "loading":
            new_count_by_id = {}
            for item in normalized:
                tid = str(item.get("id", "")).strip()
                if not tid:
                    continue
                new_count_by_id[tid] = new_count_by_id.get(tid, 0) + max(0, _to_int(item.get("count"), 0))

            back_items = []
            for item in old_trays:
                if not isinstance(item, dict):
                    continue
                tid = str(item.get("id", "")).strip()
                if not tid:
                    continue
                old_cnt = max(0, _to_int(item.get("count"), 0))
                keep_cnt = max(0, _to_int(new_count_by_id.get(tid), 0))
                back_cnt = max(0, old_cnt - keep_cnt)
                if back_cnt <= 0:
                    continue
                spec_text = str(item.get("spec", "") or "").strip()
                for _ in range(back_cnt):
                    back_items.append({"id": tid, "spec": spec_text})

            if back_items:
                flow = _read_flow_data()
                selected = flow.get("selected_tray_details", [])
                if not isinstance(selected, list):
                    selected = []
                used_ids = {
                    str(x.get("id", "")).strip()
                    for x in selected
                    if isinstance(x, dict) and str(x.get("id", "")).strip()
                }

                def _alloc_id(base_id: str) -> str:
                    base = str(base_id or "").strip() or "TRAY"
                    if base not in used_ids:
                        used_ids.add(base)
                        return base
                    n = 1
                    while True:
                        cand = f"{base}-R{n}"
                        if cand not in used_ids:
                            used_ids.add(cand)
                            return cand
                        n += 1

                for bi in back_items:
                    new_id = _alloc_id(bi.get("id", ""))
                    spec_text = str(bi.get("spec", "") or "").strip()
                    selected.append(
                        {
                            "id": new_id,
                            "spec": spec_text,
                            "specs": ([{"spec": spec_text, "qty": 1}] if spec_text else []),
                            "count": 1,
                            "volume": 0.1,
                        }
                    )
                flow["selected_tray_details"] = selected
                flow["selected_tray_pool"] = len(selected)
                _save_flow_data(flow)
                returned_to_pending = len(back_items)

        kiln["trays"] = normalized
        if kiln.get("status") == "empty" and normalized:
            kiln["status"] = "loading"
        if _to_int(kiln.get("unloaded_count"), 0) > total:
            kiln["unloaded_count"] = total
        kiln["unloading_total_trays"] = total
        # 中文注释：手工编辑后若为完成态且当前托数为0，自动置为空窑。
        if str(kiln.get("status", "") or "") == "completed" and total <= 0:
            kiln["status"] = "empty"
            kiln["status_changed_at"] = int(time.time())
            kiln["unloaded_count"] = 0
            kiln["unloading_total_trays"] = 0
        kilns[kiln_id] = kiln
        _save_kilns_data(kilns)
        audit_admin_action(
            "edit_kiln_trays",
            target=f"kiln_{kiln_id}",
            detail=f"total_trays={total}, rows={len(normalized)}, returned_to_pending={returned_to_pending}",
        )

        return jsonify({"success": True, "total_trays": total, "returned_to_pending": returned_to_pending})

    @app.route("/api/pending_kiln_trays", methods=["GET", "POST"])
    @login_required
    def api_pending_kiln_trays():
        if request.method == "GET":
            flow = _read_flow_data()
            trays = flow.get("selected_tray_details", [])
            if not isinstance(trays, list):
                trays = []
            normalized = []
            for item in trays:
                if not isinstance(item, dict):
                    continue
                tray_id = str(item.get("id", "")).strip()
                if not tray_id:
                    continue
                specs = item.get("specs", [])
                normalized.append(
                    {
                        "id": tray_id,
                        "content": summarize_specs(specs if isinstance(specs, list) else []),
                        "count": _to_int(item.get("count"), 1) or 1,
                    }
                )
            return jsonify({"trays": normalized})

        if not current_user.has_permission("admin"):
            return jsonify({"error": _t("no_admin_perm")}), 403

        data = request.get_json(silent=True) or {}
        trays = data.get("trays", [])
        if not isinstance(trays, list):
            return jsonify({"error": "invalid trays payload"}), 400

        normalized = []
        for item in trays:
            if not isinstance(item, dict):
                continue
            tray_id = str(item.get("id", "")).strip()
            content = str(item.get("content", "")).strip()
            if not tray_id or not content:
                continue
            try:
                groups = parse_sorted_kiln_trays(f"{tray_id} {content}")
                items = flatten_to_tray_items(groups)
            except Exception as exc:
                return jsonify({"error": f"{tray_id}: {exc}"}), 400
            if len(items) != 1:
                return jsonify({"error": f"{tray_id}: invalid tray content"}), 400
            tray = items[0]
            normalized.append(
                {
                    "id": tray.get("id", tray_id),
                    "specs": tray.get("specs", []),
                    "count": 1,
                }
            )

        flow = _read_flow_data()
        flow["selected_tray_details"] = normalized
        flow["selected_tray_pool"] = len(normalized)
        _save_flow_data(flow)
        audit_admin_action(
            "edit_pending_kiln_trays",
            target="pending_kiln_trays",
            detail=f"total_trays={len(normalized)}",
        )

        return jsonify({"success": True, "total_trays": len(normalized)})

    @app.route("/api/stage_sort_trays", methods=["POST"])
    @login_required
    def api_stage_sort_trays():
        data = request.get_json(silent=True) or {}
        trays = data.get("trays", [])
        if not isinstance(trays, list):
            return jsonify({"error": "invalid trays payload"}), 400

        normalized = []
        for item in trays:
            if not isinstance(item, dict):
                continue
            tray_id = str(item.get("id", "")).strip()
            content = str(item.get("content", "")).strip()
            if not tray_id or not content:
                continue
            try:
                groups = parse_sorted_kiln_trays(f"{tray_id} {content}")
                items = flatten_to_tray_items(groups)
            except Exception as exc:
                return jsonify({"error": f"{tray_id}: {exc}"}), 400
            if len(items) != 1:
                return jsonify({"error": f"{tray_id}: invalid tray content"}), 400
            tray = items[0]
            normalized.append(
                {
                    "id": tray.get("id", tray_id),
                    "specs": tray.get("specs", []),
                    "count": 1,
                }
            )

        flow = _read_flow_data()
        existing = flow.get("selected_tray_details", [])
        if not isinstance(existing, list):
            existing = []

        merged = {
            item.get("id"): item
            for item in existing
            if isinstance(item, dict) and item.get("id")
        }
        for item in normalized:
            merged[item["id"]] = item

        merged_list = list(merged.values())
        flow["selected_tray_details"] = merged_list
        flow["selected_tray_pool"] = len(merged_list)
        _save_flow_data(flow)

        return jsonify({"success": True, "total_trays": len(merged_list), "added": len(normalized)})
