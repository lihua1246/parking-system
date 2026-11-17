"""预约表读写（负责人 C，REQ-022）。"""
import sqlite3

from app.models.entities import Reservation


class ReservationRepo:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def add(self, obj: Reservation) -> int:
        """返回新记录的 id。"""
        raise NotImplementedError("REQ-022 待 C 实现")

    def update(self, obj: Reservation) -> None:
        raise NotImplementedError("REQ-022 待 C 实现")

    def delete(self, id: int) -> None:
        raise NotImplementedError("REQ-022 待 C 实现")

    def get(self, id: int) -> Reservation | None:
        """找不到返回 None。"""
        raise NotImplementedError("REQ-022 待 C 实现")

    def list_all(self) -> list[Reservation]:
        raise NotImplementedError("REQ-022 待 C 实现")
