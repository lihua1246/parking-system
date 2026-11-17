"""车位预约时间冲突判断（负责人 C，REQ-022）。"""
from datetime import datetime

from app.models.entities import Reservation


def has_conflict(existing: list[Reservation], space_id: int,
                 start: datetime, end: datetime) -> bool:
    """两个时间段首尾相接（前一个的结束等于后一个的开始）不算冲突。"""
    raise NotImplementedError("REQ-022 待 C 实现")
