"""车辆管理页面的冒烟测试（REQ-004）。

重点回归：选中一行后“清空表单”/删除，表单不能被 _on_select 回填。
"""
import pytest
from PySide6.QtWidgets import QMessageBox

from app.models.entities import VEHICLE_TEMP, Vehicle
from app.repository.db import get_connection, init_db
from app.repository.vehicle_repo import VehicleRepo
from app.ui.pages.vehicle_page import VehiclePage


@pytest.fixture(scope="module")
def qapp():
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture
def repo():
    conn = get_connection(":memory:")
    init_db(conn)
    yield VehicleRepo(conn)
    conn.close()


def _temp_vehicle(plate: str) -> Vehicle:
    return Vehicle(id=None, plate=plate, vehicle_type=VEHICLE_TEMP,
                   resident_id=None, monthly_expire=None, note="")


def test_req004_page_constructs_with_real_repo(qapp, repo):
    repo.add(_temp_vehicle("豫A12345"))
    page = VehiclePage(repo)
    assert page.service is not None
    assert page.table.rowCount() == 1
    assert page.table.item(0, 1).text() == "豫A12345"


def test_req004_clear_form_after_select_really_clears(qapp, repo):
    repo.add(_temp_vehicle("豫A12345"))
    page = VehiclePage(repo)
    page.table.selectRow(0)
    assert page.plate_edit.text() == "豫A12345"

    page.clear_form()

    assert page.plate_edit.text() == ""
    assert page.current_id is None


@pytest.mark.parametrize("text", ["abc", "12a", "-3", "１２"])
def test_req004_non_numeric_resident_id_is_rejected(qapp, repo, monkeypatch, text):
    page = VehiclePage(repo)
    warnings = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *a: warnings.append(a[2]))
    page.type_combo.setCurrentIndex(page.type_combo.findData(VEHICLE_TEMP))
    page.plate_edit.setText("豫A12345")
    page.resident_edit.setText(text)

    page.add()

    assert warnings == ["住户 ID 须为数字"]
    assert repo.list_all() == []


def test_req004_blank_resident_id_is_allowed_for_temp(qapp, repo):
    page = VehiclePage(repo)
    page.type_combo.setCurrentIndex(page.type_combo.findData(VEHICLE_TEMP))
    page.plate_edit.setText("豫A12345")

    page.add()

    assert [v.resident_id for v in repo.list_all()] == [None]


def test_req004_remove_does_not_leave_stale_id(qapp, repo, monkeypatch):
    repo.add(_temp_vehicle("豫A12345"))
    page = VehiclePage(repo)
    page.table.selectRow(0)
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.Yes)

    page.remove()

    assert page.table.rowCount() == 0
    assert page.current_id is None
    assert page.plate_edit.text() == ""
