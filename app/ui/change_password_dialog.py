"""修改密码对话框（负责人 A，REQ-002）。

和登录窗口一样，对话框不知道怎么改密码：调用方传入函数 change(old, new)，
规则不通过时该函数抛 ValueError，对话框把消息显示出来。
"""
from typing import Callable

from PySide6.QtWidgets import (
    QDialog, QFormLayout, QLabel, QLineEdit, QMessageBox, QPushButton, QVBoxLayout,
)

CONFIRM_MISMATCH_MSG = "两次输入的新密码不一致"


class ChangePasswordDialog(QDialog):
    def __init__(self, change: Callable[[str, str], None], parent=None):
        super().__init__(parent)
        self._change = change
        self.setWindowTitle("修改密码")

        self.old_password = QLineEdit()
        self.new_password = QLineEdit()
        self.confirm_password = QLineEdit()
        for edit in (self.old_password, self.new_password, self.confirm_password):
            edit.setEchoMode(QLineEdit.Password)
        self.message = QLabel("")
        self.message.setStyleSheet("color: #c0392b;")
        button = QPushButton("确定")

        form = QFormLayout()
        form.addRow("旧密码", self.old_password)
        form.addRow("新密码", self.new_password)
        form.addRow("确认新密码", self.confirm_password)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(self.message)
        layout.addWidget(button)

        button.clicked.connect(self._on_submit)
        self.confirm_password.returnPressed.connect(self._on_submit)

    def _on_submit(self) -> None:
        new = self.new_password.text()
        if new != self.confirm_password.text():
            self.message.setText(CONFIRM_MISMATCH_MSG)
            return
        try:
            self._change(self.old_password.text(), new)
        except ValueError as e:
            self.message.setText(str(e))
            return
        QMessageBox.information(self, "修改密码", "密码已修改，下次登录请使用新密码")
        self.accept()
