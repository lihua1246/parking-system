"""车辆服务层测试（负责人 B，REQ-004；任务卡 B-2）。

预期值来自任务卡 B-2 的验收条件；使用内存数据库，不依赖界面。
"""
from datetime import date, datetime

import pytest

from app.models.entities import (
    VEHICLE_MONTHLY, VEHICLE_TEMP, VEHICLE_VISITOR, Vehicle,
)
from app.repository.db import get_connection, init_db
from app.repository.fee_rule_repo import FeeRuleRepo
from app.repository.record_repo import RecordRepo
from app.repository.vehicle_repo import VehicleRepo
from app.services.gate import GateService
from app.services.vehicle import VehicleService


@pytest.fixture
def env():
    """内存库 + 一个住户（id=1），返回 (conn, repo, service)。"""
    conn = get_connection(":memory:")
    init_db(conn)
    conn.execute(
        "INSERT INTO residents (name, building, room, phone) VALUES (?, ?, ?, ?)",
        ("张三", "3号楼", "2-501", "13800000000"),
    )
    repo = VehicleRepo(conn)
    yield conn, repo, VehicleService(repo)
    conn.close()


def _monthly(plate="豫A12345", resident_id=1, expire=date(2026, 12, 31)):
    return Vehicle(id=None, plate=plate, vehicle_type=VEHICLE_MONTHLY,
                   resident_id=resident_id, monthly_expire=expire)


def test_req004_duplicate_plate_rejected(env):
    """验收 1：重复登记同一车牌时提示"该车牌已登记"，表中仍只有一条。"""
    conn, repo, service = env
    service.add(_monthly())
    with pytest.raises(ValueError) as excinfo:
        service.add(_monthly())
    assert str(excinfo.value) == "该车牌已登记"
    assert len(repo.list_all()) == 1


def test_req004_unknown_resident_rejected_on_add(env):
    """住户 ID 不存在时提示住户不存在，而不是误报车牌重复。"""
    conn, repo, service = env
    with pytest.raises(ValueError) as excinfo:
        service.add(_monthly(resident_id=999))
    assert str(excinfo.value) == "住户不存在，请检查住户 ID"
    assert repo.list_all() == []


def test_req004_unknown_resident_rejected_on_update(env):
    """修改时把住户改成不存在的 ID，同样提示住户不存在，原记录不变。"""
    conn, repo, service = env
    vehicle_id = service.add(_monthly())
    vehicle = repo.get(vehicle_id)
    vehicle.resident_id = 999
    with pytest.raises(ValueError) as excinfo:
        service.update(vehicle)
    assert str(excinfo.value) == "住户不存在，请检查住户 ID"
    assert repo.get(vehicle_id).resident_id == 1


def test_req004_duplicate_plate_rejected_on_update(env):
    """修改时把车牌改成别人的，仍提示该车牌已登记。"""
    conn, repo, service = env
    service.add(_monthly(plate="豫A12345"))
    other_id = service.add(_monthly(plate="豫B12345"))
    other = repo.get(other_id)
    other.plate = "豫A12345"
    with pytest.raises(ValueError) as excinfo:
        service.update(other)
    assert str(excinfo.value) == "该车牌已登记"


def test_req004_monthly_requires_resident(env):
    """验收 2（缺项一）：月租车必须绑定住户。"""
    conn, repo, service = env
    with pytest.raises(ValueError) as excinfo:
        service.add(_monthly(resident_id=None))
    assert str(excinfo.value) == "月租车必须绑定住户"


def test_req004_monthly_requires_expire_date(env):
    """验收 2（缺项二）：月租车必须填写到期日。"""
    conn, repo, service = env
    with pytest.raises(ValueError) as excinfo:
        service.add(_monthly(expire=None))
    assert str(excinfo.value) == "月租车必须填写到期日"


def test_req004_invalid_plate_rejected(env):
    """验收 3：豫a12345（小写）车牌格式不正确。"""
    conn, repo, service = env
    with pytest.raises(ValueError) as excinfo:
        service.add(_monthly(plate="豫a12345"))
    assert str(excinfo.value) == "车牌格式不正确"


def test_req004_invalid_vehicle_type_rejected(env):
    """补充：车辆类型不在 VEHICLE_TYPES 中。"""
    conn, repo, service = env
    with pytest.raises(ValueError) as excinfo:
        service.add(Vehicle(None, "豫A12345", "truck", 1, date(2026, 12, 31)))
    assert str(excinfo.value) == "车辆类型不正确"


def test_req004_visitor_requires_resident(env):
    """访客车必须填写被访住户。"""
    conn, repo, service = env
    with pytest.raises(ValueError) as excinfo:
        service.add(Vehicle(None, "豫A12345", VEHICLE_VISITOR, None, None))
    assert str(excinfo.value) == "访客车必须填写被访住户"


def test_req004_temp_vehicle_expire_cleared(env):
    """补充：非月租车保存后到期日被置为 None。"""
    conn, repo, service = env
    new_id = service.add(
        Vehicle(None, "豫A12345", VEHICLE_TEMP, None, date(2026, 12, 31))
    )
    assert repo.get(new_id).monthly_expire is None


def test_req004_monthly_vehicle_enters_as_monthly(env):
    """验收 5：登记月租车后入场，记录的车辆类型为 monthly。"""
    conn, repo, service = env
    service.add(_monthly())
    gate = GateService(RecordRepo(conn), repo, FeeRuleRepo(conn))
    record = gate.enter("豫A12345", datetime(2026, 11, 20, 8, 0), "admin")
    assert record.vehicle_type == VEHICLE_MONTHLY


def test_req004_delete_blocked_by_fixed_space(env):
    """验收 6：车辆被固定车位引用时不能删除。"""
    conn, repo, service = env
    vehicle_id = service.add(_monthly())
    conn.execute(
        "INSERT INTO spaces (code, zone, status, fixed_vehicle_id) VALUES (?, ?, ?, ?)",
        ("A-001", "A区", "free", vehicle_id),
    )
    with pytest.raises(ValueError) as excinfo:
        service.delete(vehicle_id)
    assert str(excinfo.value) == "请先释放该车辆的固定车位"
    assert repo.get(vehicle_id) is not None