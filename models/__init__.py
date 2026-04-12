"""LLM factory — single place to instantiate language models.

Usage
-----
from models import get_llm

llm = get_llm()                    # uses LLM_PROVIDER from .env (default: deepseek)
llm = get_llm("openai")            # explicit provider
structured = llm.with_structured_output(MySchema)

Supported providers
-------------------
deepseek  — DeepSeek Chat (OpenAI-compatible API)
openai    — OpenAI ChatGPT
"""

from __future__ import annotations

import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()


def get_llm(provider: str | None = None, **kwargs) -> ChatOpenAI:
    provider = provider or os.getenv("LLM_PROVIDER", "deepseek")

    if provider == "deepseek":
        return ChatOpenAI(
            model=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
            api_key=os.getenv("DEEPSEEK_API_KEY"),
            base_url="https://api.deepseek.com",
            temperature=0,
            **kwargs,
        )

    if provider == "openai":
        return ChatOpenAI(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            api_key=os.getenv("OPENAI_API_KEY"),
            temperature=0,
            **kwargs,
        )

    raise ValueError(
        f"Unknown LLM provider: {provider!r}. "
        "Supported: deepseek, openai. Set LLM_PROVIDER in .env."
    )
