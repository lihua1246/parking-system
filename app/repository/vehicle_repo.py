"""车辆表读写（负责人 B，REQ-004）。"""
import sqlite3
from datetime import date

from app.models.entities import Vehicle


class VehicleRepo:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def add(self, obj: Vehicle) -> int:
        """返回新记录的 id。"""
        with self.conn:
            cur = self.conn.execute(
                "INSERT INTO vehicles "
                "(plate, vehicle_type, resident_id, monthly_expire, note) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    obj.plate,
                    obj.vehicle_type,
                    obj.resident_id,
                    obj.monthly_expire.isoformat() if obj.monthly_expire else None,
                    obj.note,
                ),
            )
        return cur.lastrowid

    def update(self, obj: Vehicle) -> None:
        with self.conn:
            self.conn.execute(
                "UPDATE vehicles SET plate = ?, vehicle_type = ?, resident_id = ?, "
                "monthly_expire = ?, note = ? WHERE id = ?",
                (
                    obj.plate,
                    obj.vehicle_type,
                    obj.resident_id,
                    obj.monthly_expire.isoformat() if obj.monthly_expire else None,
                    obj.note,
                    obj.id,
                ),
            )

    def delete(self, id: int) -> None:
        with self.conn:
            self.conn.execute("DELETE FROM vehicles WHERE id = ?", (id,))

    def get(self, id: int) -> Vehicle | None:
        """找不到返回 None。"""
        row = self.conn.execute(
            "SELECT id, plate, vehicle_type, resident_id, monthly_expire, note "
            "FROM vehicles WHERE id = ?",
            (id,),
        ).fetchone()
        return None if row is None else self._to_vehicle(row)

    def list_all(self) -> list[Vehicle]:
        rows = self.conn.execute(
            "SELECT id, plate, vehicle_type, resident_id, monthly_expire, note "
            "FROM vehicles ORDER BY id"
        ).fetchall()
        return [self._to_vehicle(r) for r in rows]

    def get_by_plate(self, plate: str) -> Vehicle | None:
        """GateService 入场时用来确定车辆类型。找不到返回 None。"""
        row = self.conn.execute(
            "SELECT id, plate, vehicle_type, resident_id, monthly_expire, note "
            "FROM vehicles WHERE plate = ?",
            (plate,),
        ).fetchone()
        return self._to_vehicle(row) if row is not None else None

    @staticmethod
    def _to_vehicle(row: sqlite3.Row) -> Vehicle:
        expire = row["monthly_expire"]
        return Vehicle(
            id=row["id"],
            plate=row["plate"],
            vehicle_type=row["vehicle_type"],
            resident_id=row["resident_id"],
            monthly_expire=date.fromisoformat(expire) if expire else None,
            note=row["note"],
        )
