import os
from dotenv import load_dotenv


load_dotenv()

class DbConnectConfig: #Конфиг подключения базы данных
    DB_USER = os.getenv("DB_USER")
    DB_PASS = os.getenv("DB_PASS")
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_NAME = os.getenv("DB_NAME")
    DB_PORT = os.getenv("DB_PORT", "5432")

    DATABASE_URL = f"postgresql+asyncpg://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

class BotTokenConfig:
    BOT_TOKEN = os.getenv("BOT_TOKEN")

class EncryptConfig:
    ENCRYPTION_KEY=os.getenv("ENCRYPTION_KEY")
