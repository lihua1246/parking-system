"""住户业务规则（负责人 B，REQ-003）。

规则都放在这一层：字段必填、手机号格式、名下有车不能删。
界面只负责显示和收集输入（docs/03 第一节）。
"""
import sqlite3

from app.models.entities import Resident
from app.services.validators import is_valid_phone


class ResidentService:
    def __init__(self, resident_repo):
        self.resident_repo = resident_repo

    def list_all(self) -> list[Resident]:
        return self.resident_repo.list_all()

    def search(self, keyword: str) -> list[Resident]:
        keyword = keyword.strip()
        if not keyword:
            return self.resident_repo.list_all()
        return self.resident_repo.search(keyword)

    def add(self, obj: Resident) -> int:
        """新增住户。字段缺失或手机号不合法时抛 ValueError。"""
        self._check(obj)
        return self.resident_repo.add(obj)

    def update(self, obj: Resident) -> None:
        """修改住户。字段缺失或手机号不合法时抛 ValueError。"""
        self._check(obj)
        self.resident_repo.update(obj)

    def delete(self, resident_id: int) -> None:
        """删除住户。名下有车时数据库外键拒绝，这里翻译成中文提示。"""
        try:
            self.resident_repo.delete(resident_id)
        except sqlite3.IntegrityError:
            # vehicles.resident_id 外键引用 residents(id)，名下有车时数据库拒绝删除
            raise ValueError("请先删除或转移该住户名下的车辆") from None

    @staticmethod
    def _check(obj: Resident) -> None:
        if not obj.name or not obj.building or not obj.room:
            raise ValueError("姓名、楼栋、房号都必须填写")
        if not is_valid_phone(obj.phone):
            raise ValueError("手机号必须是 11 位数字，且以 1 开头")