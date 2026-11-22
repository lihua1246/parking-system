"""车位预约页面（REQ-022；原属 C，见任务卡 A-5）。

上方表格显示全部预约，下方选择车位、填写车牌和起止时间后点"预约"；选中一行可"取消预约"。
界面只负责显示和收集输入；状态检查、车牌格式、时间冲突都在 services/reservation.py。
页面构造为 ReservationPage(reservation_repo, space_repo)。
"""
from datetime import datetime, timedelta

from PySide6.QtCore import QDateTime, Qt
from PySide6.QtWidgets import (
    QComboBox, QDateTimeEdit, QFormLayout, QHBoxLayout, QHeaderView, QLabel, QLineEdit,
    QMessageBox, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from app.models.entities import SPACE_OCCUPIED
from app.services.reservation import add_reservation, cancel_reservation

COLUMNS = ["车位", "车牌", "开始时间", "结束时间"]
TIME_FORMAT = "%Y-%m-%d %H:%M"


class ReservationPage(QWidget):
    TITLE = "车位预约"

    def __init__(self, reservation_repo=None, space_repo=None, parent=None):
        super().__init__(parent)
        self.reservation_repo = reservation_repo
        self.space_repo = space_repo
        self._build_ui()
        if reservation_repo is None or space_repo is None:
            self.setEnabled(False)
            self.status_label.setText("数据源未接入")
        else:
            self.reload()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        self.table = QTableWidget(0, len(COLUMNS))
        self.table.setHorizontalHeaderLabels(COLUMNS)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.table, 1)

        self.space_combo = QComboBox()
        self.plate_edit = QLineEdit()
        self.plate_edit.setPlaceholderText("如 豫A12345")
        now = QDateTime.currentDateTime()
        self.start_edit = QDateTimeEdit(now)
        self.end_edit = QDateTimeEdit(now.addSecs(2 * 3600))
        for edit in (self.start_edit, self.end_edit):
            edit.setDisplayFormat("yyyy-MM-dd HH:mm")
            edit.setCalendarPopup(True)

        form = QFormLayout()
        form.addRow("车位（不含占用中的车位）", self.space_combo)
        form.addRow("车牌", self.plate_edit)
        form.addRow("开始时间", self.start_edit)
        form.addRow("结束时间", self.end_edit)
        layout.addLayout(form)

        add_btn = QPushButton("预约")
        cancel_btn = QPushButton("取消选中的预约")
        add_btn.clicked.connect(self.add)
        cancel_btn.clicked.connect(self.cancel)
        buttons = QHBoxLayout()
        buttons.addWidget(add_btn)
        buttons.addWidget(cancel_btn)
        buttons.addStretch(1)
        layout.addLayout(buttons)

        self.status_label = QLabel("")
        layout.addWidget(self.status_label)

    def reload(self) -> None:
        spaces = self.space_repo.list_all()
        codes = {s.id: s.code for s in spaces}

        self.space_combo.clear()
        for space in spaces:
            if space.status != SPACE_OCCUPIED:
                self.space_combo.addItem(f"{space.code}（{space.zone}）", space.id)

        reservations = self.reservation_repo.list_all()
        self.table.setRowCount(len(reservations))
        for row, r in enumerate(reservations):
            values = [codes.get(r.space_id, str(r.space_id)), r.plate,
                      r.start_time.strftime(TIME_FORMAT), r.end_time.strftime(TIME_FORMAT)]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                if col == 0:
                    item.setData(Qt.UserRole, r.id)
                self.table.setItem(row, col, item)
        self.status_label.setText(f"共 {len(reservations)} 条预约")

    @staticmethod
    def _to_datetime(edit: QDateTimeEdit) -> datetime:
        """取到分钟，秒清零，避免同一分钟内的首尾相接被误判为重叠。"""
        value = edit.dateTime().toPython()
        return value.replace(second=0, microsecond=0)

    def add(self) -> None:
        space_id = self.space_combo.currentData()
        if space_id is None:
            QMessageBox.information(self, "车位预约", "没有可预约的车位")
            return
        try:
            add_reservation(
                self.reservation_repo, self.space_repo, space_id, self.plate_edit.text(),
                self._to_datetime(self.start_edit), self._to_datetime(self.end_edit),
            )
        except ValueError as e:
            QMessageBox.warning(self, "车位预约", str(e))
            return
        self.plate_edit.clear()
        self.reload()

    def cancel(self) -> None:
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, "车位预约", "请先在表格中选中一条预约")
            return
        rid = self.table.item(row, 0).data(Qt.UserRole)
        desc = f"{self.table.item(row, 0).text()} {self.table.item(row, 1).text()}"
        if QMessageBox.question(self, "车位预约", f"确定取消预约 {desc} 吗？") != QMessageBox.Yes:
            return
        try:
            cancel_reservation(self.reservation_repo, rid)
        except ValueError as e:
            QMessageBox.warning(self, "车位预约", str(e))
        self.reload()
