"""主窗口：左侧导航 + 右侧页面区（负责人 A）。

页面统一在 _build_pages 中注册，页面负责人不改本文件。
按角色隐藏页面（REQ-020）：每个页面登记一个功能编号，can_access 不通过的页面不创建、不出现在侧边栏。
预警页面（REQ-024、025）属拓展功能，本期不做，暂不注册；功能编号 FEATURE_ALERT 保留在 auth.py，以后实现时在此加回一行即可。
"""
from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QListWidget, QMainWindow, QPushButton, QStackedWidget, QVBoxLayout,
    QWidget,
)

from app.models.entities import User
from app.repository.fee_rule_repo import FeeRuleRepo
from app.repository.record_repo import RecordRepo
from app.repository.reservation_repo import ReservationRepo
from app.repository.resident_repo import ResidentRepo
from app.repository.space_repo import SpaceRepo
from app.repository.user_repo import UserRepo
from app.repository.vehicle_repo import VehicleRepo
from app.services.auth import (
    FEATURE_BACKUP, FEATURE_FEE_RULE, FEATURE_GATE, FEATURE_RECORD,
    FEATURE_RESERVATION, FEATURE_RESIDENT, FEATURE_SPACE, FEATURE_STATS, FEATURE_USER,
    FEATURE_VEHICLE, can_access, change_password,
)
from app.services.backup import DEFAULT_BACKUP_DIR
from app.services.gate import GateService
from app.services.user import UserService
from app.ui.change_password_dialog import ChangePasswordDialog
from app.ui.pages.backup_page import BackupPage
from app.ui.pages.fee_rule_page import FeeRulePage
from app.ui.pages.gate_page import GatePage
from app.ui.pages.record_page import RecordPage
from app.ui.pages.reservation_page import ReservationPage
from app.ui.pages.resident_page import ResidentPage
from app.ui.pages.space_page import SpacePage
from app.ui.pages.stats_page import StatsPage
from app.ui.pages.user_page import UserPage
from app.ui.pages.vehicle_page import VehiclePage


class MainWindow(QMainWindow):
    def __init__(self, user: User, conn):
        super().__init__()
        self.user = user
        self.conn = conn            # 数据库连接，之后用来创建各页面需要的 repo 和 service
        self.setWindowTitle("小区车辆管理系统")
        self.resize(1000, 640)

        self.nav = QListWidget()
        self.nav.setFixedWidth(160)
        self.stack = QStackedWidget()

        for page in self._build_pages():
            self.nav.addItem(page.TITLE)
            self.stack.addWidget(page)
        # 点左侧哪一项，右侧就切到同一序号的页面
        self.nav.currentRowChanged.connect(self.stack.setCurrentIndex)
        self.nav.setCurrentRow(0)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.addWidget(QLabel(f"当前用户：{user.username}（{user.role}）"))
        left_layout.addWidget(self.nav)
        change_pwd_button = QPushButton("修改密码")   # REQ-002：所有角色都能改自己的密码
        change_pwd_button.clicked.connect(self._open_change_password)
        left_layout.addWidget(change_pwd_button)

        central = QWidget()
        layout = QHBoxLayout(central)
        layout.addWidget(left)
        layout.addWidget(self.stack, 1)
        self.setCentralWidget(central)

    def _open_change_password(self) -> None:
        user_repo = UserRepo(self.conn)
        dialog = ChangePasswordDialog(
            lambda old, new: change_password(user_repo, self.user.id, old, new), self,
        )
        dialog.exec()

    def _build_pages(self) -> list[QWidget]:
        """按侧边栏显示顺序创建当前角色能用的页面。页面需要 repo 或 service 时在这里传入。

        每项是（功能编号, 创建页面的函数）：先判断权限再创建，没权限的页面根本不会被构造。
        """
        user_repo = UserRepo(self.conn)
        gate_service = GateService(
            RecordRepo(self.conn), VehicleRepo(self.conn), FeeRuleRepo(self.conn),
        )
        registry = [
            (FEATURE_GATE, lambda: GatePage(service=gate_service, operator=self.user.username)),
            (FEATURE_RECORD, lambda: RecordPage(RecordRepo(self.conn))),
            (FEATURE_RESIDENT, lambda: ResidentPage(ResidentRepo(self.conn))),
            (FEATURE_VEHICLE, lambda: VehiclePage(VehicleRepo(self.conn), ResidentRepo(self.conn))),
            (FEATURE_SPACE, lambda: SpacePage(SpaceRepo(self.conn), VehicleRepo(self.conn))),
            (FEATURE_RESERVATION, lambda: ReservationPage(ReservationRepo(self.conn), SpaceRepo(self.conn))),
            (FEATURE_FEE_RULE, lambda: FeeRulePage(FeeRuleRepo(self.conn))),
            (FEATURE_STATS, lambda: StatsPage(RecordRepo(self.conn), SpaceRepo(self.conn))),
            (FEATURE_USER, lambda: UserPage(user_repo, UserService(user_repo), self.user)),
            (FEATURE_BACKUP, lambda: BackupPage(self.conn, DEFAULT_BACKUP_DIR)),
        ]
        return [make() for feature, make in registry if can_access(self.user.role, feature)]
