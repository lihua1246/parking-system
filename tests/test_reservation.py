"""REQ-022 车位预约（任务卡 A-5，原属 C）。

验收条件（docs/02）：可为某车牌预约某个空闲车位的某一时间段；同一车位的预约时间段不能重叠。
首尾相接不算冲突（docs/03 reservation.py）。其余规则见 services/reservation.py 文件头。
"""
from datetime import datetime

import pytest

from app.models.entities import (
    ParkingSpace, Reservation, SPACE_FREE, SPACE_OCCUPIED, SPACE_RESERVED,
)
from app.repository.db import get_connection, init_db
from app.repository.reservation_repo import ReservationRepo
from app.repository.space_repo import SpaceRepo
from app.services.reservation import (
    CONFLICT_MSG, INVALID_PERIOD_MSG, INVALID_PLATE_MSG, RESERVATION_NOT_FOUND_MSG,
    SPACE_FIXED_MSG, SPACE_NOT_FOUND_MSG, SPACE_OCCUPIED_MSG, add_reservation, cancel_reservation,
    has_conflict,
)


def t(hour, minute=0, day=21):
    return datetime(2026, 11, day, hour, minute)


# ---------- has_conflict（纯函数） ----------

EXISTING = [Reservation(1, 1, "豫A12345", t(8), t(10))]


@pytest.mark.parametrize("start, end, expected", [
    (t(9), t(11), True),       # 后半段重叠
    (t(7), t(9), True),        # 前半段重叠
    (t(8, 30), t(9, 30), True),  # 被包含
    (t(7), t(11), True),       # 包含已有预约
    (t(8), t(10), True),       # 完全相同
    (t(10), t(12), False),     # 首尾相接：已有的结束 = 新的开始
    (t(6), t(8), False),       # 首尾相接：新的结束 = 已有的开始
    (t(11), t(12), False),     # 完全不相交
])
def test_req022_has_conflict(start, end, expected):
    assert has_conflict(EXISTING, 1, start, end) is expected


def test_req022_other_space_never_conflicts():
    assert has_conflict(EXISTING, 2, t(8), t(10)) is False


# ---------- 预约服务 ----------

@pytest.fixture
def ctx():
    conn = get_connection(":memory:")
    init_db(conn)
    spaces = SpaceRepo(conn)
    ids = {status: spaces.add(ParkingSpace(None, f"A-{i}", "A区", status, None))
           for i, status in enumerate([SPACE_FREE, SPACE_OCCUPIED, SPACE_RESERVED])}
    yield ReservationRepo(conn), spaces, ids
    conn.close()


def test_req022_reserve_free_space(ctx):
    reservations, spaces, ids = ctx
    rid = add_reservation(reservations, spaces, ids[SPACE_FREE], "豫A12345", t(8), t(10))
    assert reservations.get(rid) == Reservation(rid, ids[SPACE_FREE], "豫A12345", t(8), t(10))
    assert spaces.get(ids[SPACE_FREE]).status == SPACE_FREE      # 预约不改车位状态


def test_req022_overlap_on_same_space_rejected(ctx):
    reservations, spaces, ids = ctx
    add_reservation(reservations, spaces, ids[SPACE_FREE], "豫A12345", t(8), t(10))
    with pytest.raises(ValueError, match=CONFLICT_MSG):
        add_reservation(reservations, spaces, ids[SPACE_FREE], "豫B22222", t(9), t(11))
    assert len(reservations.list_all()) == 1


def test_req022_back_to_back_allowed(ctx):
    reservations, spaces, ids = ctx
    add_reservation(reservations, spaces, ids[SPACE_FREE], "豫A12345", t(8), t(10))
    add_reservation(reservations, spaces, ids[SPACE_FREE], "豫B22222", t(10), t(12))
    assert len(reservations.list_all()) == 2


