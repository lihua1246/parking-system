"""REQ-016 至 018 统计函数测试（任务卡 E-1，负责人 E）。

先手工构造 10 条出入记录，跨 2026-11-16 至 11-18 三天，其中 2 条未出场。
手算结果写在本文件的表格里，下面的断言只使用表格中的数字，不从实现反推。

记录（fee 是出场时写入的应收金额，单位：元）。金额按 docs/02「计费规则」的默认参数计算
（临时车 30 分钟/3 元/30 元，访客车 120 分钟/3 元/30 元，月租车均在有效期内）。
统计函数只对已写入的 fee 求和、不重新计费；金额与计费规则一致，是为了让演示和答辩时前后说得通。
（原表是计费接入前写的，记录 1、4、5、6、8 的金额与规则不符，A-5 收尾时订正，入场数、出场数不变。）

| #  | 车牌     | 类型    | 入场时间    | 出场时间    | 金额 | 计费依据                                   |
|----|----------|---------|-------------|-------------|------|--------------------------------------------|
| 1  | 豫A00001 | 临时    | 11-16 08:00 | 11-16 10:00 | 6    | 2 小时 × 3                                 |
| 2  | 豫A00002 | 临时    | 11-16 09:00 | 11-16 12:00 | 9    | 3 小时 × 3                                 |
| 3  | 豫A00003 | 月租    | 11-16 18:00 | 11-17 09:00 | 0    | 有效期内                                   |
| 4  | 豫A00004 | 访客    | 11-16 20:00 | 11-16 22:30 | 9    | 2 小时 30 分超过免费 120 分钟，按 3 小时 × 3 |
| 5  | 豫A00005 | 临时    | 11-17 07:30 | 11-17 09:45 | 9    | 2 小时 15 分按 3 小时 × 3                  |
| 6  | 豫A00006 | 临时    | 11-17 10:00 | 11-18 11:00 | 33   | 25 小时：第一周期封顶 30 + 第二周期 1 小时 3 |
| 7  | 豫A00007 | 月租    | 11-17 12:00 | 11-17 14:00 | 0    | 有效期内                                   |
| 8  | 豫A00008 | 访客    | 11-18 08:00 | 11-18 13:00 | 15   | 5 小时 × 3                                 |
| 9  | 豫A00009 | 临时    | 11-18 16:00 | 未出场      | —    |                                            |
| 10 | 豫A00010 | 临时    | 11-18 19:00 | 未出场      | —    |                                            |

手算（入场按 enter_time 的日期统计，出场和收入按 exit_time 的日期统计）：

| 日期  | 入场 | 出场 | 收入 |
|-------|------|------|------|
| 11-16 | 4    | 3    | 24   |
| 11-17 | 3    | 3    | 9    |
| 11-18 | 3    | 2    | 48   |
| 合计  | 10   | 8    | 81   |

- 11-16 入场 4 条（记录 1 至 4）；出场 3 条（记录 1、2、4，记录 3 在 11-17 出场）；收入 6+9+9 = 24。
- 11-17 入场 3 条（记录 5 至 7）；出场 3 条（记录 3、5、7）；收入 0+9+0 = 9。
- 11-18 入场 3 条（记录 8 至 10）；出场 2 条（记录 6、8）；收入 33+15 = 48。
- 记录 9、10 未出场，只计入场，不计出场和收入。
- 收入合计 81 元 = 8 条已出场记录金额之和 6+9+0+9+9+33+0+15。
"""
from datetime import date, datetime

import pytest

from app.models.entities import (
    ParkingRecord,
    ParkingSpace,
    SPACE_FREE,
    SPACE_OCCUPIED,
    SPACE_RESERVED,
    VEHICLE_MONTHLY,
    VEHICLE_TEMP,
    VEHICLE_VISITOR,
)
from app.services.stats import (
    daily_flow, income_by_day, month_summary, monthly_flow, utilization,
)

YEAR, MONTH = 2026, 11
DAY1 = date(2026, 11, 16)
DAY2 = date(2026, 11, 17)
DAY3 = date(2026, 11, 18)

# 手算结果（见模块文档字符串中的表格）。
HAND_DAILY_FLOW = {
    DAY1: {"in": 4, "out": 3},
    DAY2: {"in": 3, "out": 3},
    DAY3: {"in": 3, "out": 2},
}
HAND_INCOME = {DAY1: 24, DAY2: 9, DAY3: 48}
HAND_TOTAL_IN = 10
HAND_TOTAL_OUT = 8
HAND_TOTAL_INCOME = 81


