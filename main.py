import asyncio
import logging

from aiogram import Bot, Dispatcher
from core.config import BotTokenConfig
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from db.base import engine, Base
from db.models import User

from bot.schedul import check_grades_job
from bot.handlers import router
from db.requests import get_all_semesters
from bot.cache import update_cache, semester_cache


bot = Bot(token=BotTokenConfig.BOT_TOKEN)
dp = Dispatcher()

tg_id = 992941959

dp.include_router(router)

async def create_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def main():
    try:
        scheduler = AsyncIOScheduler()

        scheduler.add_job(check_grades_job, "interval", minutes=60, args=(bot,))
        scheduler.start()
        await create_db()
        await update_cache(tg_id)
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    except Exception as e:
        print(e)
    finally:
        await bot.session.close()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())