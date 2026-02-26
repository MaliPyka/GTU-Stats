import asyncio
import logging

from aiogram import Bot, Dispatcher
from core.config import BotTokenConfig
from db.base import engine, Base
from db.models import User

from bot.handlers import router

bot = Bot(token=BotTokenConfig.BOT_TOKEN)
dp = Dispatcher()

dp.include_router(router)

async def create_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def main():
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await create_db()
        await dp.start_polling(bot)
    except Exception as e:
        print(e)
    finally:
        await bot.session.close()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())