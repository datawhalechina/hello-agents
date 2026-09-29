"""RSA 密钥管理服务 - 用于前端传输密码的非对称加密"""

import base64
import os
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes, serialization

# 密钥文件存储路径（backend/data/rsa_private_key.pem）
_KEY_DIR = Path(__file__).parent.parent / "data"
_PRIVATE_KEY_PATH = _KEY_DIR / "rsa_private_key.pem"
_PUBLIC_KEY_PATH = _KEY_DIR / "rsa_public_key.pem"

_private_key = None
_public_key = None


def init_rsa_keys():
    """初始化 RSA 密钥对：如果密钥文件已存在则加载，否则生成新密钥"""
    global _private_key, _public_key

    _KEY_DIR.mkdir(parents=True, exist_ok=True)

    if _PRIVATE_KEY_PATH.exists():
        # 加载已有密钥
        with open(_PRIVATE_KEY_PATH, "rb") as f:
            _private_key = serialization.load_pem_private_key(f.read(), password=None)
        with open(_PUBLIC_KEY_PATH, "rb") as f:
            _public_key = serialization.load_pem_public_key(f.read())
    else:
        # 生成新 RSA 2048 密钥对
        _private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )
        _public_key = _private_key.public_key()

        # 保存私钥
        with open(_PRIVATE_KEY_PATH, "wb") as f:
            f.write(_private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            ))

        # 保存公钥
        with open(_PUBLIC_KEY_PATH, "wb") as f:
            f.write(_public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            ))

    print(f"✅ RSA密钥已{'加载' if _PRIVATE_KEY_PATH.exists() else '生成'}")
    print(f"   私钥: {_PRIVATE_KEY_PATH}")
    print(f"   公钥: {_PUBLIC_KEY_PATH}")


def get_public_key_pem() -> str:
    """获取公钥 PEM 字符串（用于前端加密）"""
    global _public_key
    if _public_key is None:
        init_rsa_keys()
    return _public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode()


def decrypt_data(encrypted_b64: str) -> str:
    """解密前端 RSA-OAEP 加密的 Base64 数据"""
    global _private_key
    if _private_key is None:
        init_rsa_keys()

    try:
        ciphertext = base64.b64decode(encrypted_b64)
        plaintext = _private_key.decrypt(
            ciphertext,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )
        return plaintext.decode()
    except Exception as e:
        raise ValueError(f"RSA解密失败: {e}")