def _record(record_id, plate, vehicle_type, enter_time, exit_time, fee):
    return ParkingRecord(
        id=record_id,
        plate=plate,
        vehicle_type=vehicle_type,
        enter_time=enter_time,
        exit_time=exit_time,
        fee=fee,
        space_id=None,
        operator="admin",
    )


def _records():
    """上表中的 10 条记录。"""
    return [
        _record(1, "豫A00001", VEHICLE_TEMP,
                datetime(2026, 11, 16, 8, 0), datetime(2026, 11, 16, 10, 0), 6),
        _record(2, "豫A00002", VEHICLE_TEMP,
                datetime(2026, 11, 16, 9, 0), datetime(2026, 11, 16, 12, 0), 9),
        _record(3, "豫A00003", VEHICLE_MONTHLY,
                datetime(2026, 11, 16, 18, 0), datetime(2026, 11, 17, 9, 0), 0),
        _record(4, "豫A00004", VEHICLE_VISITOR,
                datetime(2026, 11, 16, 20, 0), datetime(2026, 11, 16, 22, 30), 9),
        _record(5, "豫A00005", VEHICLE_TEMP,
                datetime(2026, 11, 17, 7, 30), datetime(2026, 11, 17, 9, 45), 9),
        _record(6, "豫A00006", VEHICLE_TEMP,
                datetime(2026, 11, 17, 10, 0), datetime(2026, 11, 18, 11, 0), 33),
        _record(7, "豫A00007", VEHICLE_MONTHLY,
                datetime(2026, 11, 17, 12, 0), datetime(2026, 11, 17, 14, 0), 0),
        _record(8, "豫A00008", VEHICLE_VISITOR,
                datetime(2026, 11, 18, 8, 0), datetime(2026, 11, 18, 13, 0), 15),
        _record(9, "豫A00009", VEHICLE_TEMP,
                datetime(2026, 11, 18, 16, 0), None, None),
        _record(10, "豫A00010", VEHICLE_TEMP,
                datetime(2026, 11, 18, 19, 0), None, None),
    ]


def _spaces(statuses):
    return [
        ParkingSpace(id=i + 1, code=f"A-{i + 1:03d}", zone="A区",
                     status=status, fixed_vehicle_id=None)
        for i, status in enumerate(statuses)
    ]


# ---------------- REQ-016 车流量 ----------------


@pytest.mark.parametrize("day", [DAY1, DAY2, DAY3], ids=str)
def test_req016_daily_flow_matches_hand_calc(day):
    assert daily_flow(_records(), day) == HAND_DAILY_FLOW[day]


def test_req016_daily_flow_on_day_without_records_is_zero():
    assert daily_flow(_records(), date(2026, 11, 25)) == {"in": 0, "out": 0}


def test_req016_exit_counted_on_exit_date_not_enter_date():
    """记录 3 在 11-16 入场、11-17 出场：11-16 的出场数不含它。"""
    assert daily_flow(_records(), DAY1)["out"] == 3
    assert daily_flow(_records(), DAY2)["out"] == 3


def test_req016_monthly_flow_matches_hand_calc():
    flow = monthly_flow(_records(), YEAR, MONTH)
    # 2026 年 11 月有 30 天，没有数据的日期也要有，值为 0。
    assert len(flow) == 30
    for day in (DAY1, DAY2, DAY3):
        assert flow[day] == HAND_DAILY_FLOW[day]
    assert sum(item["in"] for item in flow.values()) == HAND_TOTAL_IN
    assert sum(item["out"] for item in flow.values()) == HAND_TOTAL_OUT
    assert flow[date(2026, 11, 1)] == {"in": 0, "out": 0}
    assert flow[date(2026, 11, 30)] == {"in": 0, "out": 0}


def test_req016_monthly_flow_ignores_other_months():
    other_month = _record(11, "豫B00011", VEHICLE_TEMP,
                          datetime(2026, 12, 1, 8, 0), datetime(2026, 12, 2, 8, 0), 30)
    flow = monthly_flow(_records() + [other_month], YEAR, MONTH)
    assert sum(item["in"] for item in flow.values()) == HAND_TOTAL_IN
    assert sum(item["out"] for item in flow.values()) == HAND_TOTAL_OUT


def test_req016_empty_records_give_zero_flow():
    assert daily_flow([], DAY1) == {"in": 0, "out": 0}
    flow = monthly_flow([], YEAR, MONTH)
    assert len(flow) == 30
    assert all(item == {"in": 0, "out": 0} for item in flow.values())


