"""住户表读写（负责人 B，REQ-003）。"""
"""住户表读写（负责人 B，REQ-003）。"""
import sqlite3

from app.models.entities import Resident


class ResidentRepo:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def add(self, obj: Resident) -> int:
        """返回新记录的 id。"""
        with self.conn:
            cur = self.conn.execute(
                "INSERT INTO residents (name, building, room, phone) VALUES (?, ?, ?, ?)",
                (obj.name, obj.building, obj.room, obj.phone),
            )
        return cur.lastrowid

    def update(self, obj: Resident) -> None:
        with self.conn:
            self.conn.execute(
                "UPDATE residents SET name = ?, building = ?, room = ?, phone = ? WHERE id = ?",
                (obj.name, obj.building, obj.room, obj.phone, obj.id),
            )

    def delete(self, id: int) -> None:
        """直接删除住户；名下有车时由数据库外键拒绝（IntegrityError 交给服务层）。"""
        with self.conn:
            self.conn.execute("DELETE FROM residents WHERE id = ?", (id,))


    def get(self, id: int) -> Resident | None:
        """找不到返回 None。"""
        row = self.conn.execute(
            "SELECT id, name, building, room, phone FROM residents WHERE id = ?", (id,)
        ).fetchone()
        return None if row is None else self._to_resident(row)

    def list_all(self) -> list[Resident]:
        rows = self.conn.execute(
            "SELECT id, name, building, room, phone FROM residents ORDER BY id"
        ).fetchall()
        return [self._to_resident(r) for r in rows]

    def search(self, keyword: str) -> list[Resident]:
        """按姓名或楼栋房号模糊查询（任务卡 B-1）。"""
        like = f"%{keyword}%"
        rows = self.conn.execute(
            "SELECT id, name, building, room, phone FROM residents "
            "WHERE name LIKE ? OR building LIKE ? OR room LIKE ? "
            "ORDER BY id",
            (like, like, like),
        ).fetchall()
        return [self._to_resident(r) for r in rows]

    @staticmethod
    def _to_resident(row: sqlite3.Row) -> Resident:
        """把数据库一行转成 Resident 对象。"""
        return Resident(
            id=row["id"], name=row["name"], building=row["building"],
            room=row["room"], phone=row["phone"],
        )