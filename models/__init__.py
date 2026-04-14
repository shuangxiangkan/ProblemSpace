"""LLM factory — single place to instantiate language models.

Usage
-----
from models import get_llm

llm = get_llm()                    # uses LLM_PROVIDER from .env (default: deepseek)
llm = get_llm("openai")            # explicit provider
llm = get_llm("glm", thinking_type="disabled")
structured = llm.with_structured_output(MySchema)

Supported providers
-------------------
deepseek  — DeepSeek Chat (OpenAI-compatible API)
openai    — OpenAI ChatGPT
glm       — Zhipu GLM (OpenAI-compatible API)

Environment variables
---------------------
Each provider uses the same naming convention:
<PROVIDER>_API_KEY
<PROVIDER>_MODEL
<PROVIDER>_BASE_URL

GLM-specific optional environment variables:
GLM_THINKING_TYPE
"""

from __future__ import annotations

import os

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()


_DEFAULT_PROVIDER = "deepseek"
_SUPPORTED_PROVIDERS = ("deepseek", "openai", "glm")


def _env_name(provider: str, field: str) -> str:
    return f"{provider.upper()}_{field}"


def _get_required_env(provider: str, field: str) -> str:
    env_name = _env_name(provider, field)
    value = os.getenv(env_name)
    if value:
        return value
    raise ValueError(
        f"Missing required environment variable: {env_name}. "
        f"Configure {provider} in .env before calling get_llm()."
    )


def _build_chat_model(
    provider: str,
    thinking_type: str | None = None,
    **kwargs,
) -> ChatOpenAI:
    chat_kwargs = {
        "model": _get_required_env(provider, "MODEL"),
        "api_key": _get_required_env(provider, "API_KEY"),
        "base_url": _get_required_env(provider, "BASE_URL"),
        "temperature": 0,
        **kwargs,
    }

    if provider == "glm":
        glm_extra_body = dict(chat_kwargs.get("extra_body") or {})
        glm_extra_body["thinking"] = {
            "type": thinking_type or os.getenv("GLM_THINKING_TYPE", "disabled"),
        }
        chat_kwargs["extra_body"] = glm_extra_body

    return ChatOpenAI(
        **chat_kwargs,
    )


def get_llm(
    provider: str | None = None,
    thinking_type: str | None = None,
    **kwargs,
) -> ChatOpenAI:
    provider = (provider or os.getenv("LLM_PROVIDER", _DEFAULT_PROVIDER)).lower()

    if provider in _SUPPORTED_PROVIDERS:
        return _build_chat_model(provider, thinking_type=thinking_type, **kwargs)

    raise ValueError(
        f"Unknown LLM provider: {provider!r}. "
        f"Supported: {', '.join(_SUPPORTED_PROVIDERS)}. Set LLM_PROVIDER in .env."
    )
