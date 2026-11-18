"""REQ-011：按任务卡的四条记录验证查询，不依赖界面或真实数据库。"""
from datetime import datetime

import pytest

from app.models.entities import ParkingRecord, VEHICLE_TEMP
from app.repository.db import get_connection, init_db
from app.repository.record_repo import RecordRepo


@pytest.fixture
def repo():
    conn = get_connection(":memory:")
    init_db(conn)
    repository = RecordRepo(conn)
    # 任务卡指定的四次入场；故意不按时间排序插入，以验证查询的倒序要求。
    # 前三次已出场，费用用 D-1 的 0 元；第四次仍在场，费用尚未确定。
    samples = [
        ("豫A12345", datetime(2026, 11, 16, 8), datetime(2026, 11, 16, 10, 15)),
        ("豫A12345", datetime(2026, 11, 17, 9), datetime(2026, 11, 17, 10, 15)),
        ("豫B22222", datetime(2026, 11, 16, 23, 59), datetime(2026, 11, 17, 0, 30)),
        ("豫AD12345", datetime(2026, 11, 17, 0), None),
    ]
    for plate, enter_time, exit_time in samples:
        repository.add(ParkingRecord(
            id=None, plate=plate, vehicle_type=VEHICLE_TEMP,
            enter_time=enter_time, exit_time=exit_time,
            fee=0 if exit_time is not None else None,
            space_id=None, operator="guard_a",
        ))
    yield repository
    conn.close()


@pytest.mark.parametrize("plate", ["豫A12345", "A123", "  豫A12345  "])
def test_req011_search_plate_contains_and_strips_spaces(repo, plate):
    records = repo.search(plate=plate)
    assert len(records) == 2
    assert [r.plate for r in records] == ["豫A12345", "豫A12345"]
    assert [r.enter_time for r in records] == [
        datetime(2026, 11, 17, 9), datetime(2026, 11, 16, 8),
    ]


def test_req011_list_between_uses_entry_time_and_excludes_end(repo):
    start = datetime(2026, 11, 16)
    end = datetime(2026, 11, 17)
    records = repo.list_between(start, end)
    assert [(r.plate, r.enter_time) for r in records] == [
        ("豫B22222", datetime(2026, 11, 16, 23, 59)),
        ("豫A12345", datetime(2026, 11, 16, 8)),
    ]
    # B 车跨到次日才出场，仍按本次入场时间纳入，不能按出场时间筛选。
    assert records[0].exit_time == datetime(2026, 11, 17, 0, 30)


def test_req011_search_includes_exact_start_and_excludes_exact_end(repo):
    records = repo.search(start=datetime(2026, 11, 17), end=datetime(2026, 11, 17, 9))
    assert len(records) == 1
    assert records[0].plate == "豫AD12345"
    assert records[0].enter_time == datetime(2026, 11, 17)


def test_req011_search_plate_and_time_intersection(repo):
    records = repo.search("豫A12345", datetime(2026, 11, 16), datetime(2026, 11, 17))
    assert len(records) == 1
    assert records[0].plate == "豫A12345"
    assert records[0].enter_time == datetime(2026, 11, 16, 8)


@pytest.mark.parametrize("plate", ["", "   "])
def test_req011_no_conditions_returns_all_four_newest_first(repo, plate):
    records = repo.search(plate=plate)
    assert len(records) == 4
    assert [r.enter_time for r in records] == [
        datetime(2026, 11, 17, 9),
        datetime(2026, 11, 17, 0),
        datetime(2026, 11, 16, 23, 59),
        datetime(2026, 11, 16, 8),
    ]


def test_req011_only_start_leaves_end_unbounded(repo):
    records = repo.search(start=datetime(2026, 11, 17))
    assert [r.plate for r in records] == ["豫A12345", "豫AD12345"]


def test_req011_only_end_leaves_start_unbounded(repo):
    records = repo.search(end=datetime(2026, 11, 17))
    assert [r.plate for r in records] == ["豫B22222", "豫A12345"]


def test_req011_present_record_keeps_none_exit_and_fee(repo):
    records = repo.search(plate="豫AD12345")
    assert len(records) == 1
    assert records[0].exit_time is None
    assert records[0].fee is None


def test_req011_repository_has_no_delete(repo):
    assert not hasattr(repo, "delete")


@pytest.mark.parametrize("plate", ["不存在", "%", "_", "' OR 1=1 --"])
def test_req011_unmatched_or_special_text_is_literal(repo, plate):
    # 包含匹配针对字面文字，不能把用户输入解释为 SQL 通配符或 SQL 语句。
    assert repo.search(plate=plate) == []


def test_req011_empty_database_returns_empty_list():
    conn = get_connection(":memory:")
    try:
        init_db(conn)
        repository = RecordRepo(conn)
        assert repository.search() == []
        assert repository.list_between(datetime(2026, 11, 16), datetime(2026, 11, 17)) == []
    finally:
        conn.close()
