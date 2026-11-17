"""密码哈希、登录验证、权限判断（负责人 A，REQ-001、REQ-020）。"""


def hash_password(password: str) -> str:
    """用标准库 hashlib.pbkdf2_hmac 加随机盐生成哈希。"""
    raise NotImplementedError("REQ-001 任务卡 A-1 实现")


def verify_password(password: str, password_hash: str) -> bool:
    raise NotImplementedError("REQ-001 任务卡 A-1 实现")


def can_access(role: str, feature: str) -> bool:
    """角色能否使用某功能。"""
    raise NotImplementedError("REQ-020 待 A 实现")
