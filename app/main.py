# app/bot/main.py

import asyncio

from aiogram import Bot, Dispatcher

from core.config import bot_settings
from bot.handlers import router


async def main() -> None:
    bot = Bot(token=bot_settings.BOT_TOKEN)
    dp = Dispatcher()

    dp.include_router(router)

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
