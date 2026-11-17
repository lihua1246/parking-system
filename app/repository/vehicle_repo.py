"""车辆表读写（负责人 B，REQ-004）。"""
import sqlite3

from app.models.entities import Vehicle


class VehicleRepo:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def add(self, obj: Vehicle) -> int:
        """返回新记录的 id。"""
        raise NotImplementedError("REQ-004 待 B 实现")

    def update(self, obj: Vehicle) -> None:
        raise NotImplementedError("REQ-004 待 B 实现")

    def delete(self, id: int) -> None:
        raise NotImplementedError("REQ-004 待 B 实现")

    def get(self, id: int) -> Vehicle | None:
        """找不到返回 None。"""
        raise NotImplementedError("REQ-004 待 B 实现")

    def list_all(self) -> list[Vehicle]:
        raise NotImplementedError("REQ-004 待 B 实现")

    def get_by_plate(self, plate: str) -> Vehicle | None:
        """GateService 入场时用来确定车辆类型。"""
        raise NotImplementedError("REQ-004 待 B 实现")
