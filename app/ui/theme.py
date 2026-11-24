"""全局界面主题：深灰 + 橙色配色、统一样式表、校徽图片。

用法：main.py 里创建 QApplication 后调用一次 apply_theme(app)，所有窗口和页面自动生效，
各页面不需要改代码。想让某个按钮变成橙色实心的主要按钮，给它设置属性：
    button.setProperty("primary", True)

配色只在 PALETTE 里定义一次，样式表由 build_stylesheet() 按配色生成，
改颜色只改 PALETTE，不要在各页面里另写颜色。
"""
from pathlib import Path

ASSETS_DIR = Path(__file__).resolve().parent / "assets"
SEAL_PATH = ASSETS_DIR / "zzuli_seal.svg"
SEAL_ORIGINAL_COLOR = "#174481"   # 校徽原图的深蓝色，侧边栏上换色时按这个颜色替换
CHEVRON_PATH = ASSETS_DIR / "chevron_down.svg"   # 下拉框箭头

PALETTE = {
    # 侧边栏
    "sidebar_bg": "#2C2C2A",
    "sidebar_hover": "#3A3A37",
    "sidebar_selected": "#444441",
    "sidebar_text": "#D3D1C7",
    "sidebar_text_selected": "#FFFFFF",
    "sidebar_marker": "#EF9F27",      # 选中项左边的竖条
    # 页面
    "page_bg": "#F7F6F3",
    "surface": "#FFFFFF",
    "surface_alt": "#FAF9F6",         # 表格隔行
    "header_bg": "#F1EFE8",           # 表头
    "border": "#D3D1C7",
    "text": "#2C2C2A",
    "text_secondary": "#5F5E5A",
    "text_muted": "#888780",
    # 主色（橙）
    "primary": "#D85A30",
    "primary_hover": "#C24E27",
    "primary_pressed": "#993C1D",
    "primary_soft": "#FAECE7",        # 选中行、悬停的浅橙底
    "primary_text": "#712B13",        # 浅橙底上的文字
    # 提示色：成功 / 失败 / 提醒，不随主题主色变化
    "success": "#3B6D11",
    "success_bg": "#EAF3DE",
    "danger": "#A32D2D",
    "danger_bg": "#FCEBEB",
    "warning": "#854F0B",
    "warning_bg": "#FAEEDA",
}

FONT_FAMILY = '"Microsoft YaHei", "PingFang SC", "Noto Sans CJK SC", sans-serif'


