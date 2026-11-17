"""用户管理页面（负责人 A，REQ-021）。

骨架阶段只是占位。负责人实现时可以给构造函数加上需要的 service 或 repo 参数，
改完在合并请求里说明，由组长在 main_window.py 中改注册代码。
"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class UserPage(QWidget):
    TITLE = "用户管理"

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        label = QLabel("用户管理\n（REQ-021，负责人 A，待实现）")
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)
