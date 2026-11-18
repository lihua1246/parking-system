"""REQ-002 修改自己的密码（Issue #3）。

验收条件（docs/02-需求清单.md REQ-002）：
  1. 需输入旧密码：旧密码错误时拒绝
  2. 新密码少于 6 位时拒绝
  3. 修改后旧密码不能再登录（新密码可以）
"""
import pytest

from app.repository.db import get_connection, init_db
from app.repository.user_repo import UserRepo
from app.services.auth import authenticate, change_password, ensure_default_admin


@pytest.fixture
def repo():
    conn = get_connection(":memory:")
    init_db(conn)
    r = UserRepo(conn)
    ensure_default_admin(r)
    yield r
    conn.close()


@pytest.fixture
def admin_id(repo):
    return repo.get_by_username("admin").id


# ---------- 验收 1：需输入正确的旧密码 ----------

def test_req002_wrong_old_password_rejected(repo, admin_id):
    with pytest.raises(ValueError, match="旧密码不正确"):
        change_password(repo, admin_id, "wrong123", "newpass1")
    # 拒绝后密码没变
    assert authenticate(repo, "admin", "admin123") is not None
    assert authenticate(repo, "admin", "newpass1") is None


def test_req002_empty_old_password_rejected(repo, admin_id):
    with pytest.raises(ValueError, match="旧密码不正确"):
        change_password(repo, admin_id, "", "newpass1")


# ---------- 验收 2：新密码少于 6 位时拒绝 ----------

@pytest.mark.parametrize("short", ["", "a", "12345"])
def test_req002_new_password_shorter_than_6_rejected(repo, admin_id, short):
    with pytest.raises(ValueError, match="新密码不能少于 6 位"):
        change_password(repo, admin_id, "admin123", short)
    assert authenticate(repo, "admin", "admin123") is not None


def test_req002_new_password_exactly_6_accepted(repo, admin_id):
    change_password(repo, admin_id, "admin123", "123456")
    assert authenticate(repo, "admin", "123456") is not None


# ---------- 验收 3：修改后旧密码不能再登录 ----------

def test_req002_old_password_cannot_login_after_change(repo, admin_id):
    change_password(repo, admin_id, "admin123", "newpass1")
    assert authenticate(repo, "admin", "admin123") is None
    assert authenticate(repo, "admin", "newpass1") is not None


def test_req002_new_password_stored_as_hash(repo, admin_id):
    change_password(repo, admin_id, "admin123", "newpass1")
    stored = repo.get(admin_id).password_hash
    assert "newpass1" not in stored


def test_req002_unknown_user_rejected(repo):
    with pytest.raises(ValueError, match="用户不存在"):
        change_password(repo, 999, "admin123", "newpass1")
