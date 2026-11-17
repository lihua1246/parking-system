"""住户表读写（负责人 B，REQ-003）。"""
import sqlite3

from app.models.entities import Resident


class ResidentRepo:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def add(self, obj: Resident) -> int:
        """返回新记录的 id。"""
        raise NotImplementedError("REQ-003 待 B 实现")

    def update(self, obj: Resident) -> None:
        raise NotImplementedError("REQ-003 待 B 实现")

    def delete(self, id: int) -> None:
        raise NotImplementedError("REQ-003 待 B 实现")

    def get(self, id: int) -> Resident | None:
        """找不到返回 None。"""
        raise NotImplementedError("REQ-003 待 B 实现")

    def list_all(self) -> list[Resident]:
        raise NotImplementedError("REQ-003 待 B 实现")

    def search(self, keyword: str) -> list[Resident]:
        """按姓名或楼栋房号模糊查询（任务卡 B-1）。"""
        raise NotImplementedError("REQ-003 待 B 实现")