def test_req022_same_period_on_different_spaces_allowed(ctx):
    reservations, spaces, ids = ctx
    add_reservation(reservations, spaces, ids[SPACE_FREE], "豫A12345", t(8), t(10))
    add_reservation(reservations, spaces, ids[SPACE_RESERVED], "豫B22222", t(8), t(10))
    assert len(reservations.list_all()) == 2


def test_req022_occupied_space_rejected(ctx):
    reservations, spaces, ids = ctx
    with pytest.raises(ValueError, match=SPACE_OCCUPIED_MSG):
        add_reservation(reservations, spaces, ids[SPACE_OCCUPIED], "豫A12345", t(8), t(10))
    assert reservations.list_all() == []


def test_req022_bound_fixed_space_rejected_even_if_marked_free(ctx):
    """固定车位被手动改成"空闲"后，仍不能给别人预约（ADR-006、ADR-011）。"""
    reservations, spaces, _ = ctx
    conn = spaces.conn
    conn.execute("INSERT INTO residents (name, building, room, phone) VALUES ('张三','3','101','13800000000')")
    vehicle_id = conn.execute(
        "INSERT INTO vehicles (plate, vehicle_type, resident_id, monthly_expire) "
        "VALUES ('豫A12345', 'monthly', 1, '2026-12-31')").lastrowid
    conn.commit()
    space_id = spaces.add(ParkingSpace(None, "A-9", "A区", SPACE_FREE, vehicle_id))
    with pytest.raises(ValueError, match=SPACE_FIXED_MSG):
        add_reservation(reservations, spaces, space_id, "豫B22222", t(8), t(10))
    assert reservations.list_all() == []


def test_req022_missing_space_rejected(ctx):
    reservations, spaces, _ = ctx
    with pytest.raises(ValueError, match=SPACE_NOT_FOUND_MSG):
        add_reservation(reservations, spaces, 999, "豫A12345", t(8), t(10))


@pytest.mark.parametrize("plate", ["豫a12345", "A12345", ""])
def test_req022_invalid_plate_rejected(ctx, plate):
    reservations, spaces, ids = ctx
    with pytest.raises(ValueError, match=INVALID_PLATE_MSG):
        add_reservation(reservations, spaces, ids[SPACE_FREE], plate, t(8), t(10))


def test_req022_unregistered_plate_allowed(ctx):
    reservations, spaces, ids = ctx                         # 车辆表为空，只校验格式
    add_reservation(reservations, spaces, ids[SPACE_FREE], "豫AD12345", t(8), t(10))
    assert len(reservations.list_all()) == 1


@pytest.mark.parametrize("start, end", [(t(10), t(10)), (t(10), t(8))])
def test_req022_end_not_after_start_rejected(ctx, start, end):
    reservations, spaces, ids = ctx
    with pytest.raises(ValueError, match=INVALID_PERIOD_MSG):
        add_reservation(reservations, spaces, ids[SPACE_FREE], "豫A12345", start, end)


def test_req022_cancel_then_slot_available_again(ctx):
    reservations, spaces, ids = ctx
    rid = add_reservation(reservations, spaces, ids[SPACE_FREE], "豫A12345", t(8), t(10))
    cancel_reservation(reservations, rid)
    assert reservations.get(rid) is None
    add_reservation(reservations, spaces, ids[SPACE_FREE], "豫B22222", t(8), t(10))


def test_req022_cancel_missing_rejected(ctx):
    reservations, _, _ = ctx
    with pytest.raises(ValueError, match=RESERVATION_NOT_FOUND_MSG):
        cancel_reservation(reservations, 999)


def test_req022_repo_round_trip_keeps_datetime(ctx):
    reservations, _, ids = ctx
    rid = reservations.add(Reservation(None, ids[SPACE_FREE], "豫A12345", t(8, 30), t(10, 15)))
    got = reservations.get(rid)
    assert got.start_time == t(8, 30) and got.end_time == t(10, 15)
    reservations.update(Reservation(rid, ids[SPACE_FREE], "豫B22222", t(9), t(11)))
    assert reservations.get(rid).plate == "豫B22222"
