"""车位删除规则测试（REQ-006 验收条件：删除正被占用的车位时拒绝）。"""
from datetime import datetime, timedelta

import pytest

from app.models.entities import SPACE_FREE, SPACE_OCCUPIED, SPACE_RESERVED, ParkingSpace, Reservation
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


# ---------- REQ-007 固定车位（任务卡 C-2 验收 1 至 6，A-5 接手）----------
# 按任务卡要求，车辆用 SQL 直接写入，不依赖车辆服务。

from app.repository.reservation_repo import ReservationRepo  # noqa: E402
from app.repository.vehicle_repo import VehicleRepo  # noqa: E402

NOW = datetime(2026, 11, 20, 12, 0)     # 分配操作发生的时间，由界面传入


@pytest.fixture
def fixed(ctx):
    conn, repo, _ = ctx
    conn.execute("INSERT INTO residents (name, building, room, phone) VALUES ('张三','3','101','13800000000')")
    rows = [("豫A12345", "monthly", 1, "2026-12-31"), ("豫B22222", "monthly", 1, "2026-12-31"),
            ("豫C33333", "temp", None, None), ("豫D44444", "visitor", 1, None)]
    ids = {}
    for plate, vtype, resident, expire in rows:
        cur = conn.execute(
            "INSERT INTO vehicles (plate, vehicle_type, resident_id, monthly_expire) VALUES (?,?,?,?)",
            (plate, vtype, resident, expire))
        ids[plate] = cur.lastrowid
    conn.commit()
    a1 = _add(repo, "A-001", SPACE_FREE)
    a2 = _add(repo, "A-002", SPACE_FREE)
    return repo, SpaceService(repo, VehicleRepo(conn), ReservationRepo(conn)), ids, a1, a2


def test_req007_assign_monthly_vehicle(fixed):
    repo, service, ids, a1, _ = fixed
    service.assign_fixed(a1, "豫A12345", NOW)                                    # 验收 1
    space = repo.get(a1)
    assert space.fixed_vehicle_id == ids["豫A12345"]
    assert space.status == SPACE_OCCUPIED


def test_req007_space_already_bound_rejected(fixed):
    repo, service, ids, a1, _ = fixed
    service.assign_fixed(a1, "豫A12345", NOW)
    with pytest.raises(ValueError, match="^该车位已绑定其他车辆$"):         # 验收 2
        service.assign_fixed(a1, "豫B22222", NOW)
    assert repo.get(a1).fixed_vehicle_id == ids["豫A12345"]


def test_req007_vehicle_already_fixed_rejected(fixed):
    repo, service, _, a1, a2 = fixed
    service.assign_fixed(a1, "豫A12345", NOW)
    with pytest.raises(ValueError, match="^该车辆已有固定车位$"):           # 验收 3
        service.assign_fixed(a2, "豫A12345", NOW)
    space = repo.get(a2)
    assert space.fixed_vehicle_id is None and space.status == SPACE_FREE


@pytest.mark.parametrize("plate", ["豫C33333", "豫D44444"])
def test_req007_non_monthly_rejected(fixed, plate):
    repo, service, _, a1, _ = fixed
    with pytest.raises(ValueError, match="^只有月租车可以分配固定车位$"):   # 验收 4
        service.assign_fixed(a1, plate, NOW)
    assert repo.get(a1).fixed_vehicle_id is None


def test_req007_release_then_assign_another(fixed):
    repo, service, ids, a1, _ = fixed
    service.assign_fixed(a1, "豫A12345", NOW)
    service.release_fixed(a1)                                               # 验收 5
    space = repo.get(a1)
    assert space.fixed_vehicle_id is None and space.status == SPACE_FREE
    service.assign_fixed(a1, "豫B22222", NOW)
    assert repo.get(a1).fixed_vehicle_id == ids["豫B22222"]


def test_req007_release_unbound_rejected(fixed):
    _, service, _, a1, _ = fixed
    with pytest.raises(ValueError, match="^该车位没有绑定车辆$"):           # 验收 6
        service.release_fixed(a1)


