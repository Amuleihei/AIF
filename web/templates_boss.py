BOSS_H5_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ texts.title }} - {{ texts.boss }}</title>
    <link rel="icon" type="image/png" href="{{ url_for('static', filename='AIF_logo.png') }}">
    <style>
        :root {
            --bg: #f3f6fb;
            --card: #ffffff;
            --ink: #1f2937;
            --muted: #6b7280;
            --line: #d8e0ec;
            --accent: #0f766e;
        }
        * { box-sizing: border-box; }
        body {
            margin: 0;
            font-family: "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
            background: linear-gradient(180deg, #eaf1fb 0%, var(--bg) 40%, var(--bg) 100%);
            color: var(--ink);
        }
        .wrap { max-width: 720px; margin: 0 auto; padding: 16px 12px 24px; }
        .topbar {
            background: var(--card);
            border: 1px solid var(--line);
            border-radius: 12px;
            padding: 10px 12px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 10px;
        }
        .topbar small { color: var(--muted); display: block; }
        .topbar-actions { display: flex; align-items: center; gap: 8px; }
        .btn-mini {
            display: inline-block;
            border: 1px solid #0ea5a5;
            color: #0f766e;
            background: #ecfeff;
            text-decoration: none;
            border-radius: 8px;
            padding: 6px 10px;
            font-size: 13px;
            font-weight: 600;
            white-space: nowrap;
        }
        .lang select { border: 1px solid var(--line); border-radius: 8px; padding: 6px 8px; background: #fff; }
        .title {
            margin: 14px 0 10px;
            padding: 14px 12px;
            border-radius: 12px;
            color: #fff;
            background: linear-gradient(135deg, #0f766e 0%, #0ea5a5 100%);
        }
        .title h1 { margin: 0; font-size: 20px; }
        .title p { margin: 6px 0 0; opacity: .92; font-size: 13px; }
        .card {
            background: var(--card);
            border: 1px solid var(--line);
            border-radius: 12px;
            padding: 12px;
            margin-top: 12px;
        }
        .card h2 {
            margin: 0 0 10px;
            color: var(--accent);
            font-size: 16px;
        }
        .grid {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 8px;
        }
        .metric {
            border: 1px solid #e3e9f3;
            border-radius: 10px;
            padding: 8px 10px;
            background: #fbfdff;
        }
        .metric .k { color: var(--muted); font-size: 12px; }
        .metric .v { margin-top: 3px; font-size: 20px; font-weight: 700; }
        .kiln-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; }
        .kiln { border: 1px solid #e3e9f3; border-radius: 10px; padding: 8px 10px; background: #fbfdff; }
        .badge {
            display: inline-block;
            padding: 2px 8px;
            border-radius: 999px;
            font-size: 12px;
            margin-left: 6px;
            background: #e2e8f0;
        }
        .badge.loading { background: #fef3c7; color: #92400e; }
        .badge.drying { background: #dbeafe; color: #1d4ed8; }
        .badge.unloading { background: #ffedd5; color: #9a3412; }
        .badge.ready, .badge.completed { background: #dcfce7; color: #166534; }
        .footer {
            margin-top: 14px;
            text-align: center;
            font-size: 13px;
            color: var(--muted);
        }
        .footer a { color: #2563eb; text-decoration: none; }
        @media (max-width: 520px) {
            .grid, .kiln-grid { grid-template-columns: 1fr; }
            .title h1 { font-size: 18px; }
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
        <div class="topbar">
            <div>
                <strong>{{ (current_user.username or '')|upper }}</strong>
                <small>{{ texts.boss }}</small>
            </div>
            <div class="topbar-actions">
                <a class="btn-mini" href="{{ url_for('report_daily_page', lang=lang) }}">{{ texts.view_daily_report }}</a>
                {% if period_reports.weekly.generated %}
                <a class="btn-mini" href="{{ period_reports.weekly.url }}&lang={{ lang }}" style="border-color:#0284c7; color:#075985; background:#e0f2fe;">周报 {{ period_reports.weekly.key }}</a>
                {% endif %}
                {% if period_reports.monthly.generated %}
                <a class="btn-mini" href="{{ period_reports.monthly.url }}&lang={{ lang }}" style="border-color:#16a34a; color:#166534; background:#dcfce7;">月报 {{ period_reports.monthly.key }}</a>
                {% endif %}
                <select onchange="changeLanguage(this.value)">
                    <option value="zh" {% if lang == 'zh' %}selected{% endif %}>{{ texts.chinese }}</option>
                    <option value="en" {% if lang == 'en' %}selected{% endif %}>{{ texts.english }}</option>
                    <option value="my" {% if lang == 'my' %}selected{% endif %}>{{ texts.burmese }}</option>
                </select>
            </div>
        </div>

        <div class="title">
            <h1>{{ texts.factory_overview }}</h1>
            <p>老板端</p>
        </div>

        {% if alerts %}
        <div class="card" style="border-left:4px solid #dc2626;">
            <h2 style="color:#b91c1c;">风险预警</h2>
            <div style="display:grid; gap:6px;">
                {% for item in alerts %}
                <div style="padding:8px 10px; border:1px solid #fee2e2; border-radius:8px; background:#fff1f2; font-size:13px;">
                    {{ item.text }}
                </div>
                {% endfor %}
            </div>
        </div>
        {% endif %}

        <div class="card">
            <h2>{{ texts.stage_stock }}</h2>
            <div class="grid">
                <div class="metric"><div class="k">原木库存</div><div class="v">{{ "%.4f"|format(log_stock) }} 缅吨</div></div>
                <div class="metric"><div class="k">锯解库存</div><div class="v">{{ saw_stock }} 锯解托</div></div>
                <div class="metric"><div class="k">药浸库存</div><div class="v">{{ dip_stock }} 锯解托</div></div>
                <div class="metric"><div class="k">待入窑库存</div><div class="v">{{ sorting_stock }} 窑托</div></div>
                <div class="metric"><div class="k">窑完成库存</div><div class="v">{{ kiln_done_stock }} 窑托</div></div>
                <div class="metric"><div class="k">成品库存</div><div class="v">{{ product_count }} 托（折合{{ "%.2f"|format(product_m3) }} m³）</div></div>
            </div>
        </div>

        <div class="card">
            <h2>{{ texts.adjust_byproduct_stock }}</h2>
            <div class="grid">
                <div class="metric"><div class="k">{{ texts.current_bark_stock }}</div><div class="v">{{ "%.2f"|format(bark_stock_m3) }} m³</div></div>
                <div class="metric"><div class="k">{{ texts.current_dust_stock }}</div><div class="v">{{ dust_bag_stock }} 袋</div></div>
                <div class="metric"><div class="k">{{ texts.current_waste_segment_stock }}</div><div class="v">{{ waste_segment_bag_stock }} 袋</div></div>
            </div>
        </div>

        <div class="card">
            <h2>{{ texts.kiln_overview_label }}</h2>
            <div class="kiln-grid">
                {% for kiln_id in ['A', 'B', 'C', 'D'] %}
                <div class="kiln">
                    <strong>{{ kiln_id }} {{ texts.kiln_label }}</strong>
                    <span class="badge {{ kiln_status[kiln_id].status }}">{{ kiln_status[kiln_id].status_display }}</span>
                    <div style="margin-top:6px; color:#4b5563; font-size:13px;">{{ kiln_status[kiln_id].progress or '-' }}</div>
                </div>
                {% endfor %}
            </div>
        </div>

        <div class="footer">
            <a href="{{ url_for('logout') }}">{{ texts.logout }}</a>
        </div>
    </div>
</body>
</html>
"""
