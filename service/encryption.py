from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
import base64
import os
from config import ENCRYPTION_KEY

def generate_key(password: str, salt: bytes = None) -> bytes:
    """
    从密码生成加密密钥
    """
    if salt is None:
        salt = os.urandom(16)
    
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
        backend=default_backend()
    )
    
    key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
    return key

def get_cipher() -> Fernet:
    """
    获取加密器实例
    """
    # 使用配置文件中的密钥
    key = ENCRYPTION_KEY.encode() if isinstance(ENCRYPTION_KEY, str) else ENCRYPTION_KEY
    return Fernet(key)

def encrypt_password(password: str) -> str:
    """
    加密密码
    """
    if not password:
        return password
    
    cipher = get_cipher()
    encrypted = cipher.encrypt(password.encode())
    return encrypted.decode()

def decrypt_password(encrypted_password: str) -> str:
    """
    解密密码
    如果解密失败（可能是旧的明文密码），返回原始值
    """
    if not encrypted_password:
        return encrypted_password
    
    cipher = get_cipher()
    try:
        decrypted = cipher.decrypt(encrypted_password.encode())
        return decrypted.decode()
    except Exception:
        # 解密失败，说明是旧的明文密码，直接返回
        return encrypted_password