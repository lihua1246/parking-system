"""REQ-016 至 018 统计函数测试（任务卡 E-1，负责人 E）。

先手工构造 10 条出入记录，跨 2026-11-16 至 11-18 三天，其中 2 条未出场。
手算结果写在本文件的表格里，下面的断言只使用表格中的数字，不从实现反推。

记录（fee 是出场时写入的应收金额，单位：元）：

| #  | 车牌     | 类型    | 入场时间    | 出场时间    | 金额 |
|----|----------|---------|-------------|-------------|------|
| 1  | 豫A00001 | 临时    | 11-16 08:00 | 11-16 10:00 | 3    |
| 2  | 豫A00002 | 临时    | 11-16 09:00 | 11-16 12:00 | 9    |
| 3  | 豫A00003 | 月租    | 11-16 18:00 | 11-17 09:00 | 0    |
| 4  | 豫A00004 | 访客    | 11-16 20:00 | 11-16 22:30 | 3    |
| 5  | 豫A00005 | 临时    | 11-17 07:30 | 11-17 09:45 | 6    |
| 6  | 豫A00006 | 临时    | 11-17 10:00 | 11-18 11:00 | 30   |
| 7  | 豫A00007 | 月租    | 11-17 12:00 | 11-17 14:00 | 0    |
| 8  | 豫A00008 | 访客    | 11-18 08:00 | 11-18 13:00 | 9    |
| 9  | 豫A00009 | 临时    | 11-18 16:00 | 未出场      | —    |
| 10 | 豫A00010 | 临时    | 11-18 19:00 | 未出场      | —    |

手算（入场按 enter_time 的日期统计，出场和收入按 exit_time 的日期统计）：

| 日期  | 入场 | 出场 | 收入 |
|-------|------|------|------|
| 11-16 | 4    | 3    | 15   |
| 11-17 | 3    | 3    | 6    |
| 11-18 | 3    | 2    | 39   |
| 合计  | 10   | 8    | 60   |

- 11-16 入场 4 条（记录 1 至 4）；出场 3 条（记录 1、2、4，记录 3 在 11-17 出场）。
- 11-17 入场 3 条（记录 5 至 7）；出场 3 条（记录 3、5、7）。
- 11-18 入场 3 条（记录 8 至 10）；出场 2 条（记录 6、8）。
- 记录 9、10 未出场，只计入场，不计出场和收入。
- 收入合计 60 元 = 8 条已出场记录金额之和 3+9+0+3+6+30+0+9。
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
from app.services.stats import daily_flow, income_by_day, monthly_flow, utilization

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
HAND_INCOME = {DAY1: 15, DAY2: 6, DAY3: 39}
HAND_TOTAL_IN = 10
HAND_TOTAL_OUT = 8
HAND_TOTAL_INCOME = 60


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
                datetime(2026, 11, 16, 8, 0), datetime(2026, 11, 16, 10, 0), 3),
        _record(2, "豫A00002", VEHICLE_TEMP,
                datetime(2026, 11, 16, 9, 0), datetime(2026, 11, 16, 12, 0), 9),
        _record(3, "豫A00003", VEHICLE_MONTHLY,
                datetime(2026, 11, 16, 18, 0), datetime(2026, 11, 17, 9, 0), 0),
        _record(4, "豫A00004", VEHICLE_VISITOR,
                datetime(2026, 11, 16, 20, 0), datetime(2026, 11, 16, 22, 30), 3),
        _record(5, "豫A00005", VEHICLE_TEMP,
                datetime(2026, 11, 17, 7, 30), datetime(2026, 11, 17, 9, 45), 6),
        _record(6, "豫A00006", VEHICLE_TEMP,
                datetime(2026, 11, 17, 10, 0), datetime(2026, 11, 18, 11, 0), 30),
        _record(7, "豫A00007", VEHICLE_MONTHLY,
                datetime(2026, 11, 17, 12, 0), datetime(2026, 11, 17, 14, 0), 0),
        _record(8, "豫A00008", VEHICLE_VISITOR,
                datetime(2026, 11, 18, 8, 0), datetime(2026, 11, 18, 13, 0), 9),
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


def test_req017_empty_records_give_zero_income():
    income = income_by_day([], YEAR, MONTH)
    assert len(income) == 30
    assert all(value == 0 for value in income.values())


# ---------------- REQ-018 车位利用率 ----------------


def test_req018_utilization_is_four_of_ten():
    spaces = _spaces([SPACE_OCCUPIED] * 4 + [SPACE_RESERVED] * 2 + [SPACE_FREE] * 4)
    assert utilization(spaces) == 0.4


def test_req018_utilization_counts_only_occupied():
    assert utilization(_spaces([SPACE_OCCUPIED, SPACE_RESERVED, SPACE_FREE, SPACE_FREE])) == 0.25
    assert utilization(_spaces([SPACE_FREE, SPACE_FREE, SPACE_FREE])) == 0.0


def test_req018_utilization_of_no_spaces_is_zero():
    assert utilization([]) == 0.0
