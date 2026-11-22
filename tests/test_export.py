"""REQ-019 导出测试（负责人 E）。

验收条件：导出的 Excel 行数与传入数据一致（不加合计行），收入按整数写入。
用与 test_stats.py 同样风格的 3 条记录：1 条未出场，车辆类型覆盖三种。
"""
from datetime import date, datetime

from openpyxl import load_workbook

from app.models.entities import (
    ParkingRecord,
    VEHICLE_MONTHLY,
    VEHICLE_TEMP,
    VEHICLE_VISITOR,
)
from app.services.export import export_income, export_records

HEADERS = ["车牌", "车辆类型", "入场时间", "出场时间", "费用（元）", "入场操作员"]


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
    return [
        _record(1, "豫A00001", VEHICLE_TEMP,
                datetime(2026, 11, 16, 8, 0), datetime(2026, 11, 16, 10, 0), 3),
        _record(2, "豫A00002", VEHICLE_VISITOR,
                datetime(2026, 11, 16, 9, 0), datetime(2026, 11, 16, 12, 0), 9),
        _record(3, "豫A00003", VEHICLE_MONTHLY,
                datetime(2026, 11, 16, 18, 0), None, None),
    ]


def test_export_records_row_count_equals_record_count(tmp_path):
    """3 条记录 -> 表头 1 行 + 数据 3 行，返回值是数据行数。"""
    path = tmp_path / "records.xlsx"

    rows = export_records(_records(), path)

    sheet = load_workbook(path).active
    assert rows == 3
    assert sheet.max_row == 4


def test_export_records_writes_expected_header(tmp_path):
    path = tmp_path / "records.xlsx"

    export_records(_records(), path)

    sheet = load_workbook(path).active
    assert [cell.value for cell in sheet[1]] == HEADERS


def test_export_records_translates_vehicle_type_and_marks_missing_exit(tmp_path):
    """车辆类型要翻成中文；未出场的记录写“未出场”，费用留空。"""
    path = tmp_path / "records.xlsx"

    export_records(_records(), path)

    sheet = load_workbook(path).active
    assert [sheet.cell(row=2, column=2).value,
            sheet.cell(row=3, column=2).value,
            sheet.cell(row=4, column=2).value] == ["临时车", "访客车", "月租车"]
    assert sheet.cell(row=4, column=4).value == "未出场"
    assert sheet.cell(row=4, column=5).value in (None, "")


def test_export_records_keeps_enter_time_format(tmp_path):
    path = tmp_path / "records.xlsx"

    export_records(_records(), path)

    sheet = load_workbook(path).active
    assert sheet.cell(row=2, column=3).value == "2026-11-16 08:00"


def test_export_empty_records_only_writes_header(tmp_path):
    path = tmp_path / "empty.xlsx"

    rows = export_records([], path)

    sheet = load_workbook(path).active
    assert rows == 0
    assert sheet.max_row == 1


def test_export_income_one_row_per_day(tmp_path):
    """收入汇总：每天一行，行数与字典长度一致。"""
    path = tmp_path / "income.xlsx"
    income = {date(2026, 11, 16): 12, date(2026, 11, 17): 9}

    rows = export_income(income, path)

    sheet = load_workbook(path).active
    assert rows == 2
    assert sheet.max_row == 3
    assert [cell.value for cell in sheet[1]] == ["日期", "收入（元）"]
    assert [sheet.cell(row=2, column=1).value, sheet.cell(row=2, column=2).value] == ["2026-11-16", 12]


def test_export_income_sorts_days_and_keeps_integers(tmp_path):
    """日期按升序排列；金额写成整数，不是浮点。"""
    path = tmp_path / "income.xlsx"
    income = {date(2026, 11, 18): 15, date(2026, 11, 16): 12}

    export_income(income, path)

    sheet = load_workbook(path).active
    days = [sheet.cell(row=row, column=1).value for row in (2, 3)]
    amounts = [sheet.cell(row=row, column=2).value for row in (2, 3)]
    assert days == ["2026-11-16", "2026-11-18"]
    assert amounts == [12, 15]
    assert all(isinstance(amount, int) for amount in amounts)


def test_export_income_empty_dict_only_writes_header(tmp_path):
    path = tmp_path / "empty_income.xlsx"

    rows = export_income({}, path)

    sheet = load_workbook(path).active
    assert rows == 0
    assert sheet.max_row == 1
