import sqlite3

from app.models.entities import ParkingSpace


class SpaceRepo:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def add(self, obj: ParkingSpace) -> int:
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

    @staticmethod
    def _to_space(row: sqlite3.Row) -> ParkingSpace:
        return ParkingSpace(
            id=row["id"],
            code=row["code"],
            zone=row["zone"],
            status=row["status"],
            fixed_vehicle_id=row["fixed_vehicle_id"],
        )
