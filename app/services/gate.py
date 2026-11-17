"""入场、出场流程（负责人 D，REQ-008 至 REQ-010）。"""
from dataclasses import replace
from datetime import datetime

from app.models.entities import ParkingRecord, VEHICLE_TEMP


class GateService:
    def __init__(self, record_repo, vehicle_repo, fee_rule_repo):
        self.record_repo = record_repo
        self.vehicle_repo = vehicle_repo
        self.fee_rule_repo = fee_rule_repo

    def enter(self, plate: str, now: datetime, operator: str) -> ParkingRecord:
        """车牌已在场时抛出 ValueError。"""
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
        """找不到在场记录时抛出 ValueError。"""
        record = self.record_repo.get_present(plate)
        if record is None:
            raise ValueError("未找到在场记录")
        # 保留入场快照；D-1 暂不使用收费规则，费用固定为整数 0。
        exited = replace(record, exit_time=now, fee=0)
        self.record_repo.update(exited)
        return exited

    def list_present(self) -> list[ParkingRecord]:
        return self.record_repo.list_present()
