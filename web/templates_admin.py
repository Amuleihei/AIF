from pathlib import Path
import re


_INCLUDE_RE = re.compile(r"{%\s*include\s+['\"]([^'\"]+)['\"]\s*%}")


def _expand_includes(content: str, base_dir: Path) -> str:
    def _replace(match: re.Match[str]) -> str:
        rel = match.group(1).strip()
        candidate = (base_dir / rel)
        if not candidate.exists():
            candidate = (base_dir.parent / rel)
        if not candidate.exists():
            candidate = (base_dir.parent.parent / rel)
        if not candidate.exists():
            return match.group(0)
        child = candidate.read_text(encoding="utf-8")
        return _expand_includes(child, candidate.parent)

    return _INCLUDE_RE.sub(_replace, content)


def _load_template_file(name: str) -> str:
    base = Path(__file__).resolve().parent / "jinja" / "admin"
    path = base / name
    content = path.read_text(encoding="utf-8")
    return _expand_includes(content, path.parent)


ADMIN_USERS_TEMPLATE = _load_template_file("admin_users.html")
ADMIN_DASHBOARD_TEMPLATE = _load_template_file("admin_dashboard.html")
ADMIN_ALERT_SETTINGS_TEMPLATE = _load_template_file("admin_alert_settings.html")
ADMIN_ALERT_CENTER_TEMPLATE = _load_template_file("admin_alert_center.html")
ADMIN_HR_SETTINGS_TEMPLATE = _load_template_file("admin_hr_settings.html")
ADMIN_HR_EMPLOYEES_TEMPLATE = _load_template_file("admin_hr_employees.html")
ADMIN_AUDIT_TEMPLATE = _load_template_file("admin_audit.html")


__all__ = ['ADMIN_USERS_TEMPLATE', 'ADMIN_DASHBOARD_TEMPLATE', 'ADMIN_AUDIT_TEMPLATE', 'ADMIN_ALERT_SETTINGS_TEMPLATE', 'ADMIN_ALERT_CENTER_TEMPLATE', 'ADMIN_HR_SETTINGS_TEMPLATE', 'ADMIN_HR_EMPLOYEES_TEMPLATE']
