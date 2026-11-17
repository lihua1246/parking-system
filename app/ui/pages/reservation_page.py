"""车位预约页面（负责人 C，REQ-022）。

骨架阶段只是占位。负责人实现时可以给构造函数加上需要的 service 或 repo 参数，
改完在合并请求里说明，由组长在 main_window.py 中改注册代码。
"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class ReservationPage(QWidget):
    TITLE = "车位预约"

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        label = QLabel("车位预约\n（REQ-022，负责人 C，待实现）")
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)
