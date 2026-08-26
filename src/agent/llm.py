"""ChatOpenAI client targeting agentgateway's OpenAI-compatible API (LM Studio upstream)."""

from __future__ import annotations

from langchain_openai import ChatOpenAI

from config import Settings


def get_chat_model(settings: Settings) -> ChatOpenAI:
    return ChatOpenAI(
        base_url=settings.chat_base_url,
        model=settings.model_name,
        api_key=settings.openai_api_key,
        temperature=0,
    )
