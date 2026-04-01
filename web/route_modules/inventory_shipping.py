# 库存、发货与导出相关路由（从 routes.py 拆分）
from web.route_support import (
    BASE,
    Workbook,
    BytesIO,
    ProductBatch,
    Session,
    current_user,
    datetime,
    delete_inventory_product,
    flash,
    get_inventory_products_by_ids,
    get_shipping_data,
    get_stock_data_with_lang,
    jsonify,
    login_required,
    pd,
    redirect,
    request,
    save_shipping_data,
    send_file,
    update_inventory_product_status,
    upsert_inventory_product,
    url_for,
    _build_label_sheet,
    _build_label_workbook_from_template,
    _collect_finished_product_rows,
    _filter_finished_product_rows,
    _infer_spec_and_volume,
    _load_kilns_data,
    _next_shipment_no,
    _parse_spec_dwl,
    _resolve_logo_path,
    _split_product_id,
    _summarize_shipping_orders,
    audit_admin_action,
    _t,
    _to_float,
    _to_int,
)


def register_inventory_shipping_routes(app):
    @app.route("/export/<data_type>")
    @login_required
    def export_data(data_type):
        if not current_user.has_permission("export"):
            flash(_t("no_export_perm"), "error")
            return redirect(url_for("index"))

        if data_type == "kiln_trays":
            session = Session()
            data = []
            kilns = _load_kilns_data()
            for kiln_id, kiln_data in kilns.items():
                if kiln_data.get("status") in ["loading", "drying", "ready"]:
                    trays = kiln_data.get("trays", [])
                    for tray in trays:
                        data.append(
                            {
                                "窑": kiln_id,
                                "批次号": tray.get("batch_number", ""),
                                "产品规格": tray.get("spec", ""),
                                "数量": tray.get("count", 0),
                                "体积": tray.get("volume", 0),
                                "状态": kiln_data.get("status", ""),
                            }
                        )
            session.close()

        elif data_type == "finished_products":
            session = Session()
            data = []
            product_batches = session.query(ProductBatch).filter_by(status="active").all()
            for batch in product_batches:
                data.append(
                    {
                        "批次号": batch.batch_number,
                        "成品数量": batch.product_count,
                        "总体积": batch.total_volume,
                        "创建时间": batch.created_at,
                        "创建者": batch.created_by,
                    }
                )
            session.close()

        elif data_type == "inventory":
            stock_data = get_stock_data_with_lang()
            data = [
                {
                    "锯解库存": stock_data.get("saw_stock", 0),
                    "药浸库存": stock_data.get("dip_stock", 0),
                    "拣选库存": stock_data.get("sorting_stock", 0),
                    "窑完成库存": stock_data.get("kiln_done_stock", 0),
                    "木渣库存(袋)": stock_data.get("dust_bag_stock", 0),
                    "树皮库存(立方)": stock_data.get("bark_stock_m3", 0.0),
                }
            ]
        else:
            return redirect(url_for("index"))

        df = pd.DataFrame(data)
        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name="Data", index=False)
        output.seek(0)

        filename = f"{data_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        return send_file(
            output,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=True,
            download_name=filename,
        )

    @app.route("/export/finished_products_full")
    @login_required
    def export_finished_products_full():
        if not current_user.has_permission("export"):
            flash(_t("no_export_perm"), "error")
            return redirect(url_for("index"))

        rows = _collect_finished_product_rows()
        df = pd.DataFrame(
            [
                {
                    "编号": r["编号"],
                    "D": r["D"],
                    "W": r["W"],
                    "L": r["L"],
                    "数量": r["数量"],
                    "m³": r["m³"],
                    "等级": r["等级"],
                    "重量(kg)": r["重量(kg)"],
                }
                for r in rows
            ]
        )
        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name="FinishedProducts", index=False)
        output.seek(0)
        filename = f"finished_products_full_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        return send_file(
            output,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=True,
            download_name=filename,
        )

    @app.route("/api/finished_inventory")
    @login_required
    def api_finished_inventory():
        rows = _filter_finished_product_rows(
            grade=request.args.get("grade", ""),
            d=request.args.get("d", ""),
            w=request.args.get("w", ""),
            l=request.args.get("l", ""),
            pcs=request.args.get("pcs", ""),
            m3=request.args.get("m3", ""),
        )
        return jsonify({"rows": rows})

    @app.route("/api/shipping_orders")
    @login_required
    def api_shipping_orders():
        return jsonify(_summarize_shipping_orders())

    @app.route("/api/shipping_orders", methods=["POST"])
    @login_required
    def api_create_shipping_order():
        payload = request.get_json(silent=True) or {}
        customer = str(payload.get("customer", "") or "").strip()
        destination = str(payload.get("destination", "") or "").strip()
        vehicle_no = str(payload.get("vehicle_no", "") or "").strip()
        driver_name = str(payload.get("driver_name", "") or "").strip()
        remark = str(payload.get("remark", "") or "").strip()
        departure_at = str(payload.get("departure_at", "") or "").strip()
        eta_hours_to_yangon = _to_int(payload.get("eta_hours_to_yangon"), 36)
        product_ids = [str(pid).strip() for pid in (payload.get("product_ids") or []) if str(pid).strip()]

        if not customer or not product_ids:
            return jsonify({"error": _t("fill_required")}), 400

        rows = get_inventory_products_by_ids(product_ids)
        if len(rows) != len(product_ids):
            return jsonify({"error": "products not found"}), 400

        unavailable = [r["product_id"] for r in rows if str(r.get("status", "")) != "库存"]
        if unavailable:
            return jsonify({"error": f"products unavailable: {', '.join(unavailable)}"}), 400

        shipping_data = get_shipping_data()
        shipment_no = _next_shipment_no(shipping_data)
        now = datetime.now().isoformat()
        if not departure_at:
            departure_at = now
        initial_status = "去仰光途中"
        try:
            if datetime.fromisoformat(departure_at) > datetime.now():
                initial_status = "待发车"
        except Exception:
            pass
        products = []
        for row in rows:
            products.append(
                {
                    "product_id": row["product_id"],
                    "spec": row["spec"],
                    "grade": row["grade"],
                    "pcs": row["pcs"],
                    "volume": row["volume"],
                }
            )
        shipping_data["shipments"].append(
            {
                "shipment_no": shipment_no,
                "customer": customer,
                "destination": destination or "仰光仓",
                "tracking_no": "",
                "vehicle_no": vehicle_no,
                "driver_name": driver_name,
                "remark": remark,
                "departure_at": departure_at,
                "eta_hours_to_yangon": max(1, eta_hours_to_yangon),
                "yangon_arrived_at": "",
                "yangon_departed_at": "",
                "china_port_arrived_at": "",
                "status": initial_status,
                "products": products,
                "created_at": now,
                "updated_at": now,
                "created_by": current_user.username,
            }
        )
        save_shipping_data(shipping_data)
        update_inventory_product_status(product_ids, initial_status)
        audit_admin_action(
            "create_shipping_order",
            target=shipment_no,
            detail=f"status={initial_status},products={len(product_ids)},customer={customer}",
        )
        return jsonify({"success": True, "shipment_no": shipment_no})

    @app.route("/api/shipping_orders/<shipment_no>", methods=["PATCH"])
    @login_required
    def api_update_shipping_order(shipment_no):
        payload = request.get_json(silent=True) or {}
        new_status = str(payload.get("status", "") or "").strip()
        if new_status not in {"待发车", "去仰光途中", "仰光仓已到", "已从仰光出港", "中国港口已到", "异常"}:
            return jsonify({"error": "invalid status"}), 400

        shipping_data = get_shipping_data()
        shipments = shipping_data.get("shipments", []) if isinstance(shipping_data.get("shipments"), list) else []
        target = None
        for item in shipments:
            if isinstance(item, dict) and str(item.get("shipment_no", "")) == str(shipment_no):
                target = item
                break
        if not target:
            return jsonify({"error": "not found"}), 404

        target["status"] = new_status
        target["updated_at"] = datetime.now().isoformat()
        if new_status == "仰光仓已到" and not target.get("yangon_arrived_at"):
            target["yangon_arrived_at"] = target["updated_at"]
        if new_status == "已从仰光出港" and not target.get("yangon_departed_at"):
            target["yangon_departed_at"] = target["updated_at"]
        if new_status == "中国港口已到" and not target.get("china_port_arrived_at"):
            target["china_port_arrived_at"] = target["updated_at"]
        save_shipping_data(shipping_data)

        product_ids = [str(p.get("product_id", "")).strip() for p in target.get("products", []) if isinstance(p, dict)]
        if new_status == "待发车":
            update_inventory_product_status(product_ids, "待发车")
        elif new_status == "去仰光途中":
            update_inventory_product_status(product_ids, "去仰光途中")
        elif new_status == "仰光仓已到":
            update_inventory_product_status(product_ids, "仰光仓已到")
        elif new_status == "已从仰光出港":
            update_inventory_product_status(product_ids, "已从仰光出港")
        elif new_status == "中国港口已到":
            update_inventory_product_status(product_ids, "中国港口已到")
        elif new_status == "异常":
            update_inventory_product_status(product_ids, "物流异常")
        audit_admin_action(
            "update_shipping_status",
            target=shipment_no,
            detail=f"status={new_status},products={len(product_ids)}",
        )
        return jsonify({"success": True})

    @app.route("/export/finished_products_current")
    @login_required
    def export_finished_products_current():
        if not current_user.has_permission("export"):
            flash(_t("no_export_perm"), "error")
            return redirect(url_for("index"))

        rows = _filter_finished_product_rows(
            grade=request.args.get("grade", ""),
            d=request.args.get("d", ""),
            w=request.args.get("w", ""),
            l=request.args.get("l", ""),
            pcs=request.args.get("pcs", ""),
            m3=request.args.get("m3", ""),
        )
        df = pd.DataFrame(
            [
                {
                    "编号": r["编号"],
                    "D": r["D"],
                    "W": r["W"],
                    "L": r["L"],
                    "数量": r["数量"],
                    "m³": r["m³"],
                    "重量(kg)": r["重量(kg)"],
                    "等级": r["等级"],
                    "状态": "库存",
                    "规格": r["规格"],
                }
                for r in rows
            ]
        )
        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name="FinishedInventory", index=False)
        output.seek(0)
        filename = f"finished_inventory_filtered_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        return send_file(
            output,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=True,
            download_name=filename,
        )

    @app.route("/export/shipping_selected_details", methods=["POST"])
    @login_required
    def export_shipping_selected_details():
        if not current_user.has_permission("export"):
            return jsonify({"error": _t("no_export_perm")}), 403

        payload = request.get_json(silent=True) or {}
        product_ids = [str(pid).strip() for pid in (payload.get("product_ids") or []) if str(pid).strip()]
        if not product_ids:
            return jsonify({"error": "no products selected"}), 400

        rows = get_inventory_products_by_ids(product_ids)
        row_map = {str(row.get("product_id", "") or ""): row for row in rows if isinstance(row, dict)}
        missing = [pid for pid in product_ids if pid not in row_map]
        if missing:
            return jsonify({"error": f"products not found: {', '.join(missing)}"}), 400

        data = []
        for pid in product_ids:
            row = row_map[pid]
            spec = str(row.get("spec", "") or "")
            d_val, w_val, l_val = _parse_spec_dwl(spec)
            code_no, grade = _split_product_id(pid, row)
            data.append(
                {
                    "编号": code_no,
                    "D": d_val,
                    "W": w_val,
                    "L": l_val,
                    "数量": int(_to_int(row.get("pcs"), 0)),
                    "m³": f"{float(_to_float(row.get('volume'), 0.0)):.4f}",
                    "等级": grade or str(row.get("grade", "") or "").strip().upper(),
                }
            )

        df = pd.DataFrame(data, columns=["编号", "D", "W", "L", "数量", "m³", "等级"])
        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name="ShipmentDetails", index=False)
        output.seek(0)
        filename = f"shipment_selected_details_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        return send_file(
            output,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=True,
            download_name=filename,
        )

    @app.route("/api/finished_inventory/<product_id>", methods=["DELETE"])
    @login_required
    def api_delete_finished_inventory(product_id):
        if not current_user.has_permission("admin"):
            return jsonify({"error": _t("no_admin_perm")}), 403
        ok = delete_inventory_product(product_id)
        if not ok:
            return jsonify({"error": "not found"}), 404
        return jsonify({"success": True})

    @app.route("/api/finished_inventory/<product_id>", methods=["PATCH"])
    @login_required
    def api_update_finished_inventory(product_id):
        if not current_user.has_permission("admin"):
            return jsonify({"error": _t("no_admin_perm")}), 403

        payload = request.get_json(silent=True) or {}
        spec = str(payload.get("spec", "") or "").strip()
        grade = str(payload.get("grade", "") or "").strip().upper()
        pcs = _to_int(payload.get("pcs"), 0)
        weight_kg = _to_float(payload.get("weight_kg"), 0.0)

        if not product_id or not spec or pcs <= 0:
            return jsonify({"error": _t("invalid_product_entry_msg")}), 400
        if weight_kg < 0:
            return jsonify({"error": _t("invalid_product_entry_msg")}), 400
        if not grade:
            grade = "AB"

        rows = get_inventory_products_by_ids([product_id])
        if not rows:
            return jsonify({"error": "not found"}), 404
        row = rows[0]
        if str(row.get("status", "") or "") != "库存":
            return jsonify({"error": "product unavailable"}), 400

        final_spec, final_volume = _infer_spec_and_volume(product_id, pcs, spec)
        upsert_inventory_product(
            product_id=product_id,
            spec=final_spec,
            grade=grade,
            pcs=pcs,
            volume=final_volume,
            status="库存",
            weight_kg=weight_kg,
        )
        d_val, w_val, l_val = _parse_spec_dwl(final_spec)
        code_no, grade_from_id = _split_product_id(product_id, {"grade": grade})

        return jsonify(
            {
                "success": True,
                "row": {
                    "product_id": product_id,
                    "编号": code_no,
                    "D": d_val,
                    "W": w_val,
                    "L": l_val,
                    "数量": pcs,
                    "m³": round(float(final_volume or 0.0), 4),
                    "重量(kg)": round(float(weight_kg or 0.0), 2),
                    "等级": grade_from_id or grade,
                    "规格": final_spec,
                    "状态": "库存",
                },
            }
        )

    @app.route("/export/finished_labels")
    @login_required
    def export_finished_labels():
        if not current_user.has_permission("export"):
            flash(_t("no_export_perm"), "error")
            return redirect(url_for("index"))

        rows = _collect_finished_product_rows()
        template_path = BASE / "biaoqian.xlsx"
        logo_path = _resolve_logo_path()
        if template_path.exists():
            wb = _build_label_workbook_from_template(template_path, rows, logo_path)
        else:
            wb = Workbook()
            _build_label_sheet(wb, rows, logo_path)

        output = BytesIO()
        wb.save(output)
        output.seek(0)
        filename = f"finished_labels_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        return send_file(
            output,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=True,
            download_name=filename,
        )