def build_stylesheet(palette: dict[str, str] | None = None) -> str:
    """按配色生成整个程序的 Qt 样式表（QSS）。纯字符串处理，不依赖 PySide6，便于测试。"""
    p = dict(PALETTE if palette is None else palette)
    p["font"] = FONT_FAMILY
    p["chevron"] = CHEVRON_PATH.as_posix()   # QSS 的 url() 要用正斜杠路径
    return """
QWidget {{
    font-family: {font};
    font-size: 14px;
    color: {text};
}}
QMainWindow, QDialog {{
    background: {page_bg};
}}

/* ---------- 侧边栏 ---------- */
QWidget#Sidebar {{
    background: {sidebar_bg};
}}
QWidget#Sidebar QLabel {{
    color: {sidebar_text};
    background: transparent;
}}
QLabel#SidebarTitle {{
    color: {sidebar_text_selected};
    font-size: 16px;
    font-weight: bold;
}}
QListWidget#Nav {{
    background: transparent;
    border: none;
    outline: none;
    padding: 4px 0;
}}
QListWidget#Nav::item {{
    color: {sidebar_text};
    padding: 10px 16px;
    border-left: 3px solid transparent;
}}
QListWidget#Nav::item:hover {{
    background: {sidebar_hover};
}}
QListWidget#Nav::item:selected {{
    background: {sidebar_selected};
    color: {sidebar_text_selected};
    border-left: 3px solid {sidebar_marker};
}}

/* ---------- 顶部栏 ---------- */
QWidget#TopBar {{
    background: {surface};
    border-bottom: 1px solid {border};
}}
QLabel#Breadcrumb {{
    color: {text_secondary};
}}
QLabel#RoleBadge {{
    background: {primary_soft};
    color: {primary_text};
    border-radius: 4px;
    padding: 1px 8px;
    font-size: 12px;
}}

/* ---------- 按钮 ---------- */
QPushButton, QToolButton {{
    background: {surface};
    color: {text};
    border: 1px solid {border};
    border-radius: 6px;
    padding: 6px 16px;
    min-height: 22px;
}}
QPushButton:hover, QToolButton:hover {{
    border-color: {primary};
    color: {primary_pressed};
}}
QPushButton:pressed, QToolButton:pressed {{
    background: {primary_soft};
}}
QPushButton:disabled {{
    color: {text_muted};
    background: {page_bg};
    border-color: {border};
}}
QPushButton[primary="true"] {{
    background: {primary};
    color: #FFFFFF;
    border: 1px solid {primary};
}}
QPushButton[primary="true"]:hover {{
    background: {primary_hover};
    border-color: {primary_hover};
    color: #FFFFFF;
}}
QPushButton[primary="true"]:pressed {{
    background: {primary_pressed};
}}
QToolButton::menu-indicator {{
    image: none;
}}

/* ---------- 输入框 ---------- */
QLineEdit, QComboBox, QSpinBox, QDateEdit, QDateTimeEdit, QTextEdit, QPlainTextEdit {{
    background: {surface};
    border: 1px solid {border};
    border-radius: 6px;
    padding: 5px 8px;
    selection-background-color: {primary};
}}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDateEdit:focus, QDateTimeEdit:focus,
QTextEdit:focus, QPlainTextEdit:focus {{
    border: 1px solid {primary};
}}
QComboBox::drop-down, QDateEdit::drop-down, QDateTimeEdit::drop-down {{
    border: none;
    width: 24px;
}}
QComboBox::down-arrow, QDateEdit::down-arrow, QDateTimeEdit::down-arrow {{
    image: url("{chevron}");
    width: 12px;
    height: 12px;
}}
QComboBox QAbstractItemView {{
    background: {surface};
    border: 1px solid {border};
    selection-background-color: {primary_soft};
    selection-color: {primary_text};
}}

/* ---------- 表格和列表 ---------- */
QTableWidget, QTableView, QListWidget {{
    background: {surface};
    alternate-background-color: {surface_alt};
    border: 1px solid {border};
    border-radius: 6px;
    gridline-color: {header_bg};
    selection-background-color: {primary_soft};
    selection-color: {primary_text};
}}
QHeaderView::section {{
    background: {header_bg};
    color: {text_secondary};
    border: none;
    border-bottom: 1px solid {border};
    padding: 6px 8px;
    font-weight: bold;
}}
QTableCornerButton::section {{
    background: {header_bg};
    border: none;
}}

/* ---------- 滚动条 ---------- */
QScrollBar:vertical {{
    background: transparent;
    width: 10px;
}}
QScrollBar::handle:vertical {{
    background: {border};
    border-radius: 5px;
    min-height: 30px;
}}
QScrollBar:horizontal {{
    background: transparent;
    height: 10px;
}}
QScrollBar::handle:horizontal {{
    background: {border};
    border-radius: 5px;
    min-width: 30px;
}}
QScrollBar::add-line, QScrollBar::sub-line {{
    width: 0;
    height: 0;
}}

/* ---------- 菜单、提示框 ---------- */
QMenu {{
    background: {surface};
    border: 1px solid {border};
    padding: 4px;
}}
QMenu::item {{
    padding: 6px 24px;
    border-radius: 4px;
}}
QMenu::item:selected {{
    background: {primary_soft};
    color: {primary_text};
}}
QToolTip {{
    background: {sidebar_bg};
    color: #FFFFFF;
    border: none;
    padding: 4px 8px;
}}

/* ---------- 登录窗口 ---------- */
QWidget#LoginWindow {{
    background: {page_bg};
}}
QLabel#LoginTitle {{
    font-size: 20px;
    font-weight: bold;
}}
QLabel#LoginSubtitle {{
    color: {text_muted};
}}
""".format(**p)


def seal_svg_bytes(color: str | None = None) -> bytes:
    """读取校徽 SVG；传入 color 时把原图的深蓝色换成该颜色（深色侧边栏上用浅色）。"""
    text = SEAL_PATH.read_text(encoding="utf-8")
    if color is not None:
        text = text.replace(SEAL_ORIGINAL_COLOR, color)
    return text.encode("utf-8")


def seal_pixmap(size: int, color: str | None = None):
    """把校徽画成 size×size 的图片，供 QLabel 显示。校徽文件缺失时返回 None，界面照常显示。"""
    if not SEAL_PATH.exists():
        return None
    from PySide6.QtCore import QByteArray, Qt
    from PySide6.QtGui import QGuiApplication, QPainter, QPixmap
    from PySide6.QtSvg import QSvgRenderer

    ratio = QGuiApplication.primaryScreen().devicePixelRatio() if QGuiApplication.primaryScreen() else 1.0
    pixmap = QPixmap(int(size * ratio), int(size * ratio))
    pixmap.fill(Qt.GlobalColor.transparent)
    renderer = QSvgRenderer(QByteArray(seal_svg_bytes(color)))
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    pixmap.setDevicePixelRatio(ratio)
    return pixmap


def apply_theme(app) -> None:
    """给整个程序套用主题：Fusion 基础风格（各平台外观一致）+ 本文件的样式表 + 窗口图标。"""
    from PySide6.QtGui import QIcon

    app.setStyle("Fusion")
    app.setStyleSheet(build_stylesheet())
    if SEAL_PATH.exists():
        app.setWindowIcon(QIcon(str(SEAL_PATH)))
