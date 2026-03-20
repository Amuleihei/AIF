from web.route_support import (
    BytesIO,
    current_user,
    datetime,
    flash,
    jsonify,
    login_required,
    pd,
    redirect,
    render_template_string,
    request,
    send_file,
    url_for,
)
from web.templates_report import DAILY_REPORT_TEMPLATE, BOSS_DAILY_REPORT_TEMPLATE
from web.utils import get_lang
from web.services.daily_report_service import build_daily_report
from web.services.period_report_service import get_report, rebuild_period_report
from web.i18n import LANGUAGES


def _period_texts(lang: str) -> dict:
    if lang == "en":
        return {
            "weekly_title": "Weekly Report",
            "monthly_title": "Monthly Report",
            "range": "Range",
            "generated_at": "Generated At",
            "summary": "Core Summary",
            "snapshot": "Current Inventory Snapshot",
            "counts": "Record Counts",
            "summary_labels": {
                "log_in_mt": "Log In (MT)",
                "saw_log_consumed_mt": "Saw Consumed Logs (MT)",
                "saw_output_trays": "Saw Output Trays",
                "dip_cans": "Dip Runs",
                "dip_trays": "Dip Trays",
                "sort_trays": "Sort Trays",
                "kiln_load_trays": "Kiln Load Trays",
                "secondary_trays": "Secondary Trays",
                "finished_pcs": "Finished PCS",
                "finished_m3": "Finished Volume (m3)",
                "bark_sale_ks": "Bark Sales (Ks)",
            },
            "snapshot_labels": {
                "log_stock_mt": "Log Stock (MT)",
                "saw_stock_tray": "Saw Stock (tray)",
                "dip_stock_tray": "Dip Stock (tray)",
                "sorting_stock_tray": "Pending Kiln Stock (tray)",
                "kiln_done_stock_tray": "Kiln Done Stock (tray)",
                "finished_product_count": "Finished Product Count",
                "finished_product_m3": "Finished Product Volume (m3)",
            },
            "count_labels": {
                "log_entries": "Log Entries",
                "saw_records": "Saw Records",
                "dip_records": "Dip Records",
                "sort_records": "Sort Records",
                "tray_batches": "Tray Batches",
                "product_batches": "Product Batches",
                "byproduct_records": "Byproduct Records",
                "second_sort_records": "Second Sort Records",
            },
        }
    if lang == "my":
        return {
            "weekly_title": "အပတ်စဉ်အစီရင်ခံစာ",
            "monthly_title": "လစဉ်အစီရင်ခံစာ",
            "range": "ကာလ",
            "generated_at": "ထုတ်ပေးချိန်",
            "summary": "အဓိကအကျဉ်းချုပ်",
            "snapshot": "လက်ရှိစတော့ Snapshot",
            "counts": "မှတ်တမ်းအရေအတွက်",
            "summary_labels": {
                "log_in_mt": "ထင်းဝင် (MT)",
                "saw_log_consumed_mt": "ခုတ်သုံး ထင်း (MT)",
                "saw_output_trays": "ခုတ်ထွက် ထပ်ခါး",
                "dip_cans": "ဆေးစိမ် ကြိမ်ရေ",
                "dip_trays": "ဆေးစိမ် ထပ်ခါး",
                "sort_trays": "ရွေးချယ် ထပ်ခါး",
                "kiln_load_trays": "မီးဖိုဝင် ထပ်ခါး",
                "secondary_trays": "ဒုတိယရွေး ထပ်ခါး",
                "finished_pcs": "ကုန်ချော အရေအတွက်",
                "finished_m3": "ကုန်ချော ပမာဏ (m3)",
                "bark_sale_ks": "ပေါက်ဖတ် ရောင်းရငွေ (Ks)",
            },
            "snapshot_labels": {
                "log_stock_mt": "ထင်းစတော့ (MT)",
                "saw_stock_tray": "ခုတ်စတော့ (ထပ်ခါး)",
                "dip_stock_tray": "ဆေးစိမ်စတော့ (ထပ်ခါး)",
                "sorting_stock_tray": "မီးဖိုဝင်ရန်စတော့ (ထပ်ခါး)",
                "kiln_done_stock_tray": "မီးဖိုပြီးစတော့ (ထပ်ခါး)",
                "finished_product_count": "ကုန်ချောစုစုပေါင်း",
                "finished_product_m3": "ကုန်ချောပမာဏ (m3)",
            },
            "count_labels": {
                "log_entries": "ထင်းဝင်စာရင်း",
                "saw_records": "ခုတ်မှတ်တမ်း",
                "dip_records": "ဆေးစိမ်မှတ်တမ်း",
                "sort_records": "ရွေးချယ်မှတ်တမ်း",
                "tray_batches": "ထပ်ခါး batch",
                "product_batches": "ကုန်ချော batch",
                "byproduct_records": "ဘေးထွက်မှတ်တမ်း",
                "second_sort_records": "ဒုတိယရွေးမှတ်တမ်း",
            },
        }
    return {
        "weekly_title": "周报",
        "monthly_title": "月报",
        "range": "统计区间",
        "generated_at": "生成时间",
        "summary": "核心汇总",
        "snapshot": "当前库存快照",
        "counts": "记录计数",
        "summary_labels": {
            "log_in_mt": "原木入库 (MT)",
            "saw_log_consumed_mt": "锯解消耗原木 (MT)",
            "saw_output_trays": "锯解产出锯托",
            "dip_cans": "药浸罐次",
            "dip_trays": "药浸托数",
            "sort_trays": "拣选托数",
            "kiln_load_trays": "入窑托数",
            "secondary_trays": "二选托数",
            "finished_pcs": "成品件数",
            "finished_m3": "成品体积 (m3)",
            "bark_sale_ks": "树皮销售 (Ks)",
        },
        "snapshot_labels": {
            "log_stock_mt": "原木库存 (MT)",
            "saw_stock_tray": "锯解库存 (托)",
            "dip_stock_tray": "药浸库存 (托)",
            "sorting_stock_tray": "待入窑库存 (托)",
            "kiln_done_stock_tray": "窑完成库存 (托)",
            "finished_product_count": "成品总件数",
            "finished_product_m3": "成品总体积 (m3)",
        },
        "count_labels": {
            "log_entries": "原木入库记录",
            "saw_records": "锯解记录",
            "dip_records": "药浸记录",
            "sort_records": "拣选记录",
            "tray_batches": "窑托批次",
            "product_batches": "成品批次",
            "byproduct_records": "副产品记录",
            "second_sort_records": "二选记录",
        },
    }


