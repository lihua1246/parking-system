"""入场、出场流程（负责人 D，REQ-008 至 REQ-010）。"""
from datetime import datetime

from app.models.entities import ParkingRecord


class GateService:
    def __init__(self, record_repo, vehicle_repo, fee_rule_repo):
        self.record_repo = record_repo
        self.vehicle_repo = vehicle_repo
        self.fee_rule_repo = fee_rule_repo

    def enter(self, plate: str, now: datetime, operator: str) -> ParkingRecord:
        """车牌已在场时抛出 ValueError。"""
        raise NotImplementedError("REQ-008 待 D 实现")

    def exit(self, plate: str, now: datetime, operator: str) -> ParkingRecord:
        """找不到在场记录时抛出 ValueError。"""
        raise NotImplementedError("REQ-009 待 D 实现")

    def list_present(self) -> list[ParkingRecord]:
        raise NotImplementedError("REQ-010 待 D 实现")
