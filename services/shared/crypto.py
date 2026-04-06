"""API Key 加密/解密 & 掩码工具

使用 Fernet 对称加密（基于 AES-128-CBC + HMAC-SHA256），
加密密钥从 Settings.secret_key 派生。
"""

from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet


def _derive_fernet_key(secret: str) -> bytes:
    """从任意长度 secret 派生 32-byte URL-safe base64 密钥"""
    digest = hashlib.sha256(secret.encode()).digest()
    return base64.urlsafe_b64encode(digest)


def encrypt_api_key(api_key: str, secret: str) -> str:
    """加密 API Key，返回 base64 密文"""
    f = Fernet(_derive_fernet_key(secret))
    return f.encrypt(api_key.encode()).decode()


def decrypt_api_key(encrypted: str, secret: str) -> str:
    """解密 API Key"""
    f = Fernet(_derive_fernet_key(secret))
    return f.decrypt(encrypted.encode()).decode()


def mask_api_key(api_key: str, visible: int = 4) -> str:
    """对 API Key 做掩码处理，仅保留首尾各 visible 字符

    例: sk-abcdef123456 → sk-a***3456
    """
    if len(api_key) <= visible * 2:
        return "***"
    return f"{api_key[:visible]}***{api_key[-visible:]}"
