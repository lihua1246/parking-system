"""住户服务层测试（负责人 B，REQ-003；任务卡 B-1 验收 4）。

预期值来自任务卡 B-1 的验收条件；使用内存数据库，不依赖界面。
"""
import pytest

from app.models.entities import Resident
from app.repository.db import get_connection, init_db
from app.repository.resident_repo import ResidentRepo
from app.services.resident import ResidentService


@pytest.fixture
def repo_and_service():
    conn = get_connection(":memory:")
    init_db(conn)
    repo = ResidentRepo(conn)
    yield repo, ResidentService(repo)
    conn.close()


def _resident() -> Resident:
    return Resident(id=None, name="张三", building="3号楼", room="2-501", phone="13800000000")


def test_req003_service_delete_rejected_when_resident_has_vehicle(repo_and_service):
    """验收 4：名下有车时抛出指定文字，且住户仍然存在。"""
    repo, service = repo_and_service
    resident_id = repo.add(_resident())
    repo.conn.execute(
        "INSERT INTO vehicles (plate, vehicle_type, resident_id, monthly_expire, note) "
        "VALUES (?, ?, ?, ?, ?)",
        ("豫A12345", "monthly", resident_id, "2026-12-31", ""),
    )
    with pytest.raises(ValueError) as excinfo:
        service.delete(resident_id)
    assert str(excinfo.value) == "请先删除或转移该住户名下的车辆"
    assert repo.get(resident_id) is not None


def test_req003_service_delete_resident_without_vehicle(repo_and_service):
    """名下没有车的住户可以正常删除。"""
    repo, service = repo_and_service
    resident_id = repo.add(_resident())
    service.delete(resident_id)
    assert repo.get(resident_id) is None