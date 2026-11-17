"""住户管理页面（负责人 B，REQ-003）。

骨架阶段只是占位。负责人实现时可以给构造函数加上需要的 service 或 repo 参数，
改完在合并请求里说明，由组长在 main_window.py 中改注册代码。
"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class ResidentPage(QWidget):
    TITLE = "住户管理"

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        label = QLabel("住户管理\n（REQ-003，负责人 B，待实现）")
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)
