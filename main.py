"""程序入口：初始化数据库，打开登录窗口，登录成功后进入主窗口。"""
import sys

from PySide6.QtWidgets import QApplication

from app.models.entities import User
from app.repository.db import get_connection, init_db
from app.repository.user_repo import UserRepo
from app.services.auth import authenticate, ensure_default_admin
from app.ui.login_window import LoginWindow
from app.ui.main_window import MainWindow
from app.ui.theme import apply_theme


def main() -> int:
    conn = get_connection()
    init_db(conn)
    user_repo = UserRepo(conn)
    ensure_default_admin(user_repo)   # 首次启动写入 admin / admin123（只存哈希）

    app = QApplication(sys.argv)
    apply_theme(app)   # 全局配色和样式表，所有窗口、页面自动生效
    login = LoginWindow(lambda username, password: authenticate(user_repo, username, password))
    windows = {}   # 保存主窗口的引用，防止被垃圾回收后窗口一闪而过

    def open_main(user: User) -> None:
        windows["main"] = MainWindow(user, conn)
        windows["main"].show()
        login.close()

    login.logged_in.connect(open_main)
    login.show()
    code = app.exec()
    conn.close()
    return code


if __name__ == "__main__":
    sys.exit(main())
