"""出入记录表读写。只增不删，不提供 delete（ADR-004）（负责人 D，REQ-008）。"""
import sqlite3
from datetime import datetime

from app.models.entities import ParkingRecord


class RecordRepo:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def add(self, obj: ParkingRecord) -> int:
        """返回新记录的 id。"""
        raise NotImplementedError("REQ-008 待 D 实现")

    def update(self, obj: ParkingRecord) -> None:
        raise NotImplementedError("REQ-008 待 D 实现")

    def get(self, id: int) -> ParkingRecord | None:
        """找不到返回 None。"""
        raise NotImplementedError("REQ-008 待 D 实现")

    def list_all(self) -> list[ParkingRecord]:
        raise NotImplementedError("REQ-008 待 D 实现")

    def get_present(self, plate: str) -> ParkingRecord | None:
        """该车牌未出场的记录，没有则返回 None。"""
        raise NotImplementedError("REQ-008 待 D 实现")

    def list_present(self) -> list[ParkingRecord]:
        raise NotImplementedError("REQ-010 待 D 实现")

    def list_between(self, start: datetime, end: datetime) -> list[ParkingRecord]:
        raise NotImplementedError("REQ-011 待 D 实现")
