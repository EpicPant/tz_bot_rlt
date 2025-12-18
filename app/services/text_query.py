from app.nlp.llm_parser import build_spec_from_text
from app.services.executor import answer_query_spec


async def answer_text_query(user_text: str) -> int:
    """
    Высокоуровневая функция:
    1) парсим текст вопроса в QuerySpec через LLM,
    2) выполняем запрос к БД,
    3) возвращаем одно число.
    """
    spec = await build_spec_from_text(user_text)
    value = await answer_query_spec(spec)
    return value
