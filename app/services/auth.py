"""密码哈希、登录验证、修改密码、角色权限（负责人 A，REQ-001、REQ-002、REQ-020）。

哈希字符串格式：pbkdf2_sha256$迭代次数$盐(十六进制)$哈希(十六进制)
把算法、迭代次数和盐都存进同一个字符串，验证时不需要再查别的地方；
以后想提高迭代次数，旧密码照样能验证。
"""
import hashlib
import hmac
import secrets

from app.models.entities import ROLE_ADMIN, ROLE_GUARD, User

ALGORITHM = "pbkdf2_sha256"
ITERATIONS = 100_000        # 迭代次数越多越难暴力破解，但登录也越慢；10 万次约几十毫秒
SALT_BYTES = 16

DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_PASSWORD = "admin123"

MIN_PASSWORD_LENGTH = 6   # REQ-002：新密码少于 6 位时拒绝
OLD_PASSWORD_WRONG_MSG = "旧密码不正确"
NEW_PASSWORD_TOO_SHORT_MSG = f"新密码不能少于 {MIN_PASSWORD_LENGTH} 位"
USER_NOT_FOUND_MSG = "用户不存在"

# ---------- REQ-020 角色权限 ----------
# 功能编号与主窗口侧边栏的页面一一对应
FEATURE_GATE = "gate"              # 出入登记
FEATURE_RECORD = "record"          # 出入记录
FEATURE_RESIDENT = "resident"      # 住户管理
FEATURE_VEHICLE = "vehicle"        # 车辆管理
FEATURE_SPACE = "space"            # 车位管理
FEATURE_RESERVATION = "reservation"  # 车位预约
FEATURE_FEE_RULE = "fee_rule"      # 收费规则
FEATURE_ALERT = "alert"            # 预警
FEATURE_STATS = "stats"            # 统计报表
FEATURE_USER = "user"              # 用户管理
FEATURE_BACKUP = "backup"          # 数据备份

ALL_FEATURES = frozenset({
    FEATURE_GATE, FEATURE_RECORD, FEATURE_RESIDENT, FEATURE_VEHICLE, FEATURE_SPACE,
    FEATURE_RESERVATION, FEATURE_FEE_RULE, FEATURE_ALERT, FEATURE_STATS, FEATURE_USER,
    FEATURE_BACKUP,
})

# 白名单：每个角色只能用列出的功能，没列出的一律不能用（ADR-007）。
# 门卫不能用住户、车辆、车位、收费规则、用户管理（REQ-020），以及数据备份（ADR-007 补充）。
ROLE_FEATURES = {
    ROLE_ADMIN: ALL_FEATURES,
    ROLE_GUARD: frozenset({
        FEATURE_GATE, FEATURE_RECORD, FEATURE_RESERVATION, FEATURE_ALERT, FEATURE_STATS,
    }),
}


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


def change_password(user_repo, user_id: int, old_password: str, new_password: str) -> None:
    """修改自己的密码（REQ-002）。

    先校验旧密码，再检查新密码长度，都通过后保存新密码的哈希。
    任何一步不通过都抛 ValueError（消息可直接显示在界面上），且数据库不变。
    修改后旧密码的哈希被覆盖，旧密码自然无法再登录。
    """
    user = user_repo.get(user_id)
    if user is None:
        raise ValueError(USER_NOT_FOUND_MSG)
    if not verify_password(old_password, user.password_hash):
        raise ValueError(OLD_PASSWORD_WRONG_MSG)
    if len(new_password) < MIN_PASSWORD_LENGTH:
        raise ValueError(NEW_PASSWORD_TOO_SHORT_MSG)
    user.password_hash = hash_password(new_password)
    user_repo.update(user)


def can_access(role: str, feature: str) -> bool:
    """角色能否使用某功能（REQ-020）。未知角色或未知功能一律返回 False。"""
    return feature in ROLE_FEATURES.get(role, frozenset())
