"""出入记录读写（D）。不提供删除，历史入场信息不随出场更新改变。"""
import sqlite3
from datetime import datetime

from app.models.entities import ParkingRecord


class RecordRepo:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    @staticmethod
    def _from_row(row) -> ParkingRecord | None:
        if row is None:
            return None
        return ParkingRecord(
            id=row["id"], plate=row["plate"], vehicle_type=row["vehicle_type"],
            enter_time=datetime.fromisoformat(row["enter_time"]),
            exit_time=datetime.fromisoformat(row["exit_time"]) if row["exit_time"] else None,
            fee=row["fee"], space_id=row["space_id"], operator=row["operator"],
        )

    def add(self, obj: ParkingRecord) -> int:
        """新增一次停车，返回数据库分配的编号。"""
        with self.conn:
            cursor = self.conn.execute(
                "INSERT INTO records "
                "(plate, vehicle_type, enter_time, exit_time, fee, space_id, operator) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (obj.plate, obj.vehicle_type, obj.enter_time.isoformat(),
                 obj.exit_time.isoformat() if obj.exit_time is not None else None,
                 obj.fee, obj.space_id, obj.operator),
            )
        return cursor.lastrowid

    def update(self, obj: ParkingRecord) -> None:
        """仅补全出场信息，不改写入场时的车牌、类型或操作员。"""
        with self.conn:
            self.conn.execute(
                "UPDATE records SET exit_time = ?, fee = ? "
                "WHERE id = ? AND exit_time IS NULL",
                (obj.exit_time.isoformat() if obj.exit_time is not None else None,
                 obj.fee, obj.id),
            )

    def get(self, id: int) -> ParkingRecord | None:
        row = self.conn.execute("SELECT * FROM records WHERE id = ?", (id,)).fetchone()
        return self._from_row(row)

    def list_all(self) -> list[ParkingRecord]:
        rows = self.conn.execute("SELECT * FROM records ORDER BY id").fetchall()
        return [self._from_row(row) for row in rows]

    def get_present(self, plate: str) -> ParkingRecord | None:
        row = self.conn.execute(
            "SELECT * FROM records WHERE plate = ? AND exit_time IS NULL ORDER BY id DESC LIMIT 1",
            (plate,),
        ).fetchone()
        return self._from_row(row)

    def list_present(self) -> list[ParkingRecord]:
        rows = self.conn.execute(
            "SELECT * FROM records WHERE exit_time IS NULL ORDER BY id"
        ).fetchall()
        return [self._from_row(row) for row in rows]

    def list_between(self, start: datetime, end: datetime) -> list[ParkingRecord]:
        """按入场时间查询，包含 start、不包含 end；最新入场的记录在前。"""
        return self.search(start=start, end=end)

    def search(self, plate: str = "", start: datetime | None = None,
               end: datetime | None = None) -> list[ParkingRecord]:
        """按车牌包含匹配、入场时间取交集；空条件表示该项不限。"""
        conditions = []
        parameters = []
        keyword = plate.strip()
        if keyword:
            # instr 按字面子串匹配，不把 %、_ 当成 SQL 通配符。
            conditions.append("instr(plate, ?) > 0")
            parameters.append(keyword)
        if start is not None:
            conditions.append("enter_time >= ?")
            parameters.append(start.isoformat())
        if end is not None:
            conditions.append("enter_time < ?")
            parameters.append(end.isoformat())

        sql = "SELECT * FROM records"
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        # 编号只用于同一入场时间下的稳定排序，不改变按入场时间倒序的约定。
        sql += " ORDER BY enter_time DESC, id DESC"
        rows = self.conn.execute(sql, parameters).fetchall()
        return [self._from_row(row) for row in rows]
