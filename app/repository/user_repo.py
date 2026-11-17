"""用户表读写（负责人 A，REQ-001）。"""
import sqlite3

from app.models.entities import User


class UserRepo:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def add(self, obj: User) -> int:
        """返回新记录的 id。"""
        raise NotImplementedError("REQ-001 待 A 实现")

    def update(self, obj: User) -> None:
        raise NotImplementedError("REQ-001 待 A 实现")

    def delete(self, id: int) -> None:
        raise NotImplementedError("REQ-001 待 A 实现")

    def get(self, id: int) -> User | None:
        """找不到返回 None。"""
        raise NotImplementedError("REQ-001 待 A 实现")

    def list_all(self) -> list[User]:
        raise NotImplementedError("REQ-001 待 A 实现")

    def get_by_username(self, username: str) -> User | None:
        raise NotImplementedError("REQ-001 任务卡 A-1 实现")
