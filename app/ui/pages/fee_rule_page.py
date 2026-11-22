"""收费规则页面（负责人 A，REQ-015，任务卡 A-4；原属 D）。

上方表格只读显示全部规则，选中一行后在下方三个输入框中修改，点"保存"。
界面只负责显示和收集输入；不能为负、封顶不小于单价等校验都在 services/fee_rule.py。
谁能看到本页面由 REQ-020 处理（门卫看不到）。
"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFormLayout, QHeaderView, QLabel, QMessageBox, QPushButton, QSpinBox,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from app.models.entities import VEHICLE_TEMP, VEHICLE_VISITOR
from app.services.fee_rule import update_rule

COLUMNS = ["车辆类型", "免费时长（分钟）", "每小时单价（元）", "每 24 小时封顶（元）"]
TYPE_NAMES = {VEHICLE_TEMP: "临时车", VEHICLE_VISITOR: "访客车"}
SPIN_MAX = 99999


class FeeRulePage(QWidget):
    TITLE = "收费规则"

    def __init__(self, fee_rule_repo, parent=None):
        super().__init__(parent)
        self.fee_rule_repo = fee_rule_repo
        self._build_ui()
        self.reload()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        self.table = QTableWidget(0, len(COLUMNS))
        self.table.setHorizontalHeaderLabels(COLUMNS)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.currentCellChanged.connect(self._on_row_changed)
        layout.addWidget(self.table)

        self.selected_label = QLabel("请先在上方表格中选中一条规则")
        layout.addWidget(self.selected_label)

        self.free_spin = QSpinBox()
        self.rate_spin = QSpinBox()
        self.cap_spin = QSpinBox()
        for spin in (self.free_spin, self.rate_spin, self.cap_spin):
            spin.setRange(0, SPIN_MAX)       # 界面先挡住负数；服务层仍会再校验一次
        form = QFormLayout()
        form.addRow("免费时长（分钟）", self.free_spin)
        form.addRow("每小时单价（元）", self.rate_spin)
        form.addRow("每 24 小时封顶（元）", self.cap_spin)
        layout.addLayout(form)

        save_btn = QPushButton("保存")
        save_btn.clicked.connect(self.save)
        layout.addWidget(save_btn)
        layout.addWidget(QLabel("修改只影响之后出场的车辆，已出场记录的金额不变。"))
        layout.addStretch(1)

    def reload(self) -> None:
        rules = self.fee_rule_repo.list_all()
        self.table.setRowCount(len(rules))
        for row, rule in enumerate(rules):
            values = [
                TYPE_NAMES.get(rule.vehicle_type, rule.vehicle_type),
                str(rule.free_minutes), str(rule.hourly_rate), str(rule.daily_cap),
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                if col == 0:
                    item.setData(Qt.UserRole, rule.vehicle_type)   # 显示中文，取值用类型常量
                self.table.setItem(row, col, item)

    def _selected_type(self) -> str | None:
        row = self.table.currentRow()
        if row < 0:
            return None
        return self.table.item(row, 0).data(Qt.UserRole)

    def _on_row_changed(self, row: int, *_) -> None:
        vehicle_type = self._selected_type()
        if vehicle_type is None:
            return
        rule = self.fee_rule_repo.get(vehicle_type)
        self.selected_label.setText(f"正在修改：{TYPE_NAMES.get(vehicle_type, vehicle_type)}")
        self.free_spin.setValue(rule.free_minutes)
        self.rate_spin.setValue(rule.hourly_rate)
        self.cap_spin.setValue(rule.daily_cap)

    def save(self) -> None:
        vehicle_type = self._selected_type()
        if vehicle_type is None:
            QMessageBox.information(self, "收费规则", "请先在表格中选中一条规则")
            return
        try:
            update_rule(
                self.fee_rule_repo, vehicle_type,
                self.free_spin.value(), self.rate_spin.value(), self.cap_spin.value(),
            )
        except ValueError as e:
            QMessageBox.warning(self, "收费规则", str(e))
            return
        row = self.table.currentRow()
        self.reload()
        self.table.selectRow(row)
        QMessageBox.information(self, "收费规则", "已保存，之后出场的车辆按新规则计费")
