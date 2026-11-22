"""车辆业务规则（负责人 B，REQ-004）。

规则都在这一层：车牌格式、车辆类型、月租车/访客车的必填项、
车牌唯一、被固定车位占用的车辆不能删。repo 只做 SQL 读写（docs/03 第一节）。
修改车辆另有两条规则（第二轮审查补充）：有固定车位的车辆只能是月租车；车辆在场时不能改车牌。
"""
import sqlite3

from app.models.entities import (
    VEHICLE_MONTHLY, VEHICLE_TYPES, VEHICLE_VISITOR, Vehicle,
)
from app.services.validators import is_valid_plate

FIXED_SPACE_NOT_MONTHLY_MSG = "该车辆有固定车位，请先释放车位再改为非月租车"
PRESENT_PLATE_CHANGE_MSG = "该车辆在场内，出场后才能修改车牌"


class VehicleService:
    def __init__(self, vehicle_repo, space_repo=None, record_repo=None):
        """space_repo、record_repo 是可选参数，原有 VehicleService(vehicle_repo) 写法不受影响；
        传入后 update 才检查固定车位和在场状态，主窗口会传入。"""
        self.vehicle_repo = vehicle_repo
        self.space_repo = space_repo      # 查车辆是否绑定了固定车位
        self.record_repo = record_repo    # 查车辆是否在场

    def add(self, obj: Vehicle) -> int:
        """登记车辆。规则不满足或车牌重复时抛 ValueError。"""
        self._check(obj)
        try:
            return self.vehicle_repo.add(obj)
        except sqlite3.IntegrityError as exc:
            raise ValueError(self._save_error(exc)) from None

    def update(self, obj: Vehicle) -> None:
        """修改车辆。规则不满足、车牌与他人重复或住户不存在时抛 ValueError。

        另外两条规则要和修改前的资料比较，所以先读出旧记录：
        - 绑定了固定车位的车辆不能改成临时车或访客车（固定车位只给月租车，REQ-007）
        - 车辆在场时不能改车牌：在场记录按车牌查找，改了以后新车牌出不了场，
          旧车牌出场又查不到车辆资料，会被按临时车收费
        """
        self._check(obj)
        old = self.vehicle_repo.get(obj.id)
        if old is not None:
            self._check_change(old, obj)
        try:
            self.vehicle_repo.update(obj)
        except sqlite3.IntegrityError as exc:
            raise ValueError(self._save_error(exc)) from None

    def _check_change(self, old: Vehicle, new: Vehicle) -> None:
        """没传对应的 repo 时跳过该项检查（兼容原有写法）。"""
        if (self.space_repo is not None and new.vehicle_type != VEHICLE_MONTHLY
                and self.space_repo.get_by_fixed_vehicle(old.id) is not None):
            raise ValueError(FIXED_SPACE_NOT_MONTHLY_MSG)
        if (self.record_repo is not None and new.plate != old.plate
                and self.record_repo.get_present(old.plate) is not None):
            raise ValueError(PRESENT_PLATE_CHANGE_MSG)

    def delete(self, vehicle_id: int) -> None:
        """删除车辆。车辆仍被固定车位引用时抛 ValueError。"""
        try:
            self.vehicle_repo.delete(vehicle_id)
        except sqlite3.IntegrityError:
            # spaces.fixed_vehicle_id 外键引用 vehicles(id)
            raise ValueError("请先释放该车辆的固定车位") from None

    @staticmethod
    def _save_error(exc: sqlite3.IntegrityError) -> str:
        """把新增/修改时的约束错误翻译成提示语。

        vehicles 表上有两类约束会被触发：plate 的 UNIQUE（车牌重复），
        resident_id 引用 residents(id) 的外键（住户不存在）。
        """
        if "FOREIGN KEY" in str(exc):
            return "住户不存在，请检查住户 ID"
        return "该车牌已登记"

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