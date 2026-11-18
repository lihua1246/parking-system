"""REQ-001 用户登录（任务卡 A-1，Issue #2）。

验收条件（docs/05-分工与任务卡.md 任务卡 A-1）：
  1. 默认账号 admin / admin123 可以登录
  2. 密码错误时停留在登录窗口并显示提示
     —— 界面部分手工截图；这里测的是校验函数返回 None，窗口据此显示"用户名或密码错误"
  3. 数据库 users 表中查不到明文 "admin123"
  4. 同一密码两次哈希的结果不同，但都能验证通过
"""
import sqlite3

import pytest

from app.models.entities import ROLE_ADMIN, ROLE_GUARD, User
from app.repository.db import get_connection, init_db
from app.repository.user_repo import UserRepo
from app.services.auth import (
    authenticate, ensure_default_admin, hash_password, verify_password,
)


@pytest.fixture
def repo():
    conn = get_connection(":memory:")
    init_db(conn)
    r = UserRepo(conn)
    ensure_default_admin(r)
    yield r
    conn.close()


# ---------- 验收 1：默认账号可以登录 ----------

def test_req001_default_admin_can_login(repo):
    user = authenticate(repo, "admin", "admin123")
    assert user is not None
    assert user.username == "admin"
    assert user.role == ROLE_ADMIN


# ---------- 验收 2：登录失败返回 None，且两种失败无法区分 ----------

def test_req001_wrong_password_fails(repo):
    assert authenticate(repo, "admin", "admin124") is None


def test_req001_unknown_username_fails(repo):
    assert authenticate(repo, "nobody", "admin123") is None


def test_req001_password_is_case_sensitive(repo):
    assert authenticate(repo, "admin", "ADMIN123") is None


# ---------- 验收 3：数据库里没有明文密码 ----------

def test_req001_no_plaintext_password_in_users_table(repo):
    rows = repo.conn.execute("SELECT * FROM users").fetchall()
    assert len(rows) == 1
    for row in rows:
        for value in tuple(row):
            assert "admin123" not in str(value)


# ---------- 验收 4：同一密码两次哈希不同，都能验证 ----------

def test_req001_same_password_hashes_differ_but_both_verify():
    h1 = hash_password("admin123")
    h2 = hash_password("admin123")
    assert h1 != h2
    assert verify_password("admin123", h1)
    assert verify_password("admin123", h2)


def test_req001_verify_rejects_wrong_password():
    h = hash_password("admin123")
    assert not verify_password("admin12", h)
    assert not verify_password("", h)


@pytest.mark.parametrize("bad_hash", ["", "admin123", "pbkdf2_sha256$abc$00$00", "md5$1$00$00"])
def test_req001_verify_malformed_hash_returns_false(bad_hash):
    assert verify_password("admin123", bad_hash) is False


# ---------- 默认管理员的写入规则 ----------

def test_req001_default_admin_written_once(repo):
    ensure_default_admin(repo)          # 模拟第二次启动程序
    assert [u.username for u in repo.list_all()] == ["admin"]


def test_req001_default_admin_not_reset_after_password_change(repo):
    admin = repo.get_by_username("admin")
    admin.password_hash = hash_password("newpass1")
    repo.update(admin)
    ensure_default_admin(repo)          # 重启后不能把密码改回 admin123
    assert authenticate(repo, "admin", "admin123") is None
    assert authenticate(repo, "admin", "newpass1") is not None


# ---------- UserRepo 读写 ----------

def test_user_repo_add_get_list(repo):
    new_id = repo.add(User(id=None, username="guard1", password_hash=hash_password("123456"), role=ROLE_GUARD))
    got = repo.get(new_id)
    assert got.username == "guard1" and got.role == ROLE_GUARD and got.id == new_id
    assert [u.username for u in repo.list_all()] == ["admin", "guard1"]


def test_user_repo_get_missing_returns_none(repo):
    assert repo.get(999) is None
    assert repo.get_by_username("nobody") is None


def test_user_repo_duplicate_username_rejected(repo):
    with pytest.raises(sqlite3.IntegrityError):
        repo.add(User(id=None, username="admin", password_hash="x", role=ROLE_GUARD))


def test_user_repo_update_and_delete(repo):
    uid = repo.add(User(id=None, username="guard1", password_hash="x", role=ROLE_GUARD))
    user = repo.get(uid)
    user.role = ROLE_ADMIN
    repo.update(user)
    assert repo.get(uid).role == ROLE_ADMIN
    repo.delete(uid)
    assert repo.get(uid) is None
