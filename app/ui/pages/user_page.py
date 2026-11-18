"""用户管理页面（负责人 A，REQ-021）。

界面只负责显示和收集输入；用户名唯一、密码长度、不能删自己、至少保留一名管理员
都在 UserService。谁能看到本页面由 REQ-020 处理。
"""
from PySide6.QtWidgets import (
    QComboBox, QHBoxLayout, QHeaderView, QLineEdit, QMessageBox, QPushButton,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from app.models.entities import ROLE_ADMIN, ROLE_GUARD, User

COLUMNS = ["ID", "用户名", "角色"]
ROLE_NAMES = {ROLE_ADMIN: "管理员", ROLE_GUARD: "门卫"}


class UserPage(QWidget):
    TITLE = "用户管理"

    def __init__(self, user_repo, service, current_user: User, parent=None):
        super().__init__(parent)
        self.user_repo = user_repo          # 只用来读列表
        self.service = service              # 新增、删除都走服务层
        self.current_user = current_user    # 删除时用来判断"不能删自己"
        self._build_ui()
        self.reload()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        self.username_edit = QLineEdit()
        self.username_edit.setPlaceholderText("用户名")
        self.password_edit = QLineEdit()
        self.password_edit.setPlaceholderText("初始密码，不少于 6 位")
        self.password_edit.setEchoMode(QLineEdit.Password)
        self.role_combo = QComboBox()
        for role, name in ROLE_NAMES.items():
            self.role_combo.addItem(name, role)   # 显示中文，取值用角色常量
        self.role_combo.setCurrentIndex(self.role_combo.findData(ROLE_GUARD))
        add_btn = QPushButton("新增用户")
        add_btn.clicked.connect(self.add)

        form_row = QHBoxLayout()
        for widget in (self.username_edit, self.password_edit, self.role_combo, add_btn):
            form_row.addWidget(widget)
        layout.addLayout(form_row)

        self.table = QTableWidget(0, len(COLUMNS))
        self.table.setHorizontalHeaderLabels(COLUMNS)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.table)

        delete_btn = QPushButton("删除选中用户")
        delete_btn.clicked.connect(self.remove)
        layout.addWidget(delete_btn)

    def reload(self) -> None:
        users = self.user_repo.list_all()
        self.table.setRowCount(len(users))
        for row, user in enumerate(users):
            name = user.username
            if user.id == self.current_user.id:
                name += "（当前登录）"
            values = [str(user.id), name, ROLE_NAMES.get(user.role, user.role)]
            for col, value in enumerate(values):
                self.table.setItem(row, col, QTableWidgetItem(value))

    def add(self) -> None:
        try:
            self.service.add(
                self.username_edit.text(), self.password_edit.text(), self.role_combo.currentData(),
            )
        except ValueError as e:
            QMessageBox.warning(self, "新增用户", str(e))
            return
        self.username_edit.clear()
        self.password_edit.clear()
        self.reload()

    def remove(self) -> None:
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, "删除用户", "请先在列表中选中一个用户")
            return
        user_id = int(self.table.item(row, 0).text())
        name = self.table.item(row, 1).text()
        if QMessageBox.question(self, "删除用户", f"确定删除用户 {name} 吗？") != QMessageBox.Yes:
            return
        try:
            self.service.delete(user_id, current_user_id=self.current_user.id)
        except ValueError as e:
            QMessageBox.warning(self, "删除用户", str(e))
        self.reload()
