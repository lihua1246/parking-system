"""住户业务规则（负责人 B，REQ-003）。

"名下有车的住户不能删除"属于业务判断，放在服务层而不是页面或 repo 层，
这样可以被测试覆盖，界面只负责显示提示（docs/03 第一节）。
"""
import sqlite3


class ResidentService:
    def __init__(self, resident_repo):
        self.resident_repo = resident_repo

    def delete(self, resident_id: int) -> None:
        """删除住户。名下有车时数据库外键拒绝，这里翻译成中文提示。"""
        try:
            self.resident_repo.delete(resident_id)
        except sqlite3.IntegrityError:
            # vehicles.resident_id 外键引用 residents(id)，名下有车时数据库拒绝删除
            raise ValueError("请先删除或转移该住户名下的车辆") from None