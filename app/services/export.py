"""REQ-019：出入记录与收入汇总导出为 Excel（负责人 E，REQ-019）。

接口签名尚未写入 docs/03 第六节；本文件按下列签名实现，待组长补进文档：

    export_records(records: list[ParkingRecord], path: str | Path) -> int
    export_income(income: dict[date, int], path: str | Path) -> int

返回值是写出的数据行数（不含表头），供界面提示“已导出 N 行”。
导出文件的行数与传入数据一致，不额外加合计行。

本模块是纯函数 + 文件写入：不访问数据库、不导入 PySide6、不写 SQL。
REQ-027（自动生成月报）按组长决定本期不做，因此这里不提供月报函数。
"""
from datetime import date
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Font

from app.models.entities import (
    ParkingRecord,
    VEHICLE_MONTHLY,
    VEHICLE_TEMP,
    VEHICLE_VISITOR,
)

VEHICLE_TYPE_LABELS = {
    VEHICLE_MONTHLY: "月租车",
    VEHICLE_TEMP: "临时车",
    VEHICLE_VISITOR: "访客车",
}

TIME_FORMAT = "%Y-%m-%d %H:%M"


def _new_sheet(title: str, headers: list[str]):
    """建一个工作簿，第一行是表头并加粗。"""
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = title
    sheet.append(headers)
    for cell in sheet[1]:
        cell.font = Font(bold=True)
    sheet.freeze_panes = "A2"
    return workbook, sheet


def _autofit(sheet) -> None:
    """按内容长度粗略调整列宽，避免出现一片 ###。"""
    for column in sheet.columns:
        longest = max(
            (len(str(cell.value)) if cell.value is not None else 0) for cell in column
        )
        letter = column[0].column_letter
        sheet.column_dimensions[letter].width = min(max(longest + 4, 10), 30)


def export_records(records: list[ParkingRecord], path: str | Path) -> int:
    """把出入记录写成 Excel，返回写出的行数（不含表头）。"""
    workbook, sheet = _new_sheet(
        "出入记录",
        ["车牌", "车辆类型", "入场时间", "出场时间", "费用（元）", "入场操作员"],
    )
    for record in records:
        sheet.append([
            record.plate,
            VEHICLE_TYPE_LABELS.get(record.vehicle_type, record.vehicle_type),
            record.enter_time.strftime(TIME_FORMAT),
            record.exit_time.strftime(TIME_FORMAT) if record.exit_time else "未出场",
            record.fee if record.fee is not None else "",
            record.operator,
        ])

    _autofit(sheet)
    workbook.save(Path(path))
    return len(records)


def export_income(income: dict[date, int], path: str | Path) -> int:
    """把按天汇总的收入写成 Excel，返回写出的行数（不含表头）。

    传入的字典是 stats.income_by_day 的返回值：{日期: 金额（元）}。
    金额按整数写入，不用浮点数。
    """
    workbook, sheet = _new_sheet("收入汇总", ["日期", "收入（元）"])
    rows = sorted(income.items())
    for day, amount in rows:
        sheet.append([day.isoformat(), int(amount)])

    _autofit(sheet)
    workbook.save(Path(path))
    return len(rows)
