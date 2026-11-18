"""REQ-021 用户管理（Issue #22）。

验收条件（docs/02-需求清单.md REQ-021）：
  1. 管理员可新增用户并指定角色
  2. 管理员可删除用户
  3. 不能删除自己
  4. 系统至少保留一名管理员
另加：用户名必填且唯一、角色只能是 admin / guard、初始密码不少于 6 位、只存哈希。
"""
import pytest

from app.models.entities import ROLE_ADMIN, ROLE_GUARD
from app.repository.db import get_connection, init_db
from app.repository.user_repo import UserRepo
from app.services.auth import authenticate, ensure_default_admin
from app.services.user import UserService


@pytest.fixture
def repo():
    conn = get_connection(":memory:")
    init_db(conn)
    r = UserRepo(conn)
    ensure_default_admin(r)
    yield r
    conn.close()


@pytest.fixture
def service(repo):
    return UserService(repo)


@pytest.fixture
def admin_id(repo):
    return repo.get_by_username("admin").id


# ---------- 验收 1：新增用户并指定角色 ----------

def test_req021_add_guard_can_login_with_role(service, repo):
    new_id = service.add("guard1", "123456", ROLE_GUARD)
    user = authenticate(repo, "guard1", "123456")
    assert user is not None and user.id == new_id and user.role == ROLE_GUARD


def test_req021_add_admin(service, repo):
    service.add("admin2", "123456", ROLE_ADMIN)
    assert repo.get_by_username("admin2").role == ROLE_ADMIN


def test_req021_password_stored_as_hash(service, repo):
    service.add("guard1", "secret99", ROLE_GUARD)
    assert "secret99" not in repo.get_by_username("guard1").password_hash


def test_req021_username_is_stripped(service, repo):
    service.add("  guard1  ", "123456", ROLE_GUARD)
    assert repo.get_by_username("guard1") is not None


def test_req021_duplicate_username_rejected(service, repo):
    with pytest.raises(ValueError, match="用户名已存在"):
        service.add("admin", "123456", ROLE_GUARD)
    assert len(repo.list_all()) == 1


@pytest.mark.parametrize("name", ["", "   "])
def test_req021_empty_username_rejected(service, name):
    with pytest.raises(ValueError, match="用户名不能为空"):
        service.add(name, "123456", ROLE_GUARD)


def test_req021_invalid_role_rejected(service):
    with pytest.raises(ValueError, match="角色只能是管理员或门卫"):
        service.add("boss", "123456", "superuser")


def test_req021_short_password_rejected(service, repo):
    with pytest.raises(ValueError, match="密码不能少于 6 位"):
        service.add("guard1", "12345", ROLE_GUARD)
    assert repo.get_by_username("guard1") is None


# ---------- 验收 2：删除用户 ----------

def test_req021_delete_guard(service, repo, admin_id):
    gid = service.add("guard1", "123456", ROLE_GUARD)
    service.delete(gid, current_user_id=admin_id)
    assert repo.get(gid) is None
    assert authenticate(repo, "guard1", "123456") is None


def test_req021_delete_missing_user_rejected(service, admin_id):
    with pytest.raises(ValueError, match="该用户已不存在"):
        service.delete(999, current_user_id=admin_id)


# ---------- 验收 3：不能删除自己 ----------

def test_req021_cannot_delete_self(service, repo, admin_id):
    service.add("admin2", "123456", ROLE_ADMIN)   # 即使还有别的管理员，也不能删自己
    with pytest.raises(ValueError, match="不能删除当前登录的用户"):
        service.delete(admin_id, current_user_id=admin_id)
    assert repo.get(admin_id) is not None


# ---------- 验收 4：至少保留一名管理员 ----------

def test_req021_cannot_delete_last_admin(service, repo, admin_id):
    # 门卫登录时（REQ-020 之前界面尚未拦截）删除唯一的管理员
    gid = service.add("guard1", "123456", ROLE_GUARD)
    with pytest.raises(ValueError, match="系统至少保留一名管理员"):
        service.delete(admin_id, current_user_id=gid)
    assert repo.get(admin_id) is not None


def test_req021_can_delete_admin_when_another_admin_remains(service, repo, admin_id):
    a2 = service.add("admin2", "123456", ROLE_ADMIN)
    service.delete(a2, current_user_id=admin_id)
    assert [u.username for u in repo.list_all()] == ["admin"]
