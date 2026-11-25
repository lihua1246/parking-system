"""主窗口：左侧导航 + 右侧页面区（负责人 A）。

页面统一在 _build_pages 中注册，页面负责人不改本文件。
按角色隐藏页面（REQ-020）：每个页面登记一个功能编号，can_access 不通过的页面不创建、不出现在侧边栏。
"""
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QListWidget, QMainWindow, QMenu, QStackedWidget, QToolButton,
    QVBoxLayout, QWidget,
)

from app.models.entities import ROLE_ADMIN, ROLE_GUARD, User
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
from app.ui.theme import PALETTE, seal_pixmap

ROLE_NAMES = {ROLE_ADMIN: "管理员", ROLE_GUARD: "门卫"}
WATERMARK_SIZE = 150
WATERMARK_OPACITY = 0.10   # 侧边栏底部校徽水印的不透明度，太深会抢导航文字的注意力


class Sidebar(QWidget):
    """左侧深色侧边栏：画底色，并在底部空白处画一枚淡淡的白色校徽水印。

    导航列表背景透明（见 theme.py），所以水印在列表下方的空白处可见。
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Sidebar")
        self._watermark = seal_pixmap(WATERMARK_SIZE, color="#FFFFFF")

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(PALETTE["sidebar_bg"]))
        if self._watermark is not None:
            size = min(WATERMARK_SIZE, self.width() - 30)
            target = QRectF((self.width() - size) / 2, self.height() - size - 28, size, size)
            painter.setOpacity(WATERMARK_OPACITY)
            painter.drawPixmap(target, self._watermark, QRectF(self._watermark.rect()))
        painter.end()


class MainWindow(QMainWindow):
    def __init__(self, user: User, conn):
        super().__init__()
        self.user = user
        self.conn = conn            # 数据库连接，之后用来创建各页面需要的 repo 和 service
        self.setWindowTitle("小区车辆管理系统")
        self.resize(1100, 700)

        self.nav = QListWidget()
        self.nav.setObjectName("Nav")              # 侧边栏样式见 theme.py 的 QListWidget#Nav
        self.nav.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.stack = QStackedWidget()
        self.breadcrumb = QLabel()
        self.breadcrumb.setObjectName("Breadcrumb")

        for page in self._build_pages():
            self.nav.addItem(page.TITLE)
            self.stack.addWidget(page)
        # 点左侧哪一项，右侧就切到同一序号的页面，顶部同时显示当前页面名
        self.nav.currentRowChanged.connect(self.stack.setCurrentIndex)
        self.nav.currentRowChanged.connect(self._update_breadcrumb)
        self.nav.setCurrentRow(0)

        central = QWidget()
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._build_sidebar())
        layout.addWidget(self._build_content(user), 1)
        self.setCentralWidget(central)

    def _build_sidebar(self) -> QWidget:
        """左侧深色侧边栏：顶部校徽和系统名，下面是页面导航，底部是校徽水印。"""
        sidebar = Sidebar()
        sidebar.setFixedWidth(180)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 12)
        sidebar_layout.setSpacing(0)

        header = QHBoxLayout()
        header.setContentsMargins(16, 18, 16, 18)
        header.setSpacing(10)
        seal = seal_pixmap(36, color=PALETTE["sidebar_text_selected"])   # 深色底上用白色校徽
        if seal is not None:
            seal_label = QLabel()
            seal_label.setPixmap(seal)
            header.addWidget(seal_label)
        title = QLabel("小区车辆管理")
        title.setObjectName("SidebarTitle")
        header.addWidget(title, 1)
        sidebar_layout.addLayout(header)
        sidebar_layout.addWidget(self.nav, 1)
        return sidebar

    def _build_content(self, user: User) -> QWidget:
        """右侧：顶部栏（当前位置、用户、账号菜单）+ 页面区。"""
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        top_bar = QWidget()
        top_bar.setObjectName("TopBar")
        top_bar.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        top_bar.setFixedHeight(52)
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(20, 0, 16, 0)
        top_layout.addWidget(self.breadcrumb)
        top_layout.addStretch()
        role_badge = QLabel(ROLE_NAMES.get(user.role, user.role))
        role_badge.setObjectName("RoleBadge")
        top_layout.addWidget(role_badge, 0, Qt.AlignmentFlag.AlignVCenter)   # 不对齐会被拉满整栏高度

        account_button = QToolButton()
        account_button.setText(f"{user.username}  ▾")
        account_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        account_menu = QMenu(account_button)
        # REQ-002：所有角色都能改自己的密码
        account_menu.addAction("修改密码", self._open_change_password)
        account_button.setMenu(account_menu)
        top_layout.addWidget(account_button)
        content_layout.addWidget(top_bar)

        page_area = QVBoxLayout()
        page_area.setContentsMargins(20, 16, 20, 16)
        page_area.addWidget(self.stack)
        content_layout.addLayout(page_area, 1)
        return content

    def _update_breadcrumb(self, row: int) -> None:
        item = self.nav.item(row)
        self.breadcrumb.setText(f"首页 / {item.text()}" if item is not None else "首页")

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
            # 车辆页、车位页额外传入的 repo 交给服务层做修改前检查（第二轮审查补充）
            (FEATURE_VEHICLE, lambda: VehiclePage(
                VehicleRepo(self.conn), ResidentRepo(self.conn),
                SpaceRepo(self.conn), RecordRepo(self.conn),
            )),
            (FEATURE_SPACE, lambda: SpacePage(
                SpaceRepo(self.conn), VehicleRepo(self.conn), ReservationRepo(self.conn),
            )),
            (FEATURE_RESERVATION, lambda: ReservationPage(ReservationRepo(self.conn), SpaceRepo(self.conn))),
            (FEATURE_FEE_RULE, lambda: FeeRulePage(FeeRuleRepo(self.conn))),
            (FEATURE_STATS, lambda: StatsPage(RecordRepo(self.conn), SpaceRepo(self.conn))),
            (FEATURE_USER, lambda: UserPage(user_repo, UserService(user_repo), self.user)),
            (FEATURE_BACKUP, lambda: BackupPage(self.conn, DEFAULT_BACKUP_DIR)),
        ]
        return [make() for feature, make in registry if can_access(self.user.role, feature)]
