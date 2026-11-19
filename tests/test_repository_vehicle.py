"""VehicleRepo.get_by_plate 测试（REQ-004 中入场所需的最小部分）。

add 尚未实现，测试数据直接用 SQL 写入内存库。
"""
from datetime import date

import pytest

from app.models.entities import VEHICLE_MONTHLY, VEHICLE_VISITOR, Vehicle
from app.repository.db import get_connection, init_db
from app.repository.vehicle_repo import VehicleRepo
import sqlite3


@pytest.fixture
def conn():
    conn = get_connection(":memory:")
    init_db(conn)
    conn.execute(
        "INSERT INTO residents (name, building, room, phone) "
        "VALUES ('张三', '3号楼', '2-501', '13800000000')"
    )
    yield conn
    conn.close()


def test_get_by_plate_unknown_returns_none(conn):
    assert VehicleRepo(conn).get_by_plate("豫A12345") is None


def test_get_by_plate_monthly_vehicle_with_expire_date(conn):
    conn.execute(
        "INSERT INTO vehicles (plate, vehicle_type, resident_id, monthly_expire, note) "
        "VALUES ('豫A12345', ?, 1, '2026-12-31', '地库')",
        (VEHICLE_MONTHLY,),
    )
    vehicle = VehicleRepo(conn).get_by_plate("豫A12345")
    assert vehicle == Vehicle(
        id=1, plate="豫A12345", vehicle_type=VEHICLE_MONTHLY,
        resident_id=1, monthly_expire=date(2026, 12, 31), note="地库",
    )


def test_get_by_plate_visitor_without_expire_date(conn):
    conn.execute(
        "INSERT INTO vehicles (plate, vehicle_type, resident_id) VALUES ('豫AD12345', ?, 1)",
        (VEHICLE_VISITOR,),
    )
    vehicle = VehicleRepo(conn).get_by_plate("豫AD12345")
    assert vehicle.vehicle_type == VEHICLE_VISITOR
    assert vehicle.monthly_expire is None
    assert vehicle.note == ""


def _vehicle(plate="豫A12345", vehicle_type=VEHICLE_MONTHLY, resident_id=1,
             monthly_expire=date(2026, 12, 31), note=""):
    return Vehicle(id=None, plate=plate, vehicle_type=vehicle_type,
                   resident_id=resident_id, monthly_expire=monthly_expire, note=note)


def test_req004_add_returns_id_and_get_roundtrip(conn):
    """新增后按 id 取回，五个字段都要和写进去的一致（含 date 类型的到期日）。"""
    repo = VehicleRepo(conn)
    new_id = repo.add(_vehicle())
    assert isinstance(new_id, int)
    assert repo.get(new_id) == Vehicle(
        id=new_id, plate="豫A12345", vehicle_type=VEHICLE_MONTHLY,
        resident_id=1, monthly_expire=date(2026, 12, 31), note="",
    )


def test_req004_duplicate_plate_rejected(conn):
    """REQ-004：车牌唯一，重复登记必须被拒绝。"""
    repo = VehicleRepo(conn)
    repo.add(_vehicle())
    with pytest.raises(sqlite3.IntegrityError):
        repo.add(_vehicle())
    assert len(repo.list_all()) == 1


def test_req004_list_all_returns_every_vehicle(conn):
    repo = VehicleRepo(conn)
    repo.add(_vehicle("豫A12345"))
    repo.add(_vehicle("豫A54321", VEHICLE_VISITOR, resident_id=None, monthly_expire=None))
    assert {v.plate for v in repo.list_all()} == {"豫A12345", "豫A54321"}

def test_req004_update_changes_fields(conn):
        """修改车牌、类型、住户、到期日、备注，全部要能写进去。

        这条特意把到期日改成 None（访客车没有到期日），顺带验证 NULL 的写入。
        """
        repo = VehicleRepo(conn)
        vehicle_id = repo.add(_vehicle())
        repo.update(Vehicle(vehicle_id, "豫A99999", VEHICLE_VISITOR, None, None, "改过"))
        assert repo.get(vehicle_id) == Vehicle(
            id=vehicle_id, plate="豫A99999", vehicle_type=VEHICLE_VISITOR,
            resident_id=None, monthly_expire=None, note="改过",
        )

def test_req004_delete_removes_vehicle(conn):
        repo = VehicleRepo(conn)
        vehicle_id = repo.add(_vehicle())
        repo.delete(vehicle_id)
        assert repo.get(vehicle_id) is None
        assert repo.list_all() == []


def test_req004_search_by_plate_fragment(conn):
    """任务卡 B-2：搜"A123"能找到 豫A12345。"""
    repo = VehicleRepo(conn)
    repo.add(_vehicle("豫A12345"))
    repo.add(_vehicle("豫A54321", VEHICLE_VISITOR, resident_id=None,
                      monthly_expire=None))
    assert [v.plate for v in repo.search("A123")] == ["豫A12345"]


def test_req004_list_by_resident_only_that_resident(conn):
    """任务卡 B-2：按住户查询只返回该住户名下的车。"""
    repo = VehicleRepo(conn)
    repo.add(_vehicle("豫A12345"))
    assert [v.plate for v in repo.list_by_resident(1)] == ["豫A12345"]
    assert repo.list_by_resident(99) == []