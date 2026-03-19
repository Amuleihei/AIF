# 日报页面模板
DAILY_REPORT_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ texts.daily_report_title }}</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 12px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; background: #fff; padding: 14px; border-radius: 8px; box-shadow: 0 1px 8px rgba(0,0,0,0.08); }
        h1 { margin: 6px 0; font-size: 22px; }
        h3 { margin: 12px 0 6px; font-size: 16px; }
        .toolbar { display:flex; gap:8px; align-items:center; margin-bottom:10px; flex-wrap:wrap; }
        input[type="date"] { padding:6px; }
        button, .btn { padding: 7px 10px; border: none; border-radius: 6px; background: #0d6efd; color: #fff; text-decoration:none; cursor:pointer; font-size: 13px; }
        .btn.gray { background: #6c757d; }
        table { width:100%; border-collapse: collapse; margin-top: 8px; background: #fff; }
        th, td { border: 1px solid #e5e7eb; padding: 6px 8px; text-align: left; font-size: 13px; }
        th { background: #f3f4f6; }
        .muted { color:#6b7280; font-size: 12px; }
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
            <a href="{{ url_for('index', lang=lang) }}" class="btn gray">{{ texts.back_home }}</a>
            <form method="GET" action="{{ url_for('report_daily_page') }}" style="display:flex; gap:8px; align-items:center;">
                <label>{{ texts.report_date_label }}</label>
                <input type="date" name="date" value="{{ report.date }}">
                <input type="hidden" name="lang" value="{{ lang }}">
                <button type="submit">{{ texts.query_btn }}</button>
            </form>
            <a class="btn" href="{{ url_for('export_daily_report', date=report.date, lang=lang) }}">{{ texts.export_daily_report }}</a>
        </div>

        <h1>{{ texts.daily_report_title }} - {{ report.date }}</h1>
        <p class="muted">{{ texts.report_range }}: {{ report.range.start }} ~ {{ report.range.end }}</p>
        <p class="muted">{{ report.meta.note }}</p>

        <h3>{{ texts.report_summary }}</h3>
        <table>
            <tbody>
                {% for k, v in report.summary.items() %}
                <tr><th style="width: 320px;">{{ report.display_labels.summary.get(k, k) }}</th><td>{{ v }}</td></tr>
                {% endfor %}
            </tbody>
        </table>

        <h3>{{ texts.report_inventory_snapshot }}</h3>
        <table>
            <tbody>
                {% for k in report.display_order.inventory_snapshot %}
                <tr><th style="width: 320px;">{{ report.display_labels.inventory_snapshot.get(k, k) }}</th><td>{{ report.inventory_snapshot.get(k, '') }}</td></tr>
                {% endfor %}
            </tbody>
        </table>

        {% if report.show_yield_loss %}
        <h3>环节产出比 / 损耗率</h3>
        <table>
            <tbody>
                {% for k in report.display_order.yield_loss %}
                <tr>
                    <th style="width: 320px;">{{ report.display_labels.yield_loss.get(k, k) }}</th>
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
                <tr><th style="width: 320px;">{{ report.display_labels.kiln_status.get(k, k) }}</th><td>{{ report.kiln_status.get(k, '') }}</td></tr>
                {% endfor %}
            </tbody>
        </table>

        <h3>{{ texts.report_breakdown_count }}</h3>
        <table>
            <tbody>
                {% for k in report.display_order.breakdown %}
                <tr><th style="width: 320px;">{{ report.display_labels.breakdown.get(k, k) }}</th><td>{{ report.breakdown.get(k, [])|length }}</td></tr>
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

        .kiln-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 6px; }
        .kiln { border: 1px solid #e3e9f3; border-radius: 10px; padding: 7px 8px; background: #fbfdff; }
        .badge { display: inline-block; padding: 2px 8px; border-radius: 999px; font-size: 12px; margin-left: 6px; background: #e2e8f0; }
        .badge.loading { background: #fef3c7; color: #92400e; }
        .badge.drying { background: #dbeafe; color: #1d4ed8; }
        .badge.unloading { background: #ffedd5; color: #9a3412; }
        .badge.ready, .badge.completed { background: #dcfce7; color: #166534; }

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
            <a href="{{ url_for('boss_h5', lang=lang) }}" class="btn gray">{{ texts.back_home }}</a>
            <label for="lang-select">{{ texts.language }}:</label>
            <select id="lang-select" onchange="changeLanguage(this.value)">
                <option value="zh" {% if lang == 'zh' %}selected{% endif %}>{{ texts.chinese }}</option>
                <option value="en" {% if lang == 'en' %}selected{% endif %}>{{ texts.english }}</option>
                <option value="my" {% if lang == 'my' %}selected{% endif %}>{{ texts.burmese }}</option>
            </select>
            <form method="GET" action="{{ url_for('report_daily_page') }}" style="display:flex; gap:8px; align-items:center;">
                <label>{{ texts.report_date_label }}</label>
                <input type="date" name="date" value="{{ report.date }}">
                <input type="hidden" name="lang" value="{{ lang }}">
                <button type="submit" class="btn">{{ texts.query_btn }}</button>
            </form>
        </div>

        <div class="panel">
            <h1>{{ texts.daily_report_title }} - {{ report.date }}</h1>
            <p class="muted">{{ texts.report_range }}: {{ report.range.start }} ~ {{ report.range.end }}</p>
            <p class="muted">{{ report.meta.note }}</p>
        </div>

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
            <h3>环节产出比 / 损耗率</h3>
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
