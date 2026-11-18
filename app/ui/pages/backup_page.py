"""备份还原页面（负责人 A，REQ-023）。

界面只负责按钮、确认对话框和提示；复制、校验、还原前自动备份都在 services/backup.py。
当前时间在这里取得后传给服务层。还原成功后提示并退出程序，重新启动后各页面读到的才是还原后的数据。
"""
from datetime import datetime
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication, QFileDialog, QHBoxLayout, QLabel, QListWidget, QMessageBox, QPushButton,
    QVBoxLayout, QWidget,
)

from app.services.backup import backup_database, list_backups, restore_database


class BackupPage(QWidget):
    TITLE = "备份还原"

    def __init__(self, conn, backup_dir: Path, parent=None):
        super().__init__(parent)
        self.conn = conn
        self.backup_dir = Path(backup_dir)
        self._build_ui()
        self.reload()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"备份目录：{self.backup_dir}"))

        backup_btn = QPushButton("立即备份")
        backup_btn.clicked.connect(self.backup)
        layout.addWidget(backup_btn)

        layout.addWidget(QLabel("已有备份（最新的在最上面）："))
        self.list = QListWidget()
        layout.addWidget(self.list)

        restore_btn = QPushButton("从选中的备份还原")
        restore_btn.clicked.connect(self.restore_selected)
        browse_btn = QPushButton("选择其他文件还原…")
        browse_btn.clicked.connect(self.restore_from_file)
        row = QHBoxLayout()
        row.addWidget(restore_btn)
        row.addWidget(browse_btn)
        layout.addLayout(row)

    def reload(self) -> None:
        self.list.clear()
        for path in list_backups(self.backup_dir):
            self.list.addItem(path.name)

    def backup(self) -> None:
        try:
            path = backup_database(self.conn, self.backup_dir, datetime.now())
        except (ValueError, OSError) as e:
            QMessageBox.warning(self, "备份", f"备份失败：{e}")
            return
        QMessageBox.information(self, "备份", f"已备份为 {path.name}")
        self.reload()

    def restore_selected(self) -> None:
        item = self.list.currentItem()
        if item is None:
            QMessageBox.information(self, "还原", "请先在列表中选中一个备份")
            return
        self._restore(self.backup_dir / item.text())

    def restore_from_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "选择备份文件", str(self.backup_dir), "数据库备份 (*.db)",
        )
        if path:
            self._restore(Path(path))

    def _restore(self, path: Path) -> None:
        # 二次确认（REQ-023）：默认按钮是"否"，误按回车不会还原
        answer = QMessageBox.warning(
            self, "确认还原",
            f"将用 {path.name} 覆盖当前全部数据。\n"
            "还原前会自动备份当前数据，还原后程序将退出，需要重新启动。\n\n确定还原吗？",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        try:
            safety = restore_database(self.conn, path, self.backup_dir, datetime.now())
        except (ValueError, OSError) as e:
            QMessageBox.warning(self, "还原", f"还原失败：{e}")
            return
        QMessageBox.information(
            self, "还原",
            f"还原完成。还原前的数据已备份为 {safety.name}。\n程序将退出，请重新启动后登录。",
        )
        QApplication.quit()
