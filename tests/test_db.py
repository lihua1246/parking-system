"""骨架：建表与默认数据。"""
import sqlite3

import pytest

from app.repository.db import get_connection, init_db

TABLES = {"users", "residents", "vehicles", "spaces", "records", "fee_rules", "reservations"}


@pytest.fixture
def conn():
    c = get_connection(":memory:")
    init_db(c)
    yield c
    c.close()


def test_init_db_creates_all_seven_tables(conn):
    rows = conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
    names = {r["name"] for r in rows}
    assert TABLES <= names


def test_init_db_writes_default_fee_rules(conn):
    rows = conn.execute("SELECT * FROM fee_rules ORDER BY vehicle_type").fetchall()
    rules = {r["vehicle_type"]: (r["free_minutes"], r["hourly_rate"], r["daily_cap"]) for r in rows}
    assert rules == {"temp": (30, 3, 30), "visitor": (120, 3, 30)}


def test_init_db_twice_does_not_duplicate(conn):
    init_db(conn)
    count = conn.execute("SELECT COUNT(*) FROM fee_rules").fetchone()[0]
    assert count == 2


def test_vehicle_plate_is_unique(conn):
    sql = "INSERT INTO vehicles (plate, vehicle_type) VALUES (?, ?)"
    conn.execute(sql, ("豫A12345", "temp"))
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(sql, ("豫A12345", "temp"))


def test_space_fixed_vehicle_is_unique(conn):
    """REQ-007 的数据库兜底：一辆月租车只能有一个固定车位。"""
    conn.execute("INSERT INTO vehicles (plate, vehicle_type) VALUES ('豫A00001', 'monthly')")
    sql = "INSERT INTO spaces (code, zone, status, fixed_vehicle_id) VALUES (?, 'A区', 'free', 1)"
    conn.execute(sql, ("A-001",))
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(sql, ("A-002",))


def test_foreign_keys_enforced(conn):
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO vehicles (plate, vehicle_type, resident_id) VALUES ('豫A1', 'monthly', 999)")


def test_get_connection_creates_parent_dir(tmp_path):
    path = tmp_path / "sub" / "parking.db"
    c = get_connection(str(path))
    init_db(c)
    c.close()
    assert path.exists()


def test_default_db_path_is_under_project_root():
    """从任意目录启动都指向同一个库文件，不受当前工作目录影响。"""
    from pathlib import Path

    from app.repository.db import DEFAULT_DB_PATH

    expected = Path(__file__).resolve().parent.parent / "data" / "parking.db"
    assert Path(DEFAULT_DB_PATH) == expected
