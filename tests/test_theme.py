"""全局主题的测试：样式表按配色生成、校徽可换色，主窗口和登录窗口套用主题后功能不变。"""
import re

import pytest

from app.models.entities import ROLE_ADMIN, ROLE_GUARD, User
from app.repository.db import get_connection, init_db
from app.ui.theme import PALETTE, SEAL_ORIGINAL_COLOR, SEAL_PATH, build_stylesheet, seal_svg_bytes


@pytest.fixture(scope="module")
def qapp():
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture
def conn():
    c = get_connection(":memory:")
    init_db(c)
    yield c
    c.close()


# ---------------------------------------------------------------- 样式表


def test_stylesheet_uses_palette_colors():
    qss = build_stylesheet()
    for key in ("sidebar_bg", "primary", "page_bg", "sidebar_marker"):
        assert PALETTE[key] in qss


def test_stylesheet_has_no_unfilled_placeholders():
    """模板里每个 {名字} 都要被配色替换掉，漏掉的会原样留在样式表里，Qt 不报错只是不生效。"""
    assert re.search(r"\{[a-z_]+\}", build_stylesheet()) is None


def test_stylesheet_follows_custom_palette():
    """改配色只改 PALETTE：传入新的主色，样式表里就是新主色，旧主色不再出现。"""
    custom = dict(PALETTE, primary="#123456", primary_hover="#123457", primary_pressed="#123458")
    qss = build_stylesheet(custom)
    assert "#123456" in qss
    assert PALETTE["primary"] not in qss


def test_stylesheet_braces_are_balanced():
    qss = build_stylesheet()
    assert qss.count("{") == qss.count("}")


# ---------------------------------------------------------------- 校徽


def test_seal_file_exists():
    assert SEAL_PATH.exists()


def test_seal_recolor_replaces_original_color():
    original = seal_svg_bytes().decode("utf-8")
    white = seal_svg_bytes("#FFFFFF").decode("utf-8")
    assert SEAL_ORIGINAL_COLOR in original
    assert SEAL_ORIGINAL_COLOR not in white
    assert "#FFFFFF" in white


def test_seal_pixmap_has_requested_size(qapp):
    from app.ui.theme import seal_pixmap
    pixmap = seal_pixmap(48)
    assert pixmap is not None
    assert round(pixmap.width() / pixmap.devicePixelRatio()) == 48


# ---------------------------------------------------------------- 窗口


def _user(role: str) -> User:
    return User(id=1, username="tester", password_hash="x", role=role)


def test_main_window_breadcrumb_follows_nav(qapp, conn):
    from app.ui.main_window import MainWindow
    window = MainWindow(_user(ROLE_ADMIN), conn)
    assert window.nav.objectName() == "Nav"
    assert window.breadcrumb.text() == f"首页 / {window.nav.item(0).text()}"
    window.nav.setCurrentRow(2)
    assert window.stack.currentIndex() == 2
    assert window.breadcrumb.text() == f"首页 / {window.nav.item(2).text()}"


def test_main_window_shows_role_name(qapp, conn):
    from PySide6.QtWidgets import QLabel
    from app.ui.main_window import MainWindow
    window = MainWindow(_user(ROLE_GUARD), conn)
    badges = [label.text() for label in window.findChildren(QLabel) if label.objectName() == "RoleBadge"]
    assert badges == ["门卫"]


def test_login_window_still_logs_in(qapp):
    from app.ui.login_window import LoginWindow
    user = _user(ROLE_ADMIN)
    window = LoginWindow(lambda name, pwd: user if (name, pwd) == ("tester", "pw") else None)
    received = []
    window.logged_in.connect(received.append)
    window.username.setText("tester")
    window.password.setText("pw")
    window._on_login()
    assert received == [user]
