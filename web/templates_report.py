# 日报页面模板
DAILY_REPORT_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ texts.daily_report_title }}</title>
    <link rel="icon" type="image/png" href="{{ url_for('static', filename='AIF_logo.png') }}">
    <style>
        body { font-family: Arial, sans-serif; margin: 12px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; background: #fff; padding: 14px; border-radius: 8px; box-shadow: 0 1px 8px rgba(0,0,0,0.08); }
        h1 { margin: 6px 0; font-size: 22px; }
        h3 { margin: 12px 0 6px; font-size: 16px; }
        .toolbar { display:flex; gap:8px; align-items:center; margin-bottom:10px; flex-wrap:wrap; }
        input[type="date"] { padding:6px; }
        button, .btn { padding: 7px 10px; border: none; border-radius: 6px; background: #0d6efd; color: #fff; text-decoration:none; cursor:pointer; font-size: 13px; }
        .btn.gray { background: #6c757d; }
        table { width:100%; border-collapse: collapse; margin-top: 8px; background: #fff; table-layout: fixed; }
        th, td { border: 1px solid #e5e7eb; padding: 6px 8px; text-align: left; font-size: 13px; }
        th { background: #f3f4f6; width: 40%; white-space: nowrap; }
        td { width: 60%; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .muted { color:#6b7280; font-size: 12px; }
        .once-warn { margin: 10px 0; padding: 10px 12px; border: 2px solid #b91c1c; border-radius: 8px; background: #fef2f2; color: #7f1d1d; font-weight: 700; }
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
            {% if not one_time_access %}
            <a href="{{ url_for('index', lang=lang) }}" class="btn gray">{{ texts.back_home }}</a>
            <form method="GET" action="{{ url_for('report_daily_page') }}" style="display:flex; gap:8px; align-items:center;">
                <label>{{ texts.report_date_label }}</label>
                <input type="date" name="date" value="{{ report.date }}">
                <input type="hidden" name="lang" value="{{ lang }}">
                <button type="submit">{{ texts.query_btn }}</button>
            </form>
            <a class="btn" href="{{ url_for('export_daily_report', date=report.date, lang=lang) }}">{{ texts.export_daily_report }}</a>
            {% endif %}
        </div>
        {% if one_time_access %}
        <div class="once-warn">{{ texts.one_time_daily_link_warning }}</div>
        {% endif %}

        <h1>{{ texts.daily_report_title }} - {{ report.date }}</h1>
        <p class="muted">{{ texts.report_range }}: {{ report.range.start }} ~ {{ report.range.end }}</p>
        <p class="muted">{{ report.meta.note }}</p>

        {% if report.ai_deep_monitor and report.ai_deep_monitor.summary %}
        <h3>{{ texts.get('intelligence_panel_title', 'AI建议') }}</h3>
        <p class="muted">{{ report.ai_deep_monitor.generated_at }} · {{ report.ai_deep_monitor.trigger }} · {{ texts.get('ai_template_version_label', 'Template') }} {{ report.ai_deep_monitor.template_version or 'deep_monitor_v2' }}</p>
        <table>
            <tbody>
                <tr><th>{{ texts.get('report_intelligence_brief_label', 'AI Brief') }}</th><td>{{ report.ai_deep_monitor.summary }}</td></tr>
                <tr><th>{{ texts.get('ai_quick_today_focus', 'Today Focus') }}</th><td>{{ report.ai_deep_monitor.focus[0] if report.ai_deep_monitor.focus else '-' }}</td></tr>
                <tr><th>{{ texts.get('risk_alerts_title', 'Risk Alerts') }}</th><td>{{ report.ai_deep_monitor.risks[0] if report.ai_deep_monitor.risks else '-' }}</td></tr>
            </tbody>
        </table>
        {% endif %}

        {% if report.factory_intelligence %}
        <h3>{{ texts.get('report_intelligence_title', 'Intelligence View') }}</h3>
        <table>
            <tbody>
                <tr><th>{{ texts.get('report_root_cause_label', 'Priority Improvement Stage') }}</th><td>{{ report.factory_intelligence.priority_stage.name if report.factory_intelligence.priority_stage else report.factory_intelligence.root_bottleneck.name }}</td></tr>
                <tr><th>{{ texts.get('report_root_reason_label', 'Improvement Basis') }}</th><td>{{ report.factory_intelligence.priority_stage.reason if report.factory_intelligence.priority_stage else report.factory_intelligence.root_bottleneck.reason }}</td></tr>
                <tr><th>{{ texts.get('report_symptom_stage_label', 'Current Pressure Stage') }}</th><td>{{ report.factory_intelligence.pressure_stage.name if report.factory_intelligence.pressure_stage else report.factory_intelligence.bottleneck.name }}</td></tr>
                <tr><th>{{ texts.get('report_intelligence_brief_label', 'AI Brief') }}</th><td>{{ report.factory_intelligence.brief }}</td></tr>
                {% if report.factory_intelligence.weekly_progress %}
                <tr><th>{{ texts.get('weekly_progress_title', 'Weekly Improvement') }}</th><td>{{ report.factory_intelligence.weekly_progress.summary }}</td></tr>
                {% endif %}
            </tbody>
        </table>
        {% endif %}

        {% if report.equipment_quality %}
        <h3>{{ report.equipment_quality.title or '设备与质量闭环' }}</h3>
        <table>
            <tbody>
                <tr><th>{{ texts.get('report_intelligence_brief_label', 'AI Brief') }}</th><td>{{ report.equipment_quality.summary }}</td></tr>
                <tr><th>{{ texts.get('equipment_quality_band_saw_label', '带锯') }}</th><td>{{ report.equipment_quality.metrics.band_saw_actual_trays }}/{{ report.equipment_quality.metrics.band_saw_target_trays }} 托</td></tr>
                <tr><th>{{ texts.get('equipment_quality_secondary_label', '二选') }}</th><td>{{ report.equipment_quality.metrics.secondary_actual_pcs if report.equipment_quality.metrics.secondary_actual_pcs is not none else '-' }}/{{ report.equipment_quality.metrics.secondary_target_pcs }} 件</td></tr>
                <tr><th>{{ texts.get('equipment_quality_utilization_label', '带锯利用率') }}</th><td>{{ report.equipment_quality.metrics.band_saw_utilization_pct }}%</td></tr>
                <tr><th>{{ texts.get('equipment_quality_risks_label', '关键风险') }}</th><td>{{ report.equipment_quality.risks|join('；') if report.equipment_quality.risks else '-' }}</td></tr>
            </tbody>
        </table>
        {% endif %}

        {% if report.role_collaboration %}
        <h3>{{ report.role_collaboration.title or '角色协同建议' }}</h3>
        <table>
            <tbody>
                <tr><th>{{ texts.get('report_personnel_changes_summary_label', 'Summary') }}</th><td>{{ report.role_collaboration.summary }}</td></tr>
                {% for item in report.role_collaboration.rows %}
                <tr><th>{{ item.role }}</th><td>{{ item.summary }}<br>{{ item.action }}</td></tr>
                {% endfor %}
            </tbody>
        </table>
        {% endif %}

        {% if report.personnel_changes %}
        <h3>{{ texts.get('report_personnel_changes_title', 'Personnel Changes') }}</h3>
        <table>
            <tbody>
                <tr><th>{{ texts.get('report_personnel_changes_summary_label', 'Summary') }}</th><td>{{ report.personnel_changes.summary }}</td></tr>
                <tr><th>{{ texts.get('report_personnel_added_label', 'Added') }}</th><td>{{ report.personnel_changes.added_count }}</td></tr>
                <tr><th>{{ texts.get('report_personnel_left_label', 'Left') }}</th><td>{{ report.personnel_changes.left_count }}</td></tr>
                <tr><th>{{ texts.get('report_personnel_net_change_label', 'Net Change') }}</th><td>{{ report.personnel_changes.net_change }}</td></tr>
                <tr><th>{{ texts.get('report_personnel_added_names_label', 'Added Names') }}</th><td>{{ report.personnel_changes.added_names|join('、') if report.personnel_changes.added_names else '-' }}</td></tr>
                <tr><th>{{ texts.get('report_personnel_left_names_label', 'Left Names') }}</th><td>{{ report.personnel_changes.left_names|join('、') if report.personnel_changes.left_names else '-' }}</td></tr>
                <tr><th>{{ texts.get('report_personnel_status_changes_label', 'Status Changes') }}</th><td>{{ report.personnel_changes.status_changes|join('；') if report.personnel_changes.status_changes else '-' }}</td></tr>
            </tbody>
        </table>
        {% endif %}

        {% if report.traceability %}
        <h3>{{ texts.get('traceability_title', '事件追溯') }}</h3>
        <table>
            <tbody>
                <tr><th>{{ texts.get('traceability_event_total', '事件总数') }}</th><td>{{ report.traceability.summary.event_total }}</td></tr>
                <tr><th>{{ texts.get('traceability_stage_total', '覆盖环节') }}</th><td>{{ report.traceability.summary.stage_total }}</td></tr>
                <tr><th>{{ texts.get('traceability_top_stage', '最活跃环节') }}</th><td>{{ report.traceability.summary.top_stage }}</td></tr>
                <tr><th>{{ texts.get('traceability_latest_time', '最近时间') }}</th><td>{{ report.traceability.summary.latest_time }}</td></tr>
                <tr><th>{{ texts.get('traceability_recent_title', '最近事件') }}</th><td>{% if report.traceability.events %}{% for item in report.traceability.events[:4] %}{{ item.created_at }} {{ item.stage_label }} · {{ item.action }}{% if not loop.last %}<br>{% endif %}{% endfor %}{% else %}-{% endif %}</td></tr>
            </tbody>
        </table>
        {% endif %}

        {% if report.forecast %}
        <h3>{{ texts.get('forecast_title', '预测层') }}</h3>
        <table>
            <tbody>
                <tr><th>{{ texts.get('report_intelligence_brief_label', 'AI Brief') }}</th><td>{{ report.forecast.summary }}</td></tr>
                <tr><th>{{ texts.get('forecast_top_risk_label', '明日主风险') }}</th><td>{{ report.forecast.top_risk }}</td></tr>
                <tr><th>{{ texts.get('forecast_tomorrow_saw_label', '明日锯解预测') }}</th><td>{{ report.forecast.predictions.tomorrow_saw_trays }}</td></tr>
                <tr><th>{{ texts.get('forecast_tomorrow_sort_label', '明日待入窑预测') }}</th><td>{{ report.forecast.predictions.tomorrow_sort_trays }}</td></tr>
                <tr><th>{{ texts.get('forecast_tomorrow_finish_label', '明日成品件数预测') }}</th><td>{{ report.forecast.predictions.tomorrow_finished_pcs }}</td></tr>
                <tr><th>{{ texts.get('forecast_tomorrow_finish_m3_label', '明日成品m³预测') }}</th><td>{{ report.forecast.predictions.tomorrow_finished_m3 }}</td></tr>
                <tr><th>{{ texts.get('forecast_actions_label', '明日动作') }}</th><td>{{ report.forecast.actions|join('；') if report.forecast.actions else '-' }}</td></tr>
                <tr><th>{{ texts.get('forecast_risk_drivers_label', '风险来源') }}</th><td>{{ report.forecast.risk_drivers|join('；') if report.forecast.risk_drivers else '-' }}</td></tr>
                <tr><th>{{ texts.get('forecast_calibration_label', '预测校准') }}</th><td>{{ texts.get('forecast_hit_rate_label', '命中率') }} {{ report.forecast.calibration.hit_rate if report.forecast.calibration.hit_rate is not none else '-' }} / {{ texts.get('forecast_avg_error_label', '平均绝对误差') }} {{ report.forecast.calibration.avg_abs_error if report.forecast.calibration.avg_abs_error is not none else '-' }}</td></tr>
            </tbody>
        </table>
        {% endif %}

        <h3>{{ texts.report_summary }}</h3>
        <table>
            <tbody>
                {% for k, v in report.summary.items() %}
                <tr><th>{{ report.display_labels.summary.get(k, k) }}</th><td>{{ v }}</td></tr>
                {% endfor %}
            </tbody>
        </table>

        <h3>{{ texts.report_inventory_snapshot }}</h3>
        <table>
            <tbody>
                {% for k in report.display_order.inventory_snapshot %}
                <tr><th>{{ report.display_labels.inventory_snapshot.get(k, k) }}</th><td>{{ report.inventory_snapshot.get(k, '') }}</td></tr>
                {% endfor %}
            </tbody>
        </table>

        {% if report.show_yield_loss %}
        <h3>{{ texts.get('report_yield_loss_title', 'Stage Output Ratio / Loss Rate') }}</h3>
        <table>
            <tbody>
                {% for k in report.display_order.yield_loss %}
                <tr>
                    <th>{{ report.display_labels.yield_loss.get(k, k) }}</th>
                    <td>
                        {% if k.endswith('_pct') %}
                            {{ report.yield_loss.get(k, 0) }}%
                        {% else %}
                            {{ report.yield_loss.get(k, 0) }}
                        {% endif %}
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        {% endif %}

        <h3>{{ texts.report_kiln_status }}</h3>
        <table>
            <tbody>
                {% for k in report.display_order.kiln_status %}
                <tr><th>{{ report.display_labels.kiln_status.get(k, k) }}</th><td>{{ report.kiln_status.get(k, '') }}</td></tr>
                {% endfor %}
            </tbody>
        </table>

        <h3>{{ texts.report_breakdown_count }}</h3>
        <table>
            <tbody>
                {% for k in report.display_order.breakdown %}
                <tr><th>{{ report.display_labels.breakdown.get(k, k) }}</th><td>{{ report.breakdown.get(k, [])|length }}</td></tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</body>
</html>
"""


BOSS_DAILY_REPORT_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ texts.daily_report_title }}</title>
    <link rel="icon" type="image/png" href="{{ url_for('static', filename='AIF_logo.png') }}">
    <style>
        :root {
            --bg: #f3f6fb;
            --card: #ffffff;
            --line: #d8e0ec;
            --ink: #1f2937;
            --muted: #6b7280;
            --accent: #0f766e;
        }
        * { box-sizing: border-box; }
        body { margin: 0; font-family: "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif; background: var(--bg); color: var(--ink); }
        .wrap { max-width: 700px; margin: 0 auto; padding: 10px 10px 18px; }
        .toolbar { display:flex; gap:6px; align-items:center; margin-bottom:8px; flex-wrap:wrap; }
        .btn { padding: 6px 9px; border: none; border-radius: 8px; background: #0d9488; color: #fff; text-decoration:none; cursor:pointer; font-size: 12px; }
        .btn.gray { background: #6b7280; }
        .toolbar input[type="date"], .toolbar select { padding: 5px 7px; border: 1px solid var(--line); border-radius: 8px; background: #fff; font-size: 12px; }
        .panel { background: var(--card); border: 1px solid var(--line); border-radius: 10px; padding: 10px; margin-top: 8px; }
        h1 { margin: 2px 0 5px; font-size: 18px; }
        h3 { margin: 0 0 6px; font-size: 15px; color: var(--accent); }
        .muted { color: var(--muted); font-size: 12px; }

        .kv-table { width:100%; border-collapse: collapse; margin-top: 6px; }
        .kv-table th, .kv-table td { border: 1px solid #e5e7eb; padding: 6px 8px; font-size: 12px; width: 50%; }
        .kv-table th { text-align: left; background: #f8fafc; }
        .kv-table td { text-align: left; background: #fff; }
        .kv-table tbody tr:nth-child(odd) th, .kv-table tbody tr:nth-child(odd) td { background: #ffffff; }
        .kv-table tbody tr:nth-child(even) th, .kv-table tbody tr:nth-child(even) td { background: #f3f6fb; }
        .kv-table.ai-tight { table-layout: fixed; }
        .kv-table.ai-tight th { width: 6.8em; white-space: nowrap; }
        .kv-table.ai-tight td { width: auto; white-space: normal; word-break: break-word; line-height: 1.55; }

        .kiln-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 6px; }
        .kiln { border: 1px solid #e3e9f3; border-radius: 10px; padding: 7px 8px; background: #fbfdff; }
        .badge { display: inline-block; padding: 2px 8px; border-radius: 999px; font-size: 12px; margin-left: 6px; background: #e2e8f0; }
        .badge.loading { background: #fef3c7; color: #92400e; }
        .badge.drying { background: #dbeafe; color: #1d4ed8; }
        .badge.unloading { background: #ffedd5; color: #9a3412; }
        .badge.ready, .badge.completed { background: #dcfce7; color: #166534; }
        .once-warn { margin: 8px 0; padding: 9px 10px; border: 2px solid #b91c1c; border-radius: 8px; background: #fef2f2; color: #7f1d1d; font-size: 12px; font-weight: 700; }

        @media (max-width: 620px) {
            .toolbar { gap: 5px; }
            .toolbar form { width: 100%; display: grid !important; grid-template-columns: 1fr auto; gap: 6px; }
            .toolbar form label { grid-column: 1 / -1; font-size: 12px; color: #4b5563; }
            .toolbar form input[type="hidden"] { display: none; }
            .kiln-grid { grid-template-columns: 1fr; }
        }
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
    <div class="wrap">
        <div class="toolbar">
            {% if not one_time_access %}
            <a href="{{ url_for('boss_h5', lang=lang) }}" class="btn gray">{{ texts.back_home }}</a>
            {% endif %}
            <label for="lang-select">{{ texts.language }}:</label>
            <select id="lang-select" onchange="changeLanguage(this.value)">
                <option value="zh" {% if lang == 'zh' %}selected{% endif %}>{{ texts.chinese }}</option>
                <option value="en" {% if lang == 'en' %}selected{% endif %}>{{ texts.english }}</option>
                <option value="my" {% if lang == 'my' %}selected{% endif %}>{{ texts.burmese }}</option>
            </select>
            {% if not one_time_access %}
            <form method="GET" action="{{ url_for('report_daily_page') }}" style="display:flex; gap:8px; align-items:center;">
                <label>{{ texts.report_date_label }}</label>
                <input type="date" name="date" value="{{ report.date }}">
                <input type="hidden" name="lang" value="{{ lang }}">
                <button type="submit" class="btn">{{ texts.query_btn }}</button>
            </form>
            {% endif %}
        </div>
        {% if one_time_access %}
        <div class="once-warn">{{ texts.one_time_daily_link_warning }}</div>
        {% endif %}

        <div class="panel">
            <h1>{{ texts.daily_report_title }} - {{ report.date }}</h1>
            <p class="muted">{{ texts.report_range }}: {{ report.range.start }} ~ {{ report.range.end }}</p>
            <p class="muted">{{ report.meta.note }}</p>
        </div>

        {% if report.ai_deep_monitor and report.ai_deep_monitor.summary %}
        <div class="panel">
            <h3>{{ texts.get('intelligence_panel_title', 'AI建议') }}</h3>
            <div class="muted">{{ report.ai_deep_monitor.generated_at }} · {{ report.ai_deep_monitor.trigger }} · {{ texts.get('ai_template_version_label', 'Template') }} {{ report.ai_deep_monitor.template_version or 'deep_monitor_v2' }}</div>
            <table class="kv-table ai-tight">
                <tbody>
                    <tr><th>{{ texts.get('report_intelligence_brief_label', 'AI Brief') }}</th><td>{{ report.ai_deep_monitor.summary }}</td></tr>
                    <tr><th>{{ texts.get('ai_quick_today_focus', 'Today Focus') }}</th><td>{{ report.ai_deep_monitor.focus[0] if report.ai_deep_monitor.focus else '-' }}</td></tr>
                    <tr><th>{{ texts.get('risk_alerts_title', 'Risk Alerts') }}</th><td>{{ report.ai_deep_monitor.risks[0] if report.ai_deep_monitor.risks else '-' }}</td></tr>
                </tbody>
            </table>
        </div>
        {% endif %}

        {% if report.factory_intelligence %}
        <div class="panel">
            <h3>{{ texts.get('report_intelligence_title', 'Intelligence View') }}</h3>
            <table class="kv-table ai-tight">
                <tbody>
                    <tr><th>{{ texts.get('report_root_cause_label', 'Priority Improvement Stage') }}</th><td>{{ report.factory_intelligence.priority_stage.name if report.factory_intelligence.priority_stage else report.factory_intelligence.root_bottleneck.name }}</td></tr>
                    <tr><th>{{ texts.get('report_root_reason_label', 'Improvement Basis') }}</th><td>{{ report.factory_intelligence.priority_stage.reason if report.factory_intelligence.priority_stage else report.factory_intelligence.root_bottleneck.reason }}</td></tr>
                    <tr><th>{{ texts.get('report_symptom_stage_label', 'Current Pressure Stage') }}</th><td>{{ report.factory_intelligence.pressure_stage.name if report.factory_intelligence.pressure_stage else report.factory_intelligence.bottleneck.name }}</td></tr>
                    <tr><th>{{ texts.get('report_intelligence_brief_label', 'AI Brief') }}</th><td>{{ report.factory_intelligence.brief }}</td></tr>
                </tbody>
            </table>
        </div>
        {% endif %}

        {% if report.personnel_changes %}
        <div class="panel">
            <h3>{{ texts.get('report_personnel_changes_title', 'Personnel Changes') }}</h3>
            <table class="kv-table ai-tight">
                <tbody>
                    <tr><th>{{ texts.get('report_personnel_changes_summary_label', 'Summary') }}</th><td>{{ report.personnel_changes.summary }}</td></tr>
                    <tr><th>{{ texts.get('report_personnel_added_label', 'Added') }}</th><td>{{ report.personnel_changes.added_count }}</td></tr>
                    <tr><th>{{ texts.get('report_personnel_left_label', 'Left') }}</th><td>{{ report.personnel_changes.left_count }}</td></tr>
                    <tr><th>{{ texts.get('report_personnel_net_change_label', 'Net Change') }}</th><td>{{ report.personnel_changes.net_change }}</td></tr>
                    <tr><th>{{ texts.get('report_personnel_added_names_label', 'Added Names') }}</th><td>{{ report.personnel_changes.added_names|join('、') if report.personnel_changes.added_names else '-' }}</td></tr>
                    <tr><th>{{ texts.get('report_personnel_left_names_label', 'Left Names') }}</th><td>{{ report.personnel_changes.left_names|join('、') if report.personnel_changes.left_names else '-' }}</td></tr>
                    <tr><th>{{ texts.get('report_personnel_status_changes_label', 'Status Changes') }}</th><td>{{ report.personnel_changes.status_changes|join('；') if report.personnel_changes.status_changes else '-' }}</td></tr>
                </tbody>
            </table>
        </div>
        {% endif %}

        <div class="panel">
            <h3>{{ texts.report_summary }}</h3>
            <table class="kv-table">
                <tbody>
                    {% for k in report.display_order.summary %}
                    <tr>
                        <th>{{ report.display_labels.summary.get(k, k) }}</th>
                        <td>{{ report.summary.get(k, '') }}</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>

        <div class="panel">
            <h3>{{ texts.report_inventory_snapshot }}</h3>
            <table class="kv-table">
                <tbody>
                    {% for k in report.display_order.inventory_snapshot %}
                    <tr>
                        <th>{{ report.display_labels.inventory_snapshot.get(k, k) }}</th>
                        <td>{{ report.inventory_snapshot.get(k, '') }}</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>

        {% if report.show_yield_loss %}
        <div class="panel">
            <h3>{{ texts.get('report_yield_loss_title', 'Stage Output Ratio / Loss Rate') }}</h3>
            <table class="kv-table">
                <tbody>
                    {% for k in report.display_order.yield_loss %}
                    <tr>
                        <th>{{ report.display_labels.yield_loss.get(k, k) }}</th>
                        <td>
                            {% if k.endswith('_pct') %}
                                {{ report.yield_loss.get(k, 0) }}%
                            {% else %}
                                {{ report.yield_loss.get(k, 0) }}
                            {% endif %}
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
        {% endif %}

        <div class="panel">
            <h3>窑当日状态</h3>
            <div class="kiln-grid">
                {% for kiln_id in report.display_order.kiln_status %}
                {% set detail = report.kiln_status_detail.get(kiln_id, {}) %}
                <div class="kiln">
                    <strong>{{ report.display_labels.kiln_status.get(kiln_id, kiln_id) }}</strong>
                    <span class="badge {{ detail.get('status', '') }}">{{ detail.get('status_display', '-') }}</span>
                    <div style="margin-top:6px; color:#4b5563; font-size:13px;">{{ detail.get('progress', report.kiln_status.get(kiln_id, '-')) }}</div>
                </div>
                {% endfor %}
            </div>
        </div>

        <div class="panel">
            <h3>{{ texts.report_breakdown_count }}</h3>
            <table class="kv-table">
                <tbody>
                    {% for k in report.display_order.breakdown %}
                    <tr>
                        <th>{{ report.display_labels.breakdown.get(k, k) }}</th>
                        <td>{{ report.breakdown.get(k, [])|length }}</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
</body>
</html>
"""
