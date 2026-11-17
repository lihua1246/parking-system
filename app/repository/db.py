"""数据库连接与建表（负责人 A）。

日期时间一律以 ISO 文本存储（如 2026-11-16T08:30:00），由各 repo 读出时转回 datetime。
"""
import sqlite3
from pathlib import Path

from app.models.entities import VEHICLE_TEMP, VEHICLE_VISITOR

DEFAULT_DB_PATH = "data/parking.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role          TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS residents (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    name     TEXT NOT NULL,
    building TEXT NOT NULL,
    room     TEXT NOT NULL,
    phone    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS vehicles (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    plate          TEXT NOT NULL UNIQUE,
    vehicle_type   TEXT NOT NULL,
    resident_id    INTEGER REFERENCES residents(id),
    monthly_expire TEXT,
    note           TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS spaces (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    code             TEXT NOT NULL UNIQUE,
    zone             TEXT NOT NULL,
    status           TEXT NOT NULL,
    fixed_vehicle_id INTEGER UNIQUE REFERENCES vehicles(id)
);

-- 出入记录只增不删，保存入场时车牌和车辆类型的副本，不用外键关联 vehicles（ADR-004）
CREATE TABLE IF NOT EXISTS records (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    plate        TEXT NOT NULL,
    vehicle_type TEXT NOT NULL,
    enter_time   TEXT NOT NULL,
    exit_time    TEXT,
    fee          INTEGER,
    space_id     INTEGER,
    operator     TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS fee_rules (
    vehicle_type TEXT PRIMARY KEY,
    free_minutes INTEGER NOT NULL,
    hourly_rate  INTEGER NOT NULL,
    daily_cap    INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS reservations (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    space_id   INTEGER NOT NULL REFERENCES spaces(id),
    plate      TEXT NOT NULL,
    start_time TEXT NOT NULL,
    end_time   TEXT NOT NULL
);
"""

# 默认收费规则，数值取自 docs/02-需求清单.md「计费规则 · 默认参数」
# (车辆类型, 免费分钟, 每小时单价/元, 每 24 小时封顶/元)
DEFAULT_FEE_RULES = [
    (VEHICLE_TEMP, 30, 3, 30),
    (VEHICLE_VISITOR, 120, 3, 30),
]


def get_connection(path: str = DEFAULT_DB_PATH) -> sqlite3.Connection:
    """打开数据库连接。文件所在目录不存在时自动创建；测试传入 ":memory:"。"""
    if path != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row          # 查询结果可以按列名取值：row["plate"]
    conn.execute("PRAGMA foreign_keys = ON")  # SQLite 默认不检查外键，需要手动打开
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    """建表并写入默认收费规则。可以重复调用，不会重复插入。

    默认管理员 admin / admin123 需要用 auth.hash_password 生成哈希，
    在任务卡 A-1（REQ-001）中接入，骨架阶段先不写入。
    """
    conn.executescript(_SCHEMA)
    conn.executemany(
        "INSERT OR IGNORE INTO fee_rules "
        "(vehicle_type, free_minutes, hourly_rate, daily_cap) VALUES (?, ?, ?, ?)",
        DEFAULT_FEE_RULES,
    )
    conn.commit()