def test_req007_unregistered_plate_rejected(fixed):
    _, service, _, a1, _ = fixed
    with pytest.raises(ValueError, match="^该车牌未登记$"):
        service.assign_fixed(a1, "豫E55555", NOW)


@pytest.mark.parametrize("status", [SPACE_OCCUPIED, SPACE_RESERVED])
def test_req007_only_free_space_can_be_assigned(fixed, status):
    repo, service, _, _, _ = fixed
    space_id = _add(repo, "B-001", status)
    with pytest.raises(ValueError, match="^只能分配空闲车位$"):
        service.assign_fixed(space_id, "豫A12345", NOW)


def test_req007_missing_space_rejected(fixed):
    _, service, _, _, _ = fixed
    with pytest.raises(ValueError, match="^该车位已不存在，请刷新$"):
        service.assign_fixed(999, "豫A12345", NOW)
    with pytest.raises(ValueError, match="^该车位已不存在，请刷新$"):
        service.release_fixed(999)


def test_req007_assigned_space_cannot_be_deleted(fixed):
    repo, service, _, a1, _ = fixed
    service.assign_fixed(a1, "豫A12345", NOW)
    with pytest.raises(ValueError, match="^车位正在使用，不能删除$"):       # 沿用 C-1 规则
        service.delete(a1)


def test_req007_bound_space_manually_set_free_cannot_be_deleted(fixed):
    """车位页可以手动把状态改成"空闲"（ADR-010），绑定不能因此被悄悄删掉。"""
    repo, service, ids, a1, _ = fixed
    service.assign_fixed(a1, "豫A12345", NOW)
    space = repo.get(a1)
    space.status = SPACE_FREE                    # 模拟车位页"保存修改"：保留绑定，只改状态
    repo.update(space)
    with pytest.raises(ValueError, match="^该车位已绑定固定车辆，请先释放$"):
        service.delete(a1)
    assert repo.get(a1).fixed_vehicle_id == ids["豫A12345"]


def test_req007_get_by_fixed_vehicle(fixed):
    repo, service, ids, a1, _ = fixed
    assert repo.get_by_fixed_vehicle(ids["豫A12345"]) is None
    service.assign_fixed(a1, "豫A12345", NOW)
    assert repo.get_by_fixed_vehicle(ids["豫A12345"]).id == a1


# ---------- 第二轮审查补充：有未结束预约的车位不能分配为固定车位 ----------

def _reserve(repo, space_id, start, end):
    ReservationRepo(repo.conn).add(Reservation(None, space_id, "豫F66666", start, end))


@pytest.mark.parametrize("start, end", [
    (datetime(2026, 11, 21, 9), datetime(2026, 11, 21, 11)),     # 还没开始
    (datetime(2026, 11, 20, 11), datetime(2026, 11, 20, 13)),    # 正在进行：NOW 在时间段内
])
def test_req007_space_with_unfinished_reservation_rejected(fixed, start, end):
    repo, service, _, a1, _ = fixed
    _reserve(repo, a1, start, end)
    with pytest.raises(ValueError, match="^该车位还有未结束的预约，请先取消预约$"):
        service.assign_fixed(a1, "豫A12345", NOW)
    space = repo.get(a1)
    assert space.fixed_vehicle_id is None and space.status == SPACE_FREE


@pytest.mark.parametrize("end", [
    datetime(2026, 11, 19, 10),    # 昨天已结束
    NOW,                           # 恰好此刻结束，不算未结束（与预约"首尾相接不算重叠"一致）
])
def test_req007_finished_reservation_does_not_block(fixed, end):
    repo, service, ids, a1, _ = fixed
    _reserve(repo, a1, end - timedelta(hours=2), end)
    service.assign_fixed(a1, "豫A12345", NOW)
    assert repo.get(a1).fixed_vehicle_id == ids["豫A12345"]


def test_req007_reservation_on_other_space_does_not_block(fixed):
    repo, service, ids, a1, a2 = fixed
    _reserve(repo, a2, datetime(2026, 11, 21, 9), datetime(2026, 11, 21, 11))
    service.assign_fixed(a1, "豫A12345", NOW)
    assert repo.get(a1).fixed_vehicle_id == ids["豫A12345"]
