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
    created_at: Mapped[DateTime] = mapped_column(DateTime,default=func.now())

