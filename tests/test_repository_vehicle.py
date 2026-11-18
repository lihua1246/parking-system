"""VehicleRepo.get_by_plate 测试（REQ-004 中入场所需的最小部分）。

add 尚未实现，测试数据直接用 SQL 写入内存库。
"""
from datetime import date

import pytest

from app.models.entities import VEHICLE_MONTHLY, VEHICLE_VISITOR, Vehicle
from app.repository.db import get_connection, init_db
from app.repository.vehicle_repo import VehicleRepo


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
