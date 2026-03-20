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
            return match.group(0)
        child = candidate.read_text(encoding="utf-8")
        return _expand_includes(child, candidate.parent)

    return _INCLUDE_RE.sub(_replace, content)


def _load_template_file(name: str) -> str:
    base = Path(__file__).resolve().parent / "jinja"
    path = base / name
    content = path.read_text(encoding="utf-8")
    return _expand_includes(content, path.parent)


LOGIN_TEMPLATE = _load_template_file("login.html")
HTML_TEMPLATE = _load_template_file("main.html")
