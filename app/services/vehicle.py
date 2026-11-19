"""车辆业务规则（负责人 B，REQ-004）。

规则都在这一层：车牌格式、车辆类型、月租车/访客车的必填项、
车牌唯一、被固定车位占用的车辆不能删。repo 只做 SQL 读写（docs/03 第一节）。
"""
import sqlite3

from app.models.entities import (
    VEHICLE_MONTHLY, VEHICLE_TYPES, VEHICLE_VISITOR, Vehicle,
)
from app.services.validators import is_valid_plate


class VehicleService:
    def __init__(self, vehicle_repo):
        self.vehicle_repo = vehicle_repo

    def add(self, obj: Vehicle) -> int:
        """登记车辆。规则不满足或车牌重复时抛 ValueError。"""
        self._check(obj)
        try:
            return self.vehicle_repo.add(obj)
        except sqlite3.IntegrityError:
            # vehicles.plate 有 UNIQUE 约束，重复登记时数据库拒绝
            raise ValueError("该车牌已登记") from None

    def update(self, obj: Vehicle) -> None:
        """修改车辆。规则不满足或车牌与他人重复时抛 ValueError。"""
        self._check(obj)
        try:
            self.vehicle_repo.update(obj)
        except sqlite3.IntegrityError:
            raise ValueError("该车牌已登记") from None

    def delete(self, vehicle_id: int) -> None:
        """删除车辆。车辆仍被固定车位引用时抛 ValueError。"""
        try:
            self.vehicle_repo.delete(vehicle_id)
        except sqlite3.IntegrityError:
            # spaces.fixed_vehicle_id 外键引用 vehicles(id)
            raise ValueError("请先释放该车辆的固定车位") from None

    @staticmethod
    def _check(obj: Vehicle) -> None:
        if not is_valid_plate(obj.plate):
            raise ValueError("车牌格式不正确")
        if obj.vehicle_type not in VEHICLE_TYPES:
            raise ValueError("车辆类型不正确")
        if obj.vehicle_type == VEHICLE_MONTHLY:
            if obj.resident_id is None:
                raise ValueError("月租车必须绑定住户")
            if obj.monthly_expire is None:
                raise ValueError("月租车必须填写到期日")
        else:
            if obj.vehicle_type == VEHICLE_VISITOR and obj.resident_id is None:
                raise ValueError("访客车必须填写被访住户")
            obj.monthly_expire = None