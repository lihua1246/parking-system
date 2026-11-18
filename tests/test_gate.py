"""D-1：预期值取自任务卡，车辆查询用替身，停车记录用真实内存库。"""
from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest

from app.models.entities import VEHICLE_MONTHLY, VEHICLE_TEMP, VEHICLE_VISITOR
from app.repository.db import get_connection, init_db
from app.repository.record_repo import RecordRepo
from app.services.gate import GateService


class VehicleLookup:
    def __init__(self):
        self.vehicles = {}

    def get_by_plate(self, plate):
        return self.vehicles.get(plate)


@pytest.fixture
def gate():
    conn = get_connection(":memory:")
    init_db(conn)
    vehicles = VehicleLookup()
    service = GateService(RecordRepo(conn), vehicles, None)
    yield service, vehicles
    conn.close()


def test_req008_unregistered_plate_is_temp(gate):
    service, _ = gate
    now = datetime(2026, 11, 17, 8)
    record = service.enter("豫A12345", now, "guard_a")
    assert record.id is not None
    assert record.plate == "豫A12345"
    assert record.vehicle_type == VEHICLE_TEMP
    assert record.enter_time == now
    assert record.exit_time is None
    assert service.record_repo.get(record.id) == record


def test_req008_duplicate_entry_rejected_without_extra_record(gate):
    service, _ = gate
    service.enter("豫A12345", datetime(2026, 11, 17, 8), "guard_a")
    with pytest.raises(ValueError, match="^该车辆已在场内$"):
        service.enter("豫A12345", datetime(2026, 11, 17, 9), "guard_a")
    assert len(service.record_repo.list_all()) == 1


@pytest.mark.parametrize("vehicle_type", [VEHICLE_MONTHLY, VEHICLE_VISITOR])
def test_req008_registered_type_is_snapshot(gate, vehicle_type):
    service, vehicles = gate
    vehicle = SimpleNamespace(vehicle_type=vehicle_type)
    vehicles.vehicles["豫A12345"] = vehicle
    record = service.enter("豫A12345", datetime(2026, 11, 17, 8), "guard_a")
    vehicle.vehicle_type = VEHICLE_TEMP
    result = service.exit("豫A12345", datetime(2026, 11, 17, 10, 15), "guard_b")
    assert record.vehicle_type == vehicle_type
    assert result.vehicle_type == vehicle_type
    assert service.record_repo.get(record.id).vehicle_type == vehicle_type


def test_req009_exit_updates_same_record_with_zero_fee(gate):
    service, _ = gate
    entered = service.enter("豫A12345", datetime(2026, 11, 17, 8), "guard_a")
    exited = service.exit("豫A12345", datetime(2026, 11, 17, 10, 15), "guard_b")
    assert exited.id == entered.id
    assert exited.exit_time == datetime(2026, 11, 17, 10, 15)
    assert exited.exit_time - exited.enter_time == timedelta(hours=2, minutes=15)
    assert exited.fee == 0
    assert exited.operator == "guard_a"  # 使用者确认：保留入场操作员
    assert service.record_repo.get(exited.id) == exited
    assert len(service.record_repo.list_all()) == 1
    assert service.list_present() == []


def test_req009_absent_plate_rejected(gate):
    service, _ = gate
    with pytest.raises(ValueError, match="^未找到在场记录$"):
        service.exit("豫A12345", datetime(2026, 11, 17, 10, 15), "guard_b")
    assert service.record_repo.list_all() == []


def test_req010_present_list_removes_only_exited_vehicle(gate):
    service, _ = gate
    assert service.list_present() == []
    service.enter("豫A12345", datetime(2026, 11, 17, 8), "guard_a")
    service.enter("豫A54321", datetime(2026, 11, 17, 9), "guard_a")
    assert {r.plate for r in service.list_present()} == {"豫A12345", "豫A54321"}
    service.exit("豫A12345", datetime(2026, 11, 17, 10, 15), "guard_b")
    assert [r.plate for r in service.list_present()] == ["豫A54321"]


@pytest.mark.parametrize("plate", ["豫a12345", "A12345", "豫A1234"])
def test_req008_invalid_plate_rejected_without_record(gate, plate):
    service, _ = gate
    with pytest.raises(ValueError, match="^车牌格式不正确$"):
        service.enter(plate, datetime(2026, 11, 17, 8), "guard_a")
    assert service.record_repo.list_all() == []


def test_req008_lowercase_plate_cannot_bypass_duplicate_check(gate):
    service, _ = gate
    service.enter("豫A12345", datetime(2026, 11, 17, 8), "guard_a")
    with pytest.raises(ValueError):
        service.enter("豫a12345", datetime(2026, 11, 17, 9), "guard_a")
    assert len(service.list_present()) == 1


def test_req008_can_enter_again_after_exit_without_changing_history(gate):
    service, _ = gate
    first = service.enter("豫A12345", datetime(2026, 11, 17, 8), "guard_a")
    service.exit("豫A12345", datetime(2026, 11, 17, 10, 15), "guard_b")
    second = service.enter("豫A12345", datetime(2026, 11, 17, 11), "guard_b")
    assert first.id != second.id
    assert service.record_repo.get(first.id).exit_time == datetime(2026, 11, 17, 10, 15)
    assert service.record_repo.get_present("豫A12345") == second
    assert len(service.record_repo.list_all()) == 2
