"""密码哈希、登录验证、权限判断（负责人 A，REQ-001、REQ-020）。

哈希字符串格式：pbkdf2_sha256$迭代次数$盐(十六进制)$哈希(十六进制)
把算法、迭代次数和盐都存进同一个字符串，验证时不需要再查别的地方；
以后想提高迭代次数，旧密码照样能验证。
"""
import hashlib
import hmac
import secrets

from app.models.entities import ROLE_ADMIN, User

ALGORITHM = "pbkdf2_sha256"
ITERATIONS = 100_000        # 迭代次数越多越难暴力破解，但登录也越慢；10 万次约几十毫秒
SALT_BYTES = 16

DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_PASSWORD = "admin123"


def _pbkdf2(password: str, salt: bytes, iterations: int) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)


def hash_password(password: str) -> str:
    """用标准库 hashlib.pbkdf2_hmac 加随机盐生成哈希。

    每次调用生成新的随机盐，所以同一个密码两次的结果不同。
    """
    salt = secrets.token_bytes(SALT_BYTES)
    digest = _pbkdf2(password, salt, ITERATIONS)
    return f"{ALGORITHM}${ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, password_hash: str) -> bool:
    """取出哈希里保存的盐和迭代次数，用同样的参数再算一遍，比较结果。

    哈希字符串格式不对时返回 False，不抛异常。
    """
    try:
        algorithm, iterations, salt_hex, digest_hex = password_hash.split("$")
        if algorithm != ALGORITHM:
            return False
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(digest_hex)
        actual = _pbkdf2(password, salt, int(iterations))
    except (ValueError, AttributeError):
        return False
    # compare_digest 的耗时与在第几位不同无关，避免通过响应时间猜出哈希
    return hmac.compare_digest(actual, expected)


def authenticate(user_repo, username: str, password: str) -> User | None:
    """登录校验：用户名存在且密码正确时返回该用户，否则返回 None。

    用户名不存在和密码错误都返回 None，调用方无法区分，
    界面统一提示"用户名或密码错误"（REQ-001）。
    """
    user = user_repo.get_by_username(username)
    if user is None:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def ensure_default_admin(user_repo) -> None:
    """users 表为空时写入默认管理员 admin / admin123（只保存哈希）。

    表里已有用户时什么都不做，所以重复启动不会重复插入，
    也不会把改过的管理员密码重置回 admin123。
    """
    if user_repo.list_all():
        return
    user_repo.add(User(
        id=None,
        username=DEFAULT_ADMIN_USERNAME,
        password_hash=hash_password(DEFAULT_ADMIN_PASSWORD),
        role=ROLE_ADMIN,
    ))


def can_access(role: str, feature: str) -> bool:
    """角色能否使用某功能。"""
    raise NotImplementedError("REQ-020 待 A 实现")
