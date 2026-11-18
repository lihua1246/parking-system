"""车位业务规则（负责人 C，REQ-006）。

"占用中的车位不能删除"属于业务判断，放在服务层而不是页面里，这样可以用测试覆盖。
"""
import sqlite3

from app.models.entities import SPACE_OCCUPIED


class SpaceService:
    def __init__(self, space_repo):
        self.space_repo = space_repo

    def delete(self, space_id: int) -> None:
        """删除车位。车位不存在、正被占用、或仍被预约引用时抛出 ValueError。"""
        space = self.space_repo.get(space_id)
        if space is None:
            raise ValueError("该车位已不存在，请刷新")
        if space.status == SPACE_OCCUPIED:
            raise ValueError("车位正在使用，不能删除")
        try:
            self.space_repo.delete(space_id)
        except sqlite3.IntegrityError:
            # reservations.space_id 外键引用 spaces(id)，有预约时数据库拒绝删除
            raise ValueError("该车位还有预约记录，不能删除") from None
