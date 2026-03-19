# HTML templates for the web application

# 登录页面模板
LOGIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ texts.login_title }}</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 0; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; display: flex; align-items: center; justify-content: center; }
        .login-container { background: white; padding: 40px; border-radius: 10px; box-shadow: 0 15px 35px rgba(0,0,0,0.1); width: 100%; max-width: 400px; }
        h1 { text-align: center; color: #333; margin-bottom: 30px; }
        .form-group { margin-bottom: 20px; }
        label { display: block; margin-bottom: 5px; color: #555; font-weight: bold; }
        input[type="text"], input[type="password"] { width: 100%; padding: 12px; border: 2px solid #ddd; border-radius: 5px; font-size: 16px; box-sizing: border-box; }
        input[type="text"]:focus, input[type="password"]:focus { border-color: #667eea; outline: none; }
        button { width: 100%; padding: 12px; background: #667eea; color: white; border: none; border-radius: 5px; font-size: 16px; cursor: pointer; transition: background 0.3s; }
        button:hover { background: #5a6fd8; }
        .alert { padding: 10px; margin-bottom: 20px; border-radius: 5px; }
        .alert-error { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
        .language-selector { text-align: right; margin-bottom: 20px; }
        .language-selector select { padding: 5px; border-radius: 3px; }
    </style>
</head>
<body>
    <div class="login-container">
        <div class="language-selector">
            <label for="lang-select">{{ texts.language }}:</label>
            <select id="lang-select" onchange="changeLanguage(this.value)">
                <option value="zh" {% if lang == 'zh' %}selected{% endif %}>{{ texts.chinese }}</option>
                <option value="en" {% if lang == 'en' %}selected{% endif %}>{{ texts.english }}</option>
                <option value="my" {% if lang == 'my' %}selected{% endif %}>{{ texts.burmese }}</option>
            </select>
        </div>

        <h1>{{ texts.login_title }}</h1>

        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="alert alert-{{ 'error' if category == 'error' else 'info' }}">{{ message }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}

        <form method="POST">
            {{ form.hidden_tag() }}
            <div class="form-group">
                <label for="username">{{ texts.username }}</label>
                {{ form.username(class="form-control") }}
            </div>
            <div class="form-group">
                <label for="password">{{ texts.password }}</label>
                {{ form.password(class="form-control") }}
            </div>
            <button type="submit">{{ texts.login_button }}</button>
        </form>
    </div>

    <script>
        function changeLanguage(lang) {
            const url = new URL(window.location);
            url.searchParams.set('lang', lang);
            window.location.href = url.toString();
        }
    </script>
</body>
</html>
"""

# HTML template
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ texts.title }}</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 12px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; background: white; padding: 14px; border-radius: 8px; box-shadow: 0 1px 8px rgba(0,0,0,0.09); }
        h1 { color: #333; text-align: center; }
        .section { margin: 16px 0; padding: 14px; border: 1px solid #ddd; border-radius: 8px; }
        .section h2 { color: #007bff; margin-top: 0; }
        .form-group { margin: 10px 0; }
        label { display: inline-block; width: 180px; font-weight: bold; }
        input[type="text"], input[type="number"] { padding: 6px 8px; border: 1px solid #ddd; border-radius: 4px; width: 150px; }
        button { background: #28a745; color: white; padding: 8px 14px; border: none; border-radius: 4px; cursor: pointer; margin: 3px; font-size: 13px; }
        button:hover { background: #218838; }
        .result { margin-top: 20px; padding: 15px; background: #f8f9fa; border-left: 4px solid #007bff; border-radius: 4px; }
        .error { border-left-color: #dc3545; background: #f8d7da; }
        .toast-msg { position: fixed; right: 20px; top: 20px; z-index: 9999; min-width: 280px; max-width: 460px; padding: 12px 14px; border-radius: 8px; box-shadow: 0 6px 18px rgba(0,0,0,0.2); background: #e7f3ff; color: #063970; border: 1px solid #9cc9ff; }
        .toast-msg.error { background: #fdeaea; color: #7f1d1d; border: 1px solid #f5a3a3; }
        .input-missing { border-color:#dc2626 !important; box-shadow:0 0 0 2px rgba(220,38,38,0.12); }
        .field-reminder-bubble { display:none; margin-top:6px; color:#b91c1c; font-size:12px; background:#fff1f2; border:1px solid #fecdd3; border-radius:999px; padding:4px 10px; width:max-content; max-width:100%; }
        .entry-reminder-strip { display:none; margin:8px 0 12px; padding:8px 12px; border-radius:8px; background:#fff7ed; border:1px solid #fed7aa; color:#9a3412; font-size:13px; }
        .entry-reminder-strip strong { margin-right:8px; }
        .status { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 12px; }
        .status.empty { background: #6c757d; color: white; }
        .status.loading { background: #ffc107; color: black; }
        .status.drying { background: #17a2b8; color: white; }
        .status.unloading { background: #fd7e14; color: white; }
        .status.ready { background: #28a745; color: white; }
        .status.completed { background: #20c997; color: white; }
        .kiln-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 14px; }
        .kiln { border: 1px solid #ddd; padding: 12px; border-radius: 8px; }
        .kiln h3 { margin-top: 0; }
        .modal-mask { position: fixed; inset: 0; background: rgba(0,0,0,0.45); z-index: 11000; display: none; align-items: center; justify-content: center; }
        .modal-box { width: min(900px, 94vw); max-height: 86vh; overflow: auto; background: #fff; border-radius: 10px; padding: 16px; }
        .tray-picker-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 10px; margin: 12px 0; }
        .tray-picker-item { border: 1px solid #d7dbe2; border-radius: 8px; padding: 10px; cursor: pointer; background: #fff; }
        .tray-picker-item.active { border-color: #0d6efd; background: #eaf3ff; }
        .tray-picker-id { font-weight: bold; font-size: 13px; color: #1f2937; }
        .tray-picker-meta { margin-top: 4px; font-size: 11px; color: #6b7280; line-height: 1.35; word-break: break-word; }
        .tray-grid { width: 100%; border-collapse: collapse; margin: 10px 0; }
        .tray-grid th, .tray-grid td { border: 1px solid #ddd; padding: 6px; }
        .tray-grid input { width: 100%; box-sizing: border-box; }
        .sp-actions { white-space: nowrap; min-width: 132px; }
        .sp-actions .btn-inline { display: inline-flex; align-items: center; justify-content: center; margin: 0 2px; min-width: 54px; }
        .edit-mini-btn { background: #0d6efd; color: #fff; border: none; border-radius: 4px; padding: 4px 10px; font-size: 12px; cursor: pointer; margin-left: 8px; }
        .summary-grid { display:grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap:12px; margin:14px 0; }
        .summary-card { border:1px solid #dbe3ef; background:linear-gradient(180deg, #ffffff 0%, #f6f9fd 100%); border-radius:10px; padding:14px; }
        .summary-card strong { display:block; font-size:13px; color:#5b6472; margin-bottom:6px; }
        .summary-card span { font-size:28px; font-weight:700; color:#16202a; }
        .summary-card.pending { border-left:5px solid #f59e0b; }
        .summary-card.transit { border-left:5px solid #0d6efd; }
        .summary-card.signed { border-left:5px solid #198754; }
        .summary-card.exception { border-left:5px solid #dc3545; }
        .overview-grid { display:grid; grid-template-columns: 1fr 1fr minmax(300px, 1.2fr); gap:14px; align-items:start; }
        .overview-col p { margin: 8px 0; }
        .overview-stack { display:grid; gap:14px; }
        .overview-radar-card { border:1px solid #dbe3ef; border-radius:10px; background:linear-gradient(180deg, #ffffff 0%, #f8fbff 100%); padding:12px; }
        .overview-radar-wrap { width:100%; max-width:400px; margin:6px auto 0; }
        .overview-radar-wrap canvas { width:100%; height:auto; display:block; }
        .overview-radar-note { margin:6px 0 0; font-size:15px; color:#475569; text-align:center; font-weight:600; }
        .pair-grid { display:grid; grid-template-columns: 1fr 1fr; gap:14px; }
        @media (max-width: 1200px) {
            .overview-grid { grid-template-columns: 1fr 1fr; }
        }
        @media (max-width: 900px) {
            .overview-grid { grid-template-columns: 1fr; }
            .pair-grid { grid-template-columns: 1fr; }
        }
        .shipment-pick-grid { max-height: 360px; overflow:auto; border:1px solid #e5e7eb; border-radius:8px; padding:8px; background:#fafafa; display:flex; flex-wrap:wrap; gap:8px; align-content:flex-start; }
        .shipment-pick-item { display:flex; gap:8px; align-items:flex-start; padding:10px; border-radius:8px; background:#fff; border:1px solid #e5e7eb; cursor:pointer; user-select:none; width:fit-content; max-width:100%; }
        .shipment-pick-item.active { border-color:#0d6efd; background:#eaf3ff; }
        .shipment-pick-code { font-weight:700; color:#111827; }
        .shipment-pick-meta { font-size:12px; color:#6b7280; line-height:1.4; white-space:nowrap; }
        .shipment-status-badge { display:inline-block; min-width:72px; text-align:center; padding:4px 10px; border-radius:999px; font-size:12px; font-weight:700; }
        .shipment-status-badge.pending { background:#fff3cd; color:#946200; }
        .shipment-status-badge.transit { background:#dbeafe; color:#1d4ed8; }
        .shipment-status-badge.signed { background:#dcfce7; color:#166534; }
        .shipment-status-badge.exception { background:#fee2e2; color:#b91c1c; }
        .report-mini-grid { display:grid; grid-template-columns: 1fr 1fr; gap:8px; margin-top:8px; }
        .report-mini-card { border:1px solid #e5e7eb; border-radius:8px; padding:6px; background:#fafafa; }
        .report-mini-card h4 { margin:0 0 4px; font-size:14px; color:#374151; }
        .report-mini-table { width:100%; border-collapse:collapse; }
        .report-mini-table th, .report-mini-table td { border:1px solid #e5e7eb; padding:4px 6px; font-size:13px; text-align:left; line-height:1.3; }
        .report-mini-table th { background:#f3f4f6; width:68%; }
        .report-mini-table td { width:32%; white-space:nowrap; }
        #daily-report-modal .modal-box { width:min(544px, 74vw); max-height:78vh; padding:12px; }
        #daily-report-modal h3 { font-size:18px; }
        #daily-report-modal label,
        #daily-report-modal input,
        #daily-report-modal button,
        #daily-report-range,
        #daily-report-note { font-size:14px !important; }
        .report-mini-table tbody tr:nth-child(odd) th,
        .report-mini-table tbody tr:nth-child(odd) td { background:#ffffff; }
        .report-mini-table tbody tr:nth-child(even) th,
        .report-mini-table tbody tr:nth-child(even) td { background:#edf2f7; }
        #daily-report-kiln-body th { width:20%; white-space:nowrap; }
        #daily-report-kiln-body td { width:80%; white-space:nowrap; }
    </style>
    <script>
        const SCROLL_STORE_KEY = 'aif_web_scroll_y';

        function storeScrollPosition() {
            try {
                sessionStorage.setItem(SCROLL_STORE_KEY, String(window.scrollY || 0));
            } catch (e) {}
        }

        function restoreScrollPosition() {
            try {
                const raw = sessionStorage.getItem(SCROLL_STORE_KEY);
                if (raw === null) return;
                sessionStorage.removeItem(SCROLL_STORE_KEY);
                const y = parseInt(raw, 10);
                if (!Number.isNaN(y)) {
                    setTimeout(function() { window.scrollTo(0, y); }, 0);
                }
            } catch (e) {}
        }

        function replacePageHtml(html) {
            storeScrollPosition();
            document.open();
            document.write(html);
            document.close();
        }

        function changeLanguage(lang) {
            const url = new URL(window.location);
            url.searchParams.set('lang', lang);
            window.location.href = url.toString();
        }

        function shipmentStatusClass(status) {
            if (status === '待发车' || status === '去仰光途中') return 'pending';
            if (status === '仰光仓已到') return 'transit';
            if (status === '已从仰光出港' || status === '中国港口已到') return 'signed';
            if (status === '异常') return 'exception';
            return '';
        }

        function renderOverviewRadar() {
            const canvas = document.getElementById('overview-radar-canvas');
            if (!canvas || !canvas.getContext) return;
            const labels = Array.isArray(OVERVIEW_RADAR_LABELS) ? OVERVIEW_RADAR_LABELS.slice(0, 5) : [];
            const radar = OVERVIEW_RADAR && typeof OVERVIEW_RADAR === 'object' ? OVERVIEW_RADAR : {};
            const datasets = [
                {name:'当前', vals: radar.current || [], color:'rgba(37,99,235,0.85)', fill:'rgba(37,99,235,0.12)'},
                {name:'日均', vals: radar.day || [], color:'rgba(16,185,129,0.85)', fill:'rgba(16,185,129,0.12)'},
                {name:'周均', vals: radar.week || [], color:'rgba(234,88,12,0.85)', fill:'rgba(234,88,12,0.10)'},
                {name:'月均', vals: radar.month || [], color:'rgba(148,163,184,0.95)', fill:'rgba(148,163,184,0.08)'}
            ];
            if (labels.length < 5) return;

            const ctx = canvas.getContext('2d');
            const w = canvas.width;
            const h = canvas.height;
            ctx.clearRect(0, 0, w, h);

            const cx = w * 0.36;
            const cy = h * 0.54;
            const radius = Math.min(w, h) * 0.40;
            const n = labels.length || 5;
            const start = -Math.PI / 2;
            const angle = (Math.PI * 2) / n;

            ctx.strokeStyle = '#d1d5db';
            ctx.lineWidth = 1;
            for (let lv = 1; lv <= 5; lv += 1) {
                const r = (radius * lv) / 5;
                ctx.beginPath();
                for (let i = 0; i < n; i += 1) {
                    const a = start + i * angle;
                    const x = cx + Math.cos(a) * r;
                    const y = cy + Math.sin(a) * r;
                    if (i === 0) ctx.moveTo(x, y);
                    else ctx.lineTo(x, y);
                }
                ctx.closePath();
                ctx.stroke();
            }

            ctx.strokeStyle = '#cbd5e1';
            for (let i = 0; i < n; i += 1) {
                const a = start + i * angle;
                ctx.beginPath();
                ctx.moveTo(cx, cy);
                ctx.lineTo(cx + Math.cos(a) * radius, cy + Math.sin(a) * radius);
                ctx.stroke();
                const x = cx + Math.cos(a) * (radius + 18);
                const y = cy + Math.sin(a) * (radius + 18);
                const t = String(labels[i] || '');
                ctx.fillStyle = '#334155';
                ctx.font = '14px sans-serif';
                const m = ctx.measureText(t).width;
                ctx.fillText(t, x - m / 2, y + 5);
            }

            datasets.forEach((ds) => {
                ctx.beginPath();
                for (let i = 0; i < n; i += 1) {
                    const v = Math.max(0, Math.min(100, Number((ds.vals || [])[i] || 0)));
                    const r = radius * v / 100;
                    const a = start + i * angle;
                    const x = cx + Math.cos(a) * r;
                    const y = cy + Math.sin(a) * r;
                    if (i === 0) ctx.moveTo(x, y);
                    else ctx.lineTo(x, y);
                }
                ctx.closePath();
                ctx.fillStyle = ds.fill;
                ctx.strokeStyle = ds.color;
                ctx.lineWidth = 2;
                ctx.fill();
                ctx.stroke();
            });

            const lgx = w - 18;
            const lgy = 20;
            datasets.forEach((ds, idx) => {
                const y = lgy + idx * 20;
                ctx.fillStyle = ds.color;
                ctx.fillRect(lgx - 14, y - 10, 14, 14);
                ctx.fillStyle = '#0f172a';
                ctx.font = '14px sans-serif';
                ctx.textAlign = 'right';
                ctx.fillText(ds.name, lgx - 20, y + 2);
                ctx.textAlign = 'left';
            });
        }

        window.onerror = function(message, source, lineno, colno) {
            try {
                var img = new Image();
                img.src = '/api/client_log?msg=' + encodeURIComponent(String(message || '')) +
                    '&src=' + encodeURIComponent(String(source || '')) +
                    '&line=' + encodeURIComponent(String(lineno || 0)) +
                    '&col=' + encodeURIComponent(String(colno || 0)) +
                    '&t=' + Date.now();
            } catch (e) {}
            return false;
        };
    </script>
</head>
<body>
    <div class="container">
        <!-- 语言选择器 -->
        <div style="text-align: right; margin-bottom: 10px;">
            <label for="lang-select">{{ texts.language }}:</label>
            <select id="lang-select" onchange="changeLanguage(this.value)">
                <option value="zh" {% if lang == 'zh' %}selected{% endif %}>{{ texts.chinese }}</option>
                <option value="en" {% if lang == 'en' %}selected{% endif %}>{{ texts.english }}</option>
                <option value="my" {% if lang == 'my' %}selected{% endif %}>{{ texts.burmese }}</option>
            </select>
        </div>

        <!-- 用户信息 -->
        <div class="user-info">
            {{ texts.login }}: {{ current_user.username }} | 
            {% set role = (current_user.role or '')|lower %}
            {% set can_hr_employees = current_user.has_permission('admin') or role in ['finance', 'stats'] %}
            {% if current_user.has_permission('admin') %}
            <a href="{{ url_for('admin_root', lang=lang) }}">{{ texts.get('admin_overview_link', texts.manage_link) }}</a> | 
            <a href="{{ url_for('admin_alert_center', lang=lang) }}">{{ texts.get('alert_center_link', 'Alert Center') }}</a> | 
            {% endif %}
            {% if can_hr_employees %}
            <a href="{{ url_for('admin_hr_employees', lang=lang) }}">{{ texts.get('employee_mgmt_link', 'Employee Management') }}</a> | 
            {% endif %}
            <a href="{{ url_for('logout') }}" class="logout-btn">{{ texts.logout }}</a>
        </div>

        <h1>🏭 {{ texts.title }}</h1>
        <div id="entry-reminder-strip" class="entry-reminder-strip">
            <strong>{{ texts.entry_reminder_title }}</strong>
            <span id="entry-reminder-text"></span>
        </div>

        {% if alerts %}
        <div class="section" style="border-left:4px solid #dc2626;">
            <h2 style="color:#b91c1c;">⚠️ {{ texts.get('system_health_warn', '预警') }}</h2>
            <div style="display:grid; gap:6px;">
                {% for item in alerts %}
                <div style="padding:8px 10px; border:1px solid #fee2e2; border-radius:8px; background:#fff1f2; font-size:13px;">
                    {{ item.text }}
                </div>
                {% endfor %}
            </div>
        </div>
        {% endif %}

        <!-- 工厂总览 -->
        <div class="section">
            <div style="display:flex; align-items:center; gap:10px; justify-content:space-between; flex-wrap:wrap;">
                <h2 style="margin:0;">📊 {{ texts.factory_overview }}</h2>
                <div style="display:flex; gap:8px; align-items:center; flex-wrap:wrap;">
                    <button type="button" onclick="openDailyReportModal()" style="background:#198754;">{{ texts.view_daily_report }}</button>
                    {% if period_reports.weekly.generated %}
                    <a href="{{ period_reports.weekly.url }}&lang={{ lang }}" style="padding:7px 10px; border-radius:6px; background:#e0f2fe; color:#075985; text-decoration:none; font-size:13px;">周报已生成 {{ period_reports.weekly.key }}</a>
                    {% endif %}
                    {% if period_reports.monthly.generated %}
                    <a href="{{ period_reports.monthly.url }}&lang={{ lang }}" style="padding:7px 10px; border-radius:6px; background:#dcfce7; color:#166534; text-decoration:none; font-size:13px;">月报已生成 {{ period_reports.monthly.key }}</a>
                    {% endif %}
                </div>
            </div>
            <div class="overview-grid">
                <div class="overview-col">
                    <p><strong>{{ texts.stage_stock }}</strong></p>
                    <p>{{ texts.log_stock }} {{ "%.4f"|format(log_stock) }} {{ texts.unit_mt }}</p>
                    <p>{{ texts.current_saw_stock }} {{ saw_stock }} {{ texts.unit_tray }}</p>
                    <p>{{ texts.current_dip_stock }} {{ dip_stock }} {{ texts.unit_tray }}</p>
                    <p>{{ texts.pending_kiln_stock }} {{ sorting_stock }} {{ texts.unit_kiln_tray }}</p>
                    <p>{{ texts.kiln_done_stock_label }} {{ kiln_done_stock }} {{ texts.unit_kiln_tray }}</p>
                    <p>{{ texts.product_stock_label }} {{ product_count }} {{ texts.unit_piece }}（{{ "%.2f"|format(product_m3) }} m³）</p>
                    <p>{{ texts.current_bark_stock }} {{ "%.2f"|format(bark_stock_m3) }} {{ texts.unit_m3 }}</p>
                    <p>{{ texts.current_dust_stock }} {{ dust_bag_stock }} {{ texts.unit_bag }}</p>
                </div>

                <div class="overview-stack">
                    <div class="overview-col">
                        <p><strong>{{ texts.kiln_overview_label }}</strong></p>
                        {% for kiln_id in ['A', 'B', 'C', 'D'] %}
                        <p>
                            {{ kiln_id }} {{ texts.kiln_label }}:
                            <span class="status {{ kiln_status[kiln_id].status }}">{{ kiln_status[kiln_id].status_display }}</span>
                            {% if kiln_status[kiln_id].progress %}
                            - {{ kiln_status[kiln_id].progress }}
                            {% endif %}
                        </p>
                        {% endfor %}
                    </div>

                    <div class="overview-col">
                        <p><strong>{{ texts.logistics_info_label }}</strong></p>
                        <p>{{ texts.shipping_pending }}: {{ shipping_summary['去仰光途中'] or 0 }} {{ texts.unit_order }}</p>
                        <p>{{ texts.shipping_in_transit }}: {{ shipping_summary['仰光仓已到'] or 0 }} {{ texts.unit_order }}</p>
                        <p>{{ texts.shipping_signed }}: {{ shipping_summary['已从仰光出港'] or 0 }} {{ texts.unit_order }}</p>
                        <p>{{ texts.shipping_exception }}: {{ shipping_summary['异常'] or 0 }} {{ texts.unit_order }}</p>
                    </div>
                </div>

                <div class="overview-radar-card">
                    <p><strong>{{ texts.get('overview_eff_radar_label', '流程效率雷达图（当前/日/周/月）') }}</strong></p>
                    <div class="overview-radar-wrap">
                        <canvas id="overview-radar-canvas" width="400" height="240"></canvas>
                    </div>
                    <p class="overview-radar-note">{{ (overview_radar_labels or [])|join(' / ') }}</p>
                </div>
            </div>
            <div style="margin-top:10px; padding:10px; border:1px solid #dbe3ef; border-radius:8px; background:#f8fbff;">
                <p style="margin:0 0 6px;"><strong>🩺 {{ texts.get('system_health', '系统健康') }}</strong>
                    <span class="status {{ 'ready' if system_health.status == 'healthy' else 'unloading' }}">
                        {{ texts.get('system_health_ok', '正常') if system_health.status == 'healthy' else texts.get('system_health_warn', '告警') }}
                    </span>
                </p>
                <p style="margin:4px 0;">{{ texts.get('system_health_db', '数据库') }}: {{ texts.get('system_health_state_ok', 'OK') if system_health.db_exists else texts.get('system_health_state_missing', 'MISSING') }} | {{ system_health.db_size_mb }} MB</p>
                <p style="margin:4px 0;">{{ texts.get('system_health_migration', '迁移') }}: {{ texts.get('system_health_state_done', 'DONE') if system_health.migration_done else texts.get('system_health_state_pending', 'PENDING') }} | {{ texts.get('system_health_users', '用户数') }}: {{ system_health.user_total }}</p>
                <p style="margin:4px 0;">{{ texts.get('system_health_backup', '最近备份') }}: {{ system_health.latest_backup_at }}{% if system_health.latest_backup_file %} ({{ system_health.latest_backup_file }}){% endif %}</p>
                <p style="margin:4px 0;">{{ texts.get('system_health_web_errors_24h', 'Web错误(24h)') }}: {{ system_health.web_errors_24h }}</p>
                {% if system_health.weak_password_user_count > 0 %}
                <p style="margin:4px 0; color:#b91c1c;">{{ texts.get('system_health_weak_users', '弱口令用户') }}: {{ system_health.weak_password_user_count }}</p>
                {% endif %}
                {% if system_health.issues %}
                <p style="margin:4px 0; color:#b91c1c;">{{ texts.get('system_health_issues', '问题') }}: {{ system_health.issues|join(' / ') }}</p>
                {% endif %}
            </div>
        </div>

        <div class="pair-grid">
            <!-- 原木入库环节 -->
            <div class="section">
                <h2>{{ texts.log_section }}</h2>
                <p>{{ texts.log_stock }} {{ "%.4f"|format(log_stock) }} {{ texts.unit_mt }}
                {% if current_user.has_permission('admin') %}
                    <button type="button" class="edit-mini-btn" onclick="openStockAdjustModal('log', '{{ '%.4f'|format(log_stock) }}')">{{ texts.edit_btn }}</button>
                {% endif %}
                </p>
                <form method="POST" action="/submit_log_entry?lang={{ lang }}" onsubmit="return beforeSubmitLogEntryForm()">
                    <div class="form-group">
                        <button type="button" onclick="openLogEntryModal()">{{ texts.log_entry_modal_btn }}</button>
                        {% if current_user.has_permission('export') %}
                        <button type="button" onclick="openLogEntryListModal()" style="background:#0d6efd;">{{ texts.log_view_history }}</button>
                        {% endif %}
                    </div>
                    <div class="form-group">
                        <label>{{ texts.driver_name }}</label>
                        <input type="text" id="log_driver_preview" readonly style="background:#f8f9fa;">
                    </div>
                    <div class="form-group">
                        <label>{{ texts.truck_number }}</label>
                        <input type="text" id="log_truck_preview" readonly style="background:#f8f9fa;">
                    </div>
                    <div class="form-group">
                        <label>{{ texts.log_amount }}</label>
                        <input type="number" id="log_amount_preview" readonly style="background:#f8f9fa;" step="0.0001"> {{ texts.unit_mt }}
                    </div>
                    <input type="hidden" name="truck_number" id="log_truck_hidden">
                    <input type="hidden" name="driver_name" id="log_driver_hidden">
                    <input type="hidden" name="log_amount" id="log_amount_hidden">
                    <input type="hidden" name="log_size_range" id="log_size_range_hidden">
                    <input type="hidden" name="log_price_per_mt" id="log_price_hidden">
                    <input type="hidden" name="log_price_rules_payload" id="log_price_rules_payload_hidden">
                    <input type="hidden" name="log_details_payload" id="log_details_payload_hidden">
                    <button type="submit" id="submit-log-entry-btn">{{ texts.submit_log }}</button>
                </form>
            </div>

            <!-- 锯解环节 -->
            <div class="section">
                <h2>🪚 {{ texts.saw_section }}</h2>
                <p>{{ texts.current_log_stock }} {{ "%.4f"|format(log_stock) }} {{ texts.unit_mt }}</p>
                <p>{{ texts.current_saw_stock }} {{ saw_stock }} {{ texts.unit_tray }}
                {% if current_user.has_permission('admin') %}
                    <button type="button" class="edit-mini-btn" onclick="openStockAdjustModal('saw', '{{ saw_stock }}')">{{ texts.edit_btn }}</button>
                {% endif %}
                </p>
                <form method="POST" action="/submit_saw?lang={{ lang }}">
                    <div class="form-group">
                        <div style="display:flex; gap:8px; align-items:center; flex-wrap:wrap;">
                            <label style="margin:0; white-space:nowrap;">{{ texts.saw_daily }}</label>
                            <input type="number" id="saw_tm_input" name="saw_tm" step="0.0001" placeholder="{{ texts.placeholder_saw_mt }}" required style="width:160px;">
                            <span style="white-space:nowrap;">{{ texts.unit_mt }}</span>
                            <button type="button" onclick="openSawMachineModal()">{{ texts.saw_machine_modal_btn }}</button>
                        </div>
                    </div>
                    <div class="form-group">
                        <label>{{ texts.saw_products }}</label>
                        <input type="number" id="saw_trays_input" name="saw_trays" placeholder="{{ texts.placeholder_tray }}" required style="width:160px;"> {{ texts.unit_tray }}
                    </div>
                    <div class="form-group">
                        <label>{{ texts.saw_bark }}</label>
                        <input type="number" id="bark_m3_input" name="bark_m3" step="0.01" min="0" placeholder="{{ texts.placeholder_m3 }}" required style="width:160px;"> {{ texts.unit_m3 }}
                    </div>
                    <div class="form-group">
                        <label>{{ texts.saw_dust }}</label>
                        <input type="number" id="dust_bags_input" name="dust_bags" min="0" placeholder="{{ texts.placeholder_bag }}" required style="width:160px;"> {{ texts.unit_bag }}
                    </div>
                    <input type="hidden" id="saw_machine_payload" name="saw_machine_payload" value="">
                    <button type="submit">{{ texts.submit_saw }}</button>
                </form>
            </div>
        </div>

        <div class="pair-grid">
            <!-- 药浸环节 -->
            <div class="section">
                <h2>{{ texts.dip_section }}</h2>
                <p>{{ texts.current_saw_stock }} {{ saw_stock }} {{ texts.unit_tray }}</p>
                <p>{{ texts.current_dip_chem_stock }} {{ "%.2f"|format(dip_chem_bag_stock) }} {{ texts.unit_bag }}
                {% if current_user.has_permission('admin') %}
                    <button type="button" class="edit-mini-btn" onclick="openStockAdjustModal('dip_chem', '{{ '%.2f'|format(dip_chem_bag_stock) }}')">{{ texts.edit_btn }}</button>
                {% endif %}
                </p>
                <p>{{ texts.current_dip_additive_stock }} {{ "%.2f"|format(dip_additive_kg_stock) }} {{ texts.unit_kg }}</p>
                <form method="POST" action="/submit_dip?lang={{ lang }}">
                    <div class="form-group">
                        <label>{{ texts.dip_daily }}</label>
                        <input type="number" name="dip_cans" min="0" placeholder="{{ texts.placeholder_can }}"> {{ texts.unit_can }}
                    </div>
                    <div class="form-group">
                        <label>{{ texts.dip_trays }}</label>
                        <input type="number" name="dip_trays" min="0" placeholder="{{ texts.placeholder_tray }}"> {{ texts.unit_tray }}
                    </div>
                    <div class="form-group">
                        <label>{{ texts.dip_chemicals }}</label>
                        <input type="number" name="dip_chemicals" step="0.01" min="0" placeholder="{{ texts.placeholder_bag }}"> {{ texts.unit_bag }}
                    </div>
                    <div style="margin:8px 0 6px; border-top:1px dashed #d1d5db; padding-top:6px; color:#6b7280; font-size:12px;">
                        {{ texts.dip_inbound_split }}
                    </div>
                    <div class="form-group">
                        <label>{{ texts.dip_chem_inbound }}</label>
                        <input type="number" name="dip_chem_inbound" step="0.01" min="0" value="0" placeholder="{{ texts.placeholder_bag }}"> {{ texts.unit_bag }}
                    </div>
                    <div class="form-group">
                        <label>{{ texts.dip_additive_inbound }}</label>
                        <input type="number" name="dip_additive_inbound" step="0.01" min="0" value="0" placeholder="{{ texts.unit_kg }}"> {{ texts.unit_kg }}
                    </div>
                    <button type="submit">{{ texts.submit_dip }}</button>
                </form>
            </div>

            <!-- 拣选环节 -->
            <div class="section">
                <h2>{{ texts.sort_section }}</h2>
                <p>{{ texts.current_dip_stock }} {{ dip_stock }} {{ texts.unit_tray }}
                {% if current_user.has_permission('admin') %}
                    <button type="button" class="edit-mini-btn" onclick="openStockAdjustModal('dip', '{{ dip_stock }}')">{{ texts.edit_btn }}</button>
                {% endif %}
                </p>
                <form method="POST" action="/submit_sort?lang={{ lang }}" onsubmit="return beforeSubmitSortForm()">
                    <div class="form-group">
                        <label>{{ texts.sort_daily }}</label>
                        <input type="number" id="sort_trays_input" name="sort_trays" placeholder="{{ texts.placeholder_tray }}" required> {{ texts.unit_tray }}
                        <div id="sort-missing-bubble" class="field-reminder-bubble">{{ texts.sort_missing_bubble }}</div>
                    </div>
                    <input type="hidden" id="sorted_kiln_trays" name="sorted_kiln_trays">
                    <div style="display:flex; gap:8px; flex-wrap:wrap;">
                        <button type="button" onclick="openSortTrayModal()">{{ texts.open_sort_tray_modal }}</button>
                        <button type="submit">{{ texts.submit_sort }}</button>
                        <span id="sort-staged-indicator" style="display:none; align-self:center; font-size:12px; color:#666;">{{ texts.sort_staged_count }} 0 {{ texts.unit_kiln_tray }}</span>
                    </div>
                </form>
            </div>
        </div>

        <!-- 窑环节 -->
        <div class="section">
            <h2>{{ texts.kiln_section }}</h2>
            <p>{{ texts.pending_kiln_stock }} {{ sorting_stock }} {{ texts.unit_kiln_tray }}
                <button type="button" class="edit-mini-btn" onclick="openPendingTrayModal()">{{ texts.view_pending_trays }}</button>
            {% if current_user.has_permission('admin') %}
                <button type="button" class="edit-mini-btn" onclick="openStockAdjustModal('sort', '{{ sorting_stock }}')">{{ texts.edit_btn }}</button>
            {% endif %}
            </p>
            <div class="kiln-grid">
                {% for kiln_id in ['A', 'B', 'C', 'D'] %}
                <div class="kiln">
                    <h3>{{ kiln_id }}</h3>
                    <p>{{ texts.status }}: <span class="status {{ kiln_status[kiln_id].status }}">{{ kiln_status[kiln_id].status_display }}</span>
                    {% if current_user.has_permission('admin') %}
                        <button type="button" class="edit-mini-btn" onclick="openKilnAdjustModal('{{ kiln_id }}','{{ kiln_status[kiln_id].status }}','{{ kiln_status[kiln_id].elapsed_hours or 0 }}','{{ kiln_status[kiln_id].remaining_hours or 0 }}','{{ kiln_status[kiln_id].total_trays or 0 }}','{{ kiln_status[kiln_id].remaining_trays or 0 }}')">{{ texts.edit_btn }}</button>
                    {% endif %}
                    </p>
                    {% if kiln_status[kiln_id].progress %}
                    <p>{{ kiln_status[kiln_id].progress }}</p>
                    {% endif %}

                    <!-- 操作按钮 -->
                    <div class="form-group" style="display: flex; gap: 8px; margin-bottom: 15px;">
                        <button type="button" onclick="startDrying('{{ kiln_id }}', {{ kiln_status[kiln_id].remaining_kiln_trays or 0 }})" style="background: #dc3545; color: white; padding: 10px 0; border: none; border-radius: 4px; cursor: pointer; width: 64px; font-size: 15px; line-height: 1.2;">{{ texts.start_dry }}</button>
                        <button type="button" onclick="startUnloading('{{ kiln_id }}', {{ kiln_status[kiln_id].elapsed_hours or 0 }}, '{{ kiln_status[kiln_id].status }}', {{ kiln_status[kiln_id].remaining_kiln_trays or 0 }})" style="background: #ffc107; color: black; padding: 10px 0; border: none; border-radius: 4px; cursor: pointer; width: 64px; font-size: 15px; line-height: 1.2;">{{ texts.start_unload }}</button>
                        <button type="button" onclick="completeKiln('{{ kiln_id }}', {{ kiln_status[kiln_id].remaining_kiln_trays or 0 }})" style="background: #28a745; color: white; padding: 10px 0; border: none; border-radius: 4px; cursor: pointer; width: 64px; font-size: 15px; line-height: 1.2;">{{ texts.complete }}</button>
                        <button type="button" onclick="openKilnTrayModal('{{ kiln_id }}')" style="background: #6f42c1; color: white; padding: 10px 0; border: none; border-radius: 4px; cursor: pointer; width: 84px; font-size: 15px; line-height: 1.2;">{{ texts.view_kiln_trays }}</button>
                    </div>

                    <div class="form-group" style="margin-top: 15px; display:flex; gap:8px; flex-wrap:wrap;">
                        <button type="button" onclick="openTrayPickerModal('load', '{{ kiln_id }}', {{ kiln_status[kiln_id].remaining_kiln_trays or 0 }})" style="background: #007bff; color: white; padding: 12px 0; border: none; border-radius: 4px; cursor: pointer; width: 146px; font-size: 15px; line-height: 1.2; text-align: center;">{{ texts.pick_load }}</button>
                        <button type="button" onclick="openTrayPickerModal('unload', '{{ kiln_id }}')" style="background: #17a2b8; color: white; padding: 12px 0; border: none; border-radius: 4px; cursor: pointer; width: 146px; font-size: 15px; line-height: 1.2; text-align: center;">{{ texts.pick_unload }}</button>
                    </div>
                </div>
                {% endfor %}
            </div>
        </div>

        <!-- 二选环节 -->
        <div class="section">
            <h2>{{ texts.secondary_section }}</h2>
            <p>{{ texts.kiln_done_stock_label }} {{ kiln_done_stock }} {{ texts.unit_kiln_tray }}
            {% if current_user.has_permission('admin') %}
                <button type="button" class="edit-mini-btn" onclick="openStockAdjustModal('kiln_done', '{{ kiln_done_stock }}')">{{ texts.edit_btn }}</button>
            {% endif %}
            </p>
            <form method="POST" action="/submit_secondary_sort?lang={{ lang }}" onsubmit="return beforeSubmitSecondarySortForm()">
                <div class="form-group">
                    <label>{{ texts.secondary_trays }}</label>
                    <input type="text" id="secondary_sort_trays" name="secondary_sort_trays" placeholder="{{ texts.placeholder_secondary_ids }}" required>
                    <div id="secondary-missing-bubble" class="field-reminder-bubble">{{ texts.secondary_sort_missing_bubble }}</div>
                </div>
                <div class="form-group">
                    <label>{{ texts.secondary_waste_segment_output }}</label>
                    <input type="number" name="waste_segment_bags" min="0" placeholder="{{ texts.placeholder_bag }}" value="0" required> {{ texts.unit_bag }}
                </div>
                <div style="display:flex; gap:8px; flex-wrap:wrap;">
                    <button type="button" onclick="openSecondaryProductModal()">{{ texts.add_product_btn }}</button>
                    <button type="submit">{{ texts.submit_secondary }}</button>
                </div>
            </form>
            <form id="secondary-products-form" method="POST" action="/submit_secondary_products?lang={{ lang }}" style="display:none;">
                <input type="hidden" id="finished_product_trays" name="finished_product_trays">
                <input type="hidden" id="confirm_missing_secondary_sort" name="confirm_missing_secondary_sort" value="0">
            </form>
        </div>

        <div class="pair-grid">
            <div class="section">
                <h2>{{ texts.finished_zone }}</h2>
                <p>{{ texts.finished_total_count }} {{ product_count }} {{ texts.unit_piece }}</p>
                <div class="summary-grid">
                    <div class="summary-card pending">
                        <strong>{{ texts.shipping_pending }}</strong>
                        <span>{{ shipping_summary['去仰光途中'] or 0 }}</span>
                    </div>
                    <div class="summary-card transit">
                        <strong>{{ texts.shipping_in_transit }}</strong>
                        <span>{{ shipping_summary['仰光仓已到'] or 0 }}</span>
                    </div>
                    <div class="summary-card signed">
                        <strong>{{ texts.shipping_signed }}</strong>
                        <span>{{ shipping_summary['已从仰光出港'] or 0 }}</span>
                    </div>
                    <div class="summary-card exception">
                        <strong>{{ texts.shipping_exception }}</strong>
                        <span>{{ shipping_summary['异常'] or 0 }}</span>
                    </div>
                </div>
                <div style="display:flex; gap:10px; flex-wrap:wrap;">
                    <button type="button" onclick="openFinishedInventoryModal()">{{ texts.view_finished_inventory }}</button>
                    <button type="button" onclick="openCreateShipmentModal()" style="background:#0d6efd;">{{ texts.create_shipment }}</button>
                    <button type="button" onclick="openShippingBoardModal()" style="background:#6c757d;">{{ texts.view_logistics_board }}</button>
                </div>
            </div>

            <div class="section">
                <h2>{{ texts.byproduct_section }}</h2>
                <p>
                    {{ texts.current_bark_stock }} {{ "%.2f"|format(bark_stock_m3) }} {{ texts.unit_m3 }}
                    {% if current_user.has_permission('admin') %}
                    <button
                        type="button"
                        class="edit-mini-btn"
                        onclick="openByproductAdjustModal('{{ '%.0f'|format(bark_stock_ks) }}', '{{ dust_bag_stock }}', '{{ waste_segment_bag_stock }}')"
                    >{{ texts.edit_btn }}</button>
                    {% endif %}
                </p>
                <p>{{ texts.current_dust_stock }} {{ dust_bag_stock }} {{ texts.unit_bag }}
                {% if current_user.has_permission('admin') %}
                    <button
                        type="button"
                        class="edit-mini-btn"
                        onclick="openByproductAdjustModal('{{ '%.0f'|format(bark_stock_ks) }}', '{{ dust_bag_stock }}', '{{ waste_segment_bag_stock }}')"
                    >{{ texts.edit_btn }}</button>
                {% endif %}
                </p>
                <p>
                    {{ texts.current_waste_segment_stock }} {{ waste_segment_bag_stock }} {{ texts.unit_bag }}
                    {% if current_user.has_permission('admin') %}
                    <button
                        type="button"
                        class="edit-mini-btn"
                        onclick="openByproductAdjustModal('{{ '%.0f'|format(bark_stock_ks) }}', '{{ dust_bag_stock }}', '{{ waste_segment_bag_stock }}')"
                    >{{ texts.edit_btn }}</button>
                    {% endif %}
                </p>
                <form method="POST" action="/submit_byproduct_sale?lang={{ lang }}">
                    <div class="form-group">
                        <label>{{ texts.sell_dust }}</label>
                        <input type="number" name="sell_dust_bags" min="0" placeholder="{{ texts.placeholder_bag }}" required> {{ texts.unit_bag }}
                    </div>
                    <div class="form-group">
                        <label>{{ texts.sell_bark }}</label>
                        <input type="number" name="sell_bark_ks" min="0" placeholder="{{ texts.placeholder_ks }}" required> {{ texts.unit_ks }}
                    </div>
                    <div class="form-group">
                        <label>{{ texts.sell_waste_segment }}</label>
                        <input type="number" name="sell_waste_segment_bags" min="0" placeholder="{{ texts.placeholder_bag }}" required> {{ texts.unit_bag }}
                    </div>
                    <button type="submit">{{ texts.submit_sale }}</button>
                </form>
                {% if current_user.has_permission('admin') %}
                <form method="POST" action="/admin/adjust_bark_sale?lang={{ lang }}" style="margin-top:10px; padding-top:10px; border-top:1px dashed #ddd;">
                    <div class="form-group">
                        <label>{{ texts.admin_adjust_bark_sale }}</label>
                        <input type="number" name="bark_sale_delta_ks" step="1" placeholder="{{ texts.admin_adjust_bark_sale_placeholder }}" required> {{ texts.unit_ks }}
                    </div>
                    <button type="submit" style="background:#6f42c1;">{{ texts.admin_adjust_bark_sale_btn }}</button>
                    <p style="margin:8px 0 0; color:#6b7280; font-size:12px;">{{ texts.admin_adjust_bark_sale_hint }}</p>
                </form>
                {% endif %}
            </div>
        </div>

        {% if result %}
        <div id="result-toast" class="toast-msg{% if error %} error{% endif %}">
            <strong>{{ texts.result_label }}</strong><br>
            <span>{{ result }}</span>
        </div>
        {% endif %}

        <div id="kiln-tray-modal" class="modal-mask">
            <div class="modal-box">
                <h3 id="kiln-modal-title">{{ texts.kiln_tray_detail_title }}</h3>
                <table class="tray-grid">
                    <thead>
                        <tr>
                            <th>{{ texts.tray_id_col }}</th>
                            <th>{{ texts.spec_col }}</th>
                            <th>{{ texts.count_col }}</th>
                            <th>{{ texts.actions }}</th>
                        </tr>
                    </thead>
                    <tbody id="kiln-tray-body"></tbody>
                </table>
                <div style="display:flex; gap:8px;">
                    {% if current_user.has_permission('admin') %}
                    <button type="button" onclick="addKilnTrayRow()">{{ texts.add_row_btn }}</button>
                    <button type="button" onclick="saveKilnTrays()">{{ texts.save_changes_btn }}</button>
                    {% endif %}
                    <button type="button" onclick="closeKilnTrayModal()">{{ texts.close_btn }}</button>
                </div>
            </div>
        </div>
        <div id="stock-adjust-modal" class="modal-mask">
            <div class="modal-box" style="width:min(520px, 92vw);">
                <h3>{{ texts.admin_adjust_title }}</h3>
                <form method="POST" action="/admin/adjust_stock?lang={{ lang }}">
                    <input type="hidden" id="adjust_section" name="section">
                    <div class="form-group" id="adjust_value_row">
                        <label>{{ texts.admin_adjust_stock }}</label>
                        <input type="number" id="adjust_value" name="value" step="0.0001" min="0">
                    </div>
                    <div id="adjust_byproduct_rows" style="display:none;">
                        <div class="form-group">
                            <label>{{ texts.current_bark_stock }}</label>
                            <input type="number" id="adjust_bark_stock_ks" name="bark_stock_ks" min="0">
                        </div>
                        <div class="form-group">
                            <label>{{ texts.current_dust_stock }}</label>
                            <input type="number" id="adjust_dust_bag_stock" name="dust_bag_stock" min="0">
                        </div>
                        <div class="form-group">
                            <label>{{ texts.current_waste_segment_stock }}</label>
                            <input type="number" id="adjust_waste_segment_bag_stock" name="waste_segment_bag_stock" min="0">
                        </div>
                    </div>
                    <div style="display:flex; gap:8px;">
                        <button type="submit">{{ texts.admin_adjust_btn }}</button>
                        <button type="button" onclick="closeStockAdjustModal()">{{ texts.close_btn }}</button>
                    </div>
                </form>
            </div>
        </div>
        <div id="kiln-adjust-modal" class="modal-mask">
            <div class="modal-box" style="width:min(560px, 92vw);">
                <h3>{{ texts.admin_kiln_status_edit }}</h3>
                <form id="kiln-adjust-form" method="POST" action="/admin/adjust_kiln?lang={{ lang }}" onsubmit="return submitKilnAdjust(event)">
                    <input type="hidden" id="kiln_adjust_id" name="kiln_id">
                    <div class="form-group">
                        <label>{{ texts.admin_kiln_status_edit }}</label>
                        <select id="kiln_adjust_status" name="status" style="padding:8px; border:1px solid #ddd; border-radius:4px;">
                            <option value="empty">{{ texts.empty }}</option>
                            <option value="loading">{{ texts.loading }}</option>
                            <option value="drying">{{ texts.drying }}</option>
                            <option value="unloading">{{ texts.unloading }}</option>
                            <option value="ready">{{ texts.ready }}</option>
                            <option value="completed">{{ texts.completed }}</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>{{ texts.admin_elapsed_hours }}</label>
                        <input type="number" id="kiln_adjust_elapsed" name="elapsed_hours" min="0">
                    </div>
                    <div class="form-group">
                        <label>{{ texts.admin_remaining_hours }}</label>
                        <input type="number" id="kiln_adjust_remaining" name="remaining_hours" min="0">
                    </div>
                    <div class="form-group">
                        <label>{{ texts.admin_total_trays }}</label>
                        <input type="number" id="kiln_adjust_total" name="total_trays" min="0">
                    </div>
                    <div class="form-group">
                        <label>{{ texts.admin_remaining_trays }}</label>
                        <input type="number" id="kiln_adjust_left" name="remaining_trays" min="0">
                    </div>
                    <div style="display:flex; gap:8px;">
                        <button type="submit">{{ texts.admin_adjust_kiln_btn }}</button>
                        <button type="button" onclick="closeKilnAdjustModal()">{{ texts.close_btn }}</button>
                    </div>
                </form>
            </div>
        </div>
        <div id="secondary-product-modal" class="modal-mask">
            <div class="modal-box" style="width:min(960px, 98vw);">
                <h3>{{ texts.secondary_product_modal_title }}</h3>
                <table class="tray-grid">
                    <thead>
                        <tr>
                            <th>{{ texts.product_id_label }}</th>
                            <th>{{ texts.quantity_label }}</th>
                            <th>{{ texts.grade_label }}</th>
                            <th>{{ texts.spec_col }}</th>
                            <th>m³</th>
                            <th style="width:140px;">{{ texts.actions }}</th>
                        </tr>
                    </thead>
                    <tbody id="secondary-product-body"></tbody>
                </table>
                <div style="display:flex; gap:8px; flex-wrap:wrap;">
                    <button type="button" onclick="addSecondaryProductRow()">{{ texts.add_row_btn }}</button>
                    <button type="button" onclick="saveSecondaryAllRows()">{{ texts.save_all_rows_btn }}</button>
                    <button type="button" onclick="closeSecondaryProductModal()">{{ texts.close_btn }}</button>
                </div>
            </div>
        </div>
        <div id="finished-inventory-modal" class="modal-mask">
            <div class="modal-box" style="width:min(1180px, 99vw);">
                <h3>{{ texts.finished_inventory_title }}</h3>
                <table class="tray-grid">
                    <thead>
                        <tr>
                            <th>{{ texts.product_id_label }}</th>
                            <th>D</th>
                            <th>W</th>
                            <th>L</th>
                            <th>{{ texts.quantity_label }}</th>
                            <th>m³</th>
                            <th>{{ texts.weight_label }}</th>
                            <th>{{ texts.grade_label }}</th>
                            <th>{{ texts.status_label }}</th>
                            <th>{{ texts.spec_col }}</th>
                            {% if current_user.has_permission('admin') %}
                            <th style="width:84px;">{{ texts.actions }}</th>
                            {% endif %}
                        </tr>
                        <tr>
                            <th></th>
                            <th>
                                <select id="fi-filter-d" style="width:100%; padding:6px; border:1px solid #ddd; border-radius:4px;" onchange="applyFinishedInventoryFilters()"></select>
                            </th>
                            <th>
                                <select id="fi-filter-w" style="width:100%; padding:6px; border:1px solid #ddd; border-radius:4px;" onchange="applyFinishedInventoryFilters()"></select>
                            </th>
                            <th>
                                <select id="fi-filter-l" style="width:100%; padding:6px; border:1px solid #ddd; border-radius:4px;" onchange="applyFinishedInventoryFilters()"></select>
                            </th>
                            <th>
                                <select id="fi-filter-pcs" style="width:100%; padding:6px; border:1px solid #ddd; border-radius:4px;" onchange="applyFinishedInventoryFilters()"></select>
                            </th>
                            <th>
                                <select id="fi-filter-m3" style="width:100%; padding:6px; border:1px solid #ddd; border-radius:4px;" onchange="applyFinishedInventoryFilters()"></select>
                            </th>
                            <th></th>
                            <th>
                                <select id="fi-filter-grade" style="width:100%; padding:6px; border:1px solid #ddd; border-radius:4px;" onchange="applyFinishedInventoryFilters()"></select>
                            </th>
                            <th></th>
                            <th></th>
                            {% if current_user.has_permission('admin') %}
                            <th></th>
                            {% endif %}
                        </tr>
                    </thead>
                    <tbody id="finished-inventory-body"></tbody>
                </table>
                <div style="display:flex; gap:8px; flex-wrap:wrap;">
                    {% if current_user.has_permission('export') %}
                    <button type="button" id="finished-inventory-export" onclick="downloadFinishedInventory()" style="background:#007bff; color:white; text-decoration:none; padding:8px 12px; border-radius:4px;">{{ texts.export_current_query }}</button>
                    <button type="button" id="finished-label-export" onclick="downloadFinishedLabels()" style="background:#198754; color:white; text-decoration:none; padding:8px 12px; border-radius:4px;">{{ texts.export_label_sheet }}</button>
                    {% endif %}
                    <button type="button" onclick="closeFinishedInventoryModal()" style="background:#6c757d;">{{ texts.close_btn }}</button>
                </div>
            </div>
        </div>
        <div id="create-shipment-modal" class="modal-mask">
            <div class="modal-box" style="width:min(1100px, 98vw);">
                <h3>{{ texts.shipment_create_title }}</h3>
                <div class="form-group">
                    <label>{{ texts.customer_label }}</label>
                    <input type="text" id="shipment-customer" style="width:240px;">
                </div>
                <div class="form-group">
                    <label>{{ texts.destination_label }}</label>
                    <input type="text" id="shipment-destination" style="width:240px;" value="仰光仓">
                </div>
                <div class="form-group">
                    <label>{{ texts.departure_at_label }}</label>
                    <input type="datetime-local" id="shipment-departure-at" style="width:240px;">
                </div>
                <div class="form-group">
                    <label>{{ texts.vehicle_no_label }}</label>
                    <input type="text" id="shipment-vehicle-no" style="width:240px;">
                </div>
                <div class="form-group">
                    <label>{{ texts.driver_label }}</label>
                    <input type="text" id="shipment-driver-name" style="width:240px;">
                </div>
                 <div class="form-group">
                    <label>{{ texts.eta_hours_label }}</label>
                    <input type="number" id="shipment-eta-hours" style="width:240px;" value="36" min="1">
                </div>
                <div class="form-group">
                    <label>{{ texts.remark_label }}</label>
                    <input type="text" id="shipment-remark" style="width:min(560px, 100%);">
                </div>
                <p><strong>{{ texts.shipment_selected_count }}</strong><span id="shipment-selected-count">0</span></p>
                <p><strong>{{ texts.select_products }}</strong></p>
                <div id="shipment-product-picker" class="shipment-pick-grid"></div>
                <div style="display:flex; gap:8px; flex-wrap:wrap; margin-top:12px;">
                    {% if current_user.has_permission('export') %}
                    <button type="button" onclick="exportSelectedShipmentDetails()" style="background:#198754;">{{ texts.export_selected_shipment_details }}</button>
                    {% endif %}
                    <button type="button" onclick="createShipment()" style="background:#0d6efd;">{{ texts.create_shipment }}</button>
                    <button type="button" onclick="closeCreateShipmentModal()">{{ texts.close_btn }}</button>
                </div>
            </div>
        </div>
        <div id="shipping-board-modal" class="modal-mask">
            <div class="modal-box" style="width:min(1240px, 99vw);">
                <div style="display:flex; justify-content:space-between; align-items:center; gap:12px; flex-wrap:wrap;">
                    <h3 style="margin:0;">{{ texts.shipment_status_title }}</h3>
                    <button type="button" onclick="loadShippingBoard()" style="background:#6c757d;">{{ texts.refresh_btn }}</button>
                </div>
                <table class="tray-grid" style="margin-top:14px;">
                    <thead>
                        <tr>
                            <th>{{ texts.shipment_no }}</th>
                            <th>{{ texts.customer_label }}</th>
                            <th>{{ texts.destination_label }}</th>
                            <th>{{ texts.departure_at_label }}</th>
                            <th>{{ texts.vehicle_no_label }}</th>
                            <th>{{ texts.driver_label }}</th>
                            <th>{{ texts.eta_hours_label }}</th>
                            <th>{{ texts.quantity_label }}</th>
                            <th>m³</th>
                            <th>{{ texts.route_stage_label }}</th>
                            <th>{{ texts.created_at }}</th>
                            <th>{{ texts.status_actions }}</th>
                        </tr>
                    </thead>
                    <tbody id="shipping-board-body"></tbody>
                </table>
                <div style="display:flex; gap:8px; flex-wrap:wrap;">
                    <button type="button" onclick="closeShippingBoardModal()">{{ texts.close_btn }}</button>
                </div>
            </div>
        </div>
        <div id="daily-report-modal" class="modal-mask">
            <div class="modal-box">
                <div style="display:flex; justify-content:space-between; align-items:center; gap:8px; flex-wrap:wrap;">
                    <h3 style="margin:0;">{{ texts.daily_report_title }}</h3>
                    <div style="display:flex; gap:8px; align-items:center;">
                        <label>{{ texts.report_date_label }}</label>
                        <input type="date" id="daily-report-date" style="padding:6px; border:1px solid #ddd; border-radius:4px;">
                        <button type="button" onclick="loadDailyReportData()">{{ texts.query_btn }}</button>
                        {% if current_user.has_permission('export') %}
                        <button type="button" onclick="exportDailyReportFromModal()" style="background:#0d6efd;">{{ texts.export_daily_report }}</button>
                        {% endif %}
                        <button type="button" onclick="closeDailyReportModal()" style="background:#6c757d;">{{ texts.close_btn }}</button>
                    </div>
                </div>
                <p id="daily-report-range" style="margin:8px 0 4px; color:#6b7280; font-size:12px;"></p>
                <p id="daily-report-note" style="margin:0 0 8px; color:#6b7280; font-size:12px;"></p>
                <div class="report-mini-grid">
                    <div class="report-mini-card">
                        <h4>{{ texts.report_summary }}</h4>
                        <table class="report-mini-table"><tbody id="daily-report-summary-body"></tbody></table>
                    </div>
                    <div class="report-mini-card">
                        <h4>{{ texts.report_inventory_snapshot }}</h4>
                        <table class="report-mini-table"><tbody id="daily-report-inv-body"></tbody></table>
                    </div>
                    <div class="report-mini-card">
                        <h4>{{ texts.report_kiln_status }}</h4>
                        <table class="report-mini-table"><tbody id="daily-report-kiln-body"></tbody></table>
                    </div>
                    <div class="report-mini-card">
                        <h4>{{ texts.report_breakdown_count }}</h4>
                        <table class="report-mini-table"><tbody id="daily-report-count-body"></tbody></table>
                    </div>
                </div>
            </div>
        </div>
        <div id="log-entry-modal" class="modal-mask">
            <div class="modal-box" style="width:min(980px, 97vw);">
                <div style="display:flex; justify-content:space-between; align-items:center; gap:8px; flex-wrap:wrap;">
                    <h3 style="margin:0;">{{ texts.log_entry_modal_title }}</h3>
                </div>
                <div style="display:grid; grid-template-columns: 0.74fr 1.46fr; gap:10px; margin-top:10px;">
                    <div>
                        <div class="form-group">
                            <label>{{ texts.driver_name }}</label>
                            <input type="text" id="log-modal-driver" placeholder="{{ texts.placeholder_driver }}" style="width:220px;">
                        </div>
                        <div class="form-group">
                            <label>{{ texts.truck_number }}</label>
                            <input type="text" id="log-modal-truck" placeholder="{{ texts.placeholder_truck }}" style="width:220px;">
                        </div>
                        <table class="tray-grid" style="margin-top:6px;">
                            <thead>
                                <tr>
                                    <th style="width:60px; text-align:center; white-space:nowrap;">阶段</th>
                                    <th style="width:90px; white-space:nowrap;">区间</th>
                                    <th style="width:102px; white-space:nowrap;">价格(Ks/MT)</th>
                                </tr>
                            </thead>
                            <tbody id="log-price-rules-body"></tbody>
                        </table>
                        <table class="tray-grid" style="margin-top:8px;">
                            <thead>
                                <tr>
                                    <th>区间</th>
                                    <th>MT</th>
                                    <th>金额(Ks)</th>
                                    <th>数量</th>
                                </tr>
                            </thead>
                            <tbody id="log-entry-summary-body"></tbody>
                        </table>
                        <p style="margin:4px 0; font-size:12px; color:#6b7280;">{{ texts.log_size_hint }}</p>
                    </div>
                    <div>
                        <table class="tray-grid">
                            <thead>
                                <tr>
                                    <th>{{ texts.saw_log_size_label }}</th>
                                    <th>{{ texts.saw_log_qty_label }}</th>
                                    <th>{{ texts.saw_log_length_label }}</th>
                                    <th>{{ texts.saw_log_total_label }}</th>
                                    <th>{{ texts.actions }}</th>
                                </tr>
                            </thead>
                            <tbody id="log-entry-detail-body"></tbody>
                        </table>
                        <div style="margin-top:6px; font-size:13px;">
                            {{ texts.log_input_total }} <strong id="log-entry-total-value">0.0000</strong> {{ texts.unit_mt }}
                        </div>
                        <div style="display:flex; gap:8px; flex-wrap:wrap; margin-top:8px;">
                            <button type="button" onclick="addLogEntryDetailRow()">{{ texts.saw_log_add_row_btn }}</button>
                            <button type="button" onclick="saveLogEntryModal()">{{ texts.log_done_fill_btn }}</button>
                            <button type="button" onclick="closeLogEntryModal()" style="background:#6c757d;">{{ texts.close_btn }}</button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        <div id="log-entry-list-modal" class="modal-mask">
            <div class="modal-box" style="width:min(920px, 96vw);">
                <div style="display:flex; justify-content:space-between; align-items:center; gap:8px; flex-wrap:wrap;">
                    <h3 style="margin:0;">{{ texts.log_history_title }}</h3>
                    <div style="display:flex; gap:8px;">
                        <button type="button" onclick="loadLogEntryList()">{{ texts.refresh_btn }}</button>
                        <button type="button" onclick="closeLogEntryListModal()" style="background:#6c757d;">{{ texts.close_btn }}</button>
                    </div>
                </div>
                <table class="tray-grid" style="margin-top:10px;">
                    <thead>
                        <tr>
                            <th>{{ texts.created_at }}</th>
                            <th>{{ texts.driver_name }}</th>
                            <th>{{ texts.truck_number }}</th>
                            <th>MT</th>
                            <th>{{ texts.actions }}</th>
                        </tr>
                    </thead>
                    <tbody id="log-entry-list-body"></tbody>
                    <tfoot>
                        <tr>
                            <th colspan="4" style="text-align:right;">合计</th>
                            <th id="log-entry-list-total">0.0000</th>
                        </tr>
                    </tfoot>
                </table>
            </div>
        </div>
        <div id="saw-machine-modal" class="modal-mask">
            <div class="modal-box" style="width:min(1180px, 98vw);">
                <h3>{{ texts.saw_machine_modal_title }}</h3>
                <table class="tray-grid">
                    <thead>
                        <tr>
                            <th style="width:90px;">{{ texts.saw_machine_no }}</th>
                            <th>{{ texts.saw_daily }}</th>
                            <th>{{ texts.saw_products }}</th>
                            <th>{{ texts.saw_bark }}</th>
                            <th>{{ texts.saw_dust }}</th>
                            <th style="width:90px;">{{ texts.actions }}</th>
                        </tr>
                    </thead>
                    <tbody id="saw-machine-body"></tbody>
                </table>
                <div style="display:flex; gap:8px; flex-wrap:wrap;">
                    <button type="button" onclick="finishSawMachineModal(false)">{{ texts.saw_machine_fill_btn }}</button>
                    <button type="button" onclick="closeSawMachineModal()">{{ texts.close_btn }}</button>
                </div>
            </div>
        </div>
        <div id="saw-log-detail-modal" class="modal-mask">
            <div class="modal-box" style="width:min(760px, 95vw);">
                <div style="display:flex; justify-content:space-between; align-items:center; gap:8px; flex-wrap:wrap;">
                    <h3 style="margin:0;">{{ texts.saw_log_detail_title }}</h3>
                    <div id="saw-log-machine-label" style="font-size:13px; color:#6b7280;"></div>
                </div>
                <table class="tray-grid">
                    <thead>
                        <tr>
                            <th>{{ texts.saw_log_size_label }}</th>
                            <th>{{ texts.saw_log_qty_label }}</th>
                            <th>{{ texts.saw_log_length_label }}</th>
                            <th>{{ texts.saw_daily }}</th>
                            <th style="width:84px;">{{ texts.actions }}</th>
                        </tr>
                    </thead>
                    <tbody id="saw-log-detail-body"></tbody>
                </table>
                <div style="margin:8px 0; font-size:13px; color:#374151;">
                    {{ texts.saw_log_total_label }}: <strong id="saw-log-total-value">0.0000</strong> {{ texts.unit_mt }}
                </div>
                <div style="margin:8px 0 4px; font-size:13px; color:#374151;">未完成（从上表扣减）</div>
                <table class="tray-grid">
                    <thead>
                        <tr>
                            <th>{{ texts.saw_log_size_label }}</th>
                            <th>{{ texts.saw_log_qty_label }}</th>
                            <th>{{ texts.saw_log_length_label }}</th>
                            <th>{{ texts.saw_daily }}</th>
                            <th style="width:84px;">{{ texts.actions }}</th>
                        </tr>
                    </thead>
                    <tbody id="saw-log-pending-body"></tbody>
                </table>
                <div style="margin:8px 0; font-size:13px; color:#6b7280;">
                    未完成合计: <strong id="saw-log-pending-total-value">0.0000</strong> {{ texts.unit_mt }}
                </div>
                <div style="display:flex; gap:8px; flex-wrap:wrap;">
                    <button type="button" onclick="addSawLogDetailRow()">{{ texts.saw_log_add_row_btn }}</button>
                    <button type="button" onclick="addPendingSawLogDetailRow()">加未完成</button>
                    <button type="button" onclick="saveSawLogDetailModal()">{{ texts.saw_log_done_btn }}</button>
                    <button type="button" onclick="closeSawLogDetailModal()">{{ texts.close_btn }}</button>
                </div>
            </div>
        </div>
        <div id="sort-tray-modal" class="modal-mask">
            <div class="modal-box" style="width:min(1180px, 99vw);">
                <h3>{{ texts.sort_tray_modal_title }}</h3>
                <table class="tray-grid">
                    <thead>
                        <tr>
                            <th>{{ texts.tray_id_label }}</th>
                            <th>{{ texts.primary_spec_label }}</th>
                            <th>{{ texts.fixed_qty_label }}</th>
                            <th>{{ texts.extra_spec_label }}</th>
                            <th>{{ texts.extra_qty_label }}</th>
                            <th>{{ texts.sort_tray_content }}</th>
                            <th style="width:84px;">{{ texts.actions }}</th>
                        </tr>
                    </thead>
                    <tbody id="sort-tray-body"></tbody>
                </table>
                <div style="display:flex; gap:8px; flex-wrap:wrap;">
                    <button type="button" onclick="addSortTrayRow()">{{ texts.add_row_btn }}</button>
                    <button type="button" onclick="saveSortTrayRows()">{{ texts.save_changes_btn }}</button>
                    <button type="button" onclick="closeSortTrayModal()">{{ texts.close_btn }}</button>
                </div>
            </div>
        </div>
        <div id="pending-tray-modal" class="modal-mask">
            <div class="modal-box" style="width:min(1080px, 98vw);">
                <h3>{{ texts.pending_tray_detail_title }}</h3>
                <table class="tray-grid">
                    <thead>
                        <tr>
                            <th style="width:160px;">{{ texts.tray_id_col }}</th>
                            <th>{{ texts.sort_tray_content }}</th>
                            {% if current_user.has_permission('admin') %}
                            <th style="width:84px;">{{ texts.actions }}</th>
                            {% endif %}
                        </tr>
                    </thead>
                    <tbody id="pending-tray-body"></tbody>
                </table>
                <div style="display:flex; gap:8px; flex-wrap:wrap;">
                    {% if current_user.has_permission('admin') %}
                    <button type="button" onclick="addPendingTrayRow()">{{ texts.add_row_btn }}</button>
                    <button type="button" onclick="savePendingTrayRows()">{{ texts.save_changes_btn }}</button>
                    {% endif %}
                    <button type="button" onclick="closePendingTrayModal()">{{ texts.close_btn }}</button>
                </div>
            </div>
        </div>
        <div id="tray-picker-modal" class="modal-mask">
            <div class="modal-box" style="width:min(980px, 98vw);">
                <h3 id="tray-picker-title"></h3>
                <div id="tray-picker-grid" class="tray-picker-grid"></div>
                <div id="tray-picker-empty" style="display:none; color:#6b7280; font-size:13px;">{{ texts.tray_picker_empty }}</div>
                <div style="display:flex; gap:8px; flex-wrap:wrap; margin-top:12px;">
                    <button type="button" onclick="closeTrayPickerModal()">{{ texts.close_btn }}</button>
                    <button type="button" id="tray-picker-confirm-btn" onclick="submitTrayPickerSelection()">{{ texts.load }}</button>
                </div>
            </div>
        </div>
    </div>

    <script>
        function startDrying(kilnId, remainingTrays) {
            const loadedTrays = Number(remainingTrays) || 0;
            let confirmFlag = '0';
            if (loadedTrays < 60) {
                const msg = `{{ texts.kiln_not_full_confirm }}`
                    .replace('{current}', String(loadedTrays))
                    .replace('{max}', '60');
                if (!confirm(msg)) return;
                confirmFlag = '1';
            }
            storeScrollPosition();
            fetch('/kiln_action?lang={{ lang }}', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: 'kiln_id=' + kilnId + '&action=start_dry&confirm_dry=' + confirmFlag
            })
            .then(response => response.text())
            .then(html => {
                replacePageHtml(html);
            });
        }

        function startUnloading(kilnId, elapsedHours, status, remainingTrays) {
            if (status === 'unloading') {
                alert(`已在出窑中 窑内剩余${remainingTrays || 0}托`);
                return;
            }
            let confirmFlag = '0';
            if (elapsedHours < 100) {
                if (!confirm(`当前时间${elapsedHours}小时不足100小时，确定要待出窑吗？`)) {
                    return;
                }
                confirmFlag = '1';
            }
            storeScrollPosition();
            fetch('/kiln_action?lang={{ lang }}', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: 'kiln_id=' + kilnId + '&action=start_unload&confirm_unload=' + confirmFlag
            })
            .then(response => response.text())
            .then(html => {
                replacePageHtml(html);
            });
        }

        function completeKiln(kilnId, remainingTrays) {
            if ((Number(remainingTrays) || 0) > 0) {
                alert(`该窑未完成，尚有${remainingTrays}托在窑中。`);
                return;
            }
            storeScrollPosition();
            fetch('/kiln_action?lang={{ lang }}', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: 'kiln_id=' + kilnId + '&action=complete'
            })
            .then(response => response.text())
            .then(html => {
                replacePageHtml(html);
            });
        }

        function submitKilnAction(kilnId, action, data, extraFormData = '') {
            storeScrollPosition();
            fetch('/kiln_action?lang={{ lang }}', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: 'kiln_id=' + kilnId + '&action=' + action + '&trays=' + encodeURIComponent(data) + (extraFormData || '')
            })
            .then(response => response.text())
            .then(html => {
                replacePageHtml(html);
            });
        }

        function loadKiln(kilnId, data) {
            const sortInput = document.getElementById('sort_trays_input');
            const sortVal = parseInt((sortInput && sortInput.value) || '0', 10) || 0;
            let extra = '';
            if (sortVal <= 0) {
                highlightMissingInput(sortInput, document.getElementById('sort-missing-bubble'));
                if (!confirm('{{ texts.sort_missing_confirm }}')) return;
                extra = '&confirm_missing_sort=1';
            }
            submitKilnAction(kilnId, 'load', data, extra);
        }

        function unloadKiln(kilnId, data) {
            submitKilnAction(kilnId, 'unload', data);
        }

        const SORTING_SPEC_PCS = {
            '84': { spec: '950x84x22', qty: 297 },
            '60': { spec: '950x60x22', qty: 405 },
            '71': { spec: '950x71x22', qty: 378 },
            '44': { spec: '950x44x22', qty: 540 }
        };

        const CURRENT_LANG = '{{ lang }}';
        const USE_DWL_SPEC_DISPLAY = CURRENT_LANG === 'en' || CURRENT_LANG === 'my';
        const CURRENT_DIP_STOCK = Number('{{ dip_stock }}') || 0;
        const CURRENT_KILN_DONE_STOCK = Number('{{ kiln_done_stock }}') || 0;
        const OVERVIEW_RADAR_LABELS = {{ (overview_radar_labels or []) | tojson }};
        const OVERVIEW_RADAR = {{ (overview_radar or {}) | tojson }};
        let DAILY_ENTRY_STATUS = { loaded: false, missing_sort: false, missing_secondary_sort: false };
        const IS_ADMIN = {{ 'true' if current_user.has_permission('admin') else 'false' }};
        const CAN_EXPORT_LOG = {{ 'true' if current_user.has_permission('export') else 'false' }};
        let currentKilnId = null;
        let trayPickerState = { mode: '', kilnId: '', selected: new Set(), dragActive: false, dragValue: true };
        let finishedInventoryRows = [];
        let shipmentInventoryRows = [];
        let selectedShipmentProducts = new Set();
        let shipmentPickerState = { dragActive: false, dragValue: true };
        let shippingOrderRows = [];
        let logEntryListRows = [];
        let logEntrySubmitting = false;
        const LOG_PRICE_RULE_DEFS = [
            { key: '15_17', label: '15-17', min_size: 15, max_size: 17, is_max_open: 0, default_price: 90000 },
            { key: '15_18', label: '15-18', min_size: 15, max_size: 18, is_max_open: 0, default_price: 90000 },
            { key: '18_24', label: '18-24', min_size: 18, max_size: 24, is_max_open: 0, default_price: 320000 },
            { key: '19_24', label: '19-24', min_size: 19, max_size: 24, is_max_open: 0, default_price: 320000 },
            { key: '25_plus_430', label: '25+', min_size: 25, max_size: 0, is_max_open: 1, default_price: 430000 },
            { key: '25_plus_450', label: '25+', min_size: 25, max_size: 0, is_max_open: 1, default_price: 450000 }
        ];
        const LOG_STAGE_ROWS = [
            { id: 'stage1', label: 'A', options: ['15_17', '15_18'], defaultKey: '15_17' },
            { id: 'stage2', label: 'B', options: ['18_24', '19_24'], defaultKey: '18_24' },
            { id: 'stage3', label: 'C', options: ['25_plus_430'], defaultKey: '25_plus_430' }
        ];
        let logEntryDraft = { driver_name: '', truck_number: '', details: [], rules: [] };
        let logDriverFetchTimer = null;
        let sawMachineDraft = [];
        let currentSawLogMachineNo = null;

        function calcLogEntryMt(size, length, quantity) {
            const sizeVal = Number(size) || 0;
            const lengthVal = Number(length) || 0;
            const qtyVal = Number(quantity) || 0;
            if (sizeVal <= 0 || qtyVal <= 0 || lengthVal <= 0) return 0;
            return (sizeVal * sizeVal * lengthVal * qtyVal) / 115200;
        }

        function parseLogDetailsPayloadSafe(rawValue) {
            if (!rawValue) return [];
            try {
                const parsed = JSON.parse(rawValue);
                return Array.isArray(parsed) ? parsed : [];
            } catch (_) {
                return [];
            }
        }

        function defaultLogRules() {
            return LOG_PRICE_RULE_DEFS.map(item => ({
                key: item.key,
                label: item.label,
                min_size: item.min_size,
                max_size: item.max_size,
                is_max_open: item.is_max_open,
                enabled: 0,
                price_per_mt: item.default_price
            }));
        }

        function ruleDefByKey(key) {
            return LOG_PRICE_RULE_DEFS.find(item => item.key === key) || null;
        }

        function parseLogRulesPayloadSafe(rawValue) {
            if (!rawValue) return defaultLogRules();
            try {
                const parsed = JSON.parse(rawValue);
                if (!Array.isArray(parsed)) return defaultLogRules();
                const map = {};
                parsed.forEach(item => { if (item && item.key) map[String(item.key)] = item; });
                return LOG_PRICE_RULE_DEFS.map(def => {
                    const from = map[def.key] || {};
                    return {
                        key: def.key,
                        label: def.label,
                        min_size: def.min_size,
                        max_size: def.max_size,
                        is_max_open: def.is_max_open,
                        enabled: Number(from.enabled || 0) === 1 ? 1 : 0,
                        price_per_mt: Number(from.price_per_mt || def.default_price) || 0
                    };
                });
            } catch (_) {
                return defaultLogRules();
            }
        }

        function rulesToStageConfig(rules) {
            const src = Array.isArray(rules) && rules.length ? rules : defaultLogRules();
            const map = {};
            src.forEach(item => { if (item && item.key) map[String(item.key)] = item; });
            const stage1Opt = LOG_STAGE_ROWS[0].options.find(key => Number((map[key] || {}).enabled || 0) === 1) || LOG_STAGE_ROWS[0].defaultKey;
            const stage2Opt = LOG_STAGE_ROWS[1].options.find(key => Number((map[key] || {}).enabled || 0) === 1) || LOG_STAGE_ROWS[1].defaultKey;
            const stage3Opts = ['25_plus_430', '25_plus_450'];
            const stage3Opt = stage3Opts.find(key => Number((map[key] || {}).enabled || 0) === 1) || '25_plus_430';
            const stage3PriceSource = map[stage3Opt] || map['25_plus_430'] || map['25_plus_450'] || {};
            return {
                stage1_key: stage1Opt,
                stage1_price: Number((map[stage1Opt] || {}).price_per_mt || (ruleDefByKey(stage1Opt) || {}).default_price || 0),
                stage2_key: stage2Opt,
                stage2_price: Number((map[stage2Opt] || {}).price_per_mt || (ruleDefByKey(stage2Opt) || {}).default_price || 0),
                stage3_price: Number(stage3PriceSource.price_per_mt || 430000)
            };
        }

        function stageConfigToRules(cfg) {
            const base = defaultLogRules();
            const map = {};
            base.forEach(item => { map[item.key] = item; });
            const stage1Key = String(cfg.stage1_key || '15_17');
            const stage2Key = String(cfg.stage2_key || '18_24');
            const stage3Key = '25_plus_430';
            if (map[stage1Key]) {
                map[stage1Key].enabled = 1;
                map[stage1Key].price_per_mt = Number(cfg.stage1_price || (ruleDefByKey(stage1Key) || {}).default_price || 0);
            }
            if (map[stage2Key]) {
                map[stage2Key].enabled = 1;
                map[stage2Key].price_per_mt = Number(cfg.stage2_price || (ruleDefByKey(stage2Key) || {}).default_price || 0);
            }
            if (map[stage3Key]) {
                map[stage3Key].enabled = 1;
                map[stage3Key].price_per_mt = Number(cfg.stage3_price || (ruleDefByKey(stage3Key) || {}).default_price || 0);
            }
            if (map['25_plus_450']) {
                map['25_plus_450'].enabled = 0;
                map['25_plus_450'].price_per_mt = Number(cfg.stage3_price || (ruleDefByKey('25_plus_450') || {}).default_price || 0);
            }
            return LOG_PRICE_RULE_DEFS.map(def => map[def.key]);
        }

        function renderLogPriceRules(rules) {
            const body = document.getElementById('log-price-rules-body');
            if (!body) return;
            body.innerHTML = '';
            const cfg = rulesToStageConfig(rules);
            LOG_STAGE_ROWS.forEach((row, idx) => {
                const tr = document.createElement('tr');
                if (row.id === 'stage1' || row.id === 'stage2') {
                    const selectedKey = cfg[`${row.id}_key`] || row.defaultKey;
                    const selectedPrice = Number(cfg[`${row.id}_price`] || 0);
                    const options = row.options.map((key) => {
                        const def = ruleDefByKey(key);
                        return `<option value="${key}"${selectedKey === key ? ' selected' : ''}>${def ? def.label : key}</option>`;
                    }).join('');
                    tr.innerHTML = `
                        <td style="text-align:center; font-weight:700;">${row.label}</td>
                        <td><select class="lpr-stage-key" data-stage="${row.id}" style="width:120px;">${options}</select></td>
                        <td><input type="number" class="lpr-stage-price" data-stage="${row.id}" min="0" step="0.0001" value="${selectedPrice}" style="width:122px;"></td>
                    `;
                } else {
                    const selectedPrice = Number(cfg.stage3_price || 0);
                    tr.innerHTML = `
                        <td style="text-align:center; font-weight:700;">${row.label}</td>
                        <td style="white-space:nowrap;">25+</td>
                        <td><input type="number" class="lpr-stage-price" data-stage="${row.id}" min="0" step="0.0001" value="${selectedPrice}" style="width:122px;"></td>
                    `;
                }
                body.appendChild(tr);
            });
            body.querySelectorAll('.lpr-stage-key,.lpr-stage-price').forEach(el => {
                el.addEventListener('input', renderLogEntryDetailTotal);
                el.addEventListener('change', renderLogEntryDetailTotal);
            });
        }

        function readRulesFromUi() {
            const cfg = {
                stage1_key: '15_17',
                stage1_price: 90000,
                stage2_key: '18_24',
                stage2_price: 320000,
                stage3_price: 430000
            };
            const stage1KeyEl = document.querySelector('#log-price-rules-body .lpr-stage-key[data-stage="stage1"]');
            const stage2KeyEl = document.querySelector('#log-price-rules-body .lpr-stage-key[data-stage="stage2"]');
            const stage1PriceEl = document.querySelector('#log-price-rules-body .lpr-stage-price[data-stage="stage1"]');
            const stage2PriceEl = document.querySelector('#log-price-rules-body .lpr-stage-price[data-stage="stage2"]');
            const stage3PriceEl = document.querySelector('#log-price-rules-body .lpr-stage-price[data-stage="stage3"]');
            cfg.stage1_key = stage1KeyEl ? String(stage1KeyEl.value || '15_17') : '15_17';
            cfg.stage2_key = stage2KeyEl ? String(stage2KeyEl.value || '18_24') : '18_24';
            cfg.stage1_price = stage1PriceEl ? (Number(stage1PriceEl.value || 0) || 0) : 90000;
            cfg.stage2_price = stage2PriceEl ? (Number(stage2PriceEl.value || 0) || 0) : 320000;
            cfg.stage3_price = stage3PriceEl ? (Number(stage3PriceEl.value || 0) || 0) : 430000;
            return stageConfigToRules(cfg);
        }

        function inLogRuleRange(sizeVal, rule) {
            if (!rule) return false;
            if (Number(rule.is_max_open || 0) === 1) return sizeVal >= Number(rule.min_size || 0);
            return sizeVal >= Number(rule.min_size || 0) && sizeVal <= Number(rule.max_size || 0);
        }

        function buildLogEntrySummary(details, rules) {
            const enabledRules = (rules || []).filter(r => Number(r.enabled || 0) === 1 && Number(r.price_per_mt || 0) > 0);
            const summaryMap = {};
            let unmatchedMt = 0;
            let unmatchedQty = 0;
            (details || []).forEach(item => {
                const sizeVal = Number(item.size_mm || 0);
                const mt = Number(item.consumed_mt || 0);
                const qty = Number(item.quantity || 0);
                if (mt <= 0) return;
                let matched = null;
                for (const rule of enabledRules) {
                    if (inLogRuleRange(sizeVal, rule)) {
                        matched = rule;
                        break;
                    }
                }
                if (!matched) {
                    unmatchedMt += mt;
                    unmatchedQty += qty;
                    return;
                }
                const key = String(matched.key || '');
                if (!summaryMap[key]) {
                    summaryMap[key] = { key, label: matched.label, price_per_mt: Number(matched.price_per_mt || 0), mt: 0, amount_ks: 0, quantity: 0 };
                }
                summaryMap[key].mt = Number((summaryMap[key].mt + mt).toFixed(4));
                summaryMap[key].amount_ks = Number((summaryMap[key].mt * summaryMap[key].price_per_mt).toFixed(2));
                summaryMap[key].quantity = Number(summaryMap[key].quantity || 0) + qty;
            });
            const rows = LOG_PRICE_RULE_DEFS
                .map(def => summaryMap[def.key])
                .filter(Boolean);
            if (unmatchedMt > 0) {
                rows.push({ key: 'unmatched', label: '未匹配区间', price_per_mt: 0, mt: Number(unmatchedMt.toFixed(4)), amount_ks: 0, quantity: unmatchedQty });
            }
            return rows;
        }

        function renderLogEntrySummaryRows(rows) {
            const body = document.getElementById('log-entry-summary-body');
            if (!body) return;
            body.innerHTML = '';
            let mtTotal = 0;
            let amountTotal = 0;
            let qtyTotal = 0;
            (rows || []).forEach(item => {
                const mtVal = Number(item.mt || 0);
                const amountVal = Number(item.amount_ks || 0);
                const qtyVal = Number(item.quantity || 0);
                const tr = document.createElement('tr');
                tr.innerHTML = `<td>${item.label || item.key || ''}</td><td>${mtVal.toFixed(4)}</td><td>${amountVal.toFixed(2)}</td><td>${qtyVal}</td>`;
                body.appendChild(tr);
                mtTotal += mtVal;
                amountTotal += amountVal;
                qtyTotal += qtyVal;
            });
            if (!rows || !rows.length) {
                const tr = document.createElement('tr');
                tr.innerHTML = `<td colspan="4" style="color:#6b7280;">暂无</td>`;
                body.appendChild(tr);
                return;
            }
            const totalRow = document.createElement('tr');
            totalRow.innerHTML = `<td><strong>合计</strong></td><td><strong>${mtTotal.toFixed(4)}</strong></td><td><strong>${amountTotal.toFixed(2)}</strong></td><td><strong>${qtyTotal}</strong></td>`;
            body.appendChild(totalRow);
        }

        function renderLogEntryDetailTotal() {
            const rows = Array.from(document.querySelectorAll('#log-entry-detail-body tr'));
            const details = rows.map(row => {
                const size_mm = Number(row.querySelector('.led-size').value || 0);
                const quantity = Number(row.querySelector('.led-qty').value || 0);
                const length_ft = Number(row.querySelector('.led-length').value || 3);
                const consumed_mt = calcLogEntryMt(size_mm, length_ft, quantity);
                return { size_mm, quantity, length_ft, consumed_mt: Number(consumed_mt.toFixed(4)) };
            }).filter(item => item.size_mm > 0 && item.quantity > 0 && (item.length_ft === 3 || item.length_ft === 4));
            const total = rows.reduce((sum, row) => {
                return sum + calcLogEntryMt(
                    row.querySelector('.led-size').value,
                    row.querySelector('.led-length').value,
                    row.querySelector('.led-qty').value
                );
            }, 0);
            const totalEl = document.getElementById('log-entry-total-value');
            if (totalEl) totalEl.textContent = total.toFixed(4);
            const totalLeftEl = document.getElementById('log-entry-total-value-left');
            if (totalLeftEl) totalLeftEl.textContent = total.toFixed(4);
            rows.forEach(row => {
                const mt = calcLogEntryMt(
                    row.querySelector('.led-size').value,
                    row.querySelector('.led-length').value,
                    row.querySelector('.led-qty').value
                );
                row.querySelector('.led-mt').value = mt > 0 ? mt.toFixed(4) : '';
            });
            renderLogEntrySummaryRows(buildLogEntrySummary(details, readRulesFromUi()));
        }

        function addLogEntryDetailRow(detail = {}, focusField = 'size') {
            const body = document.getElementById('log-entry-detail-body');
            if (!body) return;
            const lastSizeInput = body.querySelector('tr:last-child .led-size');
            const nextAutoSize = lastSizeInput ? (Number(lastSizeInput.value || 0) + 1) : 15;
            const sizeVal = Number(detail.size_mm || 0) > 0 ? Number(detail.size_mm) : nextAutoSize;
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>
                    <input type="number" class="led-size" min="1" value="${sizeVal}" readonly style="height:30px; padding:4px 6px; font-size:12px; width:90px; background:#f8f9fa;">
                </td>
                <td><input type="number" class="led-qty" min="1" value="${detail.quantity || ''}" style="height:30px; padding:4px 6px; font-size:12px; width:110px;"></td>
                <td>
                    <select class="led-length" style="height:30px; padding:2px 6px; border:1px solid #ddd; border-radius:4px; width:90px; font-size:12px;">
                        <option value="3"${Number(detail.length_ft || 3) === 3 ? ' selected' : ''}>{{ texts.saw_log_length_3 }}</option>
                        <option value="4"${Number(detail.length_ft || 3) === 4 ? ' selected' : ''}>{{ texts.saw_log_length_4 }}</option>
                    </select>
                </td>
                <td><input type="text" class="led-mt" readonly value="${detail.consumed_mt ? Number(detail.consumed_mt).toFixed(4) : ''}" style="height:30px; padding:4px 6px; font-size:12px; width:110px; background:#f8f9fa;"></td>
                <td><button type="button" onclick="this.closest('tr').remove(); renderLogEntryDetailTotal();">{{ texts.delete }}</button></td>
            `;
            body.appendChild(tr);
            const sizeInput = tr.querySelector('.led-size');
            const qtyInput = tr.querySelector('.led-qty');
            const lengthInput = tr.querySelector('.led-length');
            [qtyInput, lengthInput].forEach(input => {
                input.addEventListener('input', renderLogEntryDetailTotal);
                input.addEventListener('change', renderLogEntryDetailTotal);
            });
            qtyInput.addEventListener('keydown', event => {
                if (event.key !== 'Enter') return;
                event.preventDefault();
                addLogEntryDetailRow({}, 'qty');
            });
            renderLogEntryDetailTotal();
            const target = qtyInput;
            setTimeout(() => {
                target.focus();
                target.select();
            }, 0);
        }

        function syncLogEntryDraftFromModal() {
            const rows = Array.from(document.querySelectorAll('#log-entry-detail-body tr'));
            const details = rows.map(row => {
                const size_mm = Number(row.querySelector('.led-size').value || 0);
                const quantity = Number(row.querySelector('.led-qty').value || 0);
                const length_ft = Number(row.querySelector('.led-length').value || 3);
                const consumed_mt = calcLogEntryMt(size_mm, length_ft, quantity);
                return { size_mm, quantity, length_ft, consumed_mt: Number(consumed_mt.toFixed(4)) };
            }).filter(item => item.size_mm > 0 && item.quantity > 0 && (item.length_ft === 3 || item.length_ft === 4));
            logEntryDraft = {
                driver_name: (document.getElementById('log-modal-driver').value || '').trim(),
                truck_number: (document.getElementById('log-modal-truck').value || '').trim(),
                details,
                rules: readRulesFromUi()
            };
        }

        function updateLogMainFormFromDraft() {
            const details = Array.isArray(logEntryDraft.details) ? logEntryDraft.details : [];
            const total = details.reduce((sum, item) => sum + (Number(item.consumed_mt) || 0), 0);
            document.getElementById('log_driver_hidden').value = logEntryDraft.driver_name || '';
            document.getElementById('log_truck_hidden').value = logEntryDraft.truck_number || '';
            const summaryRows = buildLogEntrySummary(details, Array.isArray(logEntryDraft.rules) ? logEntryDraft.rules : []);
            const firstPriced = summaryRows.find(item => item.key !== 'unmatched');
            document.getElementById('log_size_range_hidden').value = firstPriced ? String(firstPriced.label || '') : '';
            document.getElementById('log_price_hidden').value = firstPriced ? String(Number(firstPriced.price_per_mt || 0).toFixed(4)) : '';
            document.getElementById('log_price_rules_payload_hidden').value = JSON.stringify(Array.isArray(logEntryDraft.rules) ? logEntryDraft.rules : []);
            document.getElementById('log_amount_hidden').value = total > 0 ? total.toFixed(4) : '';
            document.getElementById('log_details_payload_hidden').value = JSON.stringify(details);

            document.getElementById('log_driver_preview').value = logEntryDraft.driver_name || '';
            document.getElementById('log_truck_preview').value = logEntryDraft.truck_number || '';
            document.getElementById('log_amount_preview').value = total > 0 ? total.toFixed(4) : '';
        }

        function openLogEntryModal() {
            const hiddenDriver = document.getElementById('log_driver_hidden').value || '';
            const hiddenTruck = document.getElementById('log_truck_hidden').value || '';
            const hiddenRules = parseLogRulesPayloadSafe(document.getElementById('log_price_rules_payload_hidden').value || '');
            const hiddenDetails = parseLogDetailsPayloadSafe(document.getElementById('log_details_payload_hidden').value || '');

            document.getElementById('log-modal-driver').value = hiddenDriver;
            document.getElementById('log-modal-truck').value = hiddenTruck;
            renderLogPriceRules(hiddenRules);
            const body = document.getElementById('log-entry-detail-body');
            body.innerHTML = '';
            const rows = hiddenDetails.length ? hiddenDetails : [{}];
            rows.forEach((detail) => addLogEntryDetailRow(detail, 'qty'));
            document.getElementById('log-entry-modal').style.display = 'flex';
        }

        function closeLogEntryModal() {
            document.getElementById('log-entry-modal').style.display = 'none';
        }

        function saveLogEntryModal() {
            syncLogEntryDraftFromModal();
            updateLogMainFormFromDraft();
            closeLogEntryModal();
        }

        function fetchLogDriverProfile() {
            const driverInput = document.getElementById('log-modal-driver');
            if (!driverInput) return;
            const driver = (driverInput.value || '').trim();
            if (!driver) return;
            const truck = (document.getElementById('log-modal-truck').value || '').trim();
            fetch('/api/log_driver_profile?lang={{ lang }}&driver_name=' + encodeURIComponent(driver) + '&truck_number=' + encodeURIComponent(truck))
            .then(r => r.json())
            .then(data => {
                if (!data) return;
                if (data.found && data.truck_number) {
                    document.getElementById('log-modal-truck').value = data.truck_number;
                }
                const rules = parseLogRulesPayloadSafe(JSON.stringify(Array.isArray(data.rules) ? data.rules : []));
                renderLogPriceRules(rules);
                renderLogEntryDetailTotal();
            })
            .catch(() => {});
        }

        function beforeSubmitLogEntryForm() {
            if (logEntrySubmitting) return false;
            const amount = Number(document.getElementById('log_amount_hidden').value || 0);
            const driver = (document.getElementById('log_driver_hidden').value || '').trim();
            const truck = (document.getElementById('log_truck_hidden').value || '').trim();
            if (!driver || !truck || amount <= 0) {
                alert('{{ texts.log_entry_modal_btn }}');
                return false;
            }
            logEntrySubmitting = true;
            const submitBtn = document.getElementById('submit-log-entry-btn');
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.style.opacity = '0.7';
            }
            return true;
        }

        function emptySawMachineRecord(machineNo) {
            return {
                machine_no: machineNo,
                saw_mt: '',
                saw_trays: '',
                bark_m3: '',
                dust_bags: '',
                log_details: [],
                pending_log_details: []
            };
        }

        function safeParseSawMachinePayload() {
            const hidden = document.getElementById('saw_machine_payload');
            if (!hidden || !hidden.value) return [];
            try {
                const parsed = JSON.parse(hidden.value);
                return Array.isArray(parsed) ? parsed : [];
            } catch (_) {
                return [];
            }
        }

        function buildSawMachineDraft() {
            const payload = safeParseSawMachinePayload();
            const byMachine = {};
            payload.forEach(item => {
                if (!item || !item.machine_no) return;
                byMachine[Number(item.machine_no)] = {
                    machine_no: Number(item.machine_no),
                    saw_mt: item.saw_mt ?? '',
                    saw_trays: item.saw_trays ?? '',
                    bark_m3: item.bark_m3 ?? '',
                    dust_bags: item.dust_bags ?? '',
                    log_details: Array.isArray(item.log_details) ? item.log_details : [],
                    pending_log_details: Array.isArray(item.pending_log_details) ? item.pending_log_details : []
                };
            });
            sawMachineDraft = [];
            for (let machineNo = 1; machineNo <= 6; machineNo += 1) {
                sawMachineDraft.push(byMachine[machineNo] || emptySawMachineRecord(machineNo));
            }
        }

        function sawMachinePayloadRows() {
            return sawMachineDraft
                .map(item => ({
                    machine_no: Number(item.machine_no) || 0,
                    saw_mt: Number(item.saw_mt) || 0,
                    saw_trays: Number(item.saw_trays) || 0,
                    bark_m3: Number(item.bark_m3) || 0,
                    dust_bags: Number(item.dust_bags) || 0,
                    log_details: Array.isArray(item.log_details) ? item.log_details : [],
                    pending_log_details: Array.isArray(item.pending_log_details) ? item.pending_log_details : []
                }))
                .filter(item => item.machine_no > 0 && (item.saw_mt > 0 || item.saw_trays > 0 || item.bark_m3 > 0 || item.dust_bags > 0 || item.log_details.length));
        }

        function formatSawNumber(value, digits = 4) {
            const num = Number(value) || 0;
            if (!num) return '';
            return num.toFixed(digits).replace(/0+$/, '').replace(/\.$/, '');
        }

        function updateSawMainFormFromDraft() {
            const rows = sawMachinePayloadRows();
            if (!rows.length) {
                document.getElementById('saw_tm_input').value = '';
                document.getElementById('saw_trays_input').value = '';
                document.getElementById('bark_m3_input').value = '';
                document.getElementById('dust_bags_input').value = '';
                document.getElementById('saw_machine_payload').value = '';
                return;
            }
            document.getElementById('saw_tm_input').value = formatSawNumber(rows.reduce((sum, item) => sum + (Number(item.saw_mt) || 0), 0), 4);
            document.getElementById('saw_trays_input').value = rows.reduce((sum, item) => sum + (Number(item.saw_trays) || 0), 0);
            const barkSum = rows.reduce((sum, item) => sum + (Number(item.bark_m3) || 0), 0);
            document.getElementById('bark_m3_input').value = barkSum > 0 ? formatSawNumber(barkSum, 4) : '0';
            document.getElementById('dust_bags_input').value = rows.reduce((sum, item) => sum + (Number(item.dust_bags) || 0), 0);
            document.getElementById('saw_machine_payload').value = JSON.stringify(rows);
        }

        function renderSawMachineModal() {
            const body = document.getElementById('saw-machine-body');
            body.innerHTML = '';
            sawMachineDraft.forEach(item => {
                const tr = document.createElement('tr');
                tr.dataset.machineNo = item.machine_no;
                tr.innerHTML = `
                    <td>${item.machine_no}</td>
                    <td><input type="number" class="sm-mt" step="0.0001" value="${item.saw_mt}" placeholder="{{ texts.placeholder_saw_mt }}" style="height:30px; padding:4px 6px; font-size:12px; width:120px;"></td>
                    <td><input type="number" class="sm-trays" min="0" value="${item.saw_trays}" placeholder="{{ texts.placeholder_tray }}" style="height:30px; padding:4px 6px; font-size:12px; width:110px;"></td>
                    <td><input type="number" class="sm-bark" step="0.0001" min="0" value="${item.bark_m3}" placeholder="{{ texts.placeholder_m3 }}" style="height:30px; padding:4px 6px; font-size:12px; width:120px;"></td>
                    <td><input type="number" class="sm-dust" min="0" value="${item.dust_bags}" placeholder="{{ texts.placeholder_bag }}" style="height:30px; padding:4px 6px; font-size:12px; width:110px;"></td>
                    <td><button type="button" onclick="openSawLogDetailModal(${item.machine_no})">{{ texts.saw_machine_add_log_btn }}</button></td>
                `;
                body.appendChild(tr);
            });
        }

        function syncSawMachineDraftFromModal() {
            const rows = Array.from(document.querySelectorAll('#saw-machine-body tr'));
            sawMachineDraft = rows.map((row, idx) => {
                const machineNo = Number(row.dataset.machineNo || (idx + 1));
                const prev = sawMachineDraft.find(item => Number(item.machine_no) === machineNo) || emptySawMachineRecord(machineNo);
                return {
                    machine_no: machineNo,
                    saw_mt: (row.querySelector('.sm-mt').value || '').trim(),
                    saw_trays: (row.querySelector('.sm-trays').value || '').trim(),
                    bark_m3: (row.querySelector('.sm-bark').value || '').trim(),
                    dust_bags: (row.querySelector('.sm-dust').value || '').trim(),
                    log_details: Array.isArray(prev.log_details) ? prev.log_details : [],
                    pending_log_details: Array.isArray(prev.pending_log_details) ? prev.pending_log_details : []
                };
            });
        }

        function openSawMachineModal() {
            buildSawMachineDraft();
            renderSawMachineModal();
            document.getElementById('saw-machine-modal').style.display = 'flex';
        }

        function closeSawMachineModal() {
            document.getElementById('saw-machine-modal').style.display = 'none';
        }

        function finishSawMachineModal(shouldSubmit) {
            syncSawMachineDraftFromModal();
            updateSawMainFormFromDraft();
            closeSawMachineModal();
            if (shouldSubmit) {
                const form = document.querySelector('form[action^="/submit_saw"]');
                if (form) form.requestSubmit();
            }
        }

        function calcSawLogConsumedMt(size, length, quantity) {
            const sizeVal = Number(size) || 0;
            const lengthVal = Number(length) || 0;
            const qtyVal = Number(quantity) || 0;
            if (sizeVal <= 0 || qtyVal <= 0 || lengthVal <= 0) return 0;
            return (sizeVal * sizeVal * lengthVal * qtyVal) / 115200;
        }

        function renderSawLogDetailTotal() {
            const rows = Array.from(document.querySelectorAll('#saw-log-detail-body tr'));
            const total = rows.reduce((sum, row) => {
                return sum + calcSawLogConsumedMt(
                    row.querySelector('.sld-size').value,
                    row.querySelector('.sld-length').value,
                    row.querySelector('.sld-qty').value
                );
            }, 0);
            document.getElementById('saw-log-total-value').textContent = total.toFixed(4);
            rows.forEach(row => {
                const val = calcSawLogConsumedMt(
                    row.querySelector('.sld-size').value,
                    row.querySelector('.sld-length').value,
                    row.querySelector('.sld-qty').value
                );
                row.querySelector('.sld-mt').value = val > 0 ? val.toFixed(4) : '';
            });
            renderSawPendingDetailTotal();
        }

        function renderSawPendingDetailTotal() {
            const rows = Array.from(document.querySelectorAll('#saw-log-pending-body tr'));
            const total = rows.reduce((sum, row) => {
                return sum + calcSawLogConsumedMt(
                    row.querySelector('.sld-size').value,
                    row.querySelector('.sld-length').value,
                    row.querySelector('.sld-qty').value
                );
            }, 0);
            const totalEl = document.getElementById('saw-log-pending-total-value');
            if (totalEl) totalEl.textContent = total.toFixed(4);
            rows.forEach(row => {
                const val = calcSawLogConsumedMt(
                    row.querySelector('.sld-size').value,
                    row.querySelector('.sld-length').value,
                    row.querySelector('.sld-qty').value
                );
                row.querySelector('.sld-mt').value = val > 0 ? val.toFixed(4) : '';
            });
        }

        function _addSawLogRow(bodyId, detail = {}, focusField = 'size') {
            const body = document.getElementById(bodyId);
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td><input type="number" class="sld-size" min="1" value="${detail.size_mm || ''}" style="height:30px; padding:4px 6px; font-size:12px; width:110px;"></td>
                <td><input type="number" class="sld-qty" min="1" value="${detail.quantity || ''}" style="height:30px; padding:4px 6px; font-size:12px; width:110px;"></td>
                <td>
                    <select class="sld-length" style="height:30px; padding:2px 6px; border:1px solid #ddd; border-radius:4px; width:90px; font-size:12px;">
                        <option value="3"${Number(detail.length_ft || 3) === 3 ? ' selected' : ''}>{{ texts.saw_log_length_3 }}</option>
                        <option value="4"${Number(detail.length_ft || 3) === 4 ? ' selected' : ''}>{{ texts.saw_log_length_4 }}</option>
                    </select>
                </td>
                <td><input type="text" class="sld-mt" readonly value="${detail.consumed_mt ? Number(detail.consumed_mt).toFixed(4) : ''}" style="height:30px; padding:4px 6px; font-size:12px; width:110px; background:#f8f9fa;"></td>
                <td><button type="button" onclick="this.closest('tr').remove(); renderSawLogDetailTotal();">{{ texts.delete }}</button></td>
            `;
            body.appendChild(tr);
            const sizeInput = tr.querySelector('.sld-size');
            const qtyInput = tr.querySelector('.sld-qty');
            const lengthInput = tr.querySelector('.sld-length');
            [sizeInput, qtyInput, lengthInput].forEach(input => {
                input.addEventListener('input', renderSawLogDetailTotal);
                input.addEventListener('change', renderSawLogDetailTotal);
            });
            sizeInput.addEventListener('keydown', event => {
                if (event.key !== 'Enter') return;
                event.preventDefault();
                qtyInput.focus();
                qtyInput.select();
            });
            qtyInput.addEventListener('keydown', event => {
                if (event.key !== 'Enter') return;
                event.preventDefault();
                _addSawLogRow(bodyId, {}, 'size');
            });
            renderSawLogDetailTotal();
            const target = focusField === 'qty' ? qtyInput : sizeInput;
            setTimeout(() => {
                target.focus();
                target.select();
            }, 0);
        }

        function addSawLogDetailRow(detail = {}, focusField = 'size') {
            _addSawLogRow('saw-log-detail-body', detail, focusField);
        }

        function addPendingSawLogDetailRow(detail = {}, focusField = 'size') {
            _addSawLogRow('saw-log-pending-body', detail, focusField);
        }

        function _collectSawLogRows(bodyId) {
            const rows = Array.from(document.querySelectorAll(`#${bodyId} tr`));
            return rows.map(row => {
                const size_mm = Number(row.querySelector('.sld-size').value || 0);
                const quantity = Number(row.querySelector('.sld-qty').value || 0);
                const length_ft = Number(row.querySelector('.sld-length').value || 3);
                const consumed_mt = calcSawLogConsumedMt(size_mm, length_ft, quantity);
                return { size_mm, quantity, length_ft, consumed_mt: Number(consumed_mt.toFixed(4)) };
            }).filter(item => item.size_mm > 0 && item.quantity > 0 && (item.length_ft === 3 || item.length_ft === 4));
        }

        function openSawLogDetailModal(machineNo) {
            syncSawMachineDraftFromModal();
            currentSawLogMachineNo = machineNo;
            const machine = sawMachineDraft.find(item => Number(item.machine_no) === Number(machineNo)) || emptySawMachineRecord(machineNo);
            document.getElementById('saw-log-machine-label').textContent = `{{ texts.saw_machine_no }} ${machineNo}`;
            const body = document.getElementById('saw-log-detail-body');
            const pendingBody = document.getElementById('saw-log-pending-body');
            body.innerHTML = '';
            pendingBody.innerHTML = '';
            const details = Array.isArray(machine.log_details) && machine.log_details.length ? machine.log_details : [{}];
            details.forEach((detail, idx) => addSawLogDetailRow(detail, idx === 0 ? 'size' : 'size'));
            const pending = Array.isArray(machine.pending_log_details) && machine.pending_log_details.length ? machine.pending_log_details : [];
            pending.forEach((detail, idx) => addPendingSawLogDetailRow(detail, idx === 0 ? 'size' : 'size'));
            renderSawPendingDetailTotal();
            document.getElementById('saw-log-detail-modal').style.display = 'flex';
        }

        function closeSawLogDetailModal() {
            document.getElementById('saw-log-detail-modal').style.display = 'none';
            currentSawLogMachineNo = null;
        }

        function saveSawLogDetailModal() {
            const machineNo = Number(currentSawLogMachineNo || 0);
            if (!machineNo) {
                closeSawLogDetailModal();
                return;
            }
            const sourceDetails = _collectSawLogRows('saw-log-detail-body');
            const pendingDetails = _collectSawLogRows('saw-log-pending-body');

            const netMap = new Map();
            sourceDetails.forEach(item => {
                const key = `${item.size_mm}|${item.length_ft}`;
                if (!netMap.has(key)) netMap.set(key, { size_mm: item.size_mm, length_ft: item.length_ft, quantity: 0 });
                const row = netMap.get(key);
                row.quantity += Number(item.quantity || 0);
            });
            pendingDetails.forEach(item => {
                const key = `${item.size_mm}|${item.length_ft}`;
                if (!netMap.has(key)) netMap.set(key, { size_mm: item.size_mm, length_ft: item.length_ft, quantity: 0 });
                const row = netMap.get(key);
                row.quantity -= Number(item.quantity || 0);
            });
            const details = Array.from(netMap.values())
                .filter(item => Number(item.quantity || 0) > 0)
                .map(item => {
                    const consumed_mt = calcSawLogConsumedMt(item.size_mm, item.length_ft, item.quantity);
                    return {
                        size_mm: Number(item.size_mm || 0),
                        length_ft: Number(item.length_ft || 3),
                        quantity: Number(item.quantity || 0),
                        consumed_mt: Number(consumed_mt.toFixed(4)),
                    };
                });
            const total = details.reduce((sum, item) => sum + Number(item.consumed_mt || 0), 0);
            sawMachineDraft = sawMachineDraft.map(item => {
                if (Number(item.machine_no) !== machineNo) return item;
                return {
                    ...item,
                    saw_mt: formatSawNumber(total, 4),
                    log_details: details,
                    pending_log_details: pendingDetails,
                };
            });
            renderSawMachineModal();
            closeSawLogDetailModal();
        }

        function sortingWidthOptions(selected) {
            const base = Object.keys(SORTING_SPEC_PCS).map(width => `<option value="${width}"${selected === width ? ' selected' : ''}>${width}</option>`).join('');
            return `${base}<option value="other"${selected === 'other' ? ' selected' : ''}>Other</option>`;
        }

        function splitSpecParts(spec) {
            const text = String(spec || '')
                .trim()
                .toLowerCase()
                .replace(/\s+/g, '')
                .replace(/[×*]/g, 'x')
                .replace(/[^0-9x]/g, '');
            const parts = text.split('x').filter(Boolean);
            if (parts.length !== 3) return null;
            if (parts.some(part => !/^\d+$/.test(part))) return null;
            return parts;
        }

        function specToDisplay(spec) {
            const parts = splitSpecParts(spec);
            if (!parts || !USE_DWL_SPEC_DISPLAY) return String(spec || '').trim();
            return `${parts[2]}x${parts[1]}x${parts[0]}`;
        }

        function specToSystem(spec) {
            const parts = splitSpecParts(spec);
            if (!parts) return String(spec || '').trim();
            if (!USE_DWL_SPEC_DISPLAY) return parts.join('x');
            return `${parts[2]}x${parts[1]}x${parts[0]}`;
        }

        function formatTrayContentForDisplay(summary) {
            if (!USE_DWL_SPEC_DISPLAY) return String(summary || '');
            return String(summary || '').replace(/\d+x\d+x\d+/g, token => specToDisplay(token));
        }

        function buildSortingSummary(primaryWidth, extras) {
            if (primaryWidth === 'other') {
                return '1';
            }
            const base = SORTING_SPEC_PCS[primaryWidth];
            if (!base) return '';
            const parts = [`${base.spec}x${base.qty}`];
            (extras || []).forEach(item => {
                const meta = SORTING_SPEC_PCS[item.width];
                if (!meta || !item.qty || item.qty <= 0) return;
                parts.push(`${meta.spec}x${item.qty}`);
            });
            return parts.join(' + ');
        }

        function collectSortTrayEntries() {
            const rows = Array.from(document.querySelectorAll('#sort-tray-body tr'));
            const entries = [];
            rows.forEach(tr => {
                const trayId = (tr.querySelector('.st-id').value || '').trim();
                const primaryWidth = tr.querySelector('.st-primary').value;
                const summary = buildSortingSummary(primaryWidth, tr._extraSpecs || []);
                if (!trayId || !summary) {
                    return;
                }
                entries.push(`${trayId} ${summary}`);
            });
            return entries;
        }

        function refreshSortTrayPreview() {
            const entries = collectSortTrayEntries();
            document.getElementById('sorted_kiln_trays').value = entries.join(', ');
            const indicator = document.getElementById('sort-staged-indicator');
            if (indicator) {
                indicator.textContent = `{{ texts.sort_staged_count }} ${entries.length} {{ texts.unit_kiln_tray }}`;
                indicator.style.display = entries.length ? 'inline-flex' : 'none';
            }
        }

        function renderSortTrayRowSummary(tr) {
            const primaryWidth = tr.querySelector('.st-primary').value;
            const fixedQty = tr.querySelector('.st-fixed');
            const summary = tr.querySelector('.st-summary');
            const extraWidth = tr.querySelector('.st-extra-width');
            const extraQty = tr.querySelector('.st-extra-qty');
            const appendBtn = tr.querySelector('.st-append-btn');
            const meta = SORTING_SPEC_PCS[primaryWidth];
            const isOther = primaryWidth === 'other';
            fixedQty.value = isOther ? '' : (meta ? meta.qty : '');
            if (extraWidth) extraWidth.disabled = isOther;
            if (extraQty) extraQty.disabled = isOther;
            if (appendBtn) appendBtn.disabled = isOther;
            if (isOther) {
                tr._extraSpecs = [];
                if (extraQty) extraQty.value = '';
            }
            summary.value = formatTrayContentForDisplay(buildSortingSummary(primaryWidth, tr._extraSpecs || []));
        }

        function openSortTrayModal() {
            const body = document.getElementById('sort-tray-body');
            if (!body.children.length) {
                addSortTrayRow();
            }
            document.getElementById('sort-tray-modal').style.display = 'flex';
        }

        function closeSortTrayModal() {
            document.getElementById('sort-tray-modal').style.display = 'none';
        }

        function addSortTrayRow(trayId = '', primaryWidth = '84') {
            const body = document.getElementById('sort-tray-body');
            const tr = document.createElement('tr');
            tr._extraSpecs = [];
            tr.innerHTML = `
                <td><input type="text" class="st-id" value="${trayId}" placeholder="{{ texts.placeholder_tray_id }}" style="height:30px; padding:4px 6px; font-size:12px; width:150px;"></td>
                <td>
                    <select class="st-primary" style="height:30px; padding:2px 6px; border:1px solid #ddd; border-radius:4px; width:92px; font-size:12px;">
                        ${sortingWidthOptions(primaryWidth)}
                    </select>
                </td>
                <td><input type="text" class="st-fixed" readonly style="width:86px; height:30px; padding:4px 6px; font-size:12px; background:#f8f9fa;"></td>
                <td>
                    <div style="display:flex; gap:6px; align-items:center;">
                        <select class="st-extra-width" style="height:30px; padding:2px 6px; border:1px solid #ddd; border-radius:4px; width:92px; font-size:12px;">
                            ${sortingWidthOptions('44')}
                        </select>
                        <button type="button" class="btn-inline st-append-btn" onclick="appendSortTraySpec(this)" style="padding:4px 10px; background:#0d6efd; color:#fff; border:none; border-radius:4px; font-size:12px;">{{ texts.append_spec_btn }}</button>
                    </div>
                </td>
                <td><input type="number" class="st-extra-qty" min="1" placeholder="{{ texts.placeholder_qty }}" style="height:30px; padding:4px 6px; font-size:12px; width:90px;"></td>
                <td><input type="text" class="st-summary" readonly style="width:100%; min-width:340px; height:30px; padding:4px 6px; font-size:12px; background:#f8f9fa;"></td>
                <td class="sp-actions" style="width:84px;">
                    <button type="button" class="btn-inline" onclick="deleteSortTrayRow(this)" style="padding:3px 10px; background:#dc3545; color:#fff; border:none; border-radius:4px; font-size:12px;">{{ texts.delete }}</button>
                </td>
            `;
            body.appendChild(tr);
            tr.querySelector('.st-primary').addEventListener('change', () => renderSortTrayRowSummary(tr));
            renderSortTrayRowSummary(tr);
        }

        function appendSortTraySpec(btn) {
            const tr = btn.closest('tr');
            if (!tr) return;
            const width = tr.querySelector('.st-extra-width').value;
            const qty = parseInt(tr.querySelector('.st-extra-qty').value || '0', 10);
            if (!qty || qty <= 0) {
                alert('{{ texts.invalid_extra_qty_msg }}');
                return;
            }
            tr._extraSpecs = tr._extraSpecs || [];
            tr._extraSpecs.push({ width, qty });
            tr.querySelector('.st-extra-qty').value = '';
            renderSortTrayRowSummary(tr);
        }

        function saveSortTrayRows() {
            const entries = collectSortTrayEntries();
            if (!entries.length) {
                alert('{{ texts.invalid_tray_entry_msg }}');
                return;
            }
            const trays = entries.map(entry => {
                const firstSpace = entry.indexOf(' ');
                return {
                    id: entry.slice(0, firstSpace).trim(),
                    content: entry.slice(firstSpace + 1).trim()
                };
            });
            fetch('/api/stage_sort_trays?lang={{ lang }}', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ trays })
            })
            .then(r => r.json().then(data => ({ ok: r.ok, data })))
            .then(({ok, data}) => {
                if (!ok) throw new Error(data.error || '{{ texts.save_pending_trays_failed }}');
                document.getElementById('sorted_kiln_trays').value = entries.join(', ');
                refreshSortTrayPreview();
                closeSortTrayModal();
                alert(`{{ texts.sort_stage_saved }}`.replace('{count}', entries.length));
                storeScrollPosition();
                location.reload();
            })
            .catch(err => alert(err.message || '{{ texts.save_pending_trays_failed }}'));
        }

        function beforeSubmitSortForm() {
            const entries = collectSortTrayEntries();
            document.getElementById('sorted_kiln_trays').value = entries.join(', ');
            const sortInput = document.getElementById('sort_trays_input');
            if ((parseInt((sortInput && sortInput.value) || '0', 10) || 0) <= 0) {
                highlightMissingInput(sortInput, document.getElementById('sort-missing-bubble'));
            } else {
                clearMissingInput(sortInput, document.getElementById('sort-missing-bubble'));
            }
            return true;
        }

        function beforeSubmitSecondarySortForm() {
            const secondaryInput = document.getElementById('secondary_sort_trays');
            const hasValue = !!((secondaryInput && secondaryInput.value) || '').trim();
            if (!hasValue) {
                highlightMissingInput(secondaryInput, document.getElementById('secondary-missing-bubble'));
                return false;
            }
            clearMissingInput(secondaryInput, document.getElementById('secondary-missing-bubble'));
            return true;
        }

        function highlightMissingInput(input, bubble) {
            if (input) input.classList.add('input-missing');
            if (bubble) bubble.style.display = 'inline-flex';
        }

        function clearMissingInput(input, bubble) {
            if (input) input.classList.remove('input-missing');
            if (bubble) bubble.style.display = 'none';
        }

        function refreshFlowMissingReminders() {
            const sortInput = document.getElementById('sort_trays_input');
            const secondaryInput = document.getElementById('secondary_sort_trays');
            const hour = (new Date()).getHours();
            if (hour < 16) {
                clearMissingInput(sortInput, document.getElementById('sort-missing-bubble'));
                clearMissingInput(secondaryInput, document.getElementById('secondary-missing-bubble'));
                return;
            }
            const sortVal = parseInt((sortInput && sortInput.value) || '0', 10) || 0;
            const secondaryHasValue = !!((secondaryInput && secondaryInput.value) || '').trim();

            let sortMissing = CURRENT_DIP_STOCK > 0;
            let secondaryMissing = CURRENT_KILN_DONE_STOCK > 0;
            if (DAILY_ENTRY_STATUS.loaded) {
                sortMissing = !!DAILY_ENTRY_STATUS.missing_sort;
                secondaryMissing = !!DAILY_ENTRY_STATUS.missing_secondary_sort;
            }

            if (sortMissing && sortVal <= 0) {
                highlightMissingInput(sortInput, document.getElementById('sort-missing-bubble'));
            } else {
                clearMissingInput(sortInput, document.getElementById('sort-missing-bubble'));
            }

            if (secondaryMissing && !secondaryHasValue) {
                highlightMissingInput(secondaryInput, document.getElementById('secondary-missing-bubble'));
            } else {
                clearMissingInput(secondaryInput, document.getElementById('secondary-missing-bubble'));
            }
        }

        async function refreshEntryReminderStrip() {
            const strip = document.getElementById('entry-reminder-strip');
            const textEl = document.getElementById('entry-reminder-text');
            if (!strip || !textEl) return;
            const hour = (new Date()).getHours();
            if (hour < 16) {
                strip.style.display = 'none';
                return;
            }
            try {
                const res = await fetch('/api/daily_missing_entry_status?lang={{ lang }}');
                const data = await res.json();
                DAILY_ENTRY_STATUS = {
                    loaded: true,
                    missing_sort: !!(data && data.missing_sort),
                    missing_secondary_sort: !!(data && data.missing_secondary_sort),
                };
                refreshFlowMissingReminders();
                const items = [];
                if (data && data.missing_sort) items.push('{{ texts.entry_reminder_sort_missing }}');
                if (data && data.missing_secondary_sort) items.push('{{ texts.entry_reminder_secondary_missing }}');
                if (!items.length) {
                    strip.style.display = 'none';
                    return;
                }
                textEl.textContent = items.join('；');
                strip.style.display = 'block';
            } catch (e) {
                DAILY_ENTRY_STATUS = { loaded: false, missing_sort: false, missing_secondary_sort: false };
                strip.style.display = 'none';
            }
        }

        function deleteSortTrayRow(btn) {
            const tr = btn.closest('tr');
            if (!tr) return;
            tr.remove();
            refreshSortTrayPreview();
        }

        function openPendingTrayModal() {
            fetch('/api/pending_kiln_trays?lang={{ lang }}')
            .then(r => r.json())
            .then(data => {
                const body = document.getElementById('pending-tray-body');
                body.innerHTML = '';
                const trays = Array.isArray(data.trays) ? data.trays : [];
                if (trays.length) {
                    trays.forEach(t => addPendingTrayRow(t.id || '', t.content || ''));
                } else if (IS_ADMIN) {
                    addPendingTrayRow('', '');
                }
                document.getElementById('pending-tray-modal').style.display = 'flex';
            })
            .catch(() => alert('{{ texts.load_pending_trays_failed }}'));
        }

        function closePendingTrayModal() {
            document.getElementById('pending-tray-modal').style.display = 'none';
        }

        function closeTrayPickerModal() {
            document.getElementById('tray-picker-modal').style.display = 'none';
            trayPickerState = { mode: '', kilnId: '', selected: new Set(), dragActive: false, dragValue: true };
        }

        function setTrayPickerSelection(card, trayId, selected) {
            if (selected) {
                trayPickerState.selected.add(trayId);
                card.classList.add('active');
            } else {
                trayPickerState.selected.delete(trayId);
                card.classList.remove('active');
            }
        }

        function renderTrayPickerItems(items) {
            const grid = document.getElementById('tray-picker-grid');
            const empty = document.getElementById('tray-picker-empty');
            grid.innerHTML = '';
            if (!items.length) {
                empty.style.display = 'block';
                return;
            }
            empty.style.display = 'none';
            trayPickerState.dragActive = false;
            trayPickerState.dragValue = true;
            items.forEach(item => {
                const card = document.createElement('div');
                card.className = 'tray-picker-item';
                card.dataset.id = item.id;
                card.innerHTML = `
                    <div class="tray-picker-id">${item.id}</div>
                    <div class="tray-picker-meta">${item.meta || ''}</div>
                `;
                card.addEventListener('mousedown', (event) => {
                    if (event.button !== 0) return;
                    event.preventDefault();
                    trayPickerState.dragActive = true;
                    trayPickerState.dragValue = !trayPickerState.selected.has(item.id);
                    setTrayPickerSelection(card, item.id, trayPickerState.dragValue);
                });
                card.addEventListener('mouseenter', () => {
                    if (!trayPickerState.dragActive) return;
                    setTrayPickerSelection(card, item.id, trayPickerState.dragValue);
                });
                grid.appendChild(card);
            });
            grid.onmouseleave = () => {
                trayPickerState.dragActive = false;
            };
            document.onmouseup = () => {
                trayPickerState.dragActive = false;
                shipmentPickerState.dragActive = false;
            };
        }

        function openTrayPickerModal(mode, kilnId, remainingTrays) {
            if (mode === 'load') {
                const sortInput = document.getElementById('sort_trays_input');
                if ((parseInt((sortInput && sortInput.value) || '0', 10) || 0) <= 0) {
                    highlightMissingInput(sortInput, document.getElementById('sort-missing-bubble'));
                }
            }
            trayPickerState = { mode, kilnId, selected: new Set(), dragActive: false, dragValue: true };
            const title = document.getElementById('tray-picker-title');
            const btn = document.getElementById('tray-picker-confirm-btn');
            const url = mode === 'load'
                ? '/api/pending_kiln_trays?lang={{ lang }}'
                : '/api/kiln_trays/' + encodeURIComponent(kilnId) + '?lang={{ lang }}';
            title.textContent = mode === 'load'
                ? `{{ texts.load_picker_title }} ${kilnId}`
                : `{{ texts.unload_picker_title }} ${kilnId}`;
            btn.textContent = mode === 'load' ? '{{ texts.load }}' : '{{ texts.unload }}';
            fetch(url)
            .then(r => r.json())
            .then(data => {
                const trays = Array.isArray(data.trays) ? data.trays : [];
                const items = trays.map(t => ({
                    id: t.id || '',
                    meta: (t.content || t.spec || '').trim()
                })).filter(t => t.id);
                renderTrayPickerItems(items);
                document.getElementById('tray-picker-modal').style.display = 'flex';
            })
            .catch(() => alert('{{ texts.load_kiln_trays_failed }}'));
        }

        function submitTrayPickerSelection() {
            const ids = Array.from(trayPickerState.selected);
            if (!ids.length) return;
            const raw = ids.join(',');
            const kilnId = trayPickerState.kilnId;
            const mode = trayPickerState.mode;
            closeTrayPickerModal();
            if (mode === 'load') {
                loadKiln(kilnId, raw);
            } else if (mode === 'unload') {
                unloadKiln(kilnId, raw);
            }
        }

        function addPendingTrayRow(id = '', content = '') {
            const body = document.getElementById('pending-tray-body');
            const tr = document.createElement('tr');
            const readonlyAttr = IS_ADMIN ? '' : 'readonly';
            const actionCell = IS_ADMIN
                ? `<td class="sp-actions" style="width:84px;">
                        <button type="button" class="btn-inline" onclick="this.closest('tr').remove()" style="padding:3px 10px; background:#dc3545; color:#fff; border:none; border-radius:4px; font-size:12px;">{{ texts.delete }}</button>
                   </td>`
                : '';
            tr.innerHTML = `
                <td><input type="text" class="pt-id" value="${id}" style="height:28px; padding:4px 6px; font-size:12px; width:150px;" ${readonlyAttr}></td>
                <td><input type="text" class="pt-content" value="${content}" style="height:28px; padding:4px 6px; font-size:12px; width:100%; box-sizing:border-box;" ${readonlyAttr}></td>
                ${actionCell}
            `;
            body.appendChild(tr);
        }

        function savePendingTrayRows() {
            const rows = Array.from(document.querySelectorAll('#pending-tray-body tr'));
            const trays = rows.map(row => ({
                id: (row.querySelector('.pt-id').value || '').trim(),
                content: (row.querySelector('.pt-content').value || '').trim()
            })).filter(item => item.id && item.content);

            fetch('/api/pending_kiln_trays?lang={{ lang }}', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ trays })
            })
            .then(r => r.json().then(data => ({ ok: r.ok, data })))
            .then(({ok, data}) => {
                if (!ok) throw new Error(data.error || '{{ texts.save_pending_trays_failed }}');
                closePendingTrayModal();
                storeScrollPosition();
                location.reload();
            })
            .catch(err => alert(err.message || '{{ texts.save_pending_trays_failed }}'));
        }

        function submitSecondaryProducts(entries) {
            if (!Array.isArray(entries) || !entries.length) {
                alert('{{ texts.invalid_product_entry_msg }}');
                return;
            }
            const hidden = document.getElementById('finished_product_trays');
            const confirmHidden = document.getElementById('confirm_missing_secondary_sort');
            const form = document.getElementById('secondary-products-form');
            if (!hidden || !form) {
                alert('form not ready');
                return;
            }
            const secondaryInput = document.getElementById('secondary_sort_trays');
            const secondaryHasValue = !!((secondaryInput && secondaryInput.value) || '').trim();
            if (!secondaryHasValue) {
                highlightMissingInput(secondaryInput, document.getElementById('secondary-missing-bubble'));
                if (!confirm('{{ texts.secondary_sort_missing_confirm }}')) return;
                if (confirmHidden) confirmHidden.value = '1';
            } else if (confirmHidden) {
                confirmHidden.value = '0';
            }
            hidden.value = entries.map(e => `${e.id}#${e.spec}#1#${e.grade}`).join(', ');
            form.submit();
        }

        const SECONDARY_SPEC_PCS = {
            '220x81x21': 2160,
            '270x81x21': 1728,
            '370x81x21': 1248,
            '930x81x21': 517,
            '950x81x21': 517,
            '970x81x21': 517,
            '270x68x21': 2160,
            '370x68x21': 1536,
            '930x68x21': 654,
            '950x68x21': 654,
            '270x58x21': 2304,
            '370x58x21': 1632,
            '930x58x21': 705,
            '950x58x21': 705,
            '370x44x21': 2208,
            '950x44x21': 940,
            '270x44x21': 3024
        };
        const SECONDARY_SPEC_EXTRA_PCS = {
            '950x81x21': [528],
            '950x68x21': [658]
        };
        let secondarySpecRulesLoaded = false;
        let secondarySpecRuleMap = {};
        let secondarySpecListSeq = 0;

        function normalizeSecondarySpec(spec) {
            const text = specToSystem(spec).toLowerCase().replace(/\s+/g, '');
            const parts = text.split('x').filter(Boolean);
            if (parts.length !== 3) return '';
            const dims = [];
            for (const p of parts) {
                const n = Number(p);
                if (!Number.isFinite(n) || n <= 0) return '';
                dims.push(String(Math.trunc(n)));
            }
            return dims.join('x');
        }

        function rebuildSecondaryRuleMapWithDefaults() {
            const out = {};
            for (const [spec, base] of Object.entries(SECONDARY_SPEC_PCS)) {
                const key = normalizeSecondarySpec(spec);
                if (!key) continue;
                out[key] = [Number(base)];
            }
            for (const [spec, extras] of Object.entries(SECONDARY_SPEC_EXTRA_PCS)) {
                const key = normalizeSecondarySpec(spec);
                if (!key) continue;
                if (!out[key]) out[key] = [];
                (extras || []).forEach(v => {
                    const iv = Number(v);
                    if (Number.isFinite(iv) && iv > 0 && !out[key].includes(iv)) out[key].push(iv);
                });
            }
            secondarySpecRuleMap = out;
        }

        function mergeSecondaryRules(raw) {
            if (!raw || typeof raw !== 'object') return;
            for (const [spec, values] of Object.entries(raw)) {
                const key = normalizeSecondarySpec(spec);
                if (!key) continue;
                if (!secondarySpecRuleMap[key]) secondarySpecRuleMap[key] = [];
                (Array.isArray(values) ? values : []).forEach(v => {
                    const iv = Number(v);
                    if (Number.isFinite(iv) && iv > 0 && !secondarySpecRuleMap[key].includes(iv)) {
                        secondarySpecRuleMap[key].push(iv);
                    }
                });
            }
        }

        function secondaryFixedValues(spec) {
            const key = normalizeSecondarySpec(spec);
            if (!key || !secondarySpecRuleMap[key]) return [];
            return [...secondarySpecRuleMap[key]];
        }

        async function loadSecondarySpecRules() {
            if (secondarySpecRulesLoaded) return;
            rebuildSecondaryRuleMapWithDefaults();
            try {
                const res = await fetch('/api/secondary_spec_rules?lang={{ lang }}');
                if (!res.ok) throw new Error('load rules failed');
                const data = await res.json();
                mergeSecondaryRules(data.rules || {});
                secondarySpecRulesLoaded = true;
            } catch (_) {
                secondarySpecRulesLoaded = true;
            }
        }

        async function ensureSecondaryRule(spec, pcs) {
            const key = normalizeSecondarySpec(spec);
            const pcsVal = Number(pcs);
            if (!key || !Number.isFinite(pcsVal) || pcsVal <= 0) return { ok: false, error: '{{ texts.invalid_product_entry_msg }}' };
            const fixedList = secondaryFixedValues(key);
            if (fixedList.some(fixed => pcsVal % fixed === 0)) {
                return { ok: true, spec: key };
            }
            try {
                const res = await fetch('/api/secondary_spec_rules?lang={{ lang }}', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ spec: key, pcs: pcsVal }),
                });
                const data = await res.json();
                if (!res.ok) return { ok: false, error: data.error || 'save spec rule failed' };
                mergeSecondaryRules({ [key]: [pcsVal] });
                return { ok: true, spec: key };
            } catch (_) {
                return { ok: false, error: 'save spec rule failed' };
            }
        }

        function candidateSpecsByPcs(pcs) {
            if (!pcs || pcs <= 0) return [];
            const out = [];
            for (const spec of Object.keys(SECONDARY_SPEC_PCS)) {
                const fixedList = secondaryFixedValues(spec);
                if (fixedList.some(fixed => pcs % fixed === 0)) out.push(spec);
            }
            return out;
        }

        function calcSpecInfo(spec, pcs) {
            if (!spec || !pcs || pcs <= 0) return null;
            const normalized = normalizeSecondarySpec(spec);
            if (!normalized) return null;
            const parts = normalized.split('x').map(x => parseFloat(x));
            if (parts.length !== 3) return null;
            const m3 = (parts[0] * parts[1] * parts[2] * pcs) / 1000000000.0;
            return { spec: normalized, m3 };
        }

        function openSecondaryProductModal() {
            const secondaryInput = document.getElementById('secondary_sort_trays');
            if (!((secondaryInput && secondaryInput.value) || '').trim()) {
                highlightMissingInput(secondaryInput, document.getElementById('secondary-missing-bubble'));
            }
            const body = document.getElementById('secondary-product-body');
            loadSecondarySpecRules().then(() => {
                if (!body.children.length) {
                    addSecondaryProductRow();
                }
                document.getElementById('secondary-product-modal').style.display = 'flex';
            });
        }

        function closeSecondaryProductModal() {
            document.getElementById('secondary-product-modal').style.display = 'none';
        }

        function addSecondaryProductRow(pid = '', pcs = 0, grade = 'AB') {
            const body = document.getElementById('secondary-product-body');
            const tr = document.createElement('tr');
            const listId = `sp-spec-list-${++secondarySpecListSeq}`;
            tr.innerHTML = `
                <td><input type="text" class="sp-id" value="${pid}" placeholder="{{ texts.placeholder_product_id }}" style="height:28px; padding:4px 6px; font-size:12px; width:180px;"></td>
                <td><input type="number" class="sp-pcs" min="1" value="1" readonly style="height:28px; padding:4px 6px; font-size:12px; width:110px; background:#f8f9fa;"></td>
                <td>
                    <select class="sp-grade" style="height:28px; padding:2px 6px; border:1px solid #ddd; border-radius:4px; font-size:12px; width:92px;">
                        <option value="AB"${grade === 'AB' ? ' selected' : ''}>AB</option>
                        <option value="BC"${grade === 'BC' ? ' selected' : ''}>BC</option>
                        <option value="ABC"${grade === 'ABC' ? ' selected' : ''}>ABC</option>
                    </select>
                </td>
                <td>
                    <input type="text" class="sp-spec" list="${listId}" placeholder="${USE_DWL_SPEC_DISPLAY ? '21x81x950' : '950x81x21'}" style="height:28px; padding:2px 6px; border:1px solid #ddd; border-radius:4px; width:160px; font-size:12px;">
                    <datalist id="${listId}" class="sp-spec-list"></datalist>
                </td>
                <td><input type="text" class="sp-m3" readonly style="width:86px; height:28px; padding:4px 6px; font-size:12px; background:#f8f9fa;"></td>
                <td class="sp-actions" style="width:140px;">
                    <button type="button" class="btn-inline" onclick="saveSecondaryRow(this)" style="padding:3px 10px; background:#28a745; color:#fff; border:none; border-radius:4px; font-size:12px;">{{ texts.save_row_btn }}</button>
                    <button type="button" class="btn-inline" onclick="this.closest('tr').remove()" style="padding:3px 10px; background:#dc3545; color:#fff; border:none; border-radius:4px; font-size:12px;">{{ texts.delete }}</button>
                </td>
            `;
            body.appendChild(tr);
            const idInput = tr.querySelector('.sp-id');
            const pcsInput = tr.querySelector('.sp-pcs');
            const specInput = tr.querySelector('.sp-spec');
            const specList = tr.querySelector(`#${listId}`);
            const refresh = () => {
                const pcsVal = 1;
                const prev = normalizeSecondarySpec(specInput.value);
                const cands = candidateSpecsByPcs(pcsVal);
                specList.innerHTML = '';
                cands.forEach(spec => {
                    const op = document.createElement('option');
                    op.value = specToDisplay(spec);
                    specList.appendChild(op);
                });
                if (cands.length > 0) {
                    if (cands.includes(prev)) {
                        specInput.value = specToDisplay(prev);
                    } else if (!prev) {
                        specInput.value = specToDisplay(cands[0]);
                    }
                }
                const info = calcSpecInfo(specInput.value, pcsVal);
                tr.querySelector('.sp-m3').value = info ? info.m3.toFixed(4) : '';
            };
            idInput.addEventListener('input', refresh);
            pcsInput.addEventListener('input', refresh);
            specInput.addEventListener('change', refresh);
            specInput.addEventListener('input', refresh);
            refresh();
        }

        async function saveSecondaryRow(btn) {
            const tr = btn.closest('tr');
            if (!tr) return;
            const pid = (tr.querySelector('.sp-id').value || '').trim();
            const pcs = 1;
            const grade = (tr.querySelector('.sp-grade').value || 'AB').trim().toUpperCase();
            const spec = (tr.querySelector('.sp-spec').value || '').trim();
            if (!pid || !pcs || pcs <= 0 || !spec) {
                alert('{{ texts.invalid_product_entry_msg }}');
                return;
            }
            const info = calcSpecInfo(spec, pcs);
            if (!info) {
                alert('{{ texts.invalid_product_entry_msg }}');
                return;
            }
            submitSecondaryProducts([{ id: pid, pcs: pcs, grade: grade, spec: info.spec, m3: info.m3 }]);
        }

        async function saveSecondaryAllRows() {
            const rows = Array.from(document.querySelectorAll('#secondary-product-body tr'));
            let added = 0;
            const entries = [];
            for (const tr of rows) {
                const pid = (tr.querySelector('.sp-id').value || '').trim();
                const pcs = 1;
                const grade = (tr.querySelector('.sp-grade').value || 'AB').trim().toUpperCase();
                const spec = (tr.querySelector('.sp-spec').value || '').trim();
                if (!pid || !pcs || pcs <= 0 || !spec) continue;
                const info = calcSpecInfo(spec, pcs);
                if (!info) continue;
                entries.push({ id: pid, pcs: pcs, grade: grade, spec: info.spec, m3: info.m3 });
                added += 1;
            }
            if (!added) {
                alert('{{ texts.invalid_product_entry_msg }}');
                return;
            }
            submitSecondaryProducts(entries);
        }

        function finishedInventorySpec(row) {
            return `${row.L}x${row.W}x${row.D}`;
        }

        function fillFinishedInventorySelect(selectId, label, values, currentValue) {
            const select = document.getElementById(selectId);
            if (!select) return;
            select.innerHTML = '';
            const allOption = document.createElement('option');
            allOption.value = '';
            allOption.textContent = `${label}: {{ texts.filter_all }}`;
            select.appendChild(allOption);
            values.forEach(value => {
                const op = document.createElement('option');
                op.value = value;
                op.textContent = `${label}: ${value}`;
                if (value === currentValue) op.selected = true;
                select.appendChild(op);
            });
            select.value = currentValue || '';
        }

        function uniqueNonEmptyValues(values) {
            const seen = {};
            const out = [];
            (values || []).forEach(function(value) {
                const key = String(value || '');
                if (!key || seen[key]) return;
                seen[key] = true;
                out.push(key);
            });
            return out;
        }

        function getFinishedInventoryFilters() {
            const gradeEl = document.getElementById('fi-filter-grade');
            const dEl = document.getElementById('fi-filter-d');
            const wEl = document.getElementById('fi-filter-w');
            const lEl = document.getElementById('fi-filter-l');
            const pcsEl = document.getElementById('fi-filter-pcs');
            const m3El = document.getElementById('fi-filter-m3');
            return {
                grade: ((gradeEl && gradeEl.value) || '').trim(),
                d: ((dEl && dEl.value) || '').trim(),
                w: ((wEl && wEl.value) || '').trim(),
                l: ((lEl && lEl.value) || '').trim(),
                pcs: ((pcsEl && pcsEl.value) || '').trim(),
                m3: ((m3El && m3El.value) || '').trim()
            };
        }

        function getFinishedInventoryFilteredRows() {
            const filters = getFinishedInventoryFilters();
            return finishedInventoryRows.filter(row => {
                if (filters.grade && row['等级'] !== filters.grade) return false;
                if (filters.d && String(row['D']) !== filters.d) return false;
                if (filters.w && String(row['W']) !== filters.w) return false;
                if (filters.l && String(row['L']) !== filters.l) return false;
                if (filters.pcs && String(row['数量']) !== filters.pcs) return false;
                if (filters.m3 && Number(row['m³'] || 0).toFixed(4) !== filters.m3) return false;
                return true;
            });
        }

        function refreshFinishedInventoryFilterOptions() {
            const current = getFinishedInventoryFilters();
            const gradeRows = finishedInventoryRows.filter(row => {
                if (current.d && String(row['D']) !== current.d) return false;
                if (current.w && String(row['W']) !== current.w) return false;
                if (current.l && String(row['L']) !== current.l) return false;
                if (current.pcs && String(row['数量']) !== current.pcs) return false;
                if (current.m3 && Number(row['m³'] || 0).toFixed(4) !== current.m3) return false;
                return true;
            });
            const dRows = finishedInventoryRows.filter(row => {
                if (current.grade && row['等级'] !== current.grade) return false;
                if (current.w && String(row['W']) !== current.w) return false;
                if (current.l && String(row['L']) !== current.l) return false;
                if (current.pcs && String(row['数量']) !== current.pcs) return false;
                if (current.m3 && Number(row['m³'] || 0).toFixed(4) !== current.m3) return false;
                return true;
            });
            const wRows = finishedInventoryRows.filter(row => {
                if (current.grade && row['等级'] !== current.grade) return false;
                if (current.d && String(row['D']) !== current.d) return false;
                if (current.l && String(row['L']) !== current.l) return false;
                if (current.pcs && String(row['数量']) !== current.pcs) return false;
                if (current.m3 && Number(row['m³'] || 0).toFixed(4) !== current.m3) return false;
                return true;
            });
            const lRows = finishedInventoryRows.filter(row => {
                if (current.grade && row['等级'] !== current.grade) return false;
                if (current.d && String(row['D']) !== current.d) return false;
                if (current.w && String(row['W']) !== current.w) return false;
                if (current.pcs && String(row['数量']) !== current.pcs) return false;
                if (current.m3 && Number(row['m³'] || 0).toFixed(4) !== current.m3) return false;
                return true;
            });
            const pcsRows = finishedInventoryRows.filter(row => {
                if (current.grade && row['等级'] !== current.grade) return false;
                if (current.d && String(row['D']) !== current.d) return false;
                if (current.w && String(row['W']) !== current.w) return false;
                if (current.l && String(row['L']) !== current.l) return false;
                if (current.m3 && Number(row['m³'] || 0).toFixed(4) !== current.m3) return false;
                return true;
            });
            const m3Rows = finishedInventoryRows.filter(row => {
                if (current.grade && row['等级'] !== current.grade) return false;
                if (current.d && String(row['D']) !== current.d) return false;
                if (current.w && String(row['W']) !== current.w) return false;
                if (current.l && String(row['L']) !== current.l) return false;
                if (current.pcs && String(row['数量']) !== current.pcs) return false;
                return true;
            });

            fillFinishedInventorySelect('fi-filter-grade', '{{ texts.filter_grade }}', uniqueNonEmptyValues(gradeRows.map(row => row['等级'])).sort(), current.grade);
            fillFinishedInventorySelect('fi-filter-d', 'D', uniqueNonEmptyValues(dRows.map(row => String(row['D']))).sort((a, b) => Number(a) - Number(b)), current.d);
            fillFinishedInventorySelect('fi-filter-w', 'W', uniqueNonEmptyValues(wRows.map(row => String(row['W']))).sort((a, b) => Number(a) - Number(b)), current.w);
            fillFinishedInventorySelect('fi-filter-l', 'L', uniqueNonEmptyValues(lRows.map(row => String(row['L']))).sort((a, b) => Number(a) - Number(b)), current.l);
            fillFinishedInventorySelect('fi-filter-pcs', '{{ texts.filter_pcs }}', uniqueNonEmptyValues(pcsRows.map(row => String(row['数量']))).sort((a, b) => Number(a) - Number(b)), current.pcs);
            fillFinishedInventorySelect('fi-filter-m3', 'm³', uniqueNonEmptyValues(m3Rows.map(row => Number(row['m³'] || 0).toFixed(4))).sort((a, b) => Number(a) - Number(b)), current.m3);
        }

        function renderFinishedInventoryRows() {
            const body = document.getElementById('finished-inventory-body');
            const rows = getFinishedInventoryFilteredRows();
            body.innerHTML = '';
            rows.forEach(row => {
                const tr = document.createElement('tr');
                const deleteCell = IS_ADMIN
                    ? `<td class="sp-actions" style="width:84px;">
                            <button type="button" class="btn-inline" onclick="deleteFinishedInventoryRow('${row['product_id']}')" style="padding:3px 10px; background:#dc3545; color:#fff; border:none; border-radius:4px; font-size:12px;">{{ texts.delete }}</button>
                       </td>`
                    : '';
                tr.innerHTML = `
                    <td>${row['编号'] || ''}</td>
                    <td>${row['D'] || ''}</td>
                    <td>${row['W'] || ''}</td>
                    <td>${row['L'] || ''}</td>
                    <td>${row['数量'] || 0}</td>
                    <td>${Number(row['m³'] || 0).toFixed(4)}</td>
                    <td>${row['重量(kg)'] || ''}</td>
                    <td>${row['等级'] || ''}</td>
                    <td>库存</td>
                    <td>${row['规格'] || ''}</td>
                    ${deleteCell}
                `;
                body.appendChild(tr);
            });

            const exportBtn = document.getElementById('finished-inventory-export');
            if (exportBtn) {
                const filters = getFinishedInventoryFilters();
                const url = new URL('/export/finished_products_current', window.location.origin);
                url.searchParams.set('lang', '{{ lang }}');
                if (filters.grade) url.searchParams.set('grade', filters.grade);
                if (filters.d) url.searchParams.set('d', filters.d);
                if (filters.w) url.searchParams.set('w', filters.w);
                if (filters.l) url.searchParams.set('l', filters.l);
                if (filters.pcs) url.searchParams.set('pcs', filters.pcs);
                if (filters.m3) url.searchParams.set('m3', filters.m3);
                exportBtn.dataset.href = url.toString();
            }
        }

        function triggerBlobDownload(blob, filename) {
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = filename || 'download.xlsx';
            document.body.appendChild(a);
            a.click();
            a.remove();
            setTimeout(() => window.URL.revokeObjectURL(url), 1000);
        }

        function downloadFromUrl(url, fallbackName) {
            fetch(url, { credentials: 'same-origin' })
            .then(response => {
                if (!response.ok) {
                    throw new Error('download failed');
                }
                const disposition = response.headers.get('Content-Disposition') || '';
                var filename = fallbackName;
                if (disposition) {
                    const utf8Flag = "filename*=UTF-8''";
                    const utf8Pos = disposition.indexOf(utf8Flag);
                    if (utf8Pos >= 0) {
                        const raw = disposition.slice(utf8Pos + utf8Flag.length).split(';')[0].trim();
                        if (raw) filename = decodeURIComponent(raw);
                    } else {
                        const plainFlag = 'filename=';
                        const plainPos = disposition.toLowerCase().indexOf(plainFlag);
                        if (plainPos >= 0) {
                            let raw = disposition.slice(plainPos + plainFlag.length).split(';')[0].trim();
                            if ((raw[0] === '"' && raw[raw.length - 1] === '"') || (raw[0] === "'" && raw[raw.length - 1] === "'")) {
                                raw = raw.slice(1, -1);
                            }
                            if (raw) filename = raw;
                        }
                    }
                }
                return response.blob().then(blob => {
                    triggerBlobDownload(blob, filename);
                });
            })
            .catch(() => {
                window.location.href = url;
            });
        }

        function downloadFromPost(url, payload, fallbackName, failMessage) {
            fetch(url, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'same-origin',
                body: JSON.stringify(payload || {})
            })
            .then(response => {
                if (!response.ok) {
                    return response.json()
                    .then(data => {
                        throw new Error((data && data.error) || failMessage || 'download failed');
                    })
                    .catch(() => {
                        throw new Error(failMessage || 'download failed');
                    });
                }
                const disposition = response.headers.get('Content-Disposition') || '';
                let filename = fallbackName;
                if (disposition) {
                    const utf8Flag = "filename*=UTF-8''";
                    const utf8Pos = disposition.indexOf(utf8Flag);
                    if (utf8Pos >= 0) {
                        const raw = disposition.slice(utf8Pos + utf8Flag.length).split(';')[0].trim();
                        if (raw) filename = decodeURIComponent(raw);
                    } else {
                        const plainFlag = 'filename=';
                        const plainPos = disposition.toLowerCase().indexOf(plainFlag);
                        if (plainPos >= 0) {
                            let raw = disposition.slice(plainPos + plainFlag.length).split(';')[0].trim();
                            if ((raw[0] === '"' && raw[raw.length - 1] === '"') || (raw[0] === "'" && raw[raw.length - 1] === "'")) {
                                raw = raw.slice(1, -1);
                            }
                            if (raw) filename = raw;
                        }
                    }
                }
                return response.blob().then(blob => {
                    triggerBlobDownload(blob, filename);
                });
            })
            .catch(err => {
                alert((err && err.message) || (failMessage || 'download failed'));
            });
        }

        function downloadFinishedInventory() {
            const btn = document.getElementById('finished-inventory-export');
            const url = btn && btn.dataset ? btn.dataset.href : '';
            if (!url) return;
            downloadFromUrl(url, 'finished_inventory.xlsx');
        }

        function downloadFinishedLabels() {
            const url = new URL('/export/finished_labels', window.location.origin);
            url.searchParams.set('lang', '{{ lang }}');
            downloadFromUrl(url.toString(), 'finished_labels.xlsx');
        }

        function applyFinishedInventoryFilters() {
            refreshFinishedInventoryFilterOptions();
            renderFinishedInventoryRows();
        }

        function openFinishedInventoryModal() {
            fetch('/api/finished_inventory?lang={{ lang }}')
            .then(r => r.json())
            .then(data => {
                finishedInventoryRows = Array.isArray(data.rows) ? data.rows : [];
                fillFinishedInventorySelect('fi-filter-grade', '{{ texts.filter_grade }}', uniqueNonEmptyValues(finishedInventoryRows.map(row => row['等级'])).sort(), '');
                fillFinishedInventorySelect('fi-filter-d', 'D', uniqueNonEmptyValues(finishedInventoryRows.map(row => String(row['D']))).sort((a, b) => Number(a) - Number(b)), '');
                fillFinishedInventorySelect('fi-filter-w', 'W', uniqueNonEmptyValues(finishedInventoryRows.map(row => String(row['W']))).sort((a, b) => Number(a) - Number(b)), '');
                fillFinishedInventorySelect('fi-filter-l', 'L', uniqueNonEmptyValues(finishedInventoryRows.map(row => String(row['L']))).sort((a, b) => Number(a) - Number(b)), '');
                fillFinishedInventorySelect('fi-filter-pcs', '{{ texts.filter_pcs }}', uniqueNonEmptyValues(finishedInventoryRows.map(row => String(row['数量']))).sort((a, b) => Number(a) - Number(b)), '');
                fillFinishedInventorySelect('fi-filter-m3', 'm³', uniqueNonEmptyValues(finishedInventoryRows.map(row => Number(row['m³'] || 0).toFixed(4))).sort((a, b) => Number(a) - Number(b)), '');
                renderFinishedInventoryRows();
                document.getElementById('finished-inventory-modal').style.display = 'flex';
            });
        }

        function closeFinishedInventoryModal() {
            document.getElementById('finished-inventory-modal').style.display = 'none';
        }

        function updateShipmentSelectedCount() {
            const el = document.getElementById('shipment-selected-count');
            if (el) el.textContent = String(selectedShipmentProducts.size);
        }

        function renderShipmentPicker() {
            const box = document.getElementById('shipment-product-picker');
            if (!box) return;
            box.innerHTML = '';
            shipmentInventoryRows.forEach(row => {
                const item = document.createElement('div');
                item.className = 'shipment-pick-item';
                if (selectedShipmentProducts.has(row.product_id)) {
                    item.classList.add('active');
                }
                item.innerHTML = `
                    <div>
                        <div class="shipment-pick-code">${row['编号'] || row.product_id}</div>
                        <div class="shipment-pick-meta">${row['规格'] || ''} | ${row['等级'] || ''} | ${row['数量'] || 0} pcs | ${Number(row['m³'] || 0).toFixed(4)} m³</div>
                    </div>
                `;
                const setSelected = (selected) => {
                    if (selected) {
                        selectedShipmentProducts.add(row.product_id);
                        item.classList.add('active');
                    } else {
                        selectedShipmentProducts.delete(row.product_id);
                        item.classList.remove('active');
                    }
                    updateShipmentSelectedCount();
                };
                item.addEventListener('mousedown', (event) => {
                    if (event.button !== 0) return;
                    event.preventDefault();
                    shipmentPickerState.dragActive = true;
                    shipmentPickerState.dragValue = !selectedShipmentProducts.has(row.product_id);
                    setSelected(shipmentPickerState.dragValue);
                });
                item.addEventListener('mouseenter', () => {
                    if (!shipmentPickerState.dragActive) return;
                    setSelected(shipmentPickerState.dragValue);
                });
                box.appendChild(item);
            });
            if (!shipmentInventoryRows.length) {
                box.innerHTML = `<div style="padding:12px; color:#6b7280;">{{ texts.tray_picker_empty }}</div>`;
            }
            box.onmouseleave = () => {
                shipmentPickerState.dragActive = false;
            };
            updateShipmentSelectedCount();
        }

        function buildShipmentPayload() {
            return {
                customer: (document.getElementById('shipment-customer').value || '').trim(),
                destination: (document.getElementById('shipment-destination').value || '').trim(),
                departure_at: (document.getElementById('shipment-departure-at').value || '').trim(),
                vehicle_no: (document.getElementById('shipment-vehicle-no').value || '').trim(),
                driver_name: (document.getElementById('shipment-driver-name').value || '').trim(),
                eta_hours_to_yangon: parseInt(document.getElementById('shipment-eta-hours').value || '36', 10),
                remark: (document.getElementById('shipment-remark').value || '').trim(),
                product_ids: Array.from(selectedShipmentProducts)
            };
        }

        function exportSelectedShipmentDetails() {
            const payload = buildShipmentPayload();
            if (!payload.product_ids.length) {
                alert('{{ texts.shipment_select_required }}');
                return;
            }
            downloadFromPost(
                '/export/shipping_selected_details?lang={{ lang }}',
                payload,
                'shipment_selected_details.xlsx',
                '{{ texts.shipment_export_failed }}'
            );
        }

        function openCreateShipmentModal() {
            selectedShipmentProducts = new Set();
            const departureInput = document.getElementById('shipment-departure-at');
            if (departureInput && !departureInput.value) {
                departureInput.value = new Date(Date.now() - new Date().getTimezoneOffset() * 60000).toISOString().slice(0, 16);
            }
            fetch('/api/finished_inventory?lang={{ lang }}')
            .then(r => r.json())
            .then(data => {
                shipmentInventoryRows = Array.isArray(data.rows) ? data.rows : [];
                renderShipmentPicker();
                document.getElementById('create-shipment-modal').style.display = 'flex';
            })
            .catch(() => alert('{{ texts.shipment_create_failed }}'));
        }

        function closeCreateShipmentModal() {
            document.getElementById('create-shipment-modal').style.display = 'none';
        }

        function createShipment() {
            const payload = buildShipmentPayload();
            fetch('/api/shipping_orders?lang={{ lang }}', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            })
            .then(r => r.json().then(data => ({ ok: r.ok, data })))
            .then(({ok, data}) => {
                if (!ok) throw new Error(data.error || '{{ texts.shipment_create_failed }}');
                closeCreateShipmentModal();
                alert(`{{ texts.shipment_create_success }}: ${data.shipment_no || ''}`);
                storeScrollPosition();
                location.reload();
            })
            .catch(err => alert(err.message || '{{ texts.shipment_create_failed }}'));
        }

        function renderShippingBoardRows() {
            const body = document.getElementById('shipping-board-body');
            body.innerHTML = '';
            if (!shippingOrderRows.length) {
                const tr = document.createElement('tr');
                tr.innerHTML = `<td colspan="12" style="text-align:center; color:#6b7280;">{{ texts.shipment_empty }}</td>`;
                body.appendChild(tr);
                return;
            }
            shippingOrderRows.forEach(row => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td>${row.shipment_no || ''}</td>
                    <td>${row.customer || ''}</td>
                    <td>${row.destination || ''}</td>
                    <td>${(row.departure_at || '').replace('T', ' ').slice(0, 16)}</td>
                    <td>${row.vehicle_no || ''}</td>
                    <td>${row.driver_name || ''}</td>
                    <td>${row.eta_hours_to_yangon || 36}</td>
                    <td>${row.total_pcs || 0} / ${row.product_count || 0}件</td>
                    <td>${Number(row.total_volume || 0).toFixed(4)}</td>
                    <td><span class="shipment-status-badge ${shipmentStatusClass(row.status)}">${row.status || ''}</span></td>
                    <td>${(row.updated_at || row.created_at || '').replace('T', ' ').slice(0, 16)}</td>
                    <td>
                        <div style="display:flex; gap:6px; flex-wrap:wrap;">
                            <button type="button" onclick="updateShipmentStatus('${row.shipment_no}', '仰光仓已到')" style="padding:4px 8px; background:#0d6efd;">{{ texts.mark_signed }}</button>
                            <button type="button" onclick="updateShipmentStatus('${row.shipment_no}', '已从仰光出港')" style="padding:4px 8px; background:#198754;">{{ texts.mark_yangon_departed }}</button>
                            <button type="button" onclick="updateShipmentStatus('${row.shipment_no}', '中国港口已到')" style="padding:4px 8px; background:#20c997;">{{ texts.mark_china_arrived }}</button>
                            <button type="button" onclick="updateShipmentStatus('${row.shipment_no}', '异常')" style="padding:4px 8px; background:#dc3545;">{{ texts.mark_exception }}</button>
                        </div>
                    </td>
                `;
                body.appendChild(tr);
            });
        }

        function loadShippingBoard() {
            fetch('/api/shipping_orders?lang={{ lang }}')
            .then(r => r.json())
            .then(data => {
                shippingOrderRows = Array.isArray(data.rows) ? data.rows : [];
                renderShippingBoardRows();
            })
            .catch(() => alert('{{ texts.shipment_status_update_failed }}'));
        }

        function openShippingBoardModal() {
            document.getElementById('shipping-board-modal').style.display = 'flex';
            loadShippingBoard();
        }

        function closeShippingBoardModal() {
            document.getElementById('shipping-board-modal').style.display = 'none';
        }

        function _todayIsoDate() {
            const d = new Date();
            d.setMinutes(d.getMinutes() - d.getTimezoneOffset());
            return d.toISOString().slice(0, 10);
        }

        function _renderDailyRows(tbodyId, dataMap, labelMap, orderedKeys) {
            const body = document.getElementById(tbodyId);
            if (!body) return;
            body.innerHTML = '';
            const keys = Array.isArray(orderedKeys) && orderedKeys.length
                ? orderedKeys.filter((k) => Object.prototype.hasOwnProperty.call(dataMap || {}, k))
                : Object.keys(dataMap || {});
            keys.forEach((key) => {
                const tr = document.createElement('tr');
                const label = (labelMap && labelMap[key]) ? labelMap[key] : key;
                let value = dataMap[key];
                if (String(key || '').includes('_m3')) {
                    const n = Number(value);
                    if (!Number.isNaN(n)) value = n.toFixed(3);
                }
                tr.innerHTML = `<th>${label}</th><td>${value ?? ''}</td>`;
                body.appendChild(tr);
            });
        }

        function openDailyReportModal() {
            const input = document.getElementById('daily-report-date');
            if (input && !input.value) input.value = _todayIsoDate();
            document.getElementById('daily-report-modal').style.display = 'flex';
            loadDailyReportData();
        }

        function closeDailyReportModal() {
            document.getElementById('daily-report-modal').style.display = 'none';
        }

        function openLogEntryListModal() {
            document.getElementById('log-entry-list-modal').style.display = 'flex';
            loadLogEntryList();
        }

        function closeLogEntryListModal() {
            document.getElementById('log-entry-list-modal').style.display = 'none';
        }

        function loadLogEntryList() {
            const body = document.getElementById('log-entry-list-body');
            const totalEl = document.getElementById('log-entry-list-total');
            if (!body || !totalEl) return;
            fetch('/api/log_entries?lang={{ lang }}&limit=300')
            .then(r => r.json())
            .then(data => {
                const rows = Array.isArray(data.rows) ? data.rows : [];
                logEntryListRows = rows;
                body.innerHTML = '';
                rows.forEach(row => {
                    const tr = document.createElement('tr');
                    const actions = [];
                    if (CAN_EXPORT_LOG) {
                        actions.push(`<button type="button" onclick="exportSingleLogEntry(${Number(row.id || 0)})" style="background:#198754;">{{ texts.export }}</button>`);
                    }
                    if (IS_ADMIN) {
                        actions.push(`<button type="button" onclick="deleteSingleLogEntry(${Number(row.id || 0)})" style="background:#dc3545;">{{ texts.delete }}</button>`);
                    }
                    const actionCell = actions.length ? actions.join(' ') : '-';
                    tr.innerHTML = `<td>${row.created_at || ''}</td><td>${row.driver_name || ''}</td><td>${row.truck_number || ''}</td><td>${Number(row.log_amount || 0).toFixed(4)}</td><td>${actionCell}</td>`;
                    body.appendChild(tr);
                });
                if (!rows.length) {
                    const tr = document.createElement('tr');
                    tr.innerHTML = '<td colspan="5" style="color:#6b7280;">暂无</td>';
                    body.appendChild(tr);
                }
                totalEl.textContent = Number(data.total_mt || 0).toFixed(4);
            })
            .catch(() => {
                body.innerHTML = '<tr><td colspan="5" style="color:#b91c1c;">加载失败</td></tr>';
                totalEl.textContent = '0.0000';
            });
        }

        function exportSingleLogEntry(logEntryId) {
            if (!CAN_EXPORT_LOG || !Number(logEntryId || 0)) return;
            const url = new URL('/export/log_entries_detail', window.location.origin);
            url.searchParams.set('lang', '{{ lang }}');
            url.searchParams.set('log_entry_id', String(logEntryId));
            window.location.href = url.toString();
        }

        function deleteSingleLogEntry(logEntryId) {
            if (!IS_ADMIN || !Number(logEntryId || 0)) return;
            if (!window.confirm('{{ texts.confirm_delete_user }}')) return;
            fetch(`/api/log_entries/${Number(logEntryId)}?lang={{ lang }}`, { method: 'DELETE' })
            .then(r => r.json().then(data => ({ ok: r.ok, data })))
            .then(({ ok, data }) => {
                if (!ok) throw new Error((data && data.error) || 'delete failed');
                loadLogEntryList();
            })
            .catch(err => alert(err.message || 'delete failed'));
        }

        function exportDailyReportFromModal() {
            const date = encodeURIComponent((document.getElementById('daily-report-date').value || _todayIsoDate()));
            window.location.href = `/export/report/daily?lang={{ lang }}&date=${date}`;
        }

        function loadDailyReportData() {
            const date = (document.getElementById('daily-report-date').value || _todayIsoDate());
            fetch(`/api/report/daily?lang={{ lang }}&date=${encodeURIComponent(date)}`)
            .then(r => r.json().then(data => ({ ok: r.ok, data })))
            .then(({ok, data}) => {
                if (!ok) throw new Error(data.error || 'load daily report failed');
                const labels = data.display_labels || {};
                const order = data.display_order || {};
                document.getElementById('daily-report-range').textContent = `{{ texts.report_range }}: ${(data.range && data.range.start) || ''} ~ ${(data.range && data.range.end) || ''}`;
                document.getElementById('daily-report-note').textContent = (data.meta && data.meta.note) || '';
                _renderDailyRows('daily-report-summary-body', data.summary || {}, labels.summary || {}, order.summary || []);
                _renderDailyRows('daily-report-inv-body', data.inventory_snapshot || {}, labels.inventory_snapshot || {}, order.inventory_snapshot || []);
                _renderDailyRows('daily-report-kiln-body', data.kiln_status || {}, labels.kiln_status || {}, order.kiln_status || []);
                const counts = {};
                const breakdown = data.breakdown || {};
                Object.keys(breakdown).forEach((k) => { counts[k] = Array.isArray(breakdown[k]) ? breakdown[k].length : 0; });
                _renderDailyRows('daily-report-count-body', counts, labels.breakdown || {}, order.breakdown || []);
            })
            .catch(err => alert(err.message || 'load daily report failed'));
        }

        function updateShipmentStatus(shipmentNo, status) {
            fetch('/api/shipping_orders/' + encodeURIComponent(shipmentNo) + '?lang={{ lang }}', {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ status })
            })
            .then(r => r.json().then(data => ({ ok: r.ok, data })))
            .then(({ok, data}) => {
                if (!ok) throw new Error(data.error || '{{ texts.shipment_status_update_failed }}');
                loadShippingBoard();
            })
            .catch(err => alert(err.message || '{{ texts.shipment_status_update_failed }}'));
        }

        function deleteFinishedInventoryRow(productId) {
            if (!IS_ADMIN || !productId) return;
            fetch('/api/finished_inventory/' + encodeURIComponent(productId) + '?lang={{ lang }}', {
                method: 'DELETE'
            })
            .then(r => r.json().then(data => ({ ok: r.ok, data })))
            .then(({ok, data}) => {
                if (!ok) throw new Error(data.error || 'delete failed');
                finishedInventoryRows = finishedInventoryRows.filter(row => row['编号'] !== productId);
                applyFinishedInventoryFilters();
            })
            .catch(err => alert(err.message || 'delete failed'));
        }

        function openKilnTrayModal(kilnId) {
            currentKilnId = kilnId;
            fetch('/api/kiln_trays/' + encodeURIComponent(kilnId) + '?lang={{ lang }}')
            .then(r => r.json())
            .then(data => {
                const body = document.getElementById('kiln-tray-body');
                body.innerHTML = '';
                const trays = Array.isArray(data.trays) ? data.trays : [];
                // 中文注释：优先使用后端返回的权威总托数（含管理员修正值），前端仅做兜底统计。
                const fallbackTotal = trays.reduce((sum, t) => sum + (Number(t.count) > 0 ? Number(t.count) : 1), 0);
                const totalInKilnTrays = Number(data.total_trays);
                const shownTotal = Number.isFinite(totalInKilnTrays) && totalInKilnTrays >= 0 ? totalInKilnTrays : fallbackTotal;
                document.getElementById('kiln-modal-title').textContent =
                    '{{ texts.kiln_tray_detail_title }} ' + kilnId + ' | {{ texts.kiln_current_total_trays }}: ' + shownTotal;
                trays.forEach(t => addKilnTrayRow(t.id || '', t.spec || '', t.count || 1));
                if (!trays.length) addKilnTrayRow('', '', 1);
                document.getElementById('kiln-tray-modal').style.display = 'flex';
            })
            .catch(() => alert('{{ texts.load_kiln_trays_failed }}'));
        }

        function closeKilnTrayModal() {
            document.getElementById('kiln-tray-modal').style.display = 'none';
            currentKilnId = null;
        }

        function addKilnTrayRow(id = '', spec = '', count = 1) {
            const body = document.getElementById('kiln-tray-body');
            const tr = document.createElement('tr');
            const readonlyAttr = IS_ADMIN ? '' : 'readonly';
            const disabledAttr = IS_ADMIN ? '' : 'disabled';
            const actionCell = IS_ADMIN
                ? `<td><button type="button" onclick="this.closest('tr').remove()">{{ texts.delete }}</button></td>`
                : `<td></td>`;
            tr.innerHTML = `
                <td><input type="text" class="kt-id" value="${id}" ${readonlyAttr}></td>
                <td><input type="text" class="kt-spec" value="${spec}" ${readonlyAttr}></td>
                <td><input type="number" class="kt-count" min="1" value="${count}" ${disabledAttr}></td>
                ${actionCell}
            `;
            body.appendChild(tr);
        }

        function saveKilnTrays() {
            if (!IS_ADMIN) {
                alert('{{ texts.no_admin_perm }}');
                return;
            }
            if (!currentKilnId) return;
            const rows = Array.from(document.querySelectorAll('#kiln-tray-body tr'));
            const trays = rows.map(row => ({
                id: (row.querySelector('.kt-id').value || '').trim(),
                spec: (row.querySelector('.kt-spec').value || '').trim(),
                count: parseInt(row.querySelector('.kt-count').value || '0', 10)
            })).filter(t => t.id && t.count > 0);

            fetch('/api/kiln_trays/' + encodeURIComponent(currentKilnId) + '?lang={{ lang }}', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ trays })
            })
            .then(r => r.json().then(data => ({ ok: r.ok, data })))
            .then(({ok, data}) => {
                if (!ok) throw new Error(data.error || '{{ texts.save_kiln_trays_failed }}');
                closeKilnTrayModal();
                storeScrollPosition();
                location.reload();
            })
            .catch(err => alert(err.message || '{{ texts.save_kiln_trays_failed }}'));
        }

        function focusLastModalInput(bodySelector, inputSelector) {
            const body = document.querySelector(bodySelector);
            if (!body) return;
            const last = body.querySelector(`tr:last-child ${inputSelector}`);
            if (last) last.focus();
        }

        function bindModalEnterShortcuts() {
            document.addEventListener('keydown', (event) => {
                if (event.key !== 'Enter') return;
                const target = event.target;
                if (!target || target.tagName === 'TEXTAREA' || target.tagName === 'BUTTON') return;
                const modal = target.closest('.modal-mask');
                if (!modal || modal.style.display !== 'flex') return;

                let handled = false;
                if (modal.id === 'sort-tray-modal') {
                    addSortTrayRow();
                    focusLastModalInput('#sort-tray-body', '.st-id');
                    handled = true;
                } else if (modal.id === 'secondary-product-modal') {
                    addSecondaryProductRow();
                    focusLastModalInput('#secondary-product-body', '.sp-id');
                    handled = true;
                } else if (modal.id === 'kiln-tray-modal' && IS_ADMIN) {
                    addKilnTrayRow();
                    focusLastModalInput('#kiln-tray-body', '.kt-id');
                    handled = true;
                } else if (modal.id === 'pending-tray-modal' && IS_ADMIN) {
                    addPendingTrayRow();
                    focusLastModalInput('#pending-tray-body', '.pt-id');
                    handled = true;
                }

                if (handled) {
                    event.preventDefault();
                }
            });
        }

        document.addEventListener('submit', (event) => {
            if (event.target && event.target.tagName === 'FORM') {
                storeScrollPosition();
            }
        }, true);

        ['saw_tm_input', 'saw_trays_input', 'bark_m3_input', 'dust_bags_input'].forEach(id => {
            const input = document.getElementById(id);
            if (!input) return;
            input.addEventListener('input', () => {
                const hidden = document.getElementById('saw_machine_payload');
                if (hidden) hidden.value = '';
            });
        });

        const logDriverEl = document.getElementById('log-modal-driver');
        if (logDriverEl) {
            logDriverEl.addEventListener('input', () => {
                if (logDriverFetchTimer) clearTimeout(logDriverFetchTimer);
                logDriverFetchTimer = setTimeout(fetchLogDriverProfile, 260);
            });
            logDriverEl.addEventListener('blur', fetchLogDriverProfile);
        }
        const logTruckEl = document.getElementById('log-modal-truck');
        if (logTruckEl) {
            logTruckEl.addEventListener('blur', fetchLogDriverProfile);
        }

        const sortInputEl = document.getElementById('sort_trays_input');
        if (sortInputEl) {
            sortInputEl.addEventListener('input', refreshFlowMissingReminders);
            sortInputEl.addEventListener('blur', refreshFlowMissingReminders);
        }
        const secondarySortInputEl = document.getElementById('secondary_sort_trays');
        if (secondarySortInputEl) {
            secondarySortInputEl.addEventListener('input', refreshFlowMissingReminders);
            secondarySortInputEl.addEventListener('blur', refreshFlowMissingReminders);
        }
        refreshFlowMissingReminders();
        refreshEntryReminderStrip();
        setInterval(refreshEntryReminderStrip, 300000);
        renderOverviewRadar();

        restoreScrollPosition();
        bindModalEnterShortcuts();

        function openStockAdjustModal(section, value) {
            document.getElementById('adjust_section').value = section;
            const valueRow = document.getElementById('adjust_value_row');
            const byRows = document.getElementById('adjust_byproduct_rows');
            if (section === 'byproduct') {
                valueRow.style.display = 'none';
                byRows.style.display = 'block';
            } else {
                valueRow.style.display = 'block';
                byRows.style.display = 'none';
                document.getElementById('adjust_value').value = value || '';
                document.getElementById('adjust_value').step = (section === 'log') ? '0.0001' : ((section === 'dip_chem') ? '0.01' : '1');
            }
            document.getElementById('stock-adjust-modal').style.display = 'flex';
        }

        function openByproductAdjustModal(bark, dust, wasteSegment) {
            openStockAdjustModal('byproduct', '');
            document.getElementById('adjust_bark_stock_ks').value = bark || '';
            document.getElementById('adjust_dust_bag_stock').value = dust || '';
            document.getElementById('adjust_waste_segment_bag_stock').value = wasteSegment || '';
        }

        function closeStockAdjustModal() {
            document.getElementById('stock-adjust-modal').style.display = 'none';
        }

        function openKilnAdjustModal(kilnId, status, elapsed, remaining, total, left) {
            document.getElementById('kiln_adjust_id').value = kilnId;
            document.getElementById('kiln_adjust_status').value = status || 'empty';
            document.getElementById('kiln_adjust_elapsed').value = elapsed || 0;
            document.getElementById('kiln_adjust_remaining').value = remaining || 0;
            document.getElementById('kiln_adjust_total').value = total || '';
            document.getElementById('kiln_adjust_left').value = left || '';
            document.getElementById('kiln-adjust-modal').style.display = 'flex';
        }

        function closeKilnAdjustModal() {
            document.getElementById('kiln-adjust-modal').style.display = 'none';
        }

        function submitKilnAdjust(event) {
            if (event) event.preventDefault();
            const form = document.getElementById('kiln-adjust-form');
            if (!form) return false;
            const data = new URLSearchParams(new FormData(form)).toString();
            fetch(form.action, {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body: data
            })
            .then(response => response.text())
            .then(html => {
                replacePageHtml(html);
            })
            .catch(err => {
                alert(err && err.message ? err.message : 'submit failed');
            });
            return false;
        }

        (function autoHideToast(){
            const toast = document.getElementById('result-toast');
            if (!toast) return;
            setTimeout(() => {
                toast.style.transition = 'opacity 0.3s ease';
                toast.style.opacity = '0';
                setTimeout(() => toast.remove(), 320);
            }, 3000);
        })();

        (function clearResultQueryOnce(){
            try {
                const url = new URL(window.location.href);
                if (!url.searchParams.has('result') && !url.searchParams.has('error')) return;
                url.searchParams.delete('result');
                url.searchParams.delete('error');
                const clean = url.pathname + (url.searchParams.toString() ? ('?' + url.searchParams.toString()) : '') + url.hash;
                window.history.replaceState({}, '', clean);
            } catch (_) {}
        })();
    </script>
</body>
</html>
"""
