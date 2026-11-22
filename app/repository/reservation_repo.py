"""预约表读写（REQ-022；原属 C，见任务卡 A-5）。

只做 SQL 读写；时间冲突等规则在 services/reservation.py。时间以 ISO 文本存储，读出时转回 datetime。
"""
import sqlite3
from datetime import datetime

from app.models.entities import Reservation

_COLUMNS = "id, space_id, plate, start_time, end_time"


def _to_reservation(row: sqlite3.Row) -> Reservation:
    return Reservation(
        id=row["id"],
        space_id=row["space_id"],
        plate=row["plate"],
        start_time=datetime.fromisoformat(row["start_time"]),
        end_time=datetime.fromisoformat(row["end_time"]),
    )


class ReservationRepo:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def add(self, obj: Reservation) -> int:
        """返回新记录的 id。车位不存在时由外键抛出 IntegrityError。"""
        cur = self.conn.execute(
            "INSERT INTO reservations (space_id, plate, start_time, end_time) VALUES (?, ?, ?, ?)",
            (obj.space_id, obj.plate, obj.start_time.isoformat(), obj.end_time.isoformat()),
        )
        self.conn.commit()
        return cur.lastrowid

    def update(self, obj: Reservation) -> None:
        self.conn.execute(
            "UPDATE reservations SET space_id = ?, plate = ?, start_time = ?, end_time = ? WHERE id = ?",
            (obj.space_id, obj.plate, obj.start_time.isoformat(), obj.end_time.isoformat(), obj.id),
        )
        self.conn.commit()

    def delete(self, id: int) -> None:
        self.conn.execute("DELETE FROM reservations WHERE id = ?", (id,))
        self.conn.commit()

    def get(self, id: int) -> Reservation | None:
        """找不到返回 None。"""
        row = self.conn.execute(
            f"SELECT {_COLUMNS} FROM reservations WHERE id = ?", (id,)
        ).fetchone()
        return _to_reservation(row) if row else None

    def list_all(self) -> list[Reservation]:
        rows = self.conn.execute(
            f"SELECT {_COLUMNS} FROM reservations ORDER BY start_time, id"
        ).fetchall()
        return [_to_reservation(r) for r in rows]
