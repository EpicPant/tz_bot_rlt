# app/nlp/llm_parser.py

import json
from typing import Any

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from app.nlp.prompts import SPEC_SYSTEM_PROMPT
from app.nlp.spec import QuerySpec


# Инициализируем LLM один раз
llm = ChatOpenAI(
    model="gpt-4.1-mini",  # или другой, какой захочешь
    temperature=0,
)


async def call_llm(system_prompt: str, user_text: str) -> str:
    """
    Вызов langchain-openai: system + user -> content.
    Возвращает строку, которая должна быть чистым JSON.
    """
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_text),
    ]

    resp = await llm.ainvoke(messages)
    # resp.content — это уже строка-ответ от модели
    return resp.content


async def build_spec_from_text(user_text: str) -> QuerySpec:
    """
    Берёт текстовый вопрос, просит модель выдать JSON со спецификацией QuerySpec,
    валидирует через Pydantic и возвращает готовый объект.
    """
    raw = await call_llm(SPEC_SYSTEM_PROMPT, user_text)

    raw_str = raw.strip()

    data: Any = json.loads(raw_str)
    spec = QuerySpec.model_validate(data)
    return spec
