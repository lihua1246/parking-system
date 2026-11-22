"""车位预约（REQ-022；原属 C，见任务卡 A-5）。

决定（组长 A 确认，记入任务卡 A-5）：
- 预约只是时间段记录，不改变车位状态；车位状态仍由管理员维护（与 ADR-010 一致）
- 状态为"占用"的车位（含已分配的固定车位）不能预约；"空闲""预约"状态的车位可以预约
- 车牌只校验格式（REQ-005），不要求已登记，访客和临时车也能预约
- 同一车位的时间段不能重叠，首尾相接不算重叠
"""
from datetime import datetime

from app.models.entities import Reservation, SPACE_OCCUPIED
from app.services.validators import is_valid_plate

SPACE_NOT_FOUND_MSG = "该车位已不存在，请刷新"
SPACE_OCCUPIED_MSG = "该车位已被占用，不能预约"
INVALID_PLATE_MSG = "车牌格式不正确"
INVALID_PERIOD_MSG = "结束时间必须晚于开始时间"
CONFLICT_MSG = "该时间段与已有预约重叠"
RESERVATION_NOT_FOUND_MSG = "该预约已不存在，请刷新"


def add_reservation(reservation_repo, space_repo, space_id: int, plate: str,
                    start: datetime, end: datetime) -> int:
    """新增预约，返回预约 id。任一规则不通过时抛 ValueError，数据库不变。"""
    space = space_repo.get(space_id)
    if space is None:
        raise ValueError(SPACE_NOT_FOUND_MSG)
    if space.status == SPACE_OCCUPIED:
        raise ValueError(SPACE_OCCUPIED_MSG)
    plate = plate.strip()
    if not is_valid_plate(plate):
        raise ValueError(INVALID_PLATE_MSG)
    if end <= start:
        raise ValueError(INVALID_PERIOD_MSG)
    if has_conflict(reservation_repo.list_all(), space_id, start, end):
        raise ValueError(CONFLICT_MSG)
    return reservation_repo.add(Reservation(None, space_id, plate, start, end))


def cancel_reservation(reservation_repo, reservation_id: int) -> None:
    """取消预约。预约不存在时抛 ValueError。"""
    if reservation_repo.get(reservation_id) is None:
        raise ValueError(RESERVATION_NOT_FOUND_MSG)
    reservation_repo.delete(reservation_id)


def has_conflict(existing: list[Reservation], space_id: int,
                 start: datetime, end: datetime) -> bool:
    """同一车位上，新时间段 [start, end) 与已有预约是否重叠。

    两个时间段首尾相接（前一个的结束等于后一个的开始）不算冲突。
    判断方法：两段重叠 ⇔ 新段开始早于旧段结束，且旧段开始早于新段结束。
    """
    return any(
        r.space_id == space_id and start < r.end_time and r.start_time < end
        for r in existing
    )
