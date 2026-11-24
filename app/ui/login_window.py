"""登录窗口（负责人 A，REQ-001）。

窗口本身不知道怎么验证密码：验证逻辑由调用方以函数形式传进来（authenticate），
窗口只负责收集输入、显示提示、登录成功后发出信号。
这样任务卡 A-1 接入真正的密码校验时，不用改这个窗口。
"""
from typing import Callable

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFormLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget,
)

from app.models.entities import User
from app.ui.theme import PALETTE, seal_pixmap

LOGIN_FAILED_MSG = "用户名或密码错误"
EMPTY_INPUT_MSG = "请输入用户名和密码"


class LoginWindow(QWidget):
    logged_in = Signal(object)   # 登录成功时发出，参数是 User

    def __init__(self, authenticate: Callable[[str, str], User | None]):
        super().__init__()
        self._authenticate = authenticate
        self.setWindowTitle("登录 - 小区车辆管理系统")
        self.setObjectName("LoginWindow")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setFixedSize(380, 460)

        self.username = QLineEdit()
        self.username.setPlaceholderText("输入用户名")
        self.password = QLineEdit()
        self.password.setPlaceholderText("输入密码")
        self.password.setEchoMode(QLineEdit.Password)
        self.message = QLabel("")
        self.message.setStyleSheet(f"color: {PALETTE['danger']};")
        button = QPushButton("登录")
        button.setProperty("primary", True)      # 橙色实心主按钮，样式见 theme.py
        button.setMinimumHeight(38)

        seal_label = QLabel()
        seal_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        seal = seal_pixmap(96)
        if seal is not None:
            seal_label.setPixmap(seal)
        title = QLabel("小区车辆管理系统")
        title.setObjectName("LoginTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle = QLabel("请使用分配的账号登录")
        subtitle.setObjectName("LoginSubtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)

        form = QFormLayout()
        form.setVerticalSpacing(12)
        form.addRow("用户名", self.username)
        form.addRow("密码", self.password)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 32, 40, 32)
        layout.setSpacing(10)
        layout.addWidget(seal_label)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(14)
        layout.addLayout(form)
        layout.addWidget(self.message)
        layout.addWidget(button)
        layout.addStretch()

        button.clicked.connect(self._on_login)
        self.password.returnPressed.connect(self._on_login)   # 在密码框按回车也能登录

    def _on_login(self) -> None:
        username = self.username.text().strip()
        password = self.password.text()
        if not username or not password:
            self.message.setText(EMPTY_INPUT_MSG)
            return
        user = self._authenticate(username, password)
        if user is None:
            # 不区分是用户名错还是密码错（任务卡 A-1 规则）
            self.message.setText(LOGIN_FAILED_MSG)
            self.password.clear()
            return
        self.logged_in.emit(user)
