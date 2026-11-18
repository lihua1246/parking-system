"""车位管理页面（负责人 C，REQ-006；REQ-007 在后续任务卡中接入）。

查询和保存调用 SpaceRepo，删除走 SpaceService（含占用、预约检查）；不写 SQL、不写业务公式（见 docs/03-架构与接口.md）。
页面接收已构造好的 SpaceRepo，由 main_window.py 构造 SpaceRepo 并传入。
"""
import sqlite3

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox, QFormLayout, QHBoxLayout, QLabel, QLineEdit, QMessageBox,
    QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from app.models.entities import SPACE_FREE, SPACE_OCCUPIED, SPACE_RESERVED, ParkingSpace
from app.repository.space_repo import SpaceRepo
from app.services.space import SpaceService

STATUS_LABELS = {
    SPACE_FREE: "空闲",
    SPACE_OCCUPIED: "占用",
    SPACE_RESERVED: "预约",
}
ALL = "全部"


class SpacePage(QWidget):
    TITLE = "车位管理"

    def __init__(self, space_repo: SpaceRepo | None = None, parent=None):
        super().__init__(parent)
        self.repo = space_repo
        self.service = SpaceService(space_repo) if space_repo is not None else None
        self._current_id: int | None = None
        self._build_ui()
        if self.repo is None:
            self._show_missing_repo()
        else:
            self._reload_zone_filter()
            self.refresh()

    # ---------- 界面 ----------

    def _build_ui(self) -> None:
        self.zone_filter = QComboBox()
        self.status_filter = QComboBox()
        self.status_filter.addItem(ALL, None)
        for value, label in STATUS_LABELS.items():
            self.status_filter.addItem(label, value)

        self.refresh_button = QPushButton("刷新")

        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel("区域："))
        filter_row.addWidget(self.zone_filter)
        filter_row.addWidget(QLabel("状态："))
        filter_row.addWidget(self.status_filter)
        filter_row.addWidget(self.refresh_button)
        filter_row.addStretch(1)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["编号", "区域", "状态", "固定车辆"])
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)

        self.code_edit = QLineEdit()
        self.code_edit.setPlaceholderText("如 A-001")
        self.zone_edit = QLineEdit()
        self.zone_edit.setPlaceholderText("如 A区")
        self.status_edit = QComboBox()
        for value, label in STATUS_LABELS.items():
            self.status_edit.addItem(label, value)

        form = QFormLayout()
        form.addRow("车位编号：", self.code_edit)
        form.addRow("区域：", self.zone_edit)
        form.addRow("状态：", self.status_edit)

        self.add_button = QPushButton("新增")
        self.update_button = QPushButton("保存修改")
        self.delete_button = QPushButton("删除")
        self.clear_button = QPushButton("清空表单")

        button_row = QHBoxLayout()
        for button in (self.add_button, self.update_button,
                       self.delete_button, self.clear_button):
            button_row.addWidget(button)
        button_row.addStretch(1)

        self.status_label = QLabel("")

        layout = QVBoxLayout(self)
        layout.addLayout(filter_row)
        layout.addWidget(self.table, 1)
        layout.addLayout(form)
        layout.addLayout(button_row)
        layout.addWidget(self.status_label)

        self.zone_filter.currentIndexChanged.connect(self.refresh)
        self.status_filter.currentIndexChanged.connect(self.refresh)
        self.refresh_button.clicked.connect(self._on_refresh_clicked)
        self.table.itemSelectionChanged.connect(self._fill_form_from_selection)
        self.add_button.clicked.connect(self._on_add)
        self.update_button.clicked.connect(self._on_update)
        self.delete_button.clicked.connect(self._on_delete)
        self.clear_button.clicked.connect(self._clear_form)

    def _show_missing_repo(self) -> None:
        """骨架阶段 main_window 还没有注入 repo：禁用操作，避免程序启动即崩溃。"""
        self.setEnabled(False)
        self.status_label.setText(
            "数据源未接入：等待组长在 main_window.py 中改为 SpacePage(SpaceRepo(conn))"
        )

    # ---------- 数据 ----------

    def refresh(self, *_args) -> None:
        if self.repo is None:
            return
        zone = self.zone_filter.currentData()
        status = self.status_filter.currentData()
        spaces = self.repo.list_by(zone, status)

        self.table.setRowCount(0)
        for row, space in enumerate(spaces):
            self.table.insertRow(row)
            code_item = QTableWidgetItem(space.code)
            code_item.setData(Qt.UserRole, space.id)
            self.table.setItem(row, 0, code_item)
            self.table.setItem(row, 1, QTableWidgetItem(space.zone))
            self.table.setItem(row, 2, QTableWidgetItem(STATUS_LABELS.get(space.status, space.status)))
            fixed = "—" if space.fixed_vehicle_id is None else f"车辆 {space.fixed_vehicle_id}"
            self.table.setItem(row, 3, QTableWidgetItem(fixed))

        self.status_label.setText(f"共 {len(spaces)} 个车位")
        self._current_id = None
        self._clear_form()

    def _reload_zone_filter(self) -> None:
        """区域下拉的选项来自现有车位；重建时屏蔽信号，避免触发多次刷新。"""
        if self.repo is None:
            return
        previous = self.zone_filter.currentData()
        zones = sorted({space.zone for space in self.repo.list_all()})

        self.zone_filter.blockSignals(True)
        self.zone_filter.clear()
        self.zone_filter.addItem(ALL, None)
        for zone in zones:
            self.zone_filter.addItem(zone, zone)
        index = self.zone_filter.findData(previous)
        self.zone_filter.setCurrentIndex(index if index >= 0 else 0)
        self.zone_filter.blockSignals(False)

    # ---------- 表单与操作 ----------

    def _selected_id(self) -> int | None:
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        return None if item is None else item.data(Qt.UserRole)

    def _fill_form_from_selection(self) -> None:
        space_id = self._selected_id()
        if space_id is None or self.repo is None:
            return
        space = self.repo.get(space_id)
        if space is None:
            return
        self._current_id = space.id
        self.code_edit.setText(space.code)
        self.zone_edit.setText(space.zone)
        self.status_edit.setCurrentIndex(self.status_edit.findData(space.status))

    def _clear_form(self) -> None:
        self._current_id = None
        self.code_edit.clear()
        self.zone_edit.clear()
        self.status_edit.setCurrentIndex(0)

    def _form_space(self) -> ParkingSpace | None:
        code = self.code_edit.text().strip()
        zone = self.zone_edit.text().strip()
        if not code or not zone:
            QMessageBox.warning(self, "提示", "车位编号和区域不能为空")
            return None
        return ParkingSpace(
            id=self._current_id,
            code=code,
            zone=zone,
            status=self.status_edit.currentData(),
            fixed_vehicle_id=None,      # REQ-007 接入前不在这里修改固定车辆
        )

    def _on_refresh_clicked(self) -> None:
        self._reload_zone_filter()
        self.refresh()

    def _on_add(self) -> None:
        space = self._form_space()
        if space is None:
            return
        self._current_id = None
        try:
            self.repo.add(space)
        except sqlite3.IntegrityError:
            QMessageBox.warning(self, "提示", "车位编号已存在")
            return
        self._reset_filters()
        self._reload_zone_filter()
        self.refresh()

    def _reset_filters(self) -> None:
        """新增后回到"全部"，否则车位可能被当前筛选条件挡住，看起来像没保存。"""
        for combo in (self.zone_filter, self.status_filter):
            combo.blockSignals(True)
            combo.setCurrentIndex(0)
            combo.blockSignals(False)

    def _on_update(self) -> None:
        if self._current_id is None:
            QMessageBox.warning(self, "提示", "请先在列表中选择一个车位")
            return
        space = self._form_space()
        if space is None:
            return
        # 保留原有固定车辆绑定，避免 REQ-006 的修改把 REQ-007 的数据抹掉
        existing = self.repo.get(self._current_id)
        if existing is not None:
            space.fixed_vehicle_id = existing.fixed_vehicle_id
        try:
            self.repo.update(space)
        except sqlite3.IntegrityError:
            QMessageBox.warning(self, "提示", "车位编号已存在")
            return
        self._reload_zone_filter()
        self.refresh()

    def _on_delete(self) -> None:
        if self._current_id is None:
            QMessageBox.warning(self, "提示", "请先在列表中选择一个车位")
            return
        code = self.code_edit.text().strip() or str(self._current_id)
        answer = QMessageBox.question(
            self, "确认删除", f"确定删除车位 {code} 吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        # 能否删除由 SpaceService 判断，页面只负责显示结果
        try:
            self.service.delete(self._current_id)
        except ValueError as exc:
            QMessageBox.warning(self, "提示", str(exc))
            self.refresh()
            return
        self._reload_zone_filter()
        self.refresh()
