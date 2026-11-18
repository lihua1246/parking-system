"""住户管理页面（负责人 B，REQ-003；任务卡 B-1）。

页面拿的是 ResidentRepo：列表、搜索、新增、修改直接走 repo；
只有删除走 ResidentService，因为"名下有车不能删"是业务规则，不是数据操作。
"""
from PySide6.QtWidgets import (
    QHBoxLayout, QHeaderView, QLineEdit, QMessageBox, QPushButton,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from app.models.entities import Resident
from app.repository.resident_repo import ResidentRepo
from app.services.resident import ResidentService
from app.services.validators import is_valid_phone

COLUMNS = ["ID", "姓名", "楼栋", "房号", "手机号"]


class ResidentPage(QWidget):
    TITLE = "住户管理"

    def __init__(self, resident_repo: ResidentRepo | None = None, parent=None):
        super().__init__(parent)
        self.repo = resident_repo
        self.service = ResidentService(resident_repo) if resident_repo is not None else None
        self.current_id: int | None = None
        self._build_ui()
        self.reload()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        self.keyword_edit = QLineEdit()
        self.keyword_edit.setPlaceholderText("按姓名或楼栋房号搜索，如 张 / 3号楼")
        search_btn = QPushButton("搜索")
        search_btn.clicked.connect(self.search)
        show_all_btn = QPushButton("显示全部")
        show_all_btn.clicked.connect(self.reload)
        search_row = QHBoxLayout()
        search_row.addWidget(self.keyword_edit)
        search_row.addWidget(search_btn)
        search_row.addWidget(show_all_btn)
        layout.addLayout(search_row)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("姓名")
        self.building_edit = QLineEdit()
        self.building_edit.setPlaceholderText("楼栋，如 3号楼")
        self.room_edit = QLineEdit()
        self.room_edit.setPlaceholderText("房号，如 2-501")
        self.phone_edit = QLineEdit()
        self.phone_edit.setPlaceholderText("手机号，11 位")
        form_row = QHBoxLayout()
        for widget in (self.name_edit, self.building_edit, self.room_edit, self.phone_edit):
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

    def reload(self) -> None:
        if self.repo is None:
            self.table.setRowCount(0)
            return
        self._fill(self.repo.list_all())

    def search(self) -> None:
        if self.repo is None:
            return
        keyword = self.keyword_edit.text().strip()
        if not keyword:
            self.reload()
            return
        self._fill(self.repo.search(keyword))

    def _fill(self, residents: list[Resident]) -> None:
        self.table.setRowCount(0)
        for resident in residents:
            row = self.table.rowCount()
            self.table.insertRow(row)
            values = [resident.id, resident.name, resident.building,
                      resident.room, resident.phone]
            for col, value in enumerate(values):
                self.table.setItem(row, col, QTableWidgetItem(str(value)))

    def _on_select(self) -> None:
        row = self.table.currentRow()
        if row < 0:
            return
        self.current_id = int(self.table.item(row, 0).text())
        self.name_edit.setText(self.table.item(row, 1).text())
        self.building_edit.setText(self.table.item(row, 2).text())
        self.room_edit.setText(self.table.item(row, 3).text())
        self.phone_edit.setText(self.table.item(row, 4).text())

    def _form_resident(self) -> Resident:
        return Resident(
            id=self.current_id,
            name=self.name_edit.text().strip(),
            building=self.building_edit.text().strip(),
            room=self.room_edit.text().strip(),
            phone=self.phone_edit.text().strip(),
        )

    def _checked_resident(self) -> Resident | None:
        """表单校验。返回 None 表示提示过用户、本次操作放弃。"""
        resident = self._form_resident()
        if not resident.name or not resident.building or not resident.room:
            QMessageBox.warning(self, "无法保存", "姓名、楼栋、房号都必须填写")
            return None
        if not is_valid_phone(resident.phone):
            QMessageBox.warning(self, "无法保存", "手机号必须是 11 位数字，且以 1 开头")
            return None
        return resident

    def clear_form(self) -> None:
        self.current_id = None
        for widget in (self.name_edit, self.building_edit,
                       self.room_edit, self.phone_edit):
            widget.clear()
        self.table.clearSelection()

    def add(self) -> None:
        if not self._ready():
            return
        resident = self._checked_resident()
        if resident is None:
            return
        resident.id = None
        new_id = self.repo.add(resident)
        self.clear_form()
        self.reload()
        self._select_id(new_id)

    def save(self) -> None:
        if not self._ready():
            return
        if self.current_id is None:
            QMessageBox.information(self, "提示", "请先在表格中选中要修改的住户")
            return
        resident = self._checked_resident()
        if resident is None:
            return
        self.repo.update(resident)
        self.reload()
        self._select_id(self.current_id)

    def remove(self) -> None:
        if not self._ready():
            return
        if self.current_id is None:
            QMessageBox.information(self, "提示", "请先在表格中选中要删除的住户")
            return
        if QMessageBox.question(self, "确认删除", "确定要删除该住户吗？") != QMessageBox.Yes:
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

    def _select_id(self, resident_id: int) -> None:
        for row in range(self.table.rowCount()):
            if self.table.item(row, 0).text() == str(resident_id):
                self.table.selectRow(row)
                return