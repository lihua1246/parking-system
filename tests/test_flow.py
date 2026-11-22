"""端到端联调（任务卡 A-3 规则 3、A-5）：全部用真实 repo 和 service，不用替身。

流程：登记住户和月租车 → 入场类型为月租 → 出场免费 → 在场列表消失；
临时车出场按规则收费；改收费规则后下一辆车按新规则；固定车位分配后计入利用率；
当天收入等于各条记录金额之和。预期金额取自 docs/02「计费规则」验收示例。
"""
from datetime import date, datetime

import pytest

from app.models.entities import (
    ParkingSpace, Resident, SPACE_FREE, VEHICLE_MONTHLY, VEHICLE_TEMP, VEHICLE_VISITOR, Vehicle,
)
from app.repository.db import get_connection, init_db
from app.repository.fee_rule_repo import FeeRuleRepo
from app.repository.record_repo import RecordRepo
from app.repository.resident_repo import ResidentRepo
from app.repository.space_repo import SpaceRepo
from app.repository.vehicle_repo import VehicleRepo
from app.services.fee_rule import update_rule
from app.services.gate import GateService
from app.services.space import SpaceService
from app.services.stats import income_by_day, utilization
from app.services.vehicle import VehicleService

DAY = date(2026, 11, 20)


@pytest.fixture
def app():
    conn = get_connection(":memory:")
    init_db(conn)
    repos = {
        "resident": ResidentRepo(conn), "vehicle": VehicleRepo(conn), "record": RecordRepo(conn),
        "fee": FeeRuleRepo(conn), "space": SpaceRepo(conn),
    }
    resident_id = repos["resident"].add(Resident(None, "张三", "3号楼", "2-501", "13800000000"))
    vehicles = VehicleService(repos["vehicle"])
    vehicles.add(Vehicle(None, "豫A12345", VEHICLE_MONTHLY, resident_id, date(2026, 11, 30)))
    vehicles.add(Vehicle(None, "豫V66666", VEHICLE_VISITOR, resident_id, None))
    gate = GateService(repos["record"], repos["vehicle"], repos["fee"])
    yield gate, repos
    conn.close()


def test_flow_monthly_vehicle_enters_as_monthly_and_exits_free(app):
    gate, _ = app
    record = gate.enter("豫A12345", datetime(2026, 11, 20, 8), "guard")
    assert record.vehicle_type == VEHICLE_MONTHLY
    assert [r.plate for r in gate.list_present()] == ["豫A12345"]
    exited = gate.exit("豫A12345", datetime(2026, 11, 20, 13), "guard")
    assert exited.fee == 0                                       # 示例 7：有效期内
    assert gate.list_present() == []


def test_flow_temp_and_visitor_fees_and_daily_income(app):
    gate, repos = app
    gate.enter("豫B22222", datetime(2026, 11, 20, 8), "guard")   # 未登记 → 临时车
    gate.enter("豫V66666", datetime(2026, 11, 20, 8), "guard")
    assert gate.exit("豫B22222", datetime(2026, 11, 20, 10, 15), "guard").fee == 9   # 示例 4
    assert gate.exit("豫V66666", datetime(2026, 11, 20, 10, 1), "guard").fee == 9    # 示例 10
    assert income_by_day(repos["record"].list_all(), 2026, 11)[DAY] == 18


def test_flow_rule_change_applies_to_next_exit(app):
    gate, repos = app
    gate.enter("豫B22222", datetime(2026, 11, 20, 8), "guard")
    first = gate.exit("豫B22222", datetime(2026, 11, 20, 10, 15), "guard")
    update_rule(repos["fee"], VEHICLE_TEMP, 30, 5, 40)
    gate.enter("豫C33333", datetime(2026, 11, 20, 11), "guard")
    second = gate.exit("豫C33333", datetime(2026, 11, 20, 13, 15), "guard")
    assert (first.fee, second.fee) == (9, 15)
    assert repos["record"].get(first.id).fee == 9               # 已出场记录不变


def test_flow_fixed_space_counts_in_utilization(app):
    _, repos = app
    space_id = repos["space"].add(ParkingSpace(None, "A-001", "A区", SPACE_FREE, None))
    repos["space"].add(ParkingSpace(None, "A-002", "A区", SPACE_FREE, None))
    SpaceService(repos["space"], repos["vehicle"]).assign_fixed(space_id, "豫A12345")
    assert utilization(repos["space"].list_all()) == 0.5       # ADR-006：固定车位计为占用
