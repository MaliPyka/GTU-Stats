from sqlalchemy import BigInteger, func, select, update, delete

from db.models import User, Grade, Semester

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


async def update_lessons_and_grades(tg_id: int, lesson_name: str, score: float, semester_id: int):
    async with async_session() as session:
        # 1. Ищем конкретный предмет
        query = await session.execute(
            select(Grade).where(Grade.tg_id == tg_id, Grade.lesson_name == lesson_name)
        )
        grade_obj = query.scalars().one_or_none()

        # 2. Создаем или обновляем
        if grade_obj is None:
            grade_obj = Grade(
                tg_id=tg_id,
                lesson_name=lesson_name,
                score=score,
                old_score=score,
                semester_id=semester_id
            )
            session.add(grade_obj)
        else:
            if grade_obj.score != score:
                grade_obj.old_score = grade_obj.score
                grade_obj.score = score
            grade_obj.semester_id = semester_id

        await session.commit()

        max_sem_query = await session.execute(select(func.max(Semester.id)).where(Semester.tg_id == tg_id))
        current_sem_id = max_sem_query.scalar()

        grade_obj.actual = (grade_obj.semester_id == current_sem_id)
        await session.commit()

        await session.refresh(grade_obj)

        return grade_obj
    
async def get_user_data(tg_id: int):
    async with async_session() as session:
        query = await session.execute(select(User).where(User.tg_id == tg_id))
        user = query.scalars().one_or_none()
        return user
    
async def get_all_user():
    async with async_session() as session:
        query = await session.execute(select(User))
        return query.scalars().all()
    

async def sync_old_scores_in_db(tg_id, lesson_name, current_score):
    async with async_session() as session:
        await session.execute(
            update(Grade)
            .where(Grade.tg_id == tg_id, Grade.lesson_name == lesson_name, Grade.actual == True)
            .values(old_score=current_score)
        )
        await session.commit()


async def sync_semesters(semester_name: str, tg_id: int):
    async with async_session() as session:
        session.add(Semester(semester_name=semester_name, tg_id=tg_id))
        await session.commit()


async def get_all_semesters(tg_id: int):
    async with async_session() as session:
        query = await session.execute(select(Semester).where(Semester.tg_id==tg_id))
        return query.scalars().all()


async def get_semester_grades(tg_id: int, sem_id: int):
    async with async_session() as session:
        query = await session.execute(select(Grade).where(Grade.tg_id == tg_id, Grade.semester_id == sem_id))
        return query.scalars().all()


async def get_semester_id_by_index(tg_id: int, index: int) -> int | None:
    """
    index = 0 (первый семестр)
    index = 1 (второй семестр)
    и так далее
    """
    async with async_session() as session:
        query = (
            select(Semester.id)
            .where(Semester.tg_id == tg_id)
            .order_by(Semester.id.asc())
            .limit(1)
            .offset(index)
        )
        result = await session.execute(query)
        return result.scalar()


async def delete_user(tg_id: int):
    async with async_session() as session:
        await session.execute(delete(User).where(User.tg_id==tg_id))
        await session.commit()

async def get_current_semester(tg_id: int):
    async with async_session() as session:
        query = select(func.max(Semester.id)).where(Semester.tg_id == tg_id)
        result = await session.execute(query)
        current_semester = result.scalar()

        return current_semester




