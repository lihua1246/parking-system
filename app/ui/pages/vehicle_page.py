"""车辆管理页面（负责人 B，REQ-004；任务卡 B-2）。

查询直接走 VehicleRepo；新增/修改/删除走 VehicleService，
因为车牌格式、月租车必填项、车牌唯一这些规则都在服务层。
按住户查询用 ResidentRepo.list_all 填下拉框，再调 VehicleRepo.list_by_resident。

构造：VehiclePage(vehicle_repo, resident_repo)
"""
from datetime import date

from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QComboBox, QDateEdit, QHBoxLayout, QHeaderView, QLineEdit, QMessageBox,
    QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from app.models.entities import (
    VEHICLE_MONTHLY, VEHICLE_TEMP, VEHICLE_TYPES, VEHICLE_VISITOR, Vehicle,
)
from app.repository.resident_repo import ResidentRepo
from app.repository.vehicle_repo import VehicleRepo
from app.services.vehicle import VehicleService

COLUMNS = ["ID", "车牌", "类型", "住户 ID", "到期日", "备注"]
TYPE_LABELS = {VEHICLE_MONTHLY: "月租车", VEHICLE_TEMP: "临时车", VEHICLE_VISITOR: "访客车"}


class VehiclePage(QWidget):
    TITLE = "车辆管理"

    def __init__(self, vehicle_repo: VehicleRepo | None = None,
                 resident_repo: ResidentRepo | None = None, parent=None):
        super().__init__(parent)
        self.repo = vehicle_repo
        self.resident_repo = resident_repo
        self.service = VehicleService(vehicle_repo) if vehicle_repo is not None else None
        self.current_id: int | None = None
        self._build_ui()
        self.reload()

    # ---------- 界面 ----------
    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        self.keyword_edit = QLineEdit()
        self.keyword_edit.setPlaceholderText("按车牌模糊搜索，如 A123")
        search_btn = QPushButton("搜索")
        search_btn.clicked.connect(self.search)
        show_all_btn = QPushButton("显示全部")
        show_all_btn.clicked.connect(self.reload)
        search_row = QHBoxLayout()
        search_row.addWidget(self.keyword_edit)
        search_row.addWidget(search_btn)
        search_row.addWidget(show_all_btn)

        self.resident_filter = QComboBox()
        self.resident_filter.setMinimumContentsLength(10)
        resident_search_btn = QPushButton("按住户查询")
        resident_search_btn.clicked.connect(self.search_by_resident)
        if self.resident_repo is None:
            self.resident_filter.setEnabled(False)
            resident_search_btn.setEnabled(False)
        search_row.addWidget(self.resident_filter)
        search_row.addWidget(resident_search_btn)
        layout.addLayout(search_row)

        self.plate_edit = QLineEdit()
        self.plate_edit.setPlaceholderText("车牌，如 豫A12345")

        self.type_combo = QComboBox()
        for vehicle_type in VEHICLE_TYPES:
            self.type_combo.addItem(TYPE_LABELS[vehicle_type], vehicle_type)
        self.type_combo.currentIndexChanged.connect(self._sync_expire_enabled)

        self.resident_edit = QLineEdit()
        self.resident_edit.setPlaceholderText("住户 ID（临时车可空）")

        self.expire_edit = QDateEdit()
        self.expire_edit.setCalendarPopup(True)
        self.expire_edit.setDisplayFormat("yyyy-MM-dd")
        self.expire_edit.setDate(QDate.currentDate())

        self.note_edit = QLineEdit()
        self.note_edit.setPlaceholderText("备注（可选）")

        form_row = QHBoxLayout()
        for widget in (self.plate_edit, self.type_combo, self.resident_edit,
                       self.expire_edit, self.note_edit):
            form_row.addWidget(widget)
        layout.addLayout(form_row)

        add_btn = QPushButton("新增")
        add_btn.clicked.connect(self.add)
        save_btn = QPushButton("保存修改")
        save_btn.clicked.connect(self.save)
        clear_btn = QPushButton("清空表单")
        clear_btn.clicked.connect(self.clear_form)
        delete_btn = QPushButton("删除选中")
        delete_btn.clicked.connect(self.remove)
        button_row = QHBoxLayout()
        for button in (add_btn, save_btn, clear_btn, delete_btn):
            button_row.addWidget(button)
        layout.addLayout(button_row)

        self.table = QTableWidget(0, len(COLUMNS))
        self.table.setHorizontalHeaderLabels(COLUMNS)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.itemSelectionChanged.connect(self._on_select)
        layout.addWidget(self.table)

        self._sync_expire_enabled()

    def _sync_expire_enabled(self) -> None:
        """只有月租车才需要填到期日，其他类型禁用日期框。"""
        self.expire_edit.setEnabled(self._current_type() == VEHICLE_MONTHLY)

    def _current_type(self) -> str:
        return self.type_combo.currentData()

    # ---------- 数据 ----------
    def reload(self) -> None:
        self._refresh_residents()
        if self.repo is None:
            self.table.setRowCount(0)
            return
        self._fill(self.repo.list_all())

    def showEvent(self, event) -> None:
        """主窗口启动时就构造了本页面，切换过来时再刷新一次住户下拉框。"""
        super().showEvent(event)
        self._refresh_residents()

    def _refresh_residents(self) -> None:
        """重新加载住户下拉框（住户页面可能新增了住户），尽量保留原来的选择。"""
        if self.resident_repo is None:
            return
        previous = self.resident_filter.currentData()
        self.resident_filter.clear()
        for resident in self.resident_repo.list_all():
            self.resident_filter.addItem(
                f"{resident.name}（{resident.building} {resident.room}）", resident.id)
        index = self.resident_filter.findData(previous)
        if index >= 0:
            self.resident_filter.setCurrentIndex(index)

    def search_by_resident(self) -> None:
        """只显示下拉框所选住户名下的车辆。"""
        if self.repo is None or self.resident_repo is None:
            return
        self._refresh_residents()
        resident_id = self.resident_filter.currentData()
        if resident_id is None:
            QMessageBox.information(self, "提示", "还没有住户，请先在住户管理中登记")
            return
        self._fill(self.repo.list_by_resident(resident_id))

    def search(self) -> None:
        if self.repo is None:
            return
        keyword = self.keyword_edit.text().strip()
        if not keyword:
            self.reload()
            return
        self._fill(self.repo.search(keyword))

    def _fill(self, vehicles: list[Vehicle]) -> None:
        self.table.setRowCount(0)
        for vehicle in vehicles:
            row = self.table.rowCount()
            self.table.insertRow(row)
            values = [
                vehicle.id,
                vehicle.plate,
                TYPE_LABELS.get(vehicle.vehicle_type, vehicle.vehicle_type),
                "" if vehicle.resident_id is None else vehicle.resident_id,
                "" if vehicle.monthly_expire is None else vehicle.monthly_expire.isoformat(),
                vehicle.note,
            ]
            for col, value in enumerate(values):
                self.table.setItem(row, col, QTableWidgetItem(str(value)))

    def _on_select(self) -> None:
        # clearSelection() 也会触发 itemSelectionChanged，但 currentRow() 不会被清掉，
        # 没有选中行时直接返回，否则“清空表单”会把刚清的内容回填回去。
        if not self.table.selectedItems():
            return
        row = self.table.currentRow()
        if row < 0:
            return
        self.current_id = int(self.table.item(row, 0).text())
        vehicle = self.repo.get(self.current_id)
        if vehicle is None:
            return
        self.plate_edit.setText(vehicle.plate)
        self.note_edit.setText(vehicle.note)
        self.resident_edit.setText(
            "" if vehicle.resident_id is None else str(vehicle.resident_id)
        )
        index = self.type_combo.findData(vehicle.vehicle_type)
        self.type_combo.setCurrentIndex(index if index >= 0 else 0)
        if vehicle.monthly_expire is not None:
            qdate = QDate(vehicle.monthly_expire.year, vehicle.monthly_expire.month,
                          vehicle.monthly_expire.day)
            self.expire_edit.setDate(qdate)
        self._sync_expire_enabled()

    def _vehicle_from_form(self) -> Vehicle:
        """把表单转成 Vehicle；住户 ID 留空表示 None，填了非数字抛 ValueError。"""
        resident_text = self.resident_edit.text().strip()
        if not resident_text:
            resident_id = None
        elif resident_text.isascii() and resident_text.isdigit():
            resident_id = int(resident_text)
        else:
            # 以前非数字会被静默当成空，月租车随后提示“必须绑定住户”，容易误导
            raise ValueError("住户 ID 须为数字")
        expire = None
        if self._current_type() == VEHICLE_MONTHLY:
            qdate = self.expire_edit.date()
            expire = date(qdate.year(), qdate.month(), qdate.day())
        return Vehicle(
            id=self.current_id,
            plate=self.plate_edit.text().strip(),
            vehicle_type=self._current_type(),
            resident_id=resident_id,
            monthly_expire=expire,
            note=self.note_edit.text().strip(),
        )

    def clear_form(self) -> None:
        self.current_id = None
        self.plate_edit.clear()
        self.resident_edit.clear()
        self.note_edit.clear()
        self.type_combo.setCurrentIndex(0)
        self.expire_edit.setDate(QDate.currentDate())
        self.table.clearSelection()

    # ---------- 操作 ----------
    def add(self) -> None:
        if not self._ready():
            return
        try:
            vehicle = self._vehicle_from_form()
            vehicle.id = None           # 新增不沿用选中行的 id；新增失败时保留选中状态，"保存修改"仍可用
            new_id = self.service.add(vehicle)
        except ValueError as exc:
            QMessageBox.warning(self, "无法新增", str(exc))
            return
        self.clear_form()
        self.reload()
        self._select_id(new_id)

    def save(self) -> None:
        if not self._ready():
            return
        if self.current_id is None:
            QMessageBox.information(self, "提示", "请先在表格中选中要修改的车辆")
            return
        try:
            self.service.update(self._vehicle_from_form())
        except ValueError as exc:
            QMessageBox.warning(self, "无法保存", str(exc))
            return
        self.reload()
        self._select_id(self.current_id)

    def remove(self) -> None:
        if not self._ready():
            return
        if self.current_id is None:
            QMessageBox.information(self, "提示", "请先在表格中选中要删除的车辆")
            return
        if QMessageBox.question(self, "确认删除", "确定要删除该车辆吗？") != QMessageBox.Yes:
            return
        try:
            self.service.delete(self.current_id)
        except ValueError as exc:
            QMessageBox.warning(self, "无法删除", str(exc))
            return
        self.clear_form()
        self.reload()

    def _ready(self) -> bool:
        if self.repo is None:
            QMessageBox.information(
                self, "提示", "页面还没接入数据仓库，需要组长在 main_window.py 中注册")
            return False
        return True

    def _select_id(self, vehicle_id: int) -> None:
        for row in range(self.table.rowCount()):
            if self.table.item(row, 0).text() == str(vehicle_id):
                self.table.selectRow(row)
                return