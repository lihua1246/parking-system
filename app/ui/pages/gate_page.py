"""D-1 出入登记。A 在 _build_pages 中注入 service 和 operator 后即可使用。"""
from datetime import datetime

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QAbstractItemView, QHBoxLayout, QHeaderView, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from app.models.entities import VEHICLE_MONTHLY, VEHICLE_TEMP, VEHICLE_VISITOR
from app.services.gate import GateService


def format_duration(enter: datetime, end: datetime) -> str:
    """两页共用的时长文字：只格式化时间差，不计算停车费。"""
    minutes = int((end - enter).total_seconds() // 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours} 小时 {minutes} 分"


class GatePage(QWidget):
    TITLE = "出入登记"

    def __init__(self, parent=None, *, service: GateService | None = None,
                 operator: str | None = None):
        super().__init__(parent)
        self.service = service
        self.operator = operator
        layout = QVBoxLayout(self)
        title = QLabel(self.TITLE)
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        layout.addWidget(title)
        layout.addWidget(QLabel(f"操作员：{operator or '未接入'}　｜　D-1：出场费用暂为 0 元"))

        controls = QHBoxLayout()
        self.plate_input = QLineEdit()
        self.plate_input.setPlaceholderText("请输入车牌号，例如：豫A12345")
        self.enter_button = QPushButton("车辆入场")
        self.exit_button = QPushButton("车辆出场")
        self.refresh_button = QPushButton("刷新在场列表")
        controls.addWidget(self.plate_input, 1)
        for button in (self.enter_button, self.exit_button, self.refresh_button):
            controls.addWidget(button)
        layout.addLayout(controls)

        self.message = QLabel()
        self.message.setWordWrap(True)
        layout.addWidget(self.message)
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["车牌", "车辆类型", "入场时间", "已停时长"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        layout.addWidget(self.table)

        self.enter_button.clicked.connect(self._enter)
        self.exit_button.clicked.connect(self._exit)
        self.refresh_button.clicked.connect(self._refresh)
        self.timer = QTimer(self)
        self.timer.setInterval(30_000)
        self.timer.timeout.connect(self._refresh)
        ready = service is not None and bool(operator)
        for control in (self.plate_input, self.enter_button, self.exit_button, self.refresh_button):
            control.setEnabled(ready)
        if ready:
            self._refresh()
            self.timer.start()
        else:
            self._show_message("出入登记尚未接入，请由组长传入业务服务和当前操作员。", error=True)

    def _show_message(self, text: str, error: bool = False) -> None:
        self.message.setText(text)
        color = "#b42318" if error else "#067647"
        self.message.setStyleSheet(f"color: {color}; padding: 10px; font-size: 15px;")

    def _operate(self, exiting: bool) -> None:
        plate = self.plate_input.text().strip()
        if not plate:
            self._show_message("请输入车牌号", error=True)
            return
        now = datetime.now()  # 时间在界面取得，并显式传入业务层。
        try:
            if exiting:
                record = self.service.exit(plate, now, self.operator)
                text = (f"出场成功：{record.plate}　停车时长："
                        f"{format_duration(record.enter_time, record.exit_time)}　应收：{record.fee} 元")
            else:
                record = self.service.enter(plate, now, self.operator)
                text = f"入场成功：{record.plate}"
        except ValueError as exc:
            self._show_message(str(exc), error=True)
            return
        except NotImplementedError:
            self._show_message("车辆查询尚未接入，请联系组长与车辆模块负责人。", error=True)
            return
        if self._refresh():
            self._show_message(text)

    def _enter(self) -> None:
        self._operate(exiting=False)

    def _exit(self) -> None:
        self._operate(exiting=True)

    def _refresh(self) -> bool:
        if self.service is None:
            return False
        try:
            records = self.service.list_present()
        except NotImplementedError:
            self._show_message("在场查询尚未接入，请联系组长。", error=True)
            return False
        now = datetime.now()
        names = {VEHICLE_TEMP: "临时车", VEHICLE_MONTHLY: "月租车", VEHICLE_VISITOR: "访客车"}
        self.table.setRowCount(len(records))
        for row, record in enumerate(records):
            values = (record.plate, names.get(record.vehicle_type, record.vehicle_type),
                      record.enter_time.strftime("%Y-%m-%d %H:%M"),
                      format_duration(record.enter_time, now))
            for column, value in enumerate(values):
                self.table.setItem(row, column, QTableWidgetItem(value))
        return True
