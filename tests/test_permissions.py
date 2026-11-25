"""REQ-020 角色权限（Issue #21）。

验收条件（docs/02-需求清单.md REQ-020）：
  门卫登录后看不到住户管理、车辆管理、车位管理、收费规则、用户管理的修改入口。
决策（ADR-007）：整页隐藏；权限用白名单；门卫也不能用数据备份。
界面部分（侧边栏不出现这些页面）手工截图，这里测 can_access 的判断。
"""
import pytest

from app.models.entities import ROLE_ADMIN, ROLE_GUARD
from app.services.auth import (
    ALL_FEATURES, FEATURE_BACKUP, FEATURE_FEE_RULE, FEATURE_GATE,
    FEATURE_RECORD, FEATURE_RESERVATION, FEATURE_RESIDENT, FEATURE_SPACE, FEATURE_STATS,
    FEATURE_USER, FEATURE_VEHICLE, can_access,
)

GUARD_DENIED = [FEATURE_RESIDENT, FEATURE_VEHICLE, FEATURE_SPACE, FEATURE_FEE_RULE, FEATURE_USER]
GUARD_ALLOWED = [FEATURE_GATE, FEATURE_RECORD, FEATURE_RESERVATION, FEATURE_STATS]


@pytest.mark.parametrize("feature", GUARD_DENIED)
def test_req020_guard_cannot_access_management_pages(feature):
    assert can_access(ROLE_GUARD, feature) is False


def test_req020_guard_cannot_access_backup():
    assert can_access(ROLE_GUARD, FEATURE_BACKUP) is False


@pytest.mark.parametrize("feature", GUARD_ALLOWED)
def test_req020_guard_can_access_daily_pages(feature):
    assert can_access(ROLE_GUARD, feature) is True


def test_req020_admin_can_access_all_10_features():
    assert len(ALL_FEATURES) == 10
    for feature in ALL_FEATURES:
        assert can_access(ROLE_ADMIN, feature) is True


def test_req020_unknown_feature_denied_for_everyone():
    # 白名单：没登记的功能谁都不能用，以后新增页面忘了登记也不会对门卫开放
    assert can_access(ROLE_ADMIN, "new_page") is False
    assert can_access(ROLE_GUARD, "new_page") is False


@pytest.mark.parametrize("role", ["", "superuser", "Admin"])
def test_req020_unknown_role_denied(role):
    assert can_access(role, FEATURE_GATE) is False
