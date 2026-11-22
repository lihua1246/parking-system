"""REQ-012 至 014 计费（任务卡 A-5，原属 D）。

预期值全部取自 docs/02-需求清单.md「计费规则 · 验收示例」1 至 10 和「异常输入」，
默认参数：临时车 30 分钟/3 元/30 元，访客车 120 分钟/3 元/30 元。
"""
from datetime import date, datetime, timedelta

import pytest

from app.models.entities import FeeRule, VEHICLE_MONTHLY, VEHICLE_TEMP, VEHICLE_VISITOR
from app.services.billing import (
    FeePolicy, HourlyFeePolicy, MonthlyFeePolicy, make_policy, parked_minutes,
)

TEMP_RULE = FeeRule(VEHICLE_TEMP, 30, 3, 30)
VISITOR_RULE = FeeRule(VEHICLE_VISITOR, 120, 3, 30)
RULES = {VEHICLE_TEMP: TEMP_RULE, VEHICLE_VISITOR: VISITOR_RULE}
ENTER = datetime(2026, 11, 20, 8, 0)


def fee(vehicle_type, duration, expire=None, enter=ENTER):
    return make_policy(vehicle_type, expire, RULES).calc(enter, enter + duration)


# ---------- REQ-012 临时车：示例 1 至 6 ----------

@pytest.mark.parametrize("duration, expected", [
    (timedelta(minutes=29), 0),              # 示例 1：未超过免费时长
    (timedelta(minutes=30), 0),              # 示例 2：恰好等于免费时长，仍免费
    (timedelta(minutes=31), 3),              # 示例 3：按全部时长，不足 1 小时按 1 小时
    (timedelta(hours=2, minutes=15), 9),     # 示例 4：按 3 小时计
    (timedelta(hours=12), 30),               # 示例 5：36 元封顶 30
    (timedelta(hours=26), 36),               # 示例 6：第一周期 30 + 第二周期 2 小时 6 元
])
def test_req012_temp_examples(duration, expected):
    assert fee(VEHICLE_TEMP, duration) == expected


def test_req012_seconds_are_dropped():
    assert fee(VEHICLE_TEMP, timedelta(minutes=30, seconds=59)) == 0   # 算法第 1 条


def test_req012_exactly_24_hours_is_one_capped_period():
    assert fee(VEHICLE_TEMP, timedelta(hours=24)) == 30


# ---------- REQ-013 月租车：示例 7、8 ----------

def test_req013_monthly_within_validity_is_free():
    enter = datetime(2026, 11, 20, 8, 0)          # 示例 7：到期日 11-30，11-20 出场
    assert fee(VEHICLE_MONTHLY, timedelta(hours=5), date(2026, 11, 30), enter) == 0


def test_req013_monthly_expired_charged_as_temp():
    enter = datetime(2026, 12, 1, 8, 0)           # 示例 8：到期日 11-30，12-01 出场
    assert fee(VEHICLE_MONTHLY, timedelta(hours=5), date(2026, 11, 30), enter) == 15


def test_req013_monthly_exit_on_expire_day_is_free():
    enter = datetime(2026, 11, 30, 8, 0)          # 「出场日期晚于到期日」才收费，当天仍免费
    assert fee(VEHICLE_MONTHLY, timedelta(hours=5), date(2026, 11, 30), enter) == 0


def test_req013_monthly_without_expire_charged_as_temp():
    assert fee(VEHICLE_MONTHLY, timedelta(hours=5), None) == 15


# ---------- REQ-014 访客车：示例 9、10 ----------

@pytest.mark.parametrize("duration, expected", [
    (timedelta(hours=2), 0),                 # 示例 9：恰好等于免费时长
    (timedelta(hours=2, minutes=1), 9),      # 示例 10：按 3 小时计
])
def test_req014_visitor_examples(duration, expected):
    assert fee(VEHICLE_VISITOR, duration) == expected


# ---------- 异常输入 ----------

@pytest.mark.parametrize("vehicle_type", [VEHICLE_TEMP, VEHICLE_VISITOR, VEHICLE_MONTHLY])
def test_exit_before_enter_rejected(vehicle_type):
    policy = make_policy(vehicle_type, date(2026, 11, 30), RULES)
    with pytest.raises(ValueError, match="出场时间不能早于入场时间"):
        policy.calc(ENTER, ENTER - timedelta(minutes=1))


@pytest.mark.parametrize("vehicle_type", [VEHICLE_TEMP, VEHICLE_VISITOR, VEHICLE_MONTHLY])
def test_exit_equal_enter_is_free(vehicle_type):
    assert make_policy(vehicle_type, date(2026, 11, 30), RULES).calc(ENTER, ENTER) == 0


def test_unknown_vehicle_type_rejected():
    with pytest.raises(ValueError):
        make_policy("truck", None, RULES)


def test_missing_rule_rejected():
    with pytest.raises(ValueError):
        make_policy(VEHICLE_VISITOR, None, {VEHICLE_TEMP: TEMP_RULE})


# ---------- 类设计（docs/03 第五节） ----------

def test_make_policy_returns_expected_classes():
    assert isinstance(make_policy(VEHICLE_TEMP, None, RULES), HourlyFeePolicy)
    monthly = make_policy(VEHICLE_MONTHLY, date(2026, 11, 30), RULES)
    assert isinstance(monthly, MonthlyFeePolicy)
    assert isinstance(monthly.fallback, HourlyFeePolicy)
    assert monthly.fallback.rule == TEMP_RULE     # 过期按临时车规则


def test_fee_policy_is_abstract():
    with pytest.raises(TypeError):
        FeePolicy()


def test_parked_minutes():
    assert parked_minutes(ENTER, ENTER + timedelta(hours=1, seconds=59)) == 60
