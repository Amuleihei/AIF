# 管理员用户页面模板
ADMIN_USERS_TEMPLATE = """
<!DOCTYPE html>
<html lang="{{ lang or 'zh' }}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ texts.get('user_management', '用户管理') }}</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        h1 { color: #333; text-align: center; }
        .user-table { width: 100%; border-collapse: collapse; margin: 20px 0; }
        .user-table th, .user-table td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }
        .user-table th { background: #f8f9fa; font-weight: bold; }
        .btn { padding: 8px 16px; border: none; border-radius: 4px; cursor: pointer; margin: 2px; }
        .btn-primary { background: #007bff; color: white; }
        .btn-danger { background: #dc3545; color: white; }
        .btn-success { background: #28a745; color: white; }
        .form-group { margin: 15px 0; }
        input, select { padding: 8px; border: 1px solid #ddd; border-radius: 4px; width: 200px; }
        .back-link { display: inline-block; margin-bottom: 20px; color: #007bff; text-decoration: none; }
        .link-inline { display: inline-block; margin-left: 10px; color: #007bff; text-decoration: none; }
        .role-admin { color: #dc3545; font-weight: bold; }
        .role-boss { color: #28a745; font-weight: bold; }
        .role-finance { color: #ffc107; font-weight: bold; }
    </style>
</head>
<body>
    <div class="container">
        <a href="{{ url_for('admin_root') }}" class="back-link">← 管理总览</a>
        <a href="{{ url_for('admin_audit_logs') }}" class="link-inline">{{ texts.get('audit_logs', '审计日志') }}</a>
        <a href="{{ url_for('admin_alert_settings') }}" class="link-inline">预警值设置</a>
        <h1>{{ texts.get('user_management', '用户管理') }}</h1>
        
        <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0;">
            <h3>{{ texts.get('add_user', '添加用户') }}</h3>
            <form id="addUserForm">
                <div class="form-group">
                    <label>{{ texts.get('username', '用户名') }}:</label>
                    <input type="text" id="newUsername" required>
                </div>
                <div class="form-group">
                    <label>{{ texts.get('password', '密码') }}:</label>
                    <input type="password" id="newPassword" required>
                </div>
                <div class="form-group">
                    <label>{{ texts.get('role', '角色') }}:</label>
                    <select id="newRole" required>
                        <option value="boss">{{ texts.get('boss', '老板') }}</option>
                        <option value="finance">{{ texts.get('finance', '统计财务') }}</option>
                        <option value="admin">{{ texts.get('admin', '管理员') }}</option>
                    </select>
                </div>
                <button type="submit" class="btn btn-success">{{ texts.get('add', '添加') }}</button>
            </form>
        </div>
        
        <table class="user-table">
            <thead>
                <tr>
                    <th>{{ texts.get('username', '用户名') }}</th>
                    <th>{{ texts.get('role', '角色') }}</th>
                    <th>{{ texts.get('created_at', '创建时间') }}</th>
                    <th>账号安全状态</th>
                    <th>{{ texts.get('actions', '操作') }}</th>
                </tr>
            </thead>
            <tbody>
                {% for user in users %}
                {% set sec = sec_map.get(user.username) %}
                <tr>
                    <td>{{ user.username }}</td>
                    <td>
                        {% if user.role == 'admin' %}
                            <span class="role-admin">{{ texts.get('admin', '管理员') }}</span>
                        {% elif user.role == 'boss' %}
                            <span class="role-boss">{{ texts.get('boss', '老板') }}</span>
                        {% elif user.role == 'finance' %}
                            <span class="role-finance">{{ texts.get('finance', '统计财务') }}</span>
                        {% endif %}
                    </td>
                    <td>{{ user.created_at[:10] if user.created_at else '' }}</td>
                    <td>
                        {% if sec and sec.locked_until_ts and sec.locked_until_ts > now_ts %}
                            <span style="color:#dc3545;font-weight:bold;">锁定中（约 {{ ((sec.locked_until_ts - now_ts + 59) // 60) }} 分钟）</span><br>
                            <span style="color:#6c757d;">失败次数计数：{{ sec.failed_count or 0 }}</span>
                        {% elif sec and (sec.failed_count or 0) > 0 %}
                            <span style="color:#fd7e14;font-weight:bold;">警告：失败 {{ sec.failed_count }} 次</span>
                        {% else %}
                            <span style="color:#28a745;font-weight:bold;">正常</span>
                        {% endif %}
                        <br>
                        <span style="color:#6c757d;">外网可信IP：{{ trusted_ip_count_map.get(user.username, 0) }}</span>
                    </td>
                    <td>
                        <button class="btn btn-primary" onclick="changePassword({{ user.id }}, '{{ user.username }}')">{{ texts.get('change_password', '修改密码') }}</button>
                        <button class="btn btn-success" onclick="unlockUser({{ user.id }}, '{{ user.username }}')">解锁账号</button>
                        <button class="btn btn-danger" onclick="clearTrustedIps({{ user.id }}, '{{ user.username }}')">清除外网IP信任</button>
                        {% if user.id != current_user.id %}
                            <button class="btn btn-danger" onclick="deleteUser({{ user.id }})">{{ texts.get('delete', '删除') }}</button>
                        {% else %}
                            <span style="color: #6c757d;">{{ texts.get('current_user', '当前用户') }}</span>
                        {% endif %}
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>

    <script>
        document.getElementById('addUserForm').addEventListener('submit', function(e) {
            e.preventDefault();
            const username = document.getElementById('newUsername').value;
            const password = document.getElementById('newPassword').value;
            const role = document.getElementById('newRole').value;
            fetch('/admin/add_user', {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body: 'username=' + encodeURIComponent(username) +
                      '&password=' + encodeURIComponent(password) +
                      '&role=' + encodeURIComponent(role)
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    location.reload();
                } else {
                    alert(data.error || '添加失败');
                }
            })
            .catch(() => alert('添加失败'));
        });
        
        function deleteUser(userId) {
            if (confirm('确定要删除这个用户吗？')) {
                fetch('/admin/delete_user/' + userId, { method: 'POST' })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        location.reload();
                    } else {
                        alert(data.error || '删除失败');
                    }
                })
                .catch(() => alert('删除失败'));
            }
        }

        function changePassword(userId, username) {
            const p1 = prompt('请输入用户 ' + username + ' 的新密码（至少8位）:');
            if (p1 === null) return;
            const nextPassword = (p1 || '').trim();
            if (nextPassword.length < 8) {
                alert('密码长度至少 8 位');
                return;
            }
            const p2 = prompt('请再次输入新密码:');
            if (p2 === null) return;
            if (nextPassword !== (p2 || '').trim()) {
                alert('两次输入的密码不一致');
                return;
            }

            fetch('/admin/reset_password/' + userId, {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body: 'password=' + encodeURIComponent(nextPassword)
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    alert('密码已修改');
                } else {
                    alert(data.error || '修改失败');
                }
            })
            .catch(() => alert('修改失败'));
        }

        function unlockUser(userId, username) {
            if (!confirm('确认解锁用户 ' + username + ' 吗？')) return;
            fetch('/admin/unlock_user/' + userId, { method: 'POST' })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    alert('账号已解锁');
                } else {
                    alert(data.error || '解锁失败');
                }
            })
            .catch(() => alert('解锁失败'));
        }

        function clearTrustedIps(userId, username) {
            if (!confirm('确认清除用户 ' + username + ' 的外网IP信任记录吗？')) return;
            fetch('/admin/clear_trusted_ips/' + userId, { method: 'POST' })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    alert('已清除 ' + (data.cleared || 0) + ' 条外网IP信任记录');
                    location.reload();
                } else {
                    alert(data.error || '清除失败');
                }
            })
            .catch(() => alert('清除失败'));
        }
    </script>
</body>
</html>
"""


