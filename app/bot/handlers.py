from aiogram import Router, F
from aiogram.types import Message

from services.text_query import answer_text_query

router = Router()


@router.message(F.text == "/start")
async def handle_start(message: Message) -> None:
    await message.answer(
        "Привет. Я бот-аналитик по базе видео.\n"
        "Просто задай текстовый вопрос, а я отвечу числом.\n\n"
        "Примеры:\n"
        "• Сколько всего видео есть в системе?\n"
        "• Сколько видео у креатора с id ... вышло с 1 по 5 ноября 2025 года?\n"
        "• Сколько видео набрало больше 100 000 просмотров?\n"
        "• На сколько просмотров в сумме выросли все видео 28 ноября 2025?\n"
        "• Сколько разных видео получали новые просмотры 27 ноября 2025?"
    )


@router.message(F.text)
async def handle_text(message: Message) -> None:
    user_text = (message.text or "").strip()
    if not user_text:
        await message.answer("Напиши текстовый вопрос.")
        return

    try:
        value = await answer_text_query(user_text)
    except Exception:
        # тут можно залогировать ошибку, чтобы понять, что именно сломалось
        await message.answer(
            "Не смог обработать запрос. Попробуй спросить чуть проще "
            "или другими словами."
        )
        return

    # Важно для ТЗ: просто число в ответе
    await message.answer(str(value))
