"""车位业务规则（REQ-006 负责人 C；REQ-007 固定车位由 A 接手，任务卡 A-5）。

"占用中的车位不能删除"属于业务判断，放在服务层而不是页面里，这样可以用测试覆盖。
固定车位的规则见任务卡 C-2；分配后状态为 occupied，见 ADR-006。
"""
import sqlite3
from dataclasses import replace
from datetime import datetime

from app.models.entities import SPACE_FREE, SPACE_OCCUPIED, VEHICLE_MONTHLY

SPACE_NOT_FOUND_MSG = "该车位已不存在，请刷新"
PLATE_NOT_REGISTERED_MSG = "该车牌未登记"
NOT_MONTHLY_MSG = "只有月租车可以分配固定车位"
SPACE_ALREADY_BOUND_MSG = "该车位已绑定其他车辆"
VEHICLE_ALREADY_FIXED_MSG = "该车辆已有固定车位"
SPACE_NOT_FREE_MSG = "只能分配空闲车位"
SPACE_NOT_BOUND_MSG = "该车位没有绑定车辆"
DELETE_FIXED_MSG = "该车位已绑定固定车辆，请先释放"
SPACE_HAS_RESERVATION_MSG = "该车位还有未结束的预约，请先取消预约"


class SpaceService:
    def __init__(self, space_repo, vehicle_repo=None, reservation_repo=None):
        self.space_repo = space_repo
        self.vehicle_repo = vehicle_repo          # 只在分配固定车位时需要
        self.reservation_repo = reservation_repo  # 分配固定车位前查预约；不传则不检查

    def delete(self, space_id: int) -> None:
        """删除车位。车位不存在、正被占用、绑定了固定车辆、或仍被预约引用时抛出 ValueError。"""
        space = self.space_repo.get(space_id)
        if space is None:
            raise ValueError(SPACE_NOT_FOUND_MSG)
        if space.status == SPACE_OCCUPIED:
            raise ValueError("车位正在使用，不能删除")
        # 状态可在车位页手动修改（ADR-010），不能只靠 occupied 判断是否已分配，否则绑定会被悄悄删掉
        if space.fixed_vehicle_id is not None:
            raise ValueError(DELETE_FIXED_MSG)
        try:
            self.space_repo.delete(space_id)
        except sqlite3.IntegrityError:
            # reservations.space_id 外键引用 spaces(id)，有预约时数据库拒绝删除
            raise ValueError("该车位还有预约记录，不能删除") from None

    def assign_fixed(self, space_id: int, plate: str, now: datetime) -> None:
        """把车位固定分配给一辆月租车（REQ-007）。任一规则不通过时抛 ValueError，数据不变。

        now 由界面传入：结束时间晚于 now 的预约（正在进行或还没开始）会挡住分配，
        否则同一个车位既归固定车辆，又在某个时间段预约给了别人。已结束的预约不影响。
        """
        space = self.space_repo.get(space_id)
        if space is None:
            raise ValueError(SPACE_NOT_FOUND_MSG)
        vehicle = self.vehicle_repo.get_by_plate(plate.strip())
        if vehicle is None:
            raise ValueError(PLATE_NOT_REGISTERED_MSG)
        if vehicle.vehicle_type != VEHICLE_MONTHLY:
            raise ValueError(NOT_MONTHLY_MSG)
        if space.fixed_vehicle_id is not None:
            raise ValueError(SPACE_ALREADY_BOUND_MSG)
        if self.space_repo.get_by_fixed_vehicle(vehicle.id) is not None:
            raise ValueError(VEHICLE_ALREADY_FIXED_MSG)
        if space.status != SPACE_FREE:
            raise ValueError(SPACE_NOT_FREE_MSG)
        if self._has_unfinished_reservation(space_id, now):
            raise ValueError(SPACE_HAS_RESERVATION_MSG)
        try:
            self.space_repo.update(replace(space, fixed_vehicle_id=vehicle.id, status=SPACE_OCCUPIED))
        except sqlite3.IntegrityError:
            # spaces.fixed_vehicle_id 有 UNIQUE 约束：两人同时给同一辆车分配时由数据库兜底
            raise ValueError(VEHICLE_ALREADY_FIXED_MSG) from None

    def release_fixed(self, space_id: int) -> None:
        """释放固定车位：解除绑定，状态改回 free（REQ-007）。"""
        space = self.space_repo.get(space_id)
        if space is None:
            raise ValueError(SPACE_NOT_FOUND_MSG)
        if space.fixed_vehicle_id is None:
            raise ValueError(SPACE_NOT_BOUND_MSG)
        self.space_repo.update(replace(space, fixed_vehicle_id=None, status=SPACE_FREE))

    def _has_unfinished_reservation(self, space_id: int, now: datetime) -> bool:
        """该车位是否还有结束时间晚于 now 的预约。没传 reservation_repo 时返回 False。"""
        if self.reservation_repo is None:
            return False
        return any(r.space_id == space_id and r.end_time > now
                   for r in self.reservation_repo.list_all())
