"""REQ-023 数据备份与还原（Issue #24）。

验收条件（docs/02-需求清单.md REQ-023）：
  1. 一键把数据库复制为带日期的备份文件
  2. 可从备份文件还原
  3. 还原前需二次确认 —— 界面部分，手工截图
另加（ADR-008）：还原前自动备份当前数据；不是本系统的文件拒绝还原且数据不变。
当前数据库用内存库；备份文件写在 pytest 提供的临时目录 tmp_path。
"""
import sqlite3
from datetime import datetime

import pytest

from app.models.entities import ROLE_GUARD
from app.repository.db import get_connection, init_db
from app.repository.user_repo import UserRepo
from app.services.auth import ensure_default_admin
from app.services.backup import (
    backup_database, backup_filename, list_backups, restore_database,
)
from app.services.user import UserService

T1 = datetime(2026, 11, 17, 9, 30, 5)
T2 = datetime(2026, 11, 17, 10, 0, 0)
T3 = datetime(2026, 11, 18, 8, 0, 0)


@pytest.fixture
def conn():
    c = get_connection(":memory:")
    init_db(c)
    ensure_default_admin(UserRepo(c))
    yield c
    c.close()


def usernames(conn):
    return [u.username for u in UserRepo(conn).list_all()]


# ---------- 验收 1：备份为带日期的文件 ----------

def test_req023_backup_filename_contains_date_and_time():
    assert backup_filename(T1) == "parking_20261117_093005.db"


def test_req023_backup_creates_file_with_same_data(conn, tmp_path):
    path = backup_database(conn, tmp_path / "backups", T1)
    assert path.name == "parking_20261117_093005.db" and path.is_file()
    copy = sqlite3.connect(path)
    copy.row_factory = sqlite3.Row
    assert [u.username for u in UserRepo(copy).list_all()] == ["admin"]
    copy.close()


def test_req023_two_backups_same_day_do_not_overwrite(conn, tmp_path):
    backup_database(conn, tmp_path, T1)
    backup_database(conn, tmp_path, T2)
    assert [p.name for p in list_backups(tmp_path)] == [
        "parking_20261117_100000.db", "parking_20261117_093005.db",
    ]



def test_req023_backup_in_same_second_gets_suffix(conn, tmp_path):
    # 刚备份就还原时，还原前的安全备份与刚才那份同一秒，不能互相覆盖
    first = backup_database(conn, tmp_path, T1)
    second = backup_database(conn, tmp_path, T1)
    assert first.name == "parking_20261117_093005.db"
    assert second.name == "parking_20261117_093005_2.db"
    assert [p.name for p in list_backups(tmp_path)][0] == second.name   # 后做的排在前面


def test_req023_restore_right_after_backup_in_same_second(conn, tmp_path):
    path = backup_database(conn, tmp_path, T1)
    UserService(UserRepo(conn)).add("guard1", "123456", ROLE_GUARD)
    safety = restore_database(conn, path, tmp_path, T1)
    assert safety.name == "parking_20261117_093005_2.db"
    assert usernames(conn) == ["admin"]


def test_req023_list_backups_missing_dir_is_empty(tmp_path):
    assert list_backups(tmp_path / "none") == []


# ---------- 验收 2：从备份还原 ----------

def test_req023_restore_brings_back_old_data(conn, tmp_path):
    path = backup_database(conn, tmp_path, T1)              # 备份时只有 admin
    UserService(UserRepo(conn)).add("guard1", "123456", ROLE_GUARD)
    assert usernames(conn) == ["admin", "guard1"]
    restore_database(conn, path, tmp_path, T2)
    assert usernames(conn) == ["admin"]


def test_req023_restore_makes_safety_backup_of_current_data(conn, tmp_path):
    path = backup_database(conn, tmp_path, T1)
    UserService(UserRepo(conn)).add("guard1", "123456", ROLE_GUARD)
    safety = restore_database(conn, path, tmp_path, T2)
    assert safety.name == "parking_20261117_100000.db"
    copy = sqlite3.connect(safety)
    copy.row_factory = sqlite3.Row
    assert [u.username for u in UserRepo(copy).list_all()] == ["admin", "guard1"]   # 还原前的数据还在
    copy.close()


def test_req023_foreign_keys_still_enforced_after_restore(conn, tmp_path):
    path = backup_database(conn, tmp_path, T1)
    restore_database(conn, path, tmp_path, T2)
    assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1


# ---------- 错误的备份文件：拒绝且数据不变 ----------

def test_req023_missing_file_rejected(conn, tmp_path):
    with pytest.raises(ValueError, match="备份文件不存在"):
        restore_database(conn, tmp_path / "nope.db", tmp_path, T3)
    assert list_backups(tmp_path) == []           # 校验失败时不做安全备份


def test_req023_non_sqlite_file_rejected(conn, tmp_path):
    bad = tmp_path / "parking_bad.db"
    bad.write_text("hello", encoding="utf-8")
    with pytest.raises(ValueError, match="不是本系统的备份文件"):
        restore_database(conn, bad, tmp_path / "out", T3)
    assert usernames(conn) == ["admin"]


def test_req023_other_sqlite_db_rejected(conn, tmp_path):
    other = tmp_path / "other.db"
    c = sqlite3.connect(other)
    c.execute("CREATE TABLE users (id INTEGER)")    # 只有 users 一张表，不是本系统的库
    c.commit()
    c.close()
    with pytest.raises(ValueError, match="不是本系统的备份文件"):
        restore_database(conn, other, tmp_path / "out", T3)
    assert usernames(conn) == ["admin"]
    assert list_backups(tmp_path / "out") == []
