"""REQ-011：只读查询出入记录；由 A 在主窗口注入 RecordRepo。"""
from datetime import datetime, time, timedelta

from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QAbstractItemView, QCheckBox, QDateEdit, QHBoxLayout, QHeaderView,
    QLabel, QLineEdit, QPushButton, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget,
)

from app.models.entities import VEHICLE_MONTHLY, VEHICLE_TEMP, VEHICLE_VISITOR
from app.repository.record_repo import RecordRepo
from app.ui.pages.gate_page import format_duration


class RecordPage(QWidget):
    TITLE = "出入记录"

    def __init__(self, record_repo: RecordRepo | None = None, parent=None):
        super().__init__(parent)
        self.record_repo = record_repo
        layout = QVBoxLayout(self)

        title = QLabel(self.TITLE)
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        layout.addWidget(title)
        layout.addWidget(QLabel("按入场时间筛选，最新记录在前；记录只读，不提供修改或删除。"))

        plate_row = QHBoxLayout()
        self.plate_input = QLineEdit()
        self.plate_input.setPlaceholderText("车牌或片段，例如：豫A12345、A123；留空表示不限")
        self.search_button = QPushButton("查询")
        self.reset_button = QPushButton("重置条件")
        plate_row.addWidget(self.plate_input, 1)
        plate_row.addWidget(self.search_button)
        plate_row.addWidget(self.reset_button)
        layout.addLayout(plate_row)

        dates_row = QHBoxLayout()
        self.start_enabled = QCheckBox("开始日期")
        self.start_date = QDateEdit(QDate.currentDate())
        self.end_enabled = QCheckBox("结束日期（含当天）")
        self.end_date = QDateEdit(QDate.currentDate())
        # 下一天 00:00 是查询上界，限制结束日期以便转换为有效的 datetime。
        self.end_date.setMaximumDate(QDate(9999, 12, 30))
        for checkbox, editor in (
            (self.start_enabled, self.start_date),
            (self.end_enabled, self.end_date),
        ):
            editor.setCalendarPopup(True)
            editor.setDisplayFormat("yyyy-MM-dd")
            editor.setEnabled(False)
            checkbox.toggled.connect(editor.setEnabled)
            dates_row.addWidget(checkbox)
            dates_row.addWidget(editor)
        dates_row.addStretch()
        layout.addLayout(dates_row)

        self.message = QLabel()
        self.message.setWordWrap(True)
        layout.addWidget(self.message)
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels([
            "车牌", "车辆类型", "入场时间", "出场时间", "停车时长", "费用（元）", "入场操作员",
        ])
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table)

        self.search_button.clicked.connect(self._search)
        self.plate_input.returnPressed.connect(self._search)
        self.reset_button.clicked.connect(self._reset)

        ready = record_repo is not None
        for control in (self.plate_input, self.search_button, self.reset_button,
                        self.start_enabled, self.end_enabled):
            control.setEnabled(ready)
        if ready:
            self._search()
        else:
            self._show_message("出入记录尚未接入，请由组长传入记录仓库。", error=True)

    def _show_message(self, text: str, error: bool = False) -> None:
        self.message.setText(text)
        color = "#b42318" if error else "#067647"
        self.message.setStyleSheet(f"color: {color}; padding: 8px; font-size: 14px;")

    def _search(self) -> None:
        if self.record_repo is None:
            return
        start_day = self.start_date.date().toPython() if self.start_enabled.isChecked() else None
        end_day = self.end_date.date().toPython() if self.end_enabled.isChecked() else None
        if start_day is not None and end_day is not None and start_day > end_day:
            self._show_message("开始日期不能晚于结束日期", error=True)
            return  # 无效日期不能调用仓库，也不覆盖上次成功查询的结果。

        start = datetime.combine(start_day, time.min) if start_day is not None else None
        # 用户选择的结束日期需要完整包含，仓库接口仍保持“含开始、不含结束”。
        end = datetime.combine(end_day + timedelta(days=1), time.min) if end_day is not None else None
        try:
            records = self.record_repo.search(self.plate_input.text(), start, end)
        except NotImplementedError:
            self._show_message("出入记录查询尚未实现，请联系负责人。", error=True)
            return

        self._display_records(records)
        self._show_message(f"共查询到 {len(records)} 条记录（按入场时间倒序）")

    def _display_records(self, records) -> None:
        names = {VEHICLE_TEMP: "临时车", VEHICLE_MONTHLY: "月租车", VEHICLE_VISITOR: "访客车"}
        now = datetime.now()  # 在场时长由页面当前时间计算，仓库查询不依赖当前时间。
        self.table.setRowCount(len(records))
        for row, record in enumerate(records):
            present = record.exit_time is None
            values = (
                record.plate,
                names.get(record.vehicle_type, record.vehicle_type),
                record.enter_time.strftime("%Y-%m-%d %H:%M"),
                "在场" if present else record.exit_time.strftime("%Y-%m-%d %H:%M"),
                format_duration(record.enter_time, now if present else record.exit_time),
                "—" if present or record.fee is None else str(record.fee),
                record.operator,
            )
            for column, value in enumerate(values):
                self.table.setItem(row, column, QTableWidgetItem(value))

    def _reset(self) -> None:
        self.plate_input.clear()
        self.start_enabled.setChecked(False)
        self.end_enabled.setChecked(False)
        self.start_date.setDate(QDate.currentDate())
        self.end_date.setDate(QDate.currentDate())
        self._search()
