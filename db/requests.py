from sqlalchemy import BigInteger, select

from db.models import User

from db.base import async_session


async def add_user(tg_id: int, login: str, password: bytes):
    async with async_session() as session:
        session.add(User(tg_id=tg_id,login=login,encrypted_password=password))
        await session.commit()

async def check_user_exists(tg_id: int) -> bool:
    async with async_session() as session:
        query = await session.execute(select(User).where(User.tg_id==tg_id))
        result = query.scalars().one_or_none()
        return result is not None