from sqlalchemy import func, Float, Boolean, LargeBinary
from sqlalchemy import String, Integer, ForeignKey, BigInteger, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from db.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tg_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    login: Mapped[str] = mapped_column(String)
    encrypted_password: Mapped[bytes] = mapped_column(LargeBinary)
    language: Mapped[str] = mapped_column(String, default = "en")
    created_at: Mapped[DateTime] = mapped_column(DateTime,default=func.now())


class Grade(Base):
    __tablename__ = "grades"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tg_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.tg_id", ondelete='CASCADE'), nullable=False)
    lesson_name: Mapped[str] = mapped_column(String, nullable=False)
    score: Mapped[float] = mapped_column(Float, default = 0.0)
    old_score: Mapped[float] = mapped_column(Float, default = 0.0)
    last_update: Mapped[DateTime] = mapped_column(DateTime, server_default = func.now())
    semester_id: Mapped[int] = mapped_column(ForeignKey("semesters.id"), nullable=False)
    actual: Mapped[bool] = mapped_column(default=True)

    def __repr__(self):
        return f"<Grade(subject={self.lesson_name}, score={self.score})>"


class Semester(Base):
    __tablename__ = "semesters"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tg_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.tg_id", ondelete='CASCADE'), nullable=False)
    semester_name: Mapped[str] = mapped_column(String, nullable=False)

