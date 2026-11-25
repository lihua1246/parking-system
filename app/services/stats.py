"""车流量、收入、利用率（负责人 E，REQ-016 至 018）。

全部是纯函数：只接收数据列表，返回计算结果，不访问数据库。收入按出场日期归属。
"""
import calendar
from datetime import date

from app.models.entities import ParkingRecord, ParkingSpace, SPACE_OCCUPIED


def _days_of_month(year: int, month: int) -> list[date]:
    """该月 1 日至月末的每一天。"""
    _, last_day = calendar.monthrange(year, month)
    return [date(year, month, day) for day in range(1, last_day + 1)]


def daily_flow(records: list[ParkingRecord], day: date) -> dict[str, int]:
    """返回 {"in": 入场数, "out": 出场数}。

    入场数按 enter_time 的日期统计，出场数按 exit_time 的日期统计；
    仍在场的记录（exit_time 为空）只计入场。
    """
    inbound = sum(1 for record in records if record.enter_time.date() == day)
    outbound = sum(
        1 for record in records
        if record.exit_time is not None and record.exit_time.date() == day
    )
    return {"in": inbound, "out": outbound}


def monthly_flow(records: list[ParkingRecord], year: int, month: int) -> dict[date, dict[str, int]]:
    """返回该月每一天的 {"in": 入场数, "out": 出场数}，没有数据的日子为 0。

    键包含该月 1 日至月末的每一天，界面直接按日期画图，不必自己补 0。
    """
    flow = {day: {"in": 0, "out": 0} for day in _days_of_month(year, month)}
    for record in records:
        enter_day = record.enter_time.date()
        if (enter_day.year, enter_day.month) == (year, month):
            flow[enter_day]["in"] += 1
        if record.exit_time is not None:
            exit_day = record.exit_time.date()
            if (exit_day.year, exit_day.month) == (year, month):
                flow[exit_day]["out"] += 1
    return flow


def income_by_day(records: list[ParkingRecord], year: int, month: int) -> dict[date, int]:
    """返回该月每一天的收入（元），没有收入的日子为 0。

    收入按出场日期归属：入场在本月、出场在下个月的记录不计入本月。
    fee 应为整数；尚未写入费用（None）的已出场记录按 0 计。
    """
    income = {day: 0 for day in _days_of_month(year, month)}
    for record in records:
        if record.exit_time is None:
            continue
        exit_day = record.exit_time.date()
        if (exit_day.year, exit_day.month) == (year, month):
            income[exit_day] += record.fee or 0
    return income


def month_summary(records: list[ParkingRecord], year: int, month: int) -> dict[str, int]:
    """该月合计 {"in": 入场数, "out": 出场数, "income": 收入}（任务卡 E-2）。

    由 monthly_flow 和 income_by_day 汇总，与图表同源；界面直接显示，不自己求和。
    """
    flow = monthly_flow(records, year, month)
    return {
        "in": sum(day["in"] for day in flow.values()),
        "out": sum(day["out"] for day in flow.values()),
        "income": sum(income_by_day(records, year, month).values()),
    }


def utilization(spaces: list[ParkingSpace]) -> float:
    """0 到 1；无车位时为 0.0。

    只统计状态为 occupied 的车位，reserved 不算占用。
    固定分配的月租车位会被 SpaceService 置为 occupied，因此计为占用（ADR-006）。
    """
    if not spaces:
        return 0.0
    occupied = sum(1 for space in spaces if space.status == SPACE_OCCUPIED)
    return occupied / len(spaces)
