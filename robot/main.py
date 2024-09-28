import asyncio
import aiohttp
from aiogram import Bot, Dispatcher, executor
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from database import get_tokens, delete_token, get_all_user_tokens
from handlers import register_handlers
from aiogram.utils.exceptions import BotBlocked, BotKicked, ChatNotFound, UserDeactivated, TelegramAPIError, Unauthorized

async def create_bot_session(token):
    connector = aiohttp.TCPConnector(ssl=False)
    session = aiohttp.ClientSession(connector=connector)
    bot = Bot(token=token)
    bot._session = session
    return bot, session

async def start_bot(token):
    try:
        bot, session = await create_bot_session(token)
        dp = Dispatcher(bot, storage=MemoryStorage())
        dp.middleware.setup(LoggingMiddleware())
        await register_handlers(dp, bot_token=token)
        await dp.skip_updates()
        await dp.start_polling()
    except (BotBlocked, BotKicked, ChatNotFound, UserDeactivated, TelegramAPIError, Unauthorized) as e:
        print(f"Ошибка запуска бота с токеном {token}: {e}")
        delete_token(token)
    finally:
        await session.close()

async def run_bot():
    tokens = get_tokens()
    custom_tokens = get_all_user_tokens()
    all_tokens = [token for token, _ in tokens] + [token[0] for token in custom_tokens]

    await asyncio.gather(*(start_bot(token) for token in all_tokens))

if __name__ == "__main__":
    asyncio.run(run_bot())
