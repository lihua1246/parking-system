"""收费规则表读写（负责人 D，REQ-015）。

fee_rules 表以 vehicle_type 为主键、没有 id，也不需要增删，
所以只提供按车辆类型读取和修改。
"""
import sqlite3

from app.models.entities import FeeRule


class FeeRuleRepo:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def get(self, vehicle_type: str) -> FeeRule | None:
        raise NotImplementedError("REQ-015 待 D 实现")

    def list_all(self) -> list[FeeRule]:
        raise NotImplementedError("REQ-015 待 D 实现")

    def update(self, rule: FeeRule) -> None:
        raise NotImplementedError("REQ-015 待 D 实现")
