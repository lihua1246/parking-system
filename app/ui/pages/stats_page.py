"""REQ-016 至 019 统计报表页面（负责人 E）。

主窗口注册方式（由 A 修改 main_window.py 第 98 行）：
    (FEATURE_STATS, lambda: StatsPage(RecordRepo(self.conn), SpaceRepo(self.conn)))

页面只负责展示和导出：车流量、收入、利用率的规则全部来自 app/services/stats.py，
页面里不写任何统计公式；导出走 app/services/export.py，不直接操作 openpyxl。
"""
from datetime import date

import matplotlib

matplotlib.use("QtAgg")

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402
from PySide6.QtWidgets import (  # noqa: E402
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.repository.record_repo import RecordRepo  # noqa: E402
from app.repository.space_repo import SpaceRepo  # noqa: E402
from app.services.export import export_income, export_records  # noqa: E402
from app.services.stats import (  # noqa: E402
    income_by_day, month_summary, monthly_flow, utilization,
)

# Windows 上 Qt 自带的字体里没有中文，不设置会画出一堆方框。
matplotlib.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
matplotlib.rcParams["axes.unicode_minus"] = False


class StatsPage(QWidget):
    TITLE = "统计报表"

    def __init__(
        self,
        record_repo: RecordRepo | None = None,
        space_repo: SpaceRepo | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self.record_repo = record_repo
        self.space_repo = space_repo
        self._records = []
        self._income: dict[date, int] = {}

        today = date.today()
        layout = QVBoxLayout(self)

        title = QLabel(self.TITLE)
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        layout.addWidget(title)
        layout.addWidget(QLabel("切换年月会自动统计；收入按出场日期归属。"))

        controls = QHBoxLayout()
        controls.addWidget(QLabel("统计月份："))
        self.year_box = QComboBox()
        for year in range(today.year - 2, today.year + 2):
            self.year_box.addItem(str(year))
        self.year_box.setCurrentText(str(today.year))
        self.month_box = QComboBox()
        for month in range(1, 13):
            self.month_box.addItem(str(month))
        self.month_box.setCurrentText(str(today.month))

        self.refresh_button = QPushButton("统计")
        self.export_records_button = QPushButton("导出全部出入记录")
        self.export_income_button = QPushButton("导出本月收入汇总")
        for widget in (
            self.year_box,
            self.month_box,
            self.refresh_button,
            self.export_records_button,
            self.export_income_button,
        ):
            controls.addWidget(widget)
        controls.addStretch()
        layout.addLayout(controls)

        self.message = QLabel()
        self.message.setWordWrap(True)
        layout.addWidget(self.message)

        self.figure = Figure(figsize=(8, 4), tight_layout=True)
        self.canvas = FigureCanvasQTAgg(self.figure)
        layout.addWidget(self.canvas, 1)

        self.refresh_button.clicked.connect(self.refresh)
        # 改了年月就重新统计，避免"导出本月收入汇总"导出的是上一次统计的月份
        self.year_box.currentIndexChanged.connect(self.refresh)
        self.month_box.currentIndexChanged.connect(self.refresh)
        self.export_records_button.clicked.connect(self._export_records)
        self.export_income_button.clicked.connect(self._export_income)

        self.refresh()

    def showEvent(self, event) -> None:
        """主窗口登录时就构造全部页面；每次切到本页时重新统计，显示最新的出入记录。"""
        super().showEvent(event)
        self.refresh()

    # ------------------------------------------------------------------ 数据

    def refresh(self) -> None:
        """按当前选中的年月重新统计并重画。"""
        year = int(self.year_box.currentText())
        month = int(self.month_box.currentText())

        if self.record_repo is None:
            self.message.setText("未注入 RecordRepo，无法读取出入记录。")
            return

        # 记录量很小，一次取出全量，再由统计函数按年月筛选。
        self._records = self.record_repo.list_all()
        flow = monthly_flow(self._records, year, month)
        self._income = income_by_day(self._records, year, month)
        spaces = self.space_repo.list_all() if self.space_repo is not None else []
        rate = utilization(spaces)

        summary = month_summary(self._records, year, month)   # 合计由服务层计算，界面不求和

        self._draw(flow, year, month)
        self.message.setText(
            f"{year} 年 {month} 月：本月入场 {summary['in']} 辆、出场 {summary['out']} 辆、"
            f"收入 {summary['income']} 元；车位利用率 {rate:.1%}（{len(spaces)} 个车位）。"
        )

    def _draw(self, flow: dict, year: int, month: int) -> None:
        self.figure.clear()
        days = sorted(flow)
        day_labels = [d.day for d in days]

        flow_axis = self.figure.add_subplot(1, 2, 1)
        # 出场用虚线，避免两条线数值相近时把入场那条完全盖住。
        flow_axis.plot(day_labels, [flow[d]["in"] for d in days],
                       marker="o", label="入场")
        flow_axis.plot(day_labels, [flow[d]["out"] for d in days],
                       marker="s", linestyle="--", label="出场")
        flow_axis.set_title(f"{year}-{month:02d} 每日车流量（辆）")
        flow_axis.set_xlabel("日")
        flow_axis.set_ylabel("车辆数")
        flow_axis.legend()

        income_axis = self.figure.add_subplot(1, 2, 2)
        income_axis.bar(day_labels, [self._income[d] for d in days], color="#4c72b0")
        income_axis.set_title(f"{year}-{month:02d} 每日收入（元）")
        income_axis.set_xlabel("日")
        income_axis.set_ylabel("元")

        self.canvas.draw_idle()

    # ------------------------------------------------------------------ 导出

    def _export_records(self) -> None:
        self.refresh()                      # 导出前重新取数，避免导出过期数据
        if not self._records:
            QMessageBox.information(self, "没有数据", "当前没有可导出的出入记录。")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "导出出入记录", "出入记录.xlsx", "Excel 文件 (*.xlsx)",
        )
        if not path:
            return
        self._run_export(lambda: export_records(self._records, path))

    def _export_income(self) -> None:
        # 按当前选中的年月重新统计后导出；income_by_day 总是返回整月每一天，收入为 0 的月份也照常导出
        self.refresh()
        path, _ = QFileDialog.getSaveFileName(
            self, "导出收入汇总", "收入汇总.xlsx", "Excel 文件 (*.xlsx)",
        )
        if not path:
            return
        self._run_export(lambda: export_income(self._income, path))

    def _run_export(self, action) -> None:
        try:
            rows = action()
        except OSError as error:
            QMessageBox.warning(self, "导出失败", str(error))
            return
        QMessageBox.information(self, "导出完成", f"已导出 {rows} 行。")
