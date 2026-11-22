"""车辆管理页面的冒烟测试（REQ-004）。

重点回归：选中一行后“清空表单”/删除，表单不能被 _on_select 回填。
"""
import pytest
from PySide6.QtWidgets import QMessageBox

from app.models.entities import VEHICLE_TEMP, Resident, Vehicle
from app.repository.db import get_connection, init_db
from app.repository.resident_repo import ResidentRepo
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


@pytest.fixture
def resident_repo(repo):
    """与 repo 共用同一个内存库。"""
    return ResidentRepo(repo.conn)


def _temp_vehicle(plate: str, resident_id: int | None = None) -> Vehicle:
    return Vehicle(id=None, plate=plate, vehicle_type=VEHICLE_TEMP,
                   resident_id=resident_id, monthly_expire=None, note="")


def _plates(page: VehiclePage) -> list[str]:
    return [page.table.item(row, 1).text() for row in range(page.table.rowCount())]


def test_req004_search_by_plate_keyword(qapp, repo):
    """验收 4（前半）：搜索"A123"能找到 豫A12345。"""
    repo.add(_temp_vehicle("豫A12345"))
    repo.add(_temp_vehicle("豫B67890"))
    page = VehiclePage(repo)
    page.keyword_edit.setText("A123")
    page.search()
    assert _plates(page) == ["豫A12345"]


def test_req004_search_by_resident_shows_only_their_vehicles(qapp, repo, resident_repo):
    """验收 4（后半）：按住户"张三"查询只显示张三名下的车辆。"""
    zhang = resident_repo.add(Resident(None, "张三", "3号楼", "2-501", "13800000000"))
    li = resident_repo.add(Resident(None, "李四", "1号楼", "1-101", "13900000001"))
    repo.add(_temp_vehicle("豫A12345", zhang))
    repo.add(_temp_vehicle("豫A54321", zhang))
    repo.add(_temp_vehicle("豫B67890", li))
    repo.add(_temp_vehicle("豫C11111"))
    page = VehiclePage(repo, resident_repo)

    page.resident_filter.setCurrentIndex(page.resident_filter.findData(zhang))
    page.search_by_resident()

    assert page.resident_filter.currentText().startswith("张三")
    assert _plates(page) == ["豫A12345", "豫A54321"]


def test_req004_resident_filter_picks_up_new_residents(qapp, repo, resident_repo):
    """住户页面后来新增的住户，点"显示全部"后出现在下拉框里。"""
    page = VehiclePage(repo, resident_repo)
    assert page.resident_filter.count() == 0
    resident_repo.add(Resident(None, "张三", "3号楼", "2-501", "13800000000"))
    page.reload()
    assert page.resident_filter.count() == 1


def test_req004_search_by_resident_with_no_residents(qapp, repo, resident_repo, monkeypatch):
    """还没有住户时提示，而不是报错。"""
    infos = []
    monkeypatch.setattr(QMessageBox, "information", lambda *a: infos.append(a[2]))
    page = VehiclePage(repo, resident_repo)
    page.search_by_resident()
    assert infos == ["还没有住户，请先在住户管理中登记"]


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
