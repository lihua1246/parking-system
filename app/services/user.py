"""用户管理业务规则（负责人 A，REQ-021）。

规则：用户名必填且唯一；角色只能是管理员或门卫；初始密码不少于 6 位（与 REQ-002 一致）；
不能删除当前登录的用户；系统至少保留一名管理员。
"谁能打开用户管理"属于 REQ-020 角色权限，不在这里判断。
"""
import sqlite3

from app.models.entities import ROLE_ADMIN, ROLES, User
from app.services.auth import MIN_PASSWORD_LENGTH, hash_password

USERNAME_EMPTY_MSG = "用户名不能为空"
USERNAME_EXISTS_MSG = "用户名已存在"
ROLE_INVALID_MSG = "角色只能是管理员或门卫"
PASSWORD_TOO_SHORT_MSG = f"密码不能少于 {MIN_PASSWORD_LENGTH} 位"
USER_NOT_FOUND_MSG = "该用户已不存在，请刷新"
DELETE_SELF_MSG = "不能删除当前登录的用户"
LAST_ADMIN_MSG = "系统至少保留一名管理员"


class UserService:
    def __init__(self, user_repo):
        self.user_repo = user_repo

    def add(self, username: str, password: str, role: str) -> int:
        """新增用户，返回新用户的 id。密码只保存哈希。规则不通过时抛 ValueError。"""
        username = username.strip()
        if not username:
            raise ValueError(USERNAME_EMPTY_MSG)
        if role not in ROLES:
            raise ValueError(ROLE_INVALID_MSG)
        if len(password) < MIN_PASSWORD_LENGTH:
            raise ValueError(PASSWORD_TOO_SHORT_MSG)
        user = User(id=None, username=username, password_hash=hash_password(password), role=role)
        try:
            return self.user_repo.add(user)
        except sqlite3.IntegrityError:
            # users.username 有 UNIQUE 约束，重复时数据库拒绝，这里翻译成中文提示
            raise ValueError(USERNAME_EXISTS_MSG) from None

    def delete(self, user_id: int, current_user_id: int) -> None:
        """删除用户。current_user_id 是当前登录用户的 id，由界面传入。"""
        target = self.user_repo.get(user_id)
        if target is None:
            raise ValueError(USER_NOT_FOUND_MSG)
        if user_id == current_user_id:
            raise ValueError(DELETE_SELF_MSG)
        if target.role == ROLE_ADMIN:
            admin_count = sum(1 for u in self.user_repo.list_all() if u.role == ROLE_ADMIN)
            if admin_count <= 1:
                raise ValueError(LAST_ADMIN_MSG)
        self.user_repo.delete(user_id)