ADMIN_DASHBOARD_TEMPLATE = """
<!DOCTYPE html>
<html lang="{{ lang or 'zh' }}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>管理总览</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; background: #fff; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .nav a { display:inline-block; margin:0 8px 8px 0; color:#0d6efd; text-decoration:none; border:1px solid #dbeafe; border-radius:999px; padding:4px 10px; font-size:13px; }
        .grid { display:grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap:10px; margin: 12px 0 16px; }
        .card { border:1px solid #e5e7eb; border-radius:10px; padding:12px; background:#f8fafc; }
        .card .k { color:#64748b; font-size:12px; }
        .card .v { margin-top:4px; font-size:22px; font-weight:bold; color:#0f172a; }
        .panel { border:1px solid #e5e7eb; border-radius:10px; padding:12px; margin-top:12px; background:#fff; }
        .btn { display:inline-block; margin: 6px 8px 0 0; text-decoration:none; border-radius:8px; padding:8px 12px; border:1px solid #dbeafe; color:#0f172a; background:#eff6ff; }
        @media (max-width: 900px) { .grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
    </style>
</head>
<body>
    <div class="container">
        <a href="{{ url_for('index', lang=lang) }}" style="color:#0d6efd; text-decoration:none;">← 返回首页</a>
        <h1 style="margin:10px 0;">管理总览</h1>
        <div class="nav">
            <a href="{{ url_for('admin_root') }}">管理总览</a>
            <a href="{{ url_for('admin_hr_employees') }}">员工管理</a>
            <a href="{{ url_for('admin_users') }}">用户管理</a>
            <a href="{{ url_for('admin_audit_logs') }}">审计日志</a>
            <a href="{{ url_for('admin_alert_settings') }}">预警阈值</a>
            <a href="{{ url_for('admin_hr_settings') }}">HR设置</a>
        </div>

        <div class="grid">
            <div class="card"><div class="k">用户数</div><div class="v">{{ stats.user_total }}</div></div>
            <div class="card"><div class="k">活动预警</div><div class="v">{{ stats.active_alerts }}</div></div>
            <div class="card"><div class="k">周报状态</div><div class="v" style="font-size:16px;">{{ '已生成' if stats.weekly_generated else '未生成' }}</div></div>
            <div class="card"><div class="k">月报状态</div><div class="v" style="font-size:16px;">{{ '已生成' if stats.monthly_generated else '未生成' }}</div></div>
        </div>

        <div class="panel">
            <strong>快捷入口</strong><br>
            <a class="btn" href="{{ url_for('admin_hr_employees') }}">员工档案管理</a>
            <a class="btn" href="{{ url_for('admin_users') }}">用户与账号安全</a>
            <a class="btn" href="{{ url_for('admin_audit_logs') }}">审计日志查询</a>
            <a class="btn" href="{{ url_for('admin_alert_settings') }}">库存预警阈值设置</a>
            <a class="btn" href="{{ url_for('admin_hr_settings') }}">HR组织与薪资设置</a>
            {% if stats.weekly_url %}
            <a class="btn" href="{{ stats.weekly_url }}&lang={{ lang }}">查看周报 {{ stats.weekly_key }}</a>
            {% endif %}
            {% if stats.monthly_url %}
            <a class="btn" href="{{ stats.monthly_url }}&lang={{ lang }}">查看月报 {{ stats.monthly_key }}</a>
            {% endif %}
        </div>
    </div>
</body>
</html>
"""


