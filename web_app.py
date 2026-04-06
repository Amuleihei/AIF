#!/usr/bin/env python3
import logging
import os
import time
from pathlib import Path

from flask import Flask, g, got_request_exception, request, session as flask_session, redirect, url_for, flash
from flask_login import LoginManager, current_user, logout_user

from aif import load_modules
from web.models import Session, User
from web.observability import configure_web_logging
from web.routes import register_routes
from web.services.ai_monitor_service import maybe_trigger_deep_monitor_by_db


BASE = Path(__file__).parent
configure_web_logging(BASE)
logger = logging.getLogger("aif.web")

# Load AIF handlers once at startup.
load_modules()

app = Flask(__name__)
secret = os.getenv("AIF_SECRET_KEY", "").strip()
if not secret:
    # 兼容本地开发；生产环境请通过 .env 提供固定密钥。
    secret = "dev-only-change-this-secret-key"
app.secret_key = secret
app.config["SECRET_KEY"] = secret
app.config["WTF_CSRF_ENABLED"] = True
SESSION_TIMEOUT_MINUTES = int(os.getenv("AIF_SESSION_TIMEOUT_MINUTES", "120") or "120")
LAN_EXEMPT_PREFIX = str(os.getenv("AIF_LAN_EXEMPT_PREFIX", "192.168.1.") or "192.168.1.").strip()

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"
login_manager.login_message = "请先登录"


@login_manager.user_loader
def load_user(user_id):
    session = Session()
    user = session.query(User).filter_by(id=int(user_id)).first()
    session.close()
    return user


register_routes(app)


def _client_ip() -> str:
    xff = (request.headers.get("X-Forwarded-For") or "").strip()
    if xff:
        return xff.split(",")[0].strip()
    return str(request.remote_addr or "").strip()


def _is_lan_exempt(ip: str) -> bool:
    return bool(ip) and ip.startswith(LAN_EXEMPT_PREFIX)


@app.before_request
def _before_request():
    g._request_started_at = time.time()
    if not current_user.is_authenticated:
        return None

    ip = _client_ip()
    now_ts = int(time.time())
    prev_seen_ts = int(flask_session.get("last_seen_ts") or now_ts)
    flask_session["last_activity_ip"] = ip

    if _is_lan_exempt(ip):
        flask_session["session_timeout_exempt"] = "lan"
        flask_session["last_seen_ts"] = now_ts
        return None

    flask_session["session_timeout_exempt"] = ""
    timeout_seconds = max(60, int(SESSION_TIMEOUT_MINUTES) * 60)
    if (now_ts - prev_seen_ts) > timeout_seconds:
        username = str(getattr(current_user, "username", "") or "")
        logout_user()
        flask_session.clear()
        flash(f"会话已超时（{SESSION_TIMEOUT_MINUTES} 分钟），请重新登录", "error")
        logger.info("session_timeout username=%s ip=%s timeout_min=%s", username, ip, SESSION_TIMEOUT_MINUTES)
        return redirect(url_for("login"))

    flask_session["last_seen_ts"] = now_ts
    return None


@app.after_request
def _after_request(response):
    started = float(getattr(g, "_request_started_at", time.time()))
    elapsed_ms = int((time.time() - started) * 1000)
    try:
        if response.status_code < 400:
            maybe_trigger_deep_monitor_by_db(lang="zh")
    except Exception:
        logger.exception("ai_monitor_trigger_failed")
    logger.info(
        "http_request method=%s path=%s status=%s dur_ms=%s ip=%s",
        request.method,
        request.path,
        response.status_code,
        elapsed_ms,
        request.remote_addr,
    )
    return response


@got_request_exception.connect_via(app)
def _log_unhandled_error(sender, exception, **extra):
    logger.exception("http_exception path=%s method=%s", request.path, request.method, exc_info=exception)


if __name__ == "__main__":
    host = os.getenv("AIF_WEB_HOST", "0.0.0.0").strip() or "0.0.0.0"
    port = int(os.getenv("AIF_WEB_PORT", "8080") or 8080)
    ssl_enable = str(os.getenv("AIF_SSL_ENABLE", "0") or "0").strip().lower() in ("1", "true", "yes", "on")
    cert_file = os.getenv("AIF_SSL_CERT", "").strip()
    key_file = os.getenv("AIF_SSL_KEY", "").strip()

    ssl_ctx = None
    scheme = "http"
    if ssl_enable and cert_file and key_file:
        ssl_ctx = (cert_file, key_file)
        scheme = "https"

    print("🌐 AIF Web界面启动中...")
    print(f"📱 打开浏览器访问: {scheme}://localhost:{port}")
    app.run(host=host, port=port, debug=False, ssl_context=ssl_ctx, threaded=True)
