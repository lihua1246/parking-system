"""车位管理页面的冒烟测试（REQ-007）。

重点：页面把预约仓库交给服务层，并在分配时传入当前时间，未结束的预约会挡住分配固定车位。
"""
from datetime import date, datetime

import pytest
from PySide6.QtWidgets import QInputDialog, QMessageBox

from app.models.entities import (
    SPACE_FREE, VEHICLE_MONTHLY, ParkingSpace, Reservation, Resident, Vehicle,
)
from app.repository.db import get_connection, init_db
from app.repository.reservation_repo import ReservationRepo
from app.repository.resident_repo import ResidentRepo
from app.repository.space_repo import SpaceRepo
from app.repository.vehicle_repo import VehicleRepo
from app.ui.pages.space_page import SpacePage


@pytest.fixture(scope="module")
def qapp():
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture
def conn():
    c = get_connection(":memory:")
    init_db(c)
    resident_id = ResidentRepo(c).add(Resident(None, "张三", "3号楼", "2-501", "13800000000"))
    VehicleRepo(c).add(Vehicle(None, "豫A12345", VEHICLE_MONTHLY, resident_id, date(2099, 12, 31)))
    yield c
    c.close()


def test_req007_assign_blocked_by_unfinished_reservation(qapp, conn, monkeypatch):
    space_repo = SpaceRepo(conn)
    space_id = space_repo.add(ParkingSpace(None, "A-001", "A区", SPACE_FREE, None))
    # 远期预约：无论哪天运行测试，它都还没结束
    ReservationRepo(conn).add(Reservation(
        None, space_id, "豫B22222", datetime(2099, 1, 1, 9), datetime(2099, 1, 1, 11)))
    page = SpacePage(space_repo, VehicleRepo(conn), ReservationRepo(conn))
    warnings = []
    monkeypatch.setattr(QInputDialog, "getText", lambda *a, **k: ("豫A12345", True))
    monkeypatch.setattr(QMessageBox, "warning", lambda *a: warnings.append(a[2]))
    page.table.selectRow(0)

    page.assign_button.click()

    assert warnings == ["该车位还有未结束的预约，请先取消预约"]
    assert space_repo.get(space_id).fixed_vehicle_id is None


def test_req007_assign_without_reservation_succeeds(qapp, conn, monkeypatch):
    space_repo = SpaceRepo(conn)
    space_id = space_repo.add(ParkingSpace(None, "A-001", "A区", SPACE_FREE, None))
    page = SpacePage(space_repo, VehicleRepo(conn), ReservationRepo(conn))
    warnings = []
    monkeypatch.setattr(QInputDialog, "getText", lambda *a, **k: ("豫A12345", True))
    monkeypatch.setattr(QMessageBox, "warning", lambda *a: warnings.append(a[2]))
    page.table.selectRow(0)

    page.assign_button.click()

    assert warnings == []
    assert space_repo.get(space_id).fixed_vehicle_id is not None
