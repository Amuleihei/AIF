import os
from typing import Any

import requests


LOCAL_AI_URL = (
    os.getenv("AIF_LOCAL_AI_URL", "http://127.0.0.1:8012/v1/chat/completions").strip()
    or "http://127.0.0.1:8012/v1/chat/completions"
)
LOCAL_AI_MODEL = (
    os.getenv("AIF_LOCAL_AI_MODEL", "current-chat-model.gguf").strip()
    or "current-chat-model.gguf"
)
LOCAL_AI_TIMEOUT = float(os.getenv("AIF_LOCAL_AI_TIMEOUT", "45") or "45")
DEFAULT_SYSTEM_PROMPT = (
    "你是 AIF 的中文工厂运营助理。"
    "回答要简洁、实用、偏木材厂管理场景。"
    "如果用户问题不够具体，就先给最实用的短建议。"
)


def _call_local_ai_messages(
    messages: list[dict[str, str]],
    temperature: float = 0.2,
    max_tokens: int = 300,
    timeout: float | None = None,
) -> str:
    payload: dict[str, Any] = {
        "model": LOCAL_AI_MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    response = requests.post(LOCAL_AI_URL, json=payload, timeout=(float(timeout) if timeout else LOCAL_AI_TIMEOUT))
    response.raise_for_status()
    data = response.json()
    choices = data.get("choices") or []
    if not choices:
        return "⚠️ AI 无返回内容"

    message = (choices[0] or {}).get("message") or {}
    content = str(message.get("content") or "").strip()
    return content or "⚠️ AI 返回为空"


def ask_ai(user_text: str, system_prompt: str | None = None, max_tokens: int = 300, timeout: float | None = None) -> str:
    prompt = str(system_prompt or DEFAULT_SYSTEM_PROMPT).strip() or DEFAULT_SYSTEM_PROMPT
    return _call_local_ai_messages(
        [
            {"role": "system", "content": prompt},
            {"role": "user", "content": user_text},
        ],
        temperature=0.2,
        max_tokens=max_tokens,
        timeout=timeout,
    )


def check_local_ai() -> str:
    try:
        response = requests.post(
            LOCAL_AI_URL,
            json={
                "model": LOCAL_AI_MODEL,
                "messages": [{"role": "user", "content": "你好"}],
                "temperature": 0,
                "max_tokens": 8,
            },
            timeout=min(LOCAL_AI_TIMEOUT, 15),
        )
        response.raise_for_status()
        return f"🧠 AI 在线\n模型: {LOCAL_AI_MODEL}\n接口: {LOCAL_AI_URL}"
    except Exception as e:
        return f"⚠️ AI 不可用\n模型: {LOCAL_AI_MODEL}\n接口: {LOCAL_AI_URL}\n原因: {e}"


def handle_ai(text):
    if text == "AI状态":
        return check_local_ai()

    if text in ("AI帮助", "AI help", "ai help"):
        return "🤖 AI用法\n1. AI状态\n2. AI 你的问题"

    if text.startswith("AI "):
        prompt = (text[3:] or "").strip()
        if not prompt:
            return "⚠️ 请输入 AI 问题"
        try:
            answer = ask_ai(prompt)
            return f"🤖 AI回答\n{answer}"
        except Exception as e:
            return f"⚠️ AI 调用失败\n{e}"

    return None
