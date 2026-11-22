"""数据库连接与建表（负责人 A）。

日期时间一律以 ISO 文本存储（如 2026-11-16T08:30:00），由各 repo 读出时转回 datetime。
"""
import sqlite3
from pathlib import Path

from app.models.entities import VEHICLE_TEMP, VEHICLE_VISITOR

# 以项目根目录为基准，避免从其他目录启动程序时新建一个空库
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB_PATH = str(PROJECT_ROOT / "data" / "parking.db")

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

    默认管理员不在这里写入：生成密码哈希属于业务规则（services/auth.py），
    repository 层不能反过来调用 services。由 main.py 在 init_db 之后调用
    auth.ensure_default_admin 写入。
    """
    conn.executescript(_SCHEMA)
    conn.executemany(
        "INSERT OR IGNORE INTO fee_rules "
        "(vehicle_type, free_minutes, hourly_rate, daily_cap) VALUES (?, ?, ?, ?)",
        DEFAULT_FEE_RULES,
    )
    conn.commit()


def list_tables(conn: sqlite3.Connection) -> set[str]:
    """返回数据库中所有表名（不含 SQLite 内部表）。"""
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
    ).fetchall()
    return {row[0] for row in rows}


def schema_objects(conn: sqlite3.Connection) -> set[tuple[str, str, str, str]]:
    """返回 sqlite_master 里的全部对象：(类型, 名称, 所属表, 建表语句)。备份还原时用来校验文件。

    表、索引、触发器、视图都算，SQLite 自动建的内部对象也算，不按名称过滤：
    按名称过滤（如 NOT LIKE 'sqlite_%'）会被 "sqlitex" 这类名字绕过。
    建表语句里连续的空白合并成一个空格，排版不同而内容相同的语句视为一致。
    """
    rows = conn.execute("SELECT type, name, tbl_name, sql FROM sqlite_master").fetchall()
    return {(row[0], row[1], row[2], " ".join((row[3] or "").split())) for row in rows}


def integrity_ok(conn: sqlite3.Connection) -> bool:
    """SQLite 自检（PRAGMA integrity_check）结果为 ok 时返回 True，文件损坏时返回 False。"""
    return conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
