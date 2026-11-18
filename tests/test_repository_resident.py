"""住户表读写测试（负责人 B，REQ-003；任务卡 B-1）。

预期值来自任务卡 B-1 与 docs/02-需求清单.md 的 REQ-003 验收条件，
不依赖界面，使用内存数据库。
"""
import pytest

from app.models.entities import Resident
from app.repository.db import get_connection, init_db
from app.repository.resident_repo import ResidentRepo


@pytest.fixture
def repo():
    conn = get_connection(":memory:")
    init_db(conn)
    yield ResidentRepo(conn)
    conn.close()


def _resident(name: str, building: str = "3号楼", room: str = "2-501",
              phone: str = "13800000000") -> Resident:
    return Resident(id=None, name=name, building=building, room=room, phone=phone)


def test_req003_add_returns_id_and_get_roundtrip(repo):
    new_id = repo.add(_resident("张三"))
    assert isinstance(new_id, int)
    assert repo.get(new_id) == Resident(
        id=new_id, name="张三", building="3号楼", room="2-501", phone="13800000000"
    )


def test_req003_list_all_returns_every_row(repo):
    repo.add(_resident("张三"))
    repo.add(_resident("李四", "1号楼", "1-101"))
    assert {r.name for r in repo.list_all()} == {"张三", "李四"}


def test_req003_list_all_empty(repo):
    assert repo.list_all() == []


def test_req003_get_missing_returns_none(repo):
    assert repo.get(999) is None

def test_req003_update_changes_fields(repo):
    resident_id = repo.add(_resident("张三"))
    repo.update(Resident(resident_id, "张三丰", "5号楼", "5-201", "13900000001"))
    assert repo.get(resident_id) == Resident(
        id=resident_id, name="张三丰", building="5号楼", room="5-201", phone="13900000001"
    )

def test_req003_search_by_name_fragment(repo):
    """任务卡 B-1 验收 2：搜索"张"能找到姓名含"张"的住户。"""
    repo.add(_resident("张三"))
    repo.add(_resident("李四", "1号楼", "1-101"))
    repo.add(_resident("张五", "5号楼", "5-201"))
    assert {r.name for r in repo.search("张")} == {"张三", "张五"}


def test_req003_search_by_building(repo):
    """任务卡 B-1 验收 2：搜索"3号楼"能找到该楼栋的住户。"""
    repo.add(_resident("张三", "3号楼", "2-501"))
    repo.add(_resident("李四", "1号楼", "1-101"))
    assert [r.name for r in repo.search("3号楼")] == ["张三"]


def test_req003_delete_removes_resident(repo):
    resident_id = repo.add(_resident("张三"))
    repo.delete(resident_id)
    assert repo.get(resident_id) is None
    assert repo.list_all() == []


def test_req003_delete_rejected_when_resident_has_vehicle(repo):
    """任务卡 B-1 验收 4：名下有车辆的住户删除时提示指定文字。"""
    resident_id = repo.add(_resident("张三"))
    repo.conn.execute(
        "INSERT INTO vehicles (plate, vehicle_type, resident_id, monthly_expire, note) "
        "VALUES (?, ?, ?, ?, ?)",
        ("豫A12345", "monthly", resident_id, "2026-12-31", ""),
    )
    with pytest.raises(ValueError, match="请先删除或转移该住户名下的车辆"):
        repo.delete(resident_id)
    assert repo.get(resident_id) is not None