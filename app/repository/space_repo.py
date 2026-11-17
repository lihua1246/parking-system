"""车位表读写（负责人 C，REQ-006）。"""
import sqlite3

from app.models.entities import ParkingSpace


class SpaceRepo:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def add(self, obj: ParkingSpace) -> int:
        """返回新记录的 id。"""
        raise NotImplementedError("REQ-006 待 C 实现")

    def update(self, obj: ParkingSpace) -> None:
        raise NotImplementedError("REQ-006 待 C 实现")

    def delete(self, id: int) -> None:
        raise NotImplementedError("REQ-006 待 C 实现")

    def get(self, id: int) -> ParkingSpace | None:
        """找不到返回 None。"""
        raise NotImplementedError("REQ-006 待 C 实现")

    def list_all(self) -> list[ParkingSpace]:
        raise NotImplementedError("REQ-006 待 C 实现")

    def list_by(self, zone: str | None, status: str | None) -> list[ParkingSpace]:
        """按区域、状态筛选；参数为 None 表示不限（任务卡 C-1）。"""
        raise NotImplementedError("REQ-006 待 C 实现")
