"""超时停放、月租到期预警。

本文件由两人共用：overstay 归 D（REQ-024），expiring_monthly 归 B（REQ-025）。
骨架已把两个函数的空壳都建好，各自只改自己的函数，不碰对方的。
"""
from datetime import date, datetime

from app.models.entities import ParkingRecord, Vehicle


def overstay(present: list[ParkingRecord], now: datetime, hours: int = 72) -> list[ParkingRecord]:
    """负责人 D。"""
    raise NotImplementedError("REQ-024 待 D 实现")


def expiring_monthly(vehicles: list[Vehicle], today: date, days: int = 7) -> list[Vehicle]:
    """负责人 B。"""
    raise NotImplementedError("REQ-025 待 B 实现")
