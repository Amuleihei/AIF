import os

def _required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"缺少环境变量: {name}")
    return value


def get_bot_token() -> str:
    return _required_env("BOT_TOKEN")


def get_bot_chat_id() -> str:
    return _required_env("BOT_CHAT_ID")


def get_miniapp_url() -> str:
    return os.getenv("TG_MINIAPP_URL", "").strip()