# ---------------- REQ-017 收入 ----------------


@pytest.mark.parametrize("day", [DAY1, DAY2, DAY3], ids=str)
def test_req017_income_by_day_matches_hand_calc(day):
    assert income_by_day(_records(), YEAR, MONTH)[day] == HAND_INCOME[day]


def test_req017_three_day_total_equals_sum_of_exited_fees():
    income = income_by_day(_records(), YEAR, MONTH)
    exited_fees = [record.fee for record in _records() if record.exit_time is not None]
    assert len(exited_fees) == 8
    assert sum(income.values()) == HAND_TOTAL_INCOME
    assert sum(exited_fees) == HAND_TOTAL_INCOME


def test_req017_income_fills_whole_month_and_skips_other_months():
    income = income_by_day(_records(), YEAR, MONTH)
    assert len(income) == 30
    assert income[date(2026, 11, 1)] == 0
    assert income[date(2026, 11, 30)] == 0
    other_month = _record(11, "豫B00011", VEHICLE_TEMP,
                          datetime(2026, 12, 1, 8, 0), datetime(2026, 12, 2, 8, 0), 30)
    assert sum(income_by_day([other_month], YEAR, MONTH).values()) == 0


def test_req017_present_record_and_none_fee_do_not_produce_income():
    present = _record(11, "豫A00011", VEHICLE_TEMP, datetime(2026, 11, 18, 20, 0), None, None)
    exited_without_fee = _record(12, "豫A00012", VEHICLE_TEMP,
                                 datetime(2026, 11, 18, 9, 0),
                                 datetime(2026, 11, 18, 10, 0), None)
    assert income_by_day([present], YEAR, MONTH)[DAY3] == 0
    assert income_by_day([exited_without_fee], YEAR, MONTH)[DAY3] == 0


def test_req017_sample_fees_follow_billing_rules():
    """测试数据里的金额与 docs/02 计费规则一致（月租车取有效期内的到期日 11-30）。

    统计函数本身不计费；这条只保证文档表格中的"计费依据"和计费模块说法一致，避免演示时前后矛盾。
    """
    from app.models.entities import FeeRule
    from app.services.billing import make_policy

    rules = {VEHICLE_TEMP: FeeRule(VEHICLE_TEMP, 30, 3, 30),
             VEHICLE_VISITOR: FeeRule(VEHICLE_VISITOR, 120, 3, 30)}
    for record in _records():
        if record.exit_time is None:
            continue
        policy = make_policy(record.vehicle_type, date(2026, 11, 30), rules)
        assert policy.calc(record.enter_time, record.exit_time) == record.fee, record.plate


def test_req017_empty_records_give_zero_income():
    income = income_by_day([], YEAR, MONTH)
    assert len(income) == 30
    assert all(value == 0 for value in income.values())


# ---------------- REQ-018 车位利用率 ----------------


# ---------- E-2：month_summary（审阅意见补充，A-5） ----------

def test_e2_month_summary_matches_hand_calc():
    # E-2 验收 1：与文档表格中手算的合计一致
    assert month_summary(_records(), YEAR, MONTH) == {
        "in": HAND_TOTAL_IN, "out": HAND_TOTAL_OUT, "income": HAND_TOTAL_INCOME,
    }


def test_e2_month_summary_income_equals_sum_of_income_by_day():
    # E-2 验收 2
    records = _records()
    assert month_summary(records, YEAR, MONTH)["income"] == sum(
        income_by_day(records, YEAR, MONTH).values())


def test_e2_month_summary_empty_is_all_zero():
    # E-2 验收 3
    assert month_summary([], YEAR, MONTH) == {"in": 0, "out": 0, "income": 0}


def test_req018_utilization_is_four_of_ten():
    spaces = _spaces([SPACE_OCCUPIED] * 4 + [SPACE_RESERVED] * 2 + [SPACE_FREE] * 4)
    assert utilization(spaces) == 0.4


def test_req018_utilization_counts_only_occupied():
    assert utilization(_spaces([SPACE_OCCUPIED, SPACE_RESERVED, SPACE_FREE, SPACE_FREE])) == 0.25
    assert utilization(_spaces([SPACE_FREE, SPACE_FREE, SPACE_FREE])) == 0.0


def test_req018_utilization_of_no_spaces_is_zero():
    assert utilization([]) == 0.0
