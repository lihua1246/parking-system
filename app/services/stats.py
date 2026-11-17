"""车流量、收入、利用率、高峰时段（负责人 E，REQ-016 至 018、REQ-026）。

全部是纯函数：只接收数据列表，返回计算结果，不访问数据库。收入按出场日期归属。
"""
from datetime import date

from app.models.entities import ParkingRecord, ParkingSpace


def daily_flow(records: list[ParkingRecord], day: date) -> dict[str, int]:
    """返回 {"in": 入场数, "out": 出场数}。"""
    raise NotImplementedError("REQ-016 待 E 实现")


def monthly_flow(records: list[ParkingRecord], year: int, month: int) -> dict[date, dict[str, int]]:
    raise NotImplementedError("REQ-016 待 E 实现")


def income_by_day(records: list[ParkingRecord], year: int, month: int) -> dict[date, int]:
    raise NotImplementedError("REQ-017 待 E 实现")


def utilization(spaces: list[ParkingSpace]) -> float:
    """0 到 1；无车位时为 0.0。"""
    raise NotImplementedError("REQ-018 待 E 实现")


def peak_hours(records: list[ParkingRecord], top_n: int = 3) -> list[tuple[int, int]]:
    """返回 [(小时, 入场数)]。"""
    raise NotImplementedError("REQ-026 待 E 实现")