PERIOD_REPORT_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }}</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 12px; background: #f5f5f5; }
        .container { max-width: 980px; margin: 0 auto; background: #fff; padding: 14px; border-radius: 8px; box-shadow: 0 1px 8px rgba(0,0,0,0.08); }
        .toolbar { display:flex; gap:8px; align-items:center; flex-wrap:wrap; margin-bottom:8px; }
        .btn { padding: 7px 10px; border: none; border-radius: 6px; background: #0d6efd; color: #fff; text-decoration:none; }
        .btn.gray { background: #6c757d; }
        h1 { margin: 4px 0 6px; font-size: 22px; }
        .muted { color:#6b7280; font-size: 12px; }
        table { width:100%; border-collapse: collapse; margin-top: 8px; background: #fff; }
        th, td { border: 1px solid #e5e7eb; padding: 6px 8px; text-align: left; font-size: 13px; }
        th { background: #f3f4f6; width: 300px; }
        table tbody tr:nth-child(odd) th, table tbody tr:nth-child(odd) td { background:#ffffff; }
        table tbody tr:nth-child(even) th, table tbody tr:nth-child(even) td { background:#edf2f7; }
    </style>
    <script>
        function changeLanguage(lang) {
            const url = new URL(window.location);
            url.searchParams.set('lang', lang);
            window.location.href = url.toString();
        }
    </script>
</head>
<body>
    <div class="container">
        <div class="toolbar">
            <label for="lang-select">{{ texts.language }}:</label>
            <select id="lang-select" onchange="changeLanguage(this.value)">
                <option value="zh" {% if lang == 'zh' %}selected{% endif %}>{{ texts.chinese }}</option>
                <option value="en" {% if lang == 'en' %}selected{% endif %}>{{ texts.english }}</option>
                <option value="my" {% if lang == 'my' %}selected{% endif %}>{{ texts.burmese }}</option>
            </select>
            <a href="{{ back_url }}" class="btn gray">{{ texts.back_home }}</a>
        </div>
        <h1>{{ title }} {{ report.key }}</h1>
        <p class="muted">{{ rpt_texts.range }}: {{ report.range.start }} ~ {{ report.range.end }}</p>
        <p class="muted">{{ rpt_texts.generated_at }}: {{ report.generated_at }}</p>

        <h3>{{ rpt_texts.summary }}</h3>
        <table><tbody>
            {% for k, v in report.summary.items() %}
            <tr><th>{{ rpt_texts.summary_labels.get(k, k) }}</th><td>{{ v }}</td></tr>
            {% endfor %}
        </tbody></table>

        <h3>{{ rpt_texts.snapshot }}</h3>
        <table><tbody>
            {% for k, v in report.inventory_snapshot.items() %}
            <tr><th>{{ rpt_texts.snapshot_labels.get(k, k) }}</th><td>{{ v }}</td></tr>
            {% endfor %}
        </tbody></table>

        <h3>{{ rpt_texts.counts }}</h3>
        <table><tbody>
            {% for k, v in report.counts.items() %}
            <tr><th>{{ rpt_texts.count_labels.get(k, k) }}</th><td>{{ v }}</td></tr>
            {% endfor %}
        </tbody></table>
    </div>
</body>
</html>
"""


def _can_view_report() -> bool:
    return bool(
        current_user.has_permission("view")
        or current_user.has_permission("export")
        or current_user.has_permission("admin")
    )


def register_reporting_routes(app):
    @app.route("/api/report/daily")
    @login_required
    def api_daily_report():
        if not _can_view_report():
            return jsonify({"error": "no permission"}), 403
        day = request.args.get("date", "")
        lang = get_lang()
        return jsonify(build_daily_report(day, lang=lang))

    @app.route("/report/daily")
    @login_required
    def report_daily_page():
        if not _can_view_report():
            flash("没有权限查看日报", "error")
            return redirect(url_for("index", lang=get_lang()))

        day = request.args.get("date", "")
        lang = get_lang()
        report = build_daily_report(day, lang=lang)
        texts = LANGUAGES.get(lang, LANGUAGES["zh"])
        tpl = BOSS_DAILY_REPORT_TEMPLATE if str(getattr(current_user, "role", "") or "") == "boss" else DAILY_REPORT_TEMPLATE
        return render_template_string(
            tpl,
            report=report,
            lang=lang,
            texts=texts,
        )

    @app.route("/export/report/daily")
    @login_required
    def export_daily_report():
        if not current_user.has_permission("export"):
            flash("没有导出权限", "error")
            return redirect(url_for("report_daily_page", date=request.args.get("date", ""), lang=get_lang()))

        day = request.args.get("date", "")
        lang = get_lang()
        report = build_daily_report(day, lang=lang)

        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            pd.DataFrame([report["summary"]]).to_excel(writer, sheet_name="summary", index=False)
            pd.DataFrame([report["inventory_snapshot"]]).to_excel(writer, sheet_name="inventory_snapshot", index=False)
            if report.get("show_yield_loss"):
                pd.DataFrame([report.get("yield_loss", {})]).to_excel(writer, sheet_name="yield_loss", index=False)
            pd.DataFrame([report.get("kiln_status", {})]).to_excel(writer, sheet_name="kiln_status", index=False)
            for sheet_name, rows in report.get("breakdown", {}).items():
                if not isinstance(rows, list):
                    continue
                df = pd.DataFrame(rows)
                if df.empty:
                    df = pd.DataFrame([{"info": "no data"}])
                df.to_excel(writer, sheet_name=sheet_name[:31], index=False)

        output.seek(0)
        filename = f"daily_report_{report['date']}_{datetime.now().strftime('%H%M%S')}.xlsx"
        return send_file(
            output,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=True,
            download_name=filename,
        )

    @app.route("/report/weekly")
    @login_required
    def report_weekly_page():
        if not _can_view_report():
            flash("没有权限查看周报", "error")
            return redirect(url_for("index", lang=get_lang()))
        lang = get_lang()
        key = (request.args.get("key") or "").strip()
        if key:
            try:
                rebuild_period_report("weekly", key)
            except Exception:
                pass
        report = get_report("weekly", key=key or None)
        if not report:
            flash("暂无周报数据", "error")
            return redirect(url_for("index", lang=lang))
        back_url = url_for("boss_h5", lang=lang) if str(getattr(current_user, "role", "") or "") == "boss" else url_for("index", lang=lang)
        rpt_texts = _period_texts(lang)
        return render_template_string(
            PERIOD_REPORT_TEMPLATE,
            title=rpt_texts["weekly_title"],
            report=report,
            back_url=back_url,
            lang=lang,
            texts=LANGUAGES.get(lang, LANGUAGES["zh"]),
            rpt_texts=rpt_texts,
        )

    @app.route("/report/monthly")
    @login_required
    def report_monthly_page():
        if not _can_view_report():
            flash("没有权限查看月报", "error")
            return redirect(url_for("index", lang=get_lang()))
        lang = get_lang()
        key = (request.args.get("key") or "").strip()
        if key:
            try:
                rebuild_period_report("monthly", key)
            except Exception:
                pass
        report = get_report("monthly", key=key or None)
        if not report:
            flash("暂无月报数据", "error")
            return redirect(url_for("index", lang=lang))
        back_url = url_for("boss_h5", lang=lang) if str(getattr(current_user, "role", "") or "") == "boss" else url_for("index", lang=lang)
        rpt_texts = _period_texts(lang)
        return render_template_string(
            PERIOD_REPORT_TEMPLATE,
            title=rpt_texts["monthly_title"],
            report=report,
            back_url=back_url,
            lang=lang,
            texts=LANGUAGES.get(lang, LANGUAGES["zh"]),
            rpt_texts=rpt_texts,
        )
