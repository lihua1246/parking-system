"""D-1：预期值取自任务卡，车辆查询用替身，停车记录用真实内存库。

A-5 接入计费后，出场费用按 docs/02「计费规则」计算，收费规则用真实内存库的默认值
（临时车 30 分钟/3 元/30 元，访客车 120 分钟/3 元/30 元）。
"""
from datetime import date, datetime, timedelta
from types import SimpleNamespace

import pytest

from app.models.entities import FeeRule, VEHICLE_MONTHLY, VEHICLE_TEMP, VEHICLE_VISITOR
from app.repository.db import get_connection, init_db
from app.repository.fee_rule_repo import FeeRuleRepo
from app.repository.record_repo import RecordRepo
from app.services.fee_rule import update_rule
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
    service = GateService(RecordRepo(conn), vehicles, FeeRuleRepo(conn))
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


def test_req009_exit_updates_same_record_and_charges_fee(gate):
    service, _ = gate
    entered = service.enter("豫A12345", datetime(2026, 11, 17, 8), "guard_a")
    exited = service.exit("豫A12345", datetime(2026, 11, 17, 10, 15), "guard_b")
    assert exited.id == entered.id
    assert exited.exit_time == datetime(2026, 11, 17, 10, 15)
    assert exited.exit_time - exited.enter_time == timedelta(hours=2, minutes=15)
    # D-1 阶段不计费时为 0；A-5 接入计费后按 docs/02 计费示例 4：临时车 2 小时 15 分收 9 元
    assert exited.fee == 9
    assert exited.operator == "guard_a"  # 使用者确认：保留入场操作员
    assert service.record_repo.get(exited.id) == exited
    assert len(service.record_repo.list_all()) == 1
    assert service.list_present() == []


def test_req009_absent_plate_rejected(gate):
    service, _ = gate
    with pytest.raises(ValueError, match="^未找到在场记录$"):
        service.exit("豫A12345", datetime(2026, 11, 17, 10, 15), "guard_b")
    assert service.record_repo.list_all() == []


def test_req009_exit_before_enter_rejected_and_record_unchanged(gate):
    service, _ = gate
    entered = service.enter("豫A12345", datetime(2026, 11, 17, 8), "guard_a")
    with pytest.raises(ValueError, match="^出场时间不能早于入场时间$"):
        service.exit("豫A12345", datetime(2026, 11, 17, 7, 59), "guard_b")
    assert service.record_repo.get(entered.id) == entered
    assert [r.plate for r in service.list_present()] == ["豫A12345"]


def test_req009_exit_at_same_moment_allowed(gate):
    service, _ = gate
    service.enter("豫A12345", datetime(2026, 11, 17, 8), "guard_a")
    exited = service.exit("豫A12345", datetime(2026, 11, 17, 8), "guard_b")
    assert exited.exit_time == exited.enter_time


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


# ---------- A-5：出场时计费（预期值取自 docs/02 计费验收示例） ----------

def test_req013_monthly_exit_within_validity_is_free(gate):
    service, vehicles = gate
    vehicles.vehicles["豫A12345"] = SimpleNamespace(
        vehicle_type=VEHICLE_MONTHLY, monthly_expire=date(2026, 11, 30))
    service.enter("豫A12345", datetime(2026, 11, 20, 8), "guard_a")
    assert service.exit("豫A12345", datetime(2026, 11, 20, 13), "guard_a").fee == 0   # 示例 7


def test_req013_monthly_exit_after_expire_charged_as_temp(gate):
    service, vehicles = gate
    vehicles.vehicles["豫A12345"] = SimpleNamespace(
        vehicle_type=VEHICLE_MONTHLY, monthly_expire=date(2026, 11, 30))
    service.enter("豫A12345", datetime(2026, 12, 1, 8), "guard_a")
    assert service.exit("豫A12345", datetime(2026, 12, 1, 13), "guard_a").fee == 15   # 示例 8


def test_req014_visitor_exit_fee(gate):
    service, vehicles = gate
    vehicles.vehicles["豫A12345"] = SimpleNamespace(vehicle_type=VEHICLE_VISITOR)
    service.enter("豫A12345", datetime(2026, 11, 20, 8), "guard_a")
    assert service.exit("豫A12345", datetime(2026, 11, 20, 10, 1), "guard_a").fee == 9  # 示例 10


def test_req015_rule_change_applies_to_next_exit_only(gate):
    """REQ-015 联调：改规则后出场的车按新规则；已出场记录金额不变。"""
    service, _ = gate
    service.enter("豫A11111", datetime(2026, 11, 20, 8), "guard_a")
    first = service.exit("豫A11111", datetime(2026, 11, 20, 10, 15), "guard_a")
    assert first.fee == 9                                       # 默认规则：3 小时 × 3 元

    update_rule(service.fee_rule_repo, VEHICLE_TEMP, 30, 5, 40)  # 同一个服务对象，不重启
    service.enter("豫A22222", datetime(2026, 11, 20, 8), "guard_a")
    second = service.exit("豫A22222", datetime(2026, 11, 20, 10, 15), "guard_a")
    assert second.fee == 15                                     # 新规则：3 小时 × 5 元
    assert service.record_repo.get(first.id).fee == 9
    assert service.fee_rule_repo.get(VEHICLE_TEMP) == FeeRule(VEHICLE_TEMP, 30, 5, 40)
