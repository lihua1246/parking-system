"""入场、出场流程（负责人 D，REQ-008 至 REQ-010；出场计费由 A 接入，任务卡 A-5）。"""
from dataclasses import replace
from datetime import datetime

from app.models.entities import ParkingRecord, VEHICLE_MONTHLY, VEHICLE_TEMP
from app.services.billing import make_policy
from app.services.validators import is_valid_plate


class GateService:
    def __init__(self, record_repo, vehicle_repo, fee_rule_repo):
        self.record_repo = record_repo
        self.vehicle_repo = vehicle_repo
        self.fee_rule_repo = fee_rule_repo

    def enter(self, plate: str, now: datetime, operator: str) -> ParkingRecord:
        """车牌格式不正确或车牌已在场时抛出 ValueError。

        先校验格式，避免 "豫a12345" 与 "豫A12345" 被当成两辆车同时在场。
        """
        if not is_valid_plate(plate):
            raise ValueError("车牌格式不正确")
        if self.record_repo.get_present(plate) is not None:
            raise ValueError("该车辆已在场内")
        vehicle = self.vehicle_repo.get_by_plate(plate)
        record = ParkingRecord(
            id=None, plate=plate,
            vehicle_type=vehicle.vehicle_type if vehicle is not None else VEHICLE_TEMP,
            enter_time=now, exit_time=None, fee=None, space_id=None, operator=operator,
        )
        record.id = self.record_repo.add(record)
        return record

    def exit(self, plate: str, now: datetime, operator: str) -> ParkingRecord:
        """找不到在场记录、或出场时间早于入场时间时抛出 ValueError。"""
        record = self.record_repo.get_present(plate)
        if record is None:
            raise ValueError("未找到在场记录")
        if now < record.enter_time:
            raise ValueError("出场时间不能早于入场时间")
        exited = replace(record, exit_time=now, fee=self._calc_fee(record, now))
        self.record_repo.update(exited)
        return exited

    def _calc_fee(self, record: ParkingRecord, now: datetime) -> int:
        """按入场时的车辆类型快照计费（ADR-004）。

        收费规则每次出场时从数据库读取，管理员改完规则（REQ-015）后立即生效，不缓存。
        月租车的到期日取车辆当前资料，出场前续费也算数；车辆资料已删除时按临时车计费。
        """
        rules = {rule.vehicle_type: rule for rule in self.fee_rule_repo.list_all()}
        expire = None
        if record.vehicle_type == VEHICLE_MONTHLY:
            vehicle = self.vehicle_repo.get_by_plate(record.plate)
            if vehicle is not None and vehicle.vehicle_type == VEHICLE_MONTHLY:
                expire = vehicle.monthly_expire
        return make_policy(record.vehicle_type, expire, rules).calc(record.enter_time, now)

    def list_present(self) -> list[ParkingRecord]:
        return self.record_repo.list_present()