ADMIN_ALERT_SETTINGS_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>预警值设置</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .container { max-width: 860px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        h1 { color: #333; text-align: center; }
        .back-link { display: inline-block; margin-bottom: 20px; color: #007bff; text-decoration: none; }
        .link-inline { display: inline-block; margin-left: 10px; color: #007bff; text-decoration: none; }
        .card { background:#f8fafc; border:1px solid #e2e8f0; border-radius:8px; padding:16px; margin:14px 0; }
        .row { display:flex; align-items:center; gap:12px; margin:10px 0; flex-wrap:wrap; }
        .row label { min-width: 260px; font-weight: bold; color:#334155; }
        .row input { width: 220px; padding:8px; border:1px solid #cbd5e1; border-radius:6px; }
        .hint { color:#64748b; font-size:12px; }
        .btn { padding: 10px 18px; border: none; border-radius: 6px; cursor: pointer; background:#16a34a; color:#fff; font-size:14px; }
        .msg { margin: 10px 0 0; font-size:13px; color:#0f766e; }
    </style>
</head>
<body>
    <div class="container">
        <a href="{{ url_for('admin_root') }}" class="back-link">← 管理总览</a>
        <a href="{{ url_for('admin_users') }}" class="link-inline">用户管理</a>
        <a href="{{ url_for('admin_audit_logs') }}" class="link-inline">审计日志</a>
        <h1>库存预警值设置</h1>
        <form method="POST" action="{{ url_for('admin_alert_settings') }}">
            <div class="card">
                <div class="row">
                    <label>原木库存最低预警（MT）</label>
                    <input type="number" step="0.0001" min="0" name="log_stock_mt_min" value="{{ settings.log_stock_mt_min }}" required>
                </div>
                <div class="row">
                    <label>待入窑库存最低预警（托）</label>
                    <input type="number" step="1" min="0" name="sorting_stock_tray_min" value="{{ settings.sorting_stock_tray_min }}" required>
                </div>
                <div class="row">
                    <label>窑完成库存最高预警（托）</label>
                    <input type="number" step="1" min="0" name="kiln_done_stock_tray_max" value="{{ settings.kiln_done_stock_tray_max }}" required>
                </div>
                <div class="row">
                    <label>成品可发货托数最低预警（托）</label>
                    <input type="number" step="1" min="0" name="product_shippable_tray_min" value="{{ settings.product_shippable_tray_min }}" required>
                </div>
                <p class="hint">保存后立即生效，首页与老板端预警将按托数阈值计算。</p>
            </div>
            <button type="submit" class="btn">保存预警值</button>
            {% if result_msg %}
            <div class="msg">{{ result_msg }}</div>
            {% endif %}
        </form>
    </div>
</body>
</html>
"""


ADMIN_ALERT_CENTER_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>预警与效率中心</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .container { max-width: 1260px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .back-link { display: inline-block; margin-bottom: 10px; color: #007bff; text-decoration: none; }
        .link-inline { display: inline-block; margin-left: 10px; color: #007bff; text-decoration: none; }
        .card { background:#f8fafc; border:1px solid #e2e8f0; border-radius:8px; padding:14px; margin:12px 0; }
        .grid { display:grid; gap:10px; grid-template-columns: repeat(4, minmax(0, 1fr)); }
        .grid3 { display:grid; gap:10px; grid-template-columns: repeat(3, minmax(0, 1fr)); }
        .metric { background:#fff; border:1px solid #e2e8f0; border-radius:8px; padding:10px; }
        .metric .k { color:#64748b; font-size:12px; }
        .metric .v { color:#0f172a; font-size:20px; font-weight:bold; margin-top:4px; }
        table { width:100%; border-collapse:collapse; }
        th, td { border-bottom:1px solid #e5e7eb; padding:8px; font-size:13px; text-align:left; vertical-align:top; }
        th { background:#f8fafc; }
        .tag { display:inline-block; padding:2px 8px; border-radius:999px; font-size:12px; }
        .tag.l1 { background:#ecfeff; color:#155e75; }
        .tag.l2 { background:#fff7ed; color:#9a3412; }
        .tag.l3 { background:#fef2f2; color:#991b1b; }
        .status { display:inline-block; padding:2px 8px; border-radius:999px; font-size:12px; border:1px solid #e2e8f0; }
        .status.open { background:#fef2f2; color:#991b1b; }
        .status.ack { background:#eff6ff; color:#1d4ed8; }
        .status.ignored { background:#f8fafc; color:#475569; }
        .status.resolved { background:#f0fdf4; color:#166534; }
        .row { display:flex; gap:8px; flex-wrap:wrap; align-items:center; }
        input, select, button { padding:7px 9px; border:1px solid #cbd5e1; border-radius:6px; }
        button { cursor:pointer; background:#2563eb; color:#fff; border:none; }
        .btn-gray { background:#475569; }
        .btn-green { background:#16a34a; }
        .muted { color:#64748b; font-size:12px; }
        .layout { display:grid; grid-template-columns: 1.2fr 1fr; gap:12px; }
        canvas { width:100%; max-width:560px; height:360px; border:1px solid #e2e8f0; border-radius:8px; background:#fff; }
        @media (max-width: 1000px) { .layout { grid-template-columns: 1fr; } .grid, .grid3 { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
    </style>
</head>
<body>
    <div class="container">
        <a href="{{ url_for('admin_root') }}" class="back-link">← 管理总览</a>
        <a href="{{ url_for('admin_users') }}" class="link-inline">用户管理</a>
        <a href="{{ url_for('admin_audit_logs') }}" class="link-inline">审计日志</a>
        <a href="{{ url_for('admin_alert_settings') }}" class="link-inline">预警阈值</a>
        <h1 style="margin:8px 0 14px;">预警与效率中心</h1>

        {% if result_msg %}
        <div class="card" style="border-color:#bbf7d0; background:#f0fdf4;">{{ result_msg }}</div>
        {% endif %}

        <div class="card">
            <div class="row" style="justify-content:space-between;">
                <div><strong>关键预警（仅原木与成品）</strong></div>
                <div class="muted">通知静默至：{{ data.silence_until_text }}</div>
            </div>
            <div class="grid" style="margin-top:10px;">
                <div class="metric"><div class="k">总预警</div><div class="v">{{ data.weekly.total }}</div></div>
                <div class="metric"><div class="k">L3/L2/L1</div><div class="v">{{ data.weekly.by_level.L3 }}/{{ data.weekly.by_level.L2 }}/{{ data.weekly.by_level.L1 }}</div></div>
                <div class="metric"><div class="k">关闭率</div><div class="v">{{ "%.1f"|format(data.weekly.resolve_rate) }}%</div></div>
                <div class="metric"><div class="k">平均关闭时长</div><div class="v">{{ "%.2f"|format(data.weekly.avg_resolve_hours) }}h</div></div>
            </div>
        </div>

        <div class="layout">
            <div class="card">
                <strong>流程效率雷达图（当前/日/周/月）</strong>
                <div class="muted" style="margin-top:4px;">越接近外圈代表效率越好，满分100</div>
                <canvas id="eff-radar" width="560" height="360"></canvas>
            </div>
            <div class="card">
                <strong>效率对比</strong>
                <div class="grid3" style="margin-top:10px;">
                    <div class="metric"><div class="k">当日均分</div><div class="v">{{ data.efficiency.day.total_score }}</div><div class="muted">前一日 {{ data.efficiency.day_prev.total_score }}</div></div>
                    <div class="metric"><div class="k">当周均分</div><div class="v">{{ data.efficiency.week.total_score }}</div><div class="muted">前一周 {{ data.efficiency.week_prev.total_score }}</div></div>
                    <div class="metric"><div class="k">当月均分</div><div class="v">{{ data.efficiency.month.total_score }}</div><div class="muted">前一月 {{ data.efficiency.month_prev.total_score }}</div></div>
                </div>
                <div class="card" style="margin-top:10px; background:#fff;">
                    <div class="muted">五维指标：原木保障 / 前段均衡 / 中段流速 / 积压健康 / 成品健康</div>
                </div>
                <form method="POST" action="{{ url_for('admin_alert_center') }}" style="margin-top:10px;">
                    <input type="hidden" name="form_type" value="engine_cfg">
                    <div class="row">
                        <label>成品可发货阈值</label><input type="number" min="1" name="product_ready_threshold" value="{{ data.engine_cfg.product_ready_threshold }}" required>
                        <span class="muted">作用：成品低于该值时，成品健康分会偏低；达到后分数回升。</span>
                    </div>
                    <div class="row">
                        <label>成品满仓阈值</label><input type="number" min="1" name="product_full_threshold" value="{{ data.engine_cfg.product_full_threshold }}" required>
                        <span class="muted">作用：高于该值触发“库存满仓”关键预警（L2）。</span>
                    </div>
                    <div class="row">
                        <label>成品爆满阈值</label><input type="number" min="1" name="product_burst_threshold" value="{{ data.engine_cfg.product_burst_threshold }}" required>
                        <span class="muted">作用：高于该值触发“库存爆满”关键预警（L3）。</span>
                    </div>
                    <div class="row">
                        <label>通知去重秒</label><input type="number" min="60" name="dedup_seconds" value="{{ data.engine_cfg.dedup_seconds }}" required>
                        <span class="muted">作用：同类预警在该时间内不重复推送 TG，防止刷屏。</span>
                    </div>
                    <div class="row">
                        <label>启用瓶颈模式</label>
                        <select name="enable_bottleneck_mode">
                            <option value="1" {% if data.engine_cfg.enable_bottleneck_mode == 1 %}selected{% endif %}>开启</option>
                            <option value="0" {% if data.engine_cfg.enable_bottleneck_mode != 1 %}selected{% endif %}>关闭</option>
                        </select>
                        <span class="muted">作用：当二次分拣积压较高时，放宽中段/积压评分，避免雷达图“塌死”。</span>
                    </div>
                    <div class="row">
                        <label>瓶颈触发阈值(窑完成托)</label><input type="number" min="1" name="bottleneck_kiln_done_threshold" value="{{ data.engine_cfg.bottleneck_kiln_done_threshold }}" required>
                        <span class="muted">作用：窑完成库存达到该值时，系统判定进入瓶颈模式。</span>
                    </div>
                    <div class="row">
                        <label>瓶颈放宽权重(%)</label><input type="number" min="0" max="100" name="bottleneck_relax_weight_pct" value="{{ data.engine_cfg.bottleneck_relax_weight_pct }}" required>
                        <span class="muted">作用：越大则瓶颈期分数越平缓（建议 20-45）。</span>
                    </div>
                    <div class="row">
                        <label>连续2天改善加分</label><input type="number" step="0.1" min="0" max="30" name="improve_bonus_2day" value="{{ data.engine_cfg.improve_bonus_2day }}" required>
                        <span class="muted">作用：积压连续2天下降时，加到中段流速/积压健康。</span>
                    </div>
                    <div class="row">
                        <label>连续3天额外加分</label><input type="number" step="0.1" min="0" max="30" name="improve_bonus_3day" value="{{ data.engine_cfg.improve_bonus_3day }}" required>
                        <span class="muted">作用：连续3天下降再追加加分，体现持续改善。</span>
                    </div>
                    <div class="row">
                        <label>日平滑窗口</label><input type="number" min="1" max="12" name="smooth_day_window_points" value="{{ data.engine_cfg.smooth_day_window_points }}" required>
                        <span class="muted">作用：越大则日对比更平滑，波动更小。</span>
                    </div>
                    <div class="row">
                        <label>周平滑窗口</label><input type="number" min="1" max="12" name="smooth_week_window_points" value="{{ data.engine_cfg.smooth_week_window_points }}" required>
                        <span class="muted">作用：越大则周对比更平滑，趋势更稳。</span>
                    </div>
                    <div class="row">
                        <label>总分权重-原木保障</label><input type="number" min="1" max="60" name="weight_raw_security" value="{{ data.engine_cfg.weight_raw_security }}" required>
                        <label>总分权重-前段均衡</label><input type="number" min="1" max="60" name="weight_front_balance" value="{{ data.engine_cfg.weight_front_balance }}" required>
                        <label>总分权重-中段流速</label><input type="number" min="1" max="60" name="weight_middle_flow" value="{{ data.engine_cfg.weight_middle_flow }}" required>
                        <label>总分权重-积压健康</label><input type="number" min="1" max="60" name="weight_backlog_health" value="{{ data.engine_cfg.weight_backlog_health }}" required>
                        <label>总分权重-成品健康</label><input type="number" min="1" max="60" name="weight_product_health" value="{{ data.engine_cfg.weight_product_health }}" required>
                        <span class="muted">作用：控制五维对“总分”的影响比例（相对权重，不要求和=100）。</span>
                    </div>
                    <div class="row">
                        <button type="submit">保存</button>
                    </div>
                </form>
                <form method="POST" action="{{ url_for('admin_alert_center') }}" style="margin-top:8px;">
                    <input type="hidden" name="form_type" value="silence">
                    <div class="row">
                        <label>L2/L3静默(分钟)</label>
                        <input type="number" min="0" name="silence_minutes" value="0" required>
                        <button type="submit" class="btn-gray">设置静默</button>
                    </div>
                </form>
            </div>
        </div>

        <div class="card">
            <strong>关键预警处理（{{ data.active|length }}）</strong>
            <table style="margin-top:10px;">
                <thead>
                    <tr><th>等级</th><th>状态</th><th>标题</th><th>内容</th><th>负责人</th><th>时间</th><th>操作</th></tr>
                </thead>
                <tbody>
                    {% for a in data.active %}
                    <tr>
                        <td><span class="tag {{ (a.level or 'L1')|lower }}">{{ a.level or 'L1' }}</span></td>
                        <td><span class="status {{ a.status }}">{{ a.status }}</span></td>
                        <td>{{ a.title }}</td>
                        <td>{{ a.text }}</td>
                        <td>{{ a.owner or '-' }}</td>
                        <td>{{ a.created_at_text }}<br><span class="muted">last: {{ a.last_seen_at_text }}</span></td>
                        <td>
                            <form method="POST" action="{{ url_for('admin_alert_center_action') }}" class="row">
                                <input type="hidden" name="alert_id" value="{{ a.id }}">
                                <select name="action">
                                    <option value="ack">确认</option>
                                    <option value="ignore">忽略</option>
                                    <option value="resolve">关闭</option>
                                    <option value="reopen">重开</option>
                                </select>
                                <input type="text" name="owner" placeholder="负责人" value="{{ a.owner or '' }}" style="width:110px;">
                                <input type="text" name="note" placeholder="备注" style="width:120px;">
                                <button type="submit" class="btn-green">提交</button>
                            </form>
                        </td>
                    </tr>
                    {% endfor %}
                    {% if not data.active %}
                    <tr><td colspan="7" class="muted">当前无活动预警</td></tr>
                    {% endif %}
                </tbody>
            </table>
        </div>

        <div class="card">
            <strong>阈值版本（最近30次）</strong>
            <table style="margin-top:10px;">
                <thead><tr><th>时间</th><th>操作人</th><th>参数快照</th></tr></thead>
                <tbody>
                    {% for v in data.versions %}
                    <tr>
                        <td>{{ v.ts_text }}</td>
                        <td>{{ v.operator or '-' }}</td>
                        <td>
                            log_min={{ v.settings.log_stock_mt_min }},
                            sorting_min={{ v.settings.sorting_stock_tray_min }},
                            kiln_done_max={{ v.settings.kiln_done_stock_tray_max }},
                            product_tray_min={{ v.settings.product_shippable_tray_min }}
                        </td>
                    </tr>
                    {% endfor %}
                    {% if not data.versions %}
                    <tr><td colspan="3" class="muted">暂无版本记录</td></tr>
                    {% endif %}
                </tbody>
            </table>
        </div>
    </div>
    <script>
    (function(){
      const canvas = document.getElementById('eff-radar');
      if(!canvas) return;
      const ctx = canvas.getContext('2d');
      const labels = {{ data.efficiency.radar_labels | tojson }};
      const radar = {{ data.efficiency.radar | tojson }};
      const datasets = [
        {name:'当前', vals: radar.current || [], color:'rgba(37,99,235,0.85)', fill:'rgba(37,99,235,0.12)'},
        {name:'日均', vals: radar.day || [], color:'rgba(16,185,129,0.85)', fill:'rgba(16,185,129,0.12)'},
        {name:'周均', vals: radar.week || [], color:'rgba(234,88,12,0.85)', fill:'rgba(234,88,12,0.10)'},
        {name:'月均', vals: radar.month || [], color:'rgba(148,163,184,0.95)', fill:'rgba(148,163,184,0.08)'}
      ];
      const W = canvas.width, H = canvas.height;
      const cx = W * 0.45, cy = H * 0.52, R = Math.min(W,H) * 0.35;
      ctx.clearRect(0,0,W,H);
      ctx.strokeStyle = '#e2e8f0';
      ctx.fillStyle = '#475569';
      ctx.font = '12px Arial';
      const axis = labels.length || 5;
      for(let ring=1; ring<=5; ring++){
        ctx.beginPath();
        for(let i=0;i<axis;i++){
          const ang = -Math.PI/2 + (Math.PI*2*i/axis);
          const rr = R * ring/5;
          const x = cx + rr*Math.cos(ang), y = cy + rr*Math.sin(ang);
          if(i===0) ctx.moveTo(x,y); else ctx.lineTo(x,y);
        }
        ctx.closePath(); ctx.stroke();
      }
      for(let i=0;i<axis;i++){
        const ang = -Math.PI/2 + (Math.PI*2*i/axis);
        const x = cx + R*Math.cos(ang), y = cy + R*Math.sin(ang);
        ctx.beginPath(); ctx.moveTo(cx,cy); ctx.lineTo(x,y); ctx.stroke();
        const lx = cx + (R+18)*Math.cos(ang), ly = cy + (R+18)*Math.sin(ang);
        ctx.fillText(labels[i] || ('维度'+(i+1)), lx-18, ly+4);
      }
      datasets.forEach(ds => {
        ctx.beginPath();
        for(let i=0;i<axis;i++){
          const v = Math.max(0, Math.min(100, Number((ds.vals||[])[i] || 0)));
          const rr = R * v/100;
          const ang = -Math.PI/2 + (Math.PI*2*i/axis);
          const x = cx + rr*Math.cos(ang), y = cy + rr*Math.sin(ang);
          if(i===0) ctx.moveTo(x,y); else ctx.lineTo(x,y);
        }
        ctx.closePath();
        ctx.fillStyle = ds.fill; ctx.fill();
        ctx.strokeStyle = ds.color; ctx.lineWidth = 2; ctx.stroke();
      });
      const lx = W*0.80, ly = H*0.14;
      datasets.forEach((ds, idx) => {
        const y = ly + idx*22;
        ctx.fillStyle = ds.color; ctx.fillRect(lx, y-9, 14, 14);
        ctx.fillStyle = '#0f172a'; ctx.fillText(ds.name, lx+20, y+2);
      });
    })();
    </script>
</body>
</html>
"""


ADMIN_HR_SETTINGS_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ texts.get('hr_settings_title', 'HR设置') }}</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .container { max-width: 1080px; margin: 0 auto; background: #fff; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .back-link { display: inline-block; margin-bottom: 20px; color: #007bff; text-decoration: none; }
        .link-inline { display: inline-block; margin-left: 10px; color: #007bff; text-decoration: none; }
        .grid { display:grid; grid-template-columns: 1fr 1fr; gap:12px; margin: 10px 0; }
        .card { background:#f8fafc; border:1px solid #e2e8f0; border-radius:10px; padding:12px; }
        .k { color:#64748b; font-size:12px; }
        .v { margin-top:4px; font-size:20px; font-weight:bold; color:#0f172a; }
        .row { margin: 12px 0; }
        .row label { display:block; font-weight:bold; margin-bottom:6px; color:#334155; }
        textarea { width:100%; min-height:120px; box-sizing:border-box; font-family: Arial, sans-serif; border:1px solid #cbd5e1; border-radius:6px; padding:10px; }
        .notes { min-height:120px; }
        .tbl { width:100%; border-collapse:collapse; margin-top:8px; }
        .tbl th, .tbl td { border:1px solid #e2e8f0; padding:8px; text-align:left; vertical-align:top; }
        .tbl th { background:#f8fafc; color:#334155; font-size:13px; }
        .tbl input, .tbl select { width:100%; box-sizing:border-box; border:1px solid #cbd5e1; border-radius:6px; padding:6px 8px; font-size:14px; }
        .row-actions { display:flex; gap:8px; margin-top:8px; }
        .btn-mini { padding:6px 10px; border:none; border-radius:6px; cursor:pointer; font-size:13px; }
        .btn-add { background:#0ea5e9; color:#fff; }
        .btn-del { background:#ef4444; color:#fff; }
        .btn { padding: 10px 18px; border: none; border-radius: 6px; cursor: pointer; background:#16a34a; color:#fff; font-size:14px; }
        .msg-ok { margin-top:10px; color:#166534; font-size:13px; }
        .msg-err { margin-top:10px; color:#b91c1c; font-size:13px; }
        .hint { color:#64748b; font-size:12px; margin-top:6px; }
        @media (max-width: 900px) { .grid { grid-template-columns: 1fr; } }
    </style>
</head>
<body>
    <div class="container">
        <a href="{{ url_for('admin_root') }}" class="back-link">← {{ texts.get('admin_overview_title', '管理总览') }}</a>
        <a href="{{ url_for('admin_users') }}" class="link-inline">{{ texts.get('user_management', '用户管理') }}</a>
        <a href="{{ url_for('admin_audit_logs') }}" class="link-inline">{{ texts.get('audit_logs', '审计日志') }}</a>
        <a href="{{ url_for('admin_alert_settings') }}" class="link-inline">{{ texts.get('alert_threshold', '预警阈值') }}</a>
        <h1>{{ texts.get('hr_settings_heading', 'HR组织与薪资设置') }}</h1>

        <div class="grid">
            <div class="card">
                <div class="k">{{ texts.get('hr_employee_total', '员工总数') }}</div>
                <div class="v">{{ data.employee_total }}</div>
            </div>
            <div class="card">
                <div class="k">{{ texts.get('hr_employee_active', '在岗人数') }}</div>
                <div class="v">{{ data.employee_active }}</div>
            </div>
        </div>

        <form method="POST" action="{{ url_for('admin_hr_settings') }}" id="hr-settings-form">
            <div class="row">
                <label>{{ texts.get('hr_team_position_section', '班组与岗位（像填表一样即可）') }}</label>
                <table class="tbl" id="team-table">
                    <thead>
                        <tr><th style="width:28%;">{{ texts.get('hr_team_name', '班组名称') }}</th><th>{{ texts.get('hr_position_csv', '岗位（用逗号分开）') }}</th><th style="width:84px;">{{ texts.get('actions', '操作') }}</th></tr>
                    </thead>
                    <tbody>
                        {% for row in data.team_rows %}
                        <tr>
                            <td><input type="text" name="team_name" value="{{ row.name }}"></td>
                            <td><input type="text" name="team_positions" value="{{ row.positions_text }}"></td>
                            <td><button type="button" class="btn-mini btn-del" onclick="removeRow(this)">{{ texts.get('delete', '删除') }}</button></td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
                <div class="row-actions">
                    <button type="button" class="btn-mini btn-add" onclick="addTeamRow()">+ {{ texts.get('hr_add_team', '新增班组') }}</button>
                </div>
            </div>

            <div class="row">
                <label>{{ texts.get('hr_salary_rule_section', '薪资类型与发薪规则') }}</label>
                <table class="tbl" id="salary-table">
                    <thead>
                        <tr><th style="width:20%;">{{ texts.get('hr_salary_type', '薪资类型') }}</th><th style="width:20%;">{{ texts.get('hr_salary_cycle', '发薪周期') }}</th><th>{{ texts.get('remark_label', '说明') }}</th><th style="width:84px;">{{ texts.get('actions', '操作') }}</th></tr>
                    </thead>
                    <tbody>
                        {% for row in data.salary_rows %}
                        <tr>
                            <td><input type="text" name="salary_type" value="{{ row.salary_type }}"></td>
                            <td>
                                <select name="salary_cycle">
                                    <option value="weekly" {% if row.payout_cycle == 'weekly' %}selected{% endif %}>{{ texts.get('hr_cycle_weekly', 'weekly（按周）') }}</option>
                                    <option value="semi_monthly" {% if row.payout_cycle == 'semi_monthly' %}selected{% endif %}>{{ texts.get('hr_cycle_semi_monthly', 'semi_monthly（15天）') }}</option>
                                    <option value="monthly" {% if row.payout_cycle == 'monthly' %}selected{% endif %}>{{ texts.get('hr_cycle_monthly', 'monthly（按月）') }}</option>
                                </select>
                            </td>
                            <td><input type="text" name="salary_desc" value="{{ row.desc }}"></td>
                            <td><button type="button" class="btn-mini btn-del" onclick="removeRow(this)">{{ texts.get('delete', '删除') }}</button></td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
                <div class="row-actions">
                    <button type="button" class="btn-mini btn-add" onclick="addSalaryRow()">+ {{ texts.get('hr_add_salary_type', '新增薪资类型') }}</button>
                </div>
            </div>

            <div class="row">
                <label>{{ texts.get('hr_rule_notes', '规则备注（每行一条）') }}</label>
                <textarea class="notes" name="notes_text">{{ data.notes_text }}</textarea>
            </div>

            <input type="hidden" name="teams_json" value="">
            <input type="hidden" name="salary_types_json" value="">
            <input type="hidden" name="teams_text" value="">
            <input type="hidden" name="salary_types_text" value="">

            <button class="btn" type="submit">{{ texts.get('hr_save_settings', '保存HR设置') }}</button>
            {% if result_msg %}
            <div class="msg-ok">{{ result_msg }}</div>
            {% endif %}
            {% if error_msg %}
            <div class="msg-err">{{ error_msg }}</div>
            {% endif %}
        </form>
    </div>
    <script>
        function removeRow(btn) {
            const tr = btn && btn.closest ? btn.closest('tr') : null;
            if (tr) tr.remove();
        }
        function addTeamRow() {
            const body = document.querySelector('#team-table tbody');
            if (!body) return;
            const tr = document.createElement('tr');
            tr.innerHTML = '<td><input type="text" name="team_name"></td><td><input type="text" name="team_positions"></td><td><button type="button" class="btn-mini btn-del" onclick="removeRow(this)">{{ texts.get("delete", "删除") }}</button></td>';
            body.appendChild(tr);
        }
        function addSalaryRow() {
            const body = document.querySelector('#salary-table tbody');
            if (!body) return;
            const tr = document.createElement('tr');
            tr.innerHTML = '<td><input type="text" name="salary_type"></td><td><select name="salary_cycle"><option value="weekly" selected>{{ texts.get("hr_cycle_weekly", "weekly（按周）") }}</option><option value="semi_monthly">{{ texts.get("hr_cycle_semi_monthly", "semi_monthly（15天）") }}</option><option value="monthly">{{ texts.get("hr_cycle_monthly", "monthly（按月）") }}</option></select></td><td><input type="text" name="salary_desc"></td><td><button type="button" class="btn-mini btn-del" onclick="removeRow(this)">{{ texts.get("delete", "删除") }}</button></td>';
            body.appendChild(tr);
        }
    </script>
</body>
</html>
"""

ADMIN_HR_EMPLOYEES_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ texts.get('hr_employee_mgmt_title', '员工管理') }}</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; background: #fff; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .back-link { display: inline-block; margin-bottom: 20px; color: #007bff; text-decoration: none; }
        .link-inline { display: inline-block; margin-left: 10px; color: #007bff; text-decoration: none; }
        .grid { display:grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap:10px; margin: 8px 0 14px; }
        .card { background:#f8fafc; border:1px solid #e2e8f0; border-radius:10px; padding:12px; }
        .k { color:#64748b; font-size:12px; }
        .v { margin-top:4px; font-size:22px; font-weight:bold; color:#0f172a; }
        .tbl { width:100%; border-collapse:collapse; margin-top:8px; }
        .tbl th, .tbl td { border:1px solid #e2e8f0; padding:8px; text-align:left; }
        .tbl th { background:#f8fafc; color:#334155; font-size:13px; }
        .toolbar { display:flex; justify-content:flex-end; margin:6px 0 10px; }
        .btn { border:none; border-radius:8px; padding:8px 12px; cursor:pointer; font-size:14px; }
        .btn-add { background:#16a34a; color:#fff; }
        .btn-edit { background:#0369a1; color:#fff; }
        .form-card { display:none; background:#f8fafc; border:1px solid #e2e8f0; border-radius:10px; padding:12px; margin:6px 0 12px; }
        .form-card-static { display:block; background:#f8fafc; border:1px solid #e2e8f0; border-radius:10px; padding:12px; margin:6px 0 12px; }
        .form-grid { display:grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap:8px; }
        .form-grid input, .form-grid select { width:100%; box-sizing:border-box; border:1px solid #cbd5e1; border-radius:6px; padding:8px; background:#fff; }
        .msg-ok { margin:6px 0; color:#166534; font-size:13px; }
        .msg-err { margin:6px 0; color:#b91c1c; font-size:13px; }
        .tag-ok { color:#166534; font-weight:bold; }
        .tag-off { color:#b45309; font-weight:bold; }
        .tag-left { color:#b91c1c; font-weight:bold; }
        .muted { color:#64748b; font-size:12px; }
        @media (max-width: 900px) {
            .grid { grid-template-columns: 1fr; }
            .form-grid { grid-template-columns: 1fr; }
        }
    </style>
</head>
<body>
    <div class="container">
        <a href="{{ hr_back_url }}" class="back-link">← {{ texts.get('admin_overview_title', '管理总览') }}</a>
        {% if can_manage_hr_settings %}
        <a href="{{ url_for('admin_hr_settings') }}" class="link-inline">{{ texts.get('hr_settings_title', 'HR设置') }}</a>
        {% endif %}
        <h1>{{ texts.get('hr_employee_mgmt_title', '员工管理') }}</h1>

        <div class="grid">
            <div class="card"><div class="k">{{ texts.get('hr_employee_total', '员工总数') }}</div><div class="v">{{ data.employee_total }}</div></div>
            <div class="card"><div class="k">{{ texts.get('hr_employee_active', '在岗人数') }}</div><div class="v">{{ data.employee_active }}</div></div>
            <div class="card"><div class="k">{{ texts.get('hr_employee_left', '离职人数') }}</div><div class="v">{{ data.employee_left }}</div></div>
        </div>

        <div class="toolbar">
            <button type="button" class="btn btn-add" onclick="toggleAddForm()">+ {{ texts.get('hr_add_employee', '添加员工') }}</button>
        </div>
        {% if result_msg %}
        <div class="msg-ok">{{ result_msg }}</div>
        {% endif %}
        {% if error_msg %}
        <div class="msg-err">{{ error_msg }}</div>
        {% endif %}
        <div class="form-card" id="add-form">
            <form method="POST" action="{{ url_for('admin_hr_employees') }}">
                <input type="hidden" name="form_action" value="add">
                <div class="form-grid">
                    <input type="text" name="name" placeholder="{{ texts.get('hr_name_required', '姓名（必填）') }}" required>
                    <select name="team" id="team-select">
                        <option value="">{{ texts.get('hr_select_team', '请选择班组') }}</option>
                        {% for team in data.team_options %}
                        <option value="{{ team }}">{{ team }}</option>
                        {% endfor %}
                    </select>
                    <select name="position" id="position-select">
                        <option value="">{{ texts.get('hr_select_position', '请选择岗位') }}</option>
                        {% for p in data.position_options %}
                        <option value="{{ p }}">{{ p }}</option>
                        {% endfor %}
                    </select>
                    <select name="salary_type">
                        <option value="">{{ texts.get('hr_select_salary_type', '请选择薪资类型') }}</option>
                        {% for st in data.salary_type_options %}
                        <option value="{{ st }}">{{ st }}</option>
                        {% endfor %}
                    </select>
                    <input type="number" step="0.01" min="0" name="salary_value" placeholder="{{ texts.get('hr_salary_value', '薪资值') }}">
                    <input type="date" name="join_date" placeholder="{{ texts.get('hr_join_date', '入职日期') }}">
                </div>
                <div style="margin-top:8px;">
                    <button type="submit" class="btn btn-add">{{ texts.get('hr_save_employee', '保存员工') }}</button>
                </div>
            </form>
        </div>
        <div class="form-card" id="edit-form">
            <form method="POST" action="{{ url_for('admin_hr_employees') }}">
                <input type="hidden" name="form_action" value="edit">
                <input type="hidden" name="original_name" id="edit-original-name" value="">
                <div class="form-grid">
                    <input type="text" name="display_name" id="edit-name" placeholder="{{ texts.get('hr_name', '姓名') }}" readonly>
                    <select name="team" id="edit-team-select">
                        <option value="">{{ texts.get('hr_select_team', '请选择班组') }}</option>
                        {% for team in data.team_options %}
                        <option value="{{ team }}">{{ team }}</option>
                        {% endfor %}
                    </select>
                    <select name="position" id="edit-position-select">
                        <option value="">{{ texts.get('hr_select_position', '请选择岗位') }}</option>
                        {% for p in data.position_options %}
                        <option value="{{ p }}">{{ p }}</option>
                        {% endfor %}
                    </select>
                    <select name="salary_type" id="edit-salary-type-select">
                        <option value="">{{ texts.get('hr_select_salary_type', '请选择薪资类型') }}</option>
                        {% for st in data.salary_type_options %}
                        <option value="{{ st }}">{{ st }}</option>
                        {% endfor %}
                    </select>
                    <input type="number" step="0.01" min="0" name="salary_value" id="edit-salary-value" placeholder="{{ texts.get('hr_salary_value', '薪资值') }}">
                    <input type="date" name="join_date" id="edit-join-date" placeholder="{{ texts.get('hr_join_date', '入职日期') }}">
                    <select name="status" id="edit-status-select">
                        <option value="在岗">{{ texts.get('hr_status_active', '在岗') }}</option>
                        <option value="离岗">{{ texts.get('hr_status_off', '离岗') }}</option>
                        <option value="离职">{{ texts.get('hr_status_left', '离职') }}</option>
                    </select>
                </div>
                <div style="margin-top:8px; display:flex; gap:8px;">
                    <button type="submit" class="btn btn-edit">{{ texts.get('save_changes_btn', '保存修改') }}</button>
                    <button type="button" class="btn" onclick="closeEditForm()">{{ texts.get('close_btn', '取消') }}</button>
                </div>
            </form>
        </div>
        <div class="form-card-static" id="attendance-form">
            <form method="POST" action="{{ url_for('admin_hr_employees') }}">
                <input type="hidden" name="form_action" value="attendance">
                <div class="form-grid">
                    <select name="attendance_name" required>
                        <option value="">{{ texts.get('hr_select_employee', '请选择员工') }}</option>
                        {% for n in data.employee_options %}
                        <option value="{{ n }}">{{ n }}</option>
                        {% endfor %}
                    </select>
                    <input type="number" step="0.5" min="0" name="regular_hours" placeholder="{{ texts.get('hr_regular_hours', '正常工时（h）') }}" value="8" required>
                    <input type="number" step="0.5" min="0" name="overtime_hours" placeholder="{{ texts.get('hr_overtime_hours', '加班工时（h）') }}" value="0">
                    <select name="overtime_multiplier">
                        <option value="1.5" selected>{{ texts.get('hr_ot_ratio_15', '加班倍率 x1.5') }}</option>
                        <option value="2.0">{{ texts.get('hr_ot_ratio_20', '加班倍率 x2.0') }}</option>
                    </select>
                    <input type="date" name="attendance_date" placeholder="{{ texts.get('hr_attendance_date', '考勤日期') }}">
                </div>
                <div style="margin-top:8px;">
                    <button type="submit" class="btn btn-add">{{ texts.get('hr_save_attendance', '保存考勤') }}</button>
                    <span class="muted" style="margin-left:8px;">{{ texts.get('hr_attendance_hint', '工资试算将自动按小时与加班工时联动') }}</span>
                </div>
            </form>
            <table class="tbl" style="margin-top:10px;">
                <thead>
                    <tr>
                        <th style="width:130px;">{{ texts.get('report_date_label', '日期') }}</th>
                        <th style="width:140px;">{{ texts.get('hr_name', '员工') }}</th>
                        <th style="width:140px;">{{ texts.get('hr_regular_hours_short', '正常工时') }}</th>
                        <th style="width:140px;">{{ texts.get('hr_overtime_hours_short', '加班工时') }}</th>
                        <th style="width:130px;">{{ texts.get('hr_overtime_ratio', '加班倍率') }}</th>
                    </tr>
                </thead>
                <tbody>
                    {% for a in data.attendance_rows %}
                    <tr>
                        <td>{{ a.date or '-' }}</td>
                        <td>{{ a.name or '-' }}</td>
                        <td>{{ '%.2f'|format(a.regular_hours or 0) }}h</td>
                        <td>{{ '%.2f'|format(a.overtime_hours or 0) }}h</td>
                        <td>x{{ '%.2f'|format(a.overtime_multiplier or 1.5) }}</td>
                    </tr>
                    {% endfor %}
                    {% if not data.attendance_rows %}
                    <tr><td colspan="5" class="muted">{{ texts.get('hr_no_attendance', '暂无考勤记录') }}</td></tr>
                    {% endif %}
                </tbody>
            </table>
        </div>

        <table class="tbl">
            <thead>
                <tr>
                    <th style="width:120px;">{{ texts.get('hr_name', '姓名') }}</th>
                    <th style="width:140px;">{{ texts.get('hr_team', '班组') }}</th>
                    <th style="width:160px;">{{ texts.get('hr_position', '岗位') }}</th>
                    <th style="width:120px;">{{ texts.get('hr_salary_type', '薪资类型') }}</th>
                    <th style="width:120px;">{{ texts.get('hr_salary_value', '薪资值') }}</th>
                    <th style="width:130px;">{{ texts.get('hr_join_date', '入职日期') }}</th>
                    <th style="width:90px;">{{ texts.get('status', '状态') }}</th>
                    <th style="width:100px;">{{ texts.get('actions', '操作') }}</th>
                </tr>
            </thead>
            <tbody>
                {% for row in data.rows %}
                <tr>
                    <td>{{ row.name }}</td>
                    <td>{{ row.team or '-' }}</td>
                    <td>{{ row.position or '-' }}</td>
                    <td>{{ row.salary_type or '-' }}</td>
                    <td>{{ '%.2f'|format(row.salary_value or 0) }}</td>
                    <td>{{ row.join_date or '-' }}</td>
                    <td>
                        {% if row.status == '离职' %}
                        <span class="tag-left">{{ texts.get('hr_status_left', '离职') }}</span>
                        {% elif row.status == '离岗' %}
                        <span class="tag-off">{{ texts.get('hr_status_off', '离岗') }}</span>
                        {% else %}
                        <span class="tag-ok">{{ texts.get('hr_status_active', '在岗') }}</span>
                        {% endif %}
                    </td>
                    <td>
                        <button type="button" class="btn btn-edit" onclick='openEditForm({{ row|tojson }})'>{{ texts.get('edit_btn', '编辑') }}</button>
                    </td>
                </tr>
                {% endfor %}
                {% if not data.rows %}
                <tr><td colspan="8" class="muted">{{ texts.get('hr_no_employee', '暂无员工档案数据') }}</td></tr>
                {% endif %}
            </tbody>
        </table>
    </div>
    <script>
        var teamPositionsMap = {{ data.team_positions_map | tojson }};

        function toggleAddForm() {
            var box = document.getElementById('add-form');
            if (!box) return;
            closeEditForm();
            box.style.display = box.style.display === 'block' ? 'none' : 'block';
        }

        function refreshPositionOptionsByIds(teamId, posId) {
            var teamEl = document.getElementById(teamId);
            var posEl = document.getElementById(posId);
            if (!teamEl || !posEl) return;

            var selectedTeam = teamEl.value || '';
            var current = posEl.value || '';
            var positions = [];
            if (selectedTeam && Array.isArray(teamPositionsMap[selectedTeam])) {
                positions = teamPositionsMap[selectedTeam];
            } else {
                var merged = [];
                for (var team in teamPositionsMap) {
                    if (!Array.isArray(teamPositionsMap[team])) continue;
                    merged = merged.concat(teamPositionsMap[team]);
                }
                var seen = {};
                positions = merged.filter(function(v) {
                    if (!v || seen[v]) return false;
                    seen[v] = true;
                    return true;
                }).sort();
            }

            posEl.innerHTML = '<option value="">{{ texts.get("hr_select_position", "请选择岗位") }}</option>';
            positions.forEach(function(p) {
                var opt = document.createElement('option');
                opt.value = p;
                opt.textContent = p;
                if (p === current) opt.selected = true;
                posEl.appendChild(opt);
            });
        }

        function openEditForm(row) {
            var box = document.getElementById('edit-form');
            if (!box || !row) return;
            var addBox = document.getElementById('add-form');
            if (addBox) addBox.style.display = 'none';

            document.getElementById('edit-original-name').value = row.name || '';
            document.getElementById('edit-name').value = row.name || '';
            document.getElementById('edit-team-select').value = row.team || '';
            refreshPositionOptionsByIds('edit-team-select', 'edit-position-select');
            document.getElementById('edit-position-select').value = row.position || '';
            document.getElementById('edit-salary-type-select').value = row.salary_type || '';
            document.getElementById('edit-salary-value').value = (row.salary_value || 0);
            document.getElementById('edit-join-date').value = row.join_date || '';
            document.getElementById('edit-status-select').value = row.status || '在岗';
            box.style.display = 'block';
            box.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }

        function closeEditForm() {
            var box = document.getElementById('edit-form');
            if (!box) return;
            box.style.display = 'none';
        }

        document.addEventListener('DOMContentLoaded', function() {
            var teamEl = document.getElementById('team-select');
            if (teamEl) {
                teamEl.addEventListener('change', function() {
                    refreshPositionOptionsByIds('team-select', 'position-select');
                });
                refreshPositionOptionsByIds('team-select', 'position-select');
            }
            var editTeamEl = document.getElementById('edit-team-select');
            if (editTeamEl) {
                editTeamEl.addEventListener('change', function() {
                    refreshPositionOptionsByIds('edit-team-select', 'edit-position-select');
                });
                refreshPositionOptionsByIds('edit-team-select', 'edit-position-select');
            }
        });
    </script>
</body>
</html>
"""


ADMIN_AUDIT_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ texts.get('audit_logs', '审计日志') }}</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        h1 { color: #333; text-align: center; }
        .log-table { width: 100%; border-collapse: collapse; margin: 20px 0; }
        .log-table th, .log-table td { padding: 10px; text-align: left; border-bottom: 1px solid #ddd; font-size: 13px; vertical-align: top; }
        .log-table th { background: #f8f9fa; font-weight: bold; }
        .back-link { display: inline-block; margin-bottom: 20px; color: #007bff; text-decoration: none; }
        .link-inline { display: inline-block; margin-left: 10px; color: #007bff; text-decoration: none; }
        .muted { color: #6b7280; font-size: 12px; }
    </style>
</head>
<body>
    <div class="container">
        <a href="{{ url_for('admin_root') }}" class="back-link">← 管理总览</a>
        <a href="{{ url_for('admin_users') }}" class="link-inline">用户管理</a>
        <a href="{{ url_for('admin_alert_settings') }}" class="link-inline">预警阈值</a>
        <h1>{{ texts.get('audit_logs', '审计日志') }}</h1>
        <div style="display:flex; gap:8px; flex-wrap:wrap; margin:8px 0 10px;">
            <a href="/admin/audit?action=submit_log_entry" style="font-size:12px; color:#0d6efd; text-decoration:none; border:1px solid #dbeafe; padding:4px 8px; border-radius:999px;">原木入库</a>
            <a href="/admin/audit?action=submit_saw" style="font-size:12px; color:#0d6efd; text-decoration:none; border:1px solid #dbeafe; padding:4px 8px; border-radius:999px;">锯解</a>
            <a href="/admin/audit?action=submit_dip" style="font-size:12px; color:#0d6efd; text-decoration:none; border:1px solid #dbeafe; padding:4px 8px; border-radius:999px;">药浸</a>
            <a href="/admin/audit?action=submit_sort" style="font-size:12px; color:#0d6efd; text-decoration:none; border:1px solid #dbeafe; padding:4px 8px; border-radius:999px;">拣选</a>
            <a href="/admin/audit?action=kiln_action" style="font-size:12px; color:#0d6efd; text-decoration:none; border:1px solid #dbeafe; padding:4px 8px; border-radius:999px;">窑动作</a>
            <a href="/admin/audit?action=submit_secondary_sort" style="font-size:12px; color:#0d6efd; text-decoration:none; border:1px solid #dbeafe; padding:4px 8px; border-radius:999px;">二选</a>
            <a href="/admin/audit?action=submit_secondary_products" style="font-size:12px; color:#0d6efd; text-decoration:none; border:1px solid #dbeafe; padding:4px 8px; border-radius:999px;">二选成品</a>
            <a href="/admin/audit?action=clear_trusted_ips" style="font-size:12px; color:#0d6efd; text-decoration:none; border:1px solid #dbeafe; padding:4px 8px; border-radius:999px;">清除IP信任</a>
        </div>
        <form method="GET" action="{{ url_for('admin_audit_logs') }}" style="display:flex; gap:8px; flex-wrap:wrap; align-items:center; margin:10px 0 14px;">
            <input type="text" name="operator" value="{{ filters.operator }}" placeholder="操作人" style="padding:8px; border:1px solid #ddd; border-radius:4px; width:180px;">
            <input type="text" name="action" value="{{ filters.action }}" placeholder="动作" style="padding:8px; border:1px solid #ddd; border-radius:4px; width:180px;">
            <input type="text" name="keyword" value="{{ filters.keyword }}" placeholder="目标/详情关键词" style="padding:8px; border:1px solid #ddd; border-radius:4px; width:260px;">
            <button type="submit" style="padding:8px 12px; border:none; border-radius:4px; background:#007bff; color:#fff; cursor:pointer;">筛选</button>
            <a href="{{ url_for('admin_audit_logs') }}" style="color:#007bff; text-decoration:none;">清空</a>
        </form>
        <p class="muted">本页 {{ logs|length }} 条 / 共 {{ pager.total }} 条（第 {{ pager.page }} / {{ pager.total_pages }} 页）</p>

        <table class="log-table">
            <thead>
                <tr>
                    <th style="width:200px;">时间</th>
                    <th style="width:160px;">操作人</th>
                    <th style="width:180px;">动作</th>
                    <th style="width:220px;">目标</th>
                    <th>详情</th>
                </tr>
            </thead>
            <tbody>
                {% for row in logs %}
                <tr>
                    <td>{{ row.created_at or '' }}</td>
                    <td>{{ row.operator or '' }}</td>
                    <td>{{ row.action or '' }}</td>
                    <td>{{ row.target or '' }}</td>
                    <td>{{ row.detail or '' }}</td>
                </tr>
                {% endfor %}
                {% if not logs %}
                <tr><td colspan="5" class="muted">暂无日志</td></tr>
                {% endif %}
            </tbody>
        </table>
        <div style="display:flex; align-items:center; gap:10px; margin-top:10px; flex-wrap:wrap;">
            {% if pager.has_prev %}
            <a href="{{ url_for('admin_audit_logs', operator=filters.operator, action=filters.action, keyword=filters.keyword, page=pager.prev_page) }}" style="color:#0d6efd; text-decoration:none;">上一页</a>
            {% else %}
            <span class="muted">上一页</span>
            {% endif %}

            {% if pager.has_next %}
            <a href="{{ url_for('admin_audit_logs', operator=filters.operator, action=filters.action, keyword=filters.keyword, page=pager.next_page) }}" style="color:#0d6efd; text-decoration:none;">下一页</a>
            {% else %}
            <span class="muted">下一页</span>
            {% endif %}
        </div>
    </div>
</body>
</html>
"""


__all__ = ['ADMIN_USERS_TEMPLATE', 'ADMIN_DASHBOARD_TEMPLATE', 'ADMIN_AUDIT_TEMPLATE', 'ADMIN_ALERT_SETTINGS_TEMPLATE', 'ADMIN_ALERT_CENTER_TEMPLATE', 'ADMIN_HR_SETTINGS_TEMPLATE', 'ADMIN_HR_EMPLOYEES_TEMPLATE']
