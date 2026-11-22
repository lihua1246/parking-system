"""车位表读写（负责人 C，REQ-006、007）。

只负责 SQL 读写，不做业务判断（见 docs/03-架构与接口.md）。
"占用中的车位不能删除"由页面先查询状态后拦截；"状态只能是三种之一"
由页面下拉框保证，表结构上没有 CHECK，已建议组长在 db.py 中补充。
"""
import sqlite3

from app.models.entities import ParkingSpace


class SpaceRepo:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def add(self, obj: ParkingSpace) -> int:
        """返回新记录的 id。编号重复时由表的 UNIQUE 约束抛出 IntegrityError。"""
        with self.conn:
            cur = self.conn.execute(
                "INSERT INTO spaces (code, zone, status, fixed_vehicle_id) VALUES (?, ?, ?, ?)",
                (obj.code, obj.zone, obj.status, obj.fixed_vehicle_id),
            )
        return int(cur.lastrowid)

    def update(self, obj: ParkingSpace) -> None:
        if obj.id is None:
            raise ValueError("更新车位时必须提供 id")
        with self.conn:
            self.conn.execute(
                "UPDATE spaces SET code = ?, zone = ?, status = ?, fixed_vehicle_id = ? "
                "WHERE id = ?",
                (obj.code, obj.zone, obj.status, obj.fixed_vehicle_id, obj.id),
            )

    def delete(self, id: int) -> None:
        with self.conn:
            self.conn.execute("DELETE FROM spaces WHERE id = ?", (id,))

    def get(self, id: int) -> ParkingSpace | None:
        """找不到返回 None。"""
        row = self.conn.execute(
            "SELECT id, code, zone, status, fixed_vehicle_id FROM spaces WHERE id = ?",
            (id,),
        ).fetchone()
        return self._to_space(row) if row is not None else None

    def list_all(self) -> list[ParkingSpace]:
        rows = self.conn.execute(
            "SELECT id, code, zone, status, fixed_vehicle_id FROM spaces ORDER BY code"
        ).fetchall()
        return [self._to_space(row) for row in rows]

    def list_by(self, zone: str | None, status: str | None) -> list[ParkingSpace]:
        """按区域、状态筛选；参数为 None 表示不限（任务卡 C-1）。"""
        sql = "SELECT id, code, zone, status, fixed_vehicle_id FROM spaces WHERE 1 = 1"
        params: list[str] = []
        if zone is not None:
            sql += " AND zone = ?"
            params.append(zone)
        if status is not None:
            sql += " AND status = ?"
            params.append(status)
        sql += " ORDER BY code"
        rows = self.conn.execute(sql, params).fetchall()
        return [self._to_space(row) for row in rows]

    def get_by_fixed_vehicle(self, vehicle_id: int) -> ParkingSpace | None:
        """查车辆已绑定的固定车位（REQ-007）；没有返回 None。"""
        row = self.conn.execute(
            "SELECT id, code, zone, status, fixed_vehicle_id FROM spaces WHERE fixed_vehicle_id = ?",
            (vehicle_id,),
        ).fetchone()
        return self._to_space(row) if row is not None else None

    @staticmethod
    def _to_space(row: sqlite3.Row) -> ParkingSpace:
        return ParkingSpace(
            id=row["id"],
            code=row["code"],
            zone=row["zone"],
            status=row["status"],
            fixed_vehicle_id=row["fixed_vehicle_id"],
        )
