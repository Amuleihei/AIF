# 页面与管理操作路由（从 routes.py 拆分）
from web.route_support import (
    BARK_PRICE_PER_M3_KS,
    HTML_TEMPLATE,
    LANGUAGES,
    current_user,
    datetime,
    dispatch,
    get_lang,
    get_stock_data_with_lang,
    get_system_health_snapshot,
    login_required,
    jsonify,
    redirect,
    render_template_string,
    request,
    time,
    url_for,
    _load_kilns_data,
    _read_flow_data,
    _save_flow_data,
    _save_kilns_data,
    _set_raw_log_stock,
    audit_admin_action,
    _t,
    _to_float,
    _to_int,
)
from web.templates_boss import BOSS_H5_TEMPLATE
from web.services.entry_reminder_service import get_daily_missing_entry_status


def register_operations_routes(app, logger):
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

    @app.route("/", methods=["GET"])
    @login_required
    def index():
        if str(getattr(current_user, "role", "") or "") == "boss":
            req_lang = (request.args.get("lang") or "").strip()
            target_lang = req_lang if req_lang in LANGUAGES else "zh"
            return redirect(url_for("boss_h5", lang=target_lang))
        stock_data = get_stock_data_with_lang()
        result = request.args.get("result")
        error_flag = str(request.args.get("error", "0")).strip() in ("1", "true", "True")
        return render_template_string(HTML_TEMPLATE, result=result, error=error_flag, **stock_data)

    @app.route("/boss/h5", methods=["GET"])
    @login_required
    def boss_h5():
        if str(getattr(current_user, "role", "") or "") != "boss":
            return redirect(url_for("index", lang=get_lang()))
        req_lang = (request.args.get("lang") or "").strip()
        if req_lang not in LANGUAGES:
            return redirect(url_for("boss_h5", lang="zh"))
        stock_data = get_stock_data_with_lang()
        return render_template_string(BOSS_H5_TEMPLATE, **stock_data)

    @app.route("/api/system/health", methods=["GET"])
    @login_required
    def api_system_health():
        return jsonify(get_system_health_snapshot())

    @app.route("/api/daily_missing_entry_status", methods=["GET"])
    @login_required
    def api_daily_missing_entry_status():
        return jsonify(get_daily_missing_entry_status())

    @app.route("/admin/adjust_stock", methods=["POST"])
    @login_required
    def admin_adjust_stock():
        if not current_user.has_permission("admin"):
            return _redirect_index_result(f"❌ {_t('no_admin_perm')}", error=True)

        section = (request.form.get("section") or "").strip()
        try:
            if section == "log":
                value = _to_float(request.form.get("value"), -1)
                if value < 0:
                    raise ValueError("invalid")
                _set_raw_log_stock(value)
            elif section == "saw":
                value = _to_int(request.form.get("value"), -1)
                if value < 0:
                    raise ValueError("invalid")
                flow = _read_flow_data()
                flow["saw_tray_pool"] = value
                _save_flow_data(flow)
            elif section == "byproduct":
                bark_ks = _to_float(request.form.get("bark_stock_ks"), -1)
                dust = _to_int(request.form.get("dust_bag_stock"), -1)
                waste_segment = _to_int(request.form.get("waste_segment_bag_stock"), -1)
                if bark_ks < 0 or dust < 0 or waste_segment < 0:
                    raise ValueError("invalid")
                flow = _read_flow_data()
                # 中文注释：管理员修正副产品库存时，三项库存都直接写入库存池，前后端统一读取该权威值。
                flow["bark_stock_m3"] = bark_ks / BARK_PRICE_PER_M3_KS
                flow["dust_bag_pool"] = dust
                flow["waste_segment_bag_pool"] = waste_segment
                _save_flow_data(flow)
            elif section == "dip":
                value = _to_int(request.form.get("value"), -1)
                if value < 0:
                    raise ValueError("invalid")
                flow = _read_flow_data()
                flow["dip_tray_pool"] = value
                _save_flow_data(flow)
            elif section == "dip_chem":
                value = _to_float(request.form.get("value"), -1)
                if value < 0:
                    raise ValueError("invalid")
                flow = _read_flow_data()
                flow["dip_chem_bag_pool"] = value
                _save_flow_data(flow)
            elif section == "sort":
                value = _to_int(request.form.get("value"), -1)
                if value < 0:
                    raise ValueError("invalid")
                flow = _read_flow_data()
                flow["selected_tray_pool"] = value
                # 兼容：若存在托级明细，库存读取会以明细数量为准；管理员强制改库存时同步明细长度。
                if isinstance(flow.get("selected_tray_details"), list):
                    flow["selected_tray_details"] = [{"id": None, "spec": "?"} for _ in range(value)]
                _save_flow_data(flow)
            elif section == "kiln_done":
                value = _to_int(request.form.get("value"), -1)
                if value < 0:
                    raise ValueError("invalid")
                flow = _read_flow_data()
                flow["kiln_done_tray_pool"] = value
                # 兼容：若存在托级明细，库存读取会以明细数量为准；管理员强制改库存时同步明细长度。
                if isinstance(flow.get("kiln_done_trays"), list):
                    flow["kiln_done_trays"] = [{"id": None, "spec": "?"} for _ in range(value)]
                _save_flow_data(flow)
            else:
                return _redirect_index_result(f"❌ {_t('adjust_invalid_section')}", error=True)
        except Exception:
            return _redirect_index_result(f"❌ {_t('adjust_invalid_value')}", error=True)

        audit_admin_action(
            "adjust_stock",
            target=section,
            detail=str(dict(request.form) or ""),
        )
        return _redirect_index_result(f"✅ {_t('adjust_saved')}", error=False)

    @app.route("/admin/adjust_kiln", methods=["POST"])
    @login_required
    def admin_adjust_kiln():
        if not current_user.has_permission("admin"):
            return _redirect_index_result(f"❌ {_t('no_admin_perm')}", error=True)

        kiln_id = (request.form.get("kiln_id") or "").strip().upper()
        status = (request.form.get("status") or "").strip()
        if kiln_id not in ["A", "B", "C", "D"]:
            return _redirect_index_result("❌ invalid kiln id", error=True)

        valid_status = {"empty", "loading", "drying", "unloading", "ready", "completed"}
        if status not in valid_status:
            return _redirect_index_result("❌ invalid kiln status", error=True)

        elapsed_hours = _to_int(request.form.get("elapsed_hours"), -1)
        remaining_hours = _to_int(request.form.get("remaining_hours"), -1)
        total_trays = _to_int(request.form.get("total_trays"), -1)
        remaining_trays = _to_int(request.form.get("remaining_trays"), -1)

        if elapsed_hours < -1 or remaining_hours < -1 or total_trays < -1 or remaining_trays < -1:
            return _redirect_index_result(f"❌ {_t('adjust_invalid_value')}", error=True)

        kilns = _load_kilns_data()
        kiln = kilns.get(kiln_id, {})
        old_status = str(kiln.get("status", "empty") or "empty")
        kiln["status"] = status
        kiln.pop("manual_elapsed_hours", None)
        kiln.pop("manual_remaining_hours", None)

        if status == "drying":
            now_ts = int(time.time())
            elapsed_calc_hours = elapsed_hours
            remaining_calc_hours = remaining_hours
            if elapsed_calc_hours < 0 and remaining_calc_hours >= 0:
                elapsed_calc_hours = max(0, 120 - remaining_calc_hours)
            if elapsed_calc_hours < 0:
                elapsed_calc_hours = 0
            start_ts = max(0, now_ts - elapsed_calc_hours * 3600)
            kiln["dry_start"] = start_ts
            kiln["start"] = datetime.fromtimestamp(start_ts).isoformat()
        elif status in {"empty", "loading", "completed"}:
            kiln["dry_start"] = None
            kiln["start"] = None
            if status == "empty":
                kiln["trays"] = []
                kiln["unloaded_count"] = 0
                kiln["unloading_total_trays"] = 0

        if total_trays >= 0:
            kiln["unloading_total_trays"] = total_trays
            if remaining_trays >= 0:
                remaining_trays = min(remaining_trays, total_trays)
                kiln["unloaded_count"] = max(0, total_trays - remaining_trays)
        elif status == "unloading":
            tray_list = kiln.get("trays", [])
            auto_total = sum(_to_int(item.get("count"), 0) for item in tray_list) if isinstance(tray_list, list) else 0
            if auto_total > 0:
                kiln["unloading_total_trays"] = auto_total
                if remaining_trays >= 0:
                    remaining_trays = min(remaining_trays, auto_total)
                    kiln["unloaded_count"] = max(0, auto_total - remaining_trays)

        kilns[kiln_id] = kiln
        _save_kilns_data(kilns)

        lang_pack = LANGUAGES.get(get_lang(), LANGUAGES["zh"])
        old_status_label = lang_pack.get(old_status, old_status)
        new_status_label = lang_pack.get(status, status)

        logger.info("admin_adjust_kiln user=%s kiln=%s %s->%s", current_user.username, kiln_id, old_status, status)
        audit_admin_action(
            "adjust_kiln",
            target=kiln_id,
            detail=f"{old_status}->{status}, total={total_trays}, remaining={remaining_trays}",
        )
        return _redirect_index_result(
            f"✅ {_t('kiln_adjust_saved')}（{kiln_id}: {old_status_label} → {new_status_label}）",
            error=False,
        )

    @app.route("/command", methods=["POST"])
    @login_required
    def handle_command():
        command = request.form.get("command", "").strip()
        if not command:
            return _redirect_index_result(_t("enter_command"), error=True)
        try:
            result = dispatch(command) or _t("unknown_cmd")
            return _redirect_index_result(result, error=False)
        except Exception as e:
            return _redirect_index_result(f"❌ {_t('sys_error')}: {str(e)}", error=True)
