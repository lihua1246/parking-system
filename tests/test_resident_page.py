"""住户管理页面的冒烟测试（负责人 B，REQ-003）。

这次 main.py 启动即崩，是因为只测了 repo 和 service，页面从没被构造过。
"""
import pytest

from app.models.entities import Resident
from app.repository.db import get_connection, init_db
from app.repository.resident_repo import ResidentRepo
from app.ui.pages.resident_page import ResidentPage


@pytest.fixture(scope="module")
def qapp():
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture
def repo():
    conn = get_connection(":memory:")
    init_db(conn)
    yield ResidentRepo(conn)
    conn.close()


def test_req003_page_constructs_with_real_repo(qapp, repo):
    """验收 1：页面用真实 repo 构造不报错，并把列表加载进表格。"""
    repo.add(Resident(None, "张三", "3号楼", "2-501", "13800000000"))
    page = ResidentPage(resident_repo=repo)
    assert page.table.rowCount() == 1
    assert page.table.item(0, 1).text() == "张三"


def test_req003_page_search_filters_table(qapp, repo):
    """验收 2：搜索"张"只留下姓名含"张"的行。"""
    repo.add(Resident(None, "张三", "3号楼", "2-501", "13800000000"))
    repo.add(Resident(None, "李四", "1号楼", "1-101", "13900000001"))
    page = ResidentPage(resident_repo=repo)
    page.keyword_edit.setText("张")
    page.search()
    assert page.table.rowCount() == 1
    assert page.table.item(0, 1).text() == "张三"