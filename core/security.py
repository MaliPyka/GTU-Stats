from core.config import EncryptConfig
from cryptography.fernet import Fernet

SECRET_KEY = EncryptConfig.ENCRYPTION_KEY

if not SECRET_KEY:
    raise ValueError("SECRET_KEY не найден!")

cipher = Fernet(SECRET_KEY.encode())

def encrypt_password(password: str) -> bytes:
    return cipher.encrypt(password.encode())

def decrypt_password(encrypted_password: bytes) -> str:
    return cipher.decrypt(encrypted_password).decode()
