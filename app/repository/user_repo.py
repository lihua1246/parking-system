"""用户表读写（负责人 A，REQ-001）。

只做读写，不做业务判断：密码哈希由 services/auth.py 生成后传进来，这里原样保存。
用户名重复时由数据库的 UNIQUE 约束拒绝，抛出 sqlite3.IntegrityError。
"""
import sqlite3

from app.models.entities import User

_COLUMNS = "id, username, password_hash, role"


def _to_user(row: sqlite3.Row) -> User:
    return User(
        id=row["id"],
        username=row["username"],
        password_hash=row["password_hash"],
        role=row["role"],
    )


class UserRepo:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def add(self, obj: User) -> int:
        """返回新记录的 id。"""
        cur = self.conn.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
            (obj.username, obj.password_hash, obj.role),
        )
        self.conn.commit()
        return cur.lastrowid

    def update(self, obj: User) -> None:
        self.conn.execute(
            "UPDATE users SET username = ?, password_hash = ?, role = ? WHERE id = ?",
            (obj.username, obj.password_hash, obj.role, obj.id),
        )
        self.conn.commit()

    def delete(self, id: int) -> None:
        self.conn.execute("DELETE FROM users WHERE id = ?", (id,))
        self.conn.commit()

    def get(self, id: int) -> User | None:
        """找不到返回 None。"""
        row = self.conn.execute(
            f"SELECT {_COLUMNS} FROM users WHERE id = ?", (id,)
        ).fetchone()
        return _to_user(row) if row else None

    def list_all(self) -> list[User]:
        rows = self.conn.execute(f"SELECT {_COLUMNS} FROM users ORDER BY id").fetchall()
        return [_to_user(r) for r in rows]

    def get_by_username(self, username: str) -> User | None:
        row = self.conn.execute(
            f"SELECT {_COLUMNS} FROM users WHERE username = ?", (username,)
        ).fetchone()
        return _to_user(row) if row else None
