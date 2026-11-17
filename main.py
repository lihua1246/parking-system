"""程序入口：初始化数据库，打开登录窗口，登录成功后进入主窗口。"""
import sys

from PySide6.QtWidgets import QApplication

from app.models.entities import ROLE_ADMIN, User
from app.repository.db import get_connection, init_db
from app.ui.login_window import LoginWindow
from app.ui.main_window import MainWindow


def skeleton_authenticate(username: str, password: str) -> User | None:
    """骨架阶段的临时登录：只放行 admin / admin123，不查数据库。

    任务卡 A-1（REQ-001）会换成查 users 表并用 verify_password 校验，届时删除本函数。
    """
    if username == "admin" and password == "admin123":
        return User(id=None, username="admin", password_hash="", role=ROLE_ADMIN)
    return None


def main() -> int:
    conn = get_connection()
    init_db(conn)

    app = QApplication(sys.argv)
    login = LoginWindow(skeleton_authenticate)
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
