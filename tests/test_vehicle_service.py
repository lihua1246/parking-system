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
from app.repository.space_repo import SpaceRepo
from app.repository.vehicle_repo import VehicleRepo
from app.services.gate import GateService
from app.services.vehicle import VehicleService


@pytest.fixture
def env():
    """内存库 + 一个住户（id=1），返回 (conn, repo, service)。

    service 按主窗口的接法传入车位、记录仓库，修改车辆时会检查固定车位和在场状态。
    """
    conn = get_connection(":memory:")
    init_db(conn)
    conn.execute(
        "INSERT INTO residents (name, building, room, phone) VALUES (?, ?, ?, ?)",
        ("张三", "3号楼", "2-501", "13800000000"),
    )
    repo = VehicleRepo(conn)
    yield conn, repo, VehicleService(repo, SpaceRepo(conn), RecordRepo(conn))
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


# ---------- 第二轮审查补充：修改车辆时的两条规则 ----------

def _bind_fixed_space(conn, vehicle_id):
    conn.execute(
        "INSERT INTO spaces (code, zone, status, fixed_vehicle_id) VALUES (?, ?, ?, ?)",
        ("A-001", "A区", "occupied", vehicle_id),
    )


@pytest.mark.parametrize("new_type, resident_id", [(VEHICLE_TEMP, None), (VEHICLE_VISITOR, 1)])
def test_req007_vehicle_with_fixed_space_cannot_become_non_monthly(env, new_type, resident_id):
    """固定车位只给月租车：绑了固定车位的车改成临时车或访客车时拒绝，资料不变。"""
    conn, repo, service = env
    vehicle_id = service.add(_monthly())
    _bind_fixed_space(conn, vehicle_id)
    vehicle = repo.get(vehicle_id)
    vehicle.vehicle_type, vehicle.resident_id = new_type, resident_id
    with pytest.raises(ValueError) as excinfo:
        service.update(vehicle)
    assert str(excinfo.value) == "该车辆有固定车位，请先释放车位再改为非月租车"
    assert repo.get(vehicle_id).vehicle_type == VEHICLE_MONTHLY


def test_req007_vehicle_with_fixed_space_can_still_renew(env):
    """有固定车位的月租车照常续费（改到期日），不受影响。"""
    conn, repo, service = env
    vehicle_id = service.add(_monthly())
    _bind_fixed_space(conn, vehicle_id)
    vehicle = repo.get(vehicle_id)
    vehicle.monthly_expire = date(2027, 12, 31)
    service.update(vehicle)
    assert repo.get(vehicle_id).monthly_expire == date(2027, 12, 31)


def test_req007_vehicle_without_fixed_space_can_change_type(env):
    """没有固定车位的月租车可以改成临时车，规则只管有固定车位的车。"""
    conn, repo, service = env
    vehicle_id = service.add(_monthly())
    vehicle = repo.get(vehicle_id)
    vehicle.vehicle_type, vehicle.resident_id = VEHICLE_TEMP, None
    service.update(vehicle)
    assert repo.get(vehicle_id).vehicle_type == VEHICLE_TEMP


def test_req004_plate_change_rejected_while_parked(env):
    """车辆在场时改车牌会让在场记录对不上，出场被按临时车收费，所以拒绝。"""
    conn, repo, service = env
    vehicle_id = service.add(_monthly())
    gate = GateService(RecordRepo(conn), repo, FeeRuleRepo(conn))
    gate.enter("豫A12345", datetime(2026, 11, 20, 8, 0), "admin")
    vehicle = repo.get(vehicle_id)
    vehicle.plate = "豫A12346"
    with pytest.raises(ValueError) as excinfo:
        service.update(vehicle)
    assert str(excinfo.value) == "该车辆在场内，出场后才能修改车牌"
    assert repo.get(vehicle_id).plate == "豫A12345"
    # 车牌没被改动，出场时仍是有效期内的月租车，免费
    assert gate.exit("豫A12345", datetime(2026, 11, 20, 13, 0), "admin").fee == 0


def test_req004_plate_change_allowed_after_exit(env):
    """出场以后可以正常改车牌。"""
    conn, repo, service = env
    vehicle_id = service.add(_monthly())
    gate = GateService(RecordRepo(conn), repo, FeeRuleRepo(conn))
    gate.enter("豫A12345", datetime(2026, 11, 20, 8, 0), "admin")
    gate.exit("豫A12345", datetime(2026, 11, 20, 13, 0), "admin")
    vehicle = repo.get(vehicle_id)
    vehicle.plate = "豫A12346"
    service.update(vehicle)
    assert repo.get(vehicle_id).plate == "豫A12346"
