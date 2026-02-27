from sqlalchemy import BigInteger, select, update

from db.models import User, Grade

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
    
async def update_lessons_and_grades(tg_id: int, lesson_name: str, score: float):
    async with async_session() as session:
        query = await session.execute(select(Grade).where(Grade.tg_id == tg_id, Grade.lesson_name == lesson_name))
        grade_obj = query.scalars().one_or_none()
        
        if grade_obj is None:
            session.add(Grade(tg_id=tg_id, lesson_name=lesson_name, score=score, old_score=score))
            await session.commit()
        else:
            if grade_obj.score != score:
                grade_obj.old_score = grade_obj.score 
                grade_obj.score = score              
                await session.commit()

        result = await session.execute(select(Grade).where(Grade.tg_id == tg_id, Grade.actual == True))
        return result.scalars().all()
    
async def get_user_data(tg_id: int):
    async with async_session() as session:
        query = await session.execute(select(User).where(User.tg_id == tg_id))
        user = query.scalars().one_or_none()
        return user



