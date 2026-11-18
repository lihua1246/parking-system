"""车位删除规则测试（REQ-006 验收条件：删除正被占用的车位时拒绝）。"""
from datetime import datetime

import pytest

from app.models.entities import SPACE_FREE, SPACE_OCCUPIED, SPACE_RESERVED, ParkingSpace
from app.repository.db import get_connection, init_db
from app.repository.space_repo import SpaceRepo
from app.services.space import SpaceService


@pytest.fixture
def ctx():
    conn = get_connection(":memory:")
    init_db(conn)
    repo = SpaceRepo(conn)
    yield conn, repo, SpaceService(repo)
    conn.close()


def _add(repo, code, status):
    return repo.add(ParkingSpace(None, code, "A区", status, None))


@pytest.mark.parametrize("status", [SPACE_FREE, SPACE_RESERVED])
def test_req006_delete_not_occupied_space(ctx, status):
    _, repo, service = ctx
    space_id = _add(repo, "A-001", status)
    service.delete(space_id)
    assert repo.get(space_id) is None


def test_req006_delete_occupied_space_rejected(ctx):
    _, repo, service = ctx
    space_id = _add(repo, "A-001", SPACE_OCCUPIED)
    with pytest.raises(ValueError, match="^车位正在使用，不能删除$"):
        service.delete(space_id)
    assert repo.get(space_id) is not None


def test_req006_delete_missing_space_rejected(ctx):
    _, _, service = ctx
    with pytest.raises(ValueError, match="^该车位已不存在，请刷新$"):
        service.delete(999)


def test_req006_delete_space_with_reservation_rejected(ctx):
    conn, repo, service = ctx
    space_id = _add(repo, "A-001", SPACE_RESERVED)
    conn.execute(
        "INSERT INTO reservations (space_id, plate, start_time, end_time) VALUES (?, ?, ?, ?)",
        (space_id, "豫A12345",
         datetime(2026, 11, 17, 8).isoformat(), datetime(2026, 11, 17, 10).isoformat()),
    )
    conn.commit()
    with pytest.raises(ValueError, match="^该车位还有预约记录，不能删除$"):
        service.delete(space_id)
    assert repo.get(space_id) is not None
