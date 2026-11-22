"""收费规则表读写（负责人 A，REQ-015；原属 D，见任务卡 A-4）。

fee_rules 表以 vehicle_type 为主键、没有 id，也不需要增删，
所以只提供按车辆类型读取和修改。取值是否合规由 services/fee_rule.py 判断，这里原样读写。
"""
import sqlite3

from app.models.entities import FeeRule

_COLUMNS = "vehicle_type, free_minutes, hourly_rate, daily_cap"


def _to_rule(row: sqlite3.Row) -> FeeRule:
    return FeeRule(
        vehicle_type=row["vehicle_type"],
        free_minutes=row["free_minutes"],
        hourly_rate=row["hourly_rate"],
        daily_cap=row["daily_cap"],
    )


class FeeRuleRepo:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def get(self, vehicle_type: str) -> FeeRule | None:
        """找不到返回 None（例如月租车没有收费规则）。"""
        row = self.conn.execute(
            f"SELECT {_COLUMNS} FROM fee_rules WHERE vehicle_type = ?", (vehicle_type,)
        ).fetchone()
        return _to_rule(row) if row else None

    def list_all(self) -> list[FeeRule]:
        rows = self.conn.execute(
            f"SELECT {_COLUMNS} FROM fee_rules ORDER BY vehicle_type"
        ).fetchall()
        return [_to_rule(r) for r in rows]

    def update(self, rule: FeeRule) -> None:
        """按 vehicle_type 覆盖三项数值；该车辆类型不存在时什么也不改。"""
        self.conn.execute(
            "UPDATE fee_rules SET free_minutes = ?, hourly_rate = ?, daily_cap = ? "
            "WHERE vehicle_type = ?",
            (rule.free_minutes, rule.hourly_rate, rule.daily_cap, rule.vehicle_type),
        )
        self.conn.commit()
