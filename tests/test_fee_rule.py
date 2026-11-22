"""REQ-015 收费规则可配置（任务卡 A-4，Issue #16）。

本文件第一部分是 FeeRuleRepo 的读写测试（合并请求 ①），
第二部分是 services/fee_rule.update_rule 的校验测试（合并请求 ②，验收 3、4）。
默认规则取自 docs/02-需求清单.md「计费规则 · 默认参数」：
  临时车 免费 30 分钟、每小时 3 元、每 24 小时封顶 30 元
  访客车 免费 120 分钟、每小时 3 元、每 24 小时封顶 30 元
"""
from datetime import datetime

import pytest

from app.models.entities import (
    FeeRule, ParkingRecord, VEHICLE_MONTHLY, VEHICLE_TEMP, VEHICLE_VISITOR,
)
from app.repository.db import get_connection, init_db
from app.repository.fee_rule_repo import FeeRuleRepo
from app.repository.record_repo import RecordRepo
from app.services.fee_rule import (
    CAP_BELOW_RATE_MSG, NEGATIVE_MSG, NOT_INTEGER_MSG, RULE_NOT_FOUND_MSG, update_rule,
)

DEFAULT_TEMP = FeeRule(VEHICLE_TEMP, 30, 3, 30)


@pytest.fixture
def conn():
    c = get_connection(":memory:")
    init_db(c)
    yield c
    c.close()


@pytest.fixture
def repo(conn):
    return FeeRuleRepo(conn)


# ---------- FeeRuleRepo：读取默认规则 ----------

def test_req015_get_default_temp_rule(repo):
    assert repo.get(VEHICLE_TEMP) == FeeRule(VEHICLE_TEMP, 30, 3, 30)


def test_req015_get_default_visitor_rule(repo):
    assert repo.get(VEHICLE_VISITOR) == FeeRule(VEHICLE_VISITOR, 120, 3, 30)


def test_req015_get_monthly_returns_none(repo):
    assert repo.get(VEHICLE_MONTHLY) is None      # 月租车没有收费规则


def test_req015_list_all_returns_both_rules(repo):
    assert {r.vehicle_type for r in repo.list_all()} == {VEHICLE_TEMP, VEHICLE_VISITOR}


# ---------- 验收 1：修改后读出新值，另一条规则不受影响 ----------

def test_req015_update_temp_rule_then_get_new_values(repo):
    repo.update(FeeRule(VEHICLE_TEMP, 15, 5, 40))
    assert repo.get(VEHICLE_TEMP) == FeeRule(VEHICLE_TEMP, 15, 5, 40)
    assert repo.get(VEHICLE_VISITOR) == FeeRule(VEHICLE_VISITOR, 120, 3, 30)


def test_req015_update_survives_reinit(conn, repo):
    repo.update(FeeRule(VEHICLE_TEMP, 15, 5, 40))
    init_db(conn)                                 # 模拟重启程序，INSERT OR IGNORE 不覆盖
    assert repo.get(VEHICLE_TEMP) == FeeRule(VEHICLE_TEMP, 15, 5, 40)


def test_req015_update_unknown_type_changes_nothing(repo):
    repo.update(FeeRule(VEHICLE_MONTHLY, 0, 0, 0))
    assert repo.get(VEHICLE_MONTHLY) is None
    assert len(repo.list_all()) == 2


# ---------- 验收 2：已出场记录的金额不变 ----------

def test_req015_exited_record_fee_unchanged_after_rule_update(conn, repo):
    records = RecordRepo(conn)
    record_id = records.add(ParkingRecord(
        id=None, plate="豫A12345", vehicle_type=VEHICLE_TEMP,
        enter_time=datetime(2026, 11, 16, 8, 0), exit_time=datetime(2026, 11, 16, 13, 0),
        fee=15, space_id=None, operator="admin",
    ))
    repo.update(FeeRule(VEHICLE_TEMP, 0, 10, 100))
    assert records.get(record_id).fee == 15


# ---------- update_rule：合规的修改被保存 ----------

def test_req015_update_rule_saves_valid_values(repo):
    update_rule(repo, VEHICLE_TEMP, 15, 5, 40)
    assert repo.get(VEHICLE_TEMP) == FeeRule(VEHICLE_TEMP, 15, 5, 40)


def test_req015_update_rule_cap_equal_to_rate_accepted(repo):
    update_rule(repo, VEHICLE_TEMP, 30, 5, 5)          # 验收 3：封顶等于单价时接受
    assert repo.get(VEHICLE_TEMP) == FeeRule(VEHICLE_TEMP, 30, 5, 5)


def test_req015_update_rule_all_zero_accepted(repo):
    update_rule(repo, VEHICLE_VISITOR, 0, 0, 0)        # 不为负数即可，0 表示免费
    assert repo.get(VEHICLE_VISITOR) == FeeRule(VEHICLE_VISITOR, 0, 0, 0)


# ---------- 验收 3：不合规时拒绝，数据库不变 ----------

@pytest.mark.parametrize("free_minutes, hourly_rate, daily_cap", [
    (-1, 3, 30),     # 免费时长为负
    (30, -1, 30),    # 单价为负
    (30, 3, -1),     # 封顶为负
])
def test_req015_update_rule_negative_rejected(repo, free_minutes, hourly_rate, daily_cap):
    with pytest.raises(ValueError, match=NEGATIVE_MSG):
        update_rule(repo, VEHICLE_TEMP, free_minutes, hourly_rate, daily_cap)
    assert repo.get(VEHICLE_TEMP) == DEFAULT_TEMP


def test_req015_update_rule_cap_below_rate_rejected(repo):
    with pytest.raises(ValueError, match=CAP_BELOW_RATE_MSG):
        update_rule(repo, VEHICLE_TEMP, 30, 5, 4)
    assert repo.get(VEHICLE_TEMP) == DEFAULT_TEMP


@pytest.mark.parametrize("hourly_rate", [3.5, "3", True])
def test_req015_update_rule_non_integer_rejected(repo, hourly_rate):
    with pytest.raises(ValueError, match=NOT_INTEGER_MSG):
        update_rule(repo, VEHICLE_TEMP, 30, hourly_rate, 30)
    assert repo.get(VEHICLE_TEMP) == DEFAULT_TEMP


# ---------- 验收 4：车辆类型不存在时拒绝 ----------

@pytest.mark.parametrize("vehicle_type", [VEHICLE_MONTHLY, "truck"])
def test_req015_update_rule_unknown_type_rejected(repo, vehicle_type):
    with pytest.raises(ValueError, match=RULE_NOT_FOUND_MSG):
        update_rule(repo, vehicle_type, 30, 3, 30)
    assert len(repo.list_all()) == 2
