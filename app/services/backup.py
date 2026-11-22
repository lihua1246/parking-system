"""数据备份与还原（负责人 A，REQ-023）。

用标准库 sqlite3 的 Connection.backup 在两个连接之间复制整个数据库（ADR-008）：
程序运行时连接一直开着，直接复制文件可能拿到写了一半的数据，还原时文件也可能被占用；
backup 接口由 SQLite 保证复制的是一致的完整数据，还原时直接写进当前连接，不用关闭重开。
还原前校验：文件结构必须与本系统建表结果完全一致（不多不少），并且通过 SQLite 自检。

时间由调用方传入，本模块不调用 datetime.now()。
"""
import sqlite3
from datetime import datetime
from pathlib import Path

from app.repository.db import PROJECT_ROOT, get_connection, init_db, integrity_ok, schema_objects

DEFAULT_BACKUP_DIR = PROJECT_ROOT / "data" / "backups"
BACKUP_PREFIX = "parking_"
BACKUP_SUFFIX = ".db"

BACKUP_NOT_FOUND_MSG = "备份文件不存在"
NOT_A_BACKUP_MSG = "不是本系统的备份文件"


def backup_filename(now: datetime) -> str:
    """带日期和时间的备份文件名，如 parking_20261117_093005.db。精确到秒，同一天多次备份不会重名。"""
    return f"{BACKUP_PREFIX}{now:%Y%m%d_%H%M%S}{BACKUP_SUFFIX}"


def backup_database(conn: sqlite3.Connection, backup_dir: Path, now: datetime) -> Path:
    """把当前数据库完整复制到 backup_dir 下的新文件，返回备份文件路径。"""
    backup_dir = Path(backup_dir)
    backup_dir.mkdir(parents=True, exist_ok=True)
    stem = backup_filename(now).removesuffix(BACKUP_SUFFIX)
    target = backup_dir / f"{stem}{BACKUP_SUFFIX}"
    n = 2
    while target.exists():      # 同一秒内再次备份（如刚备份就还原）时加序号，不覆盖已有备份
        target = backup_dir / f"{stem}_{n}{BACKUP_SUFFIX}"
        n += 1
    dest = sqlite3.connect(target)
    try:
        conn.backup(dest)
    finally:
        dest.close()
    return target


def list_backups(backup_dir: Path) -> list[Path]:
    """列出 backup_dir 下的备份文件，最新的在前。目录不存在时返回空列表。"""
    backup_dir = Path(backup_dir)
    if not backup_dir.is_dir():
        return []
    files = backup_dir.glob(f"{BACKUP_PREFIX}*{BACKUP_SUFFIX}")
    return sorted(files, key=lambda p: p.name, reverse=True)   # 文件名含时间，按名字倒序即按时间倒序


def _expected_schema() -> set[tuple[str, str, str, str]]:
    """按本系统的建表语句新建一个内存库，取出它的结构作为比对标准。"""
    fresh = get_connection(":memory:")
    try:
        init_db(fresh)
        return schema_objects(fresh)
    finally:
        fresh.close()


def _open_backup(backup_path: Path) -> sqlite3.Connection:
    """只读打开备份文件，确认结构与本系统建表结果完全一致且文件完好；不合格时抛 ValueError。

    只检查表名不够：还原会把整个文件原样复制进当前数据库，伪造的文件可以带着触发器进来，
    例如出场写入费用后立刻改成 0。所以多一个对象、少一个对象、建表语句不同都拒绝。
    """
    backup_path = Path(backup_path)
    if not backup_path.is_file():
        raise ValueError(BACKUP_NOT_FOUND_MSG)
    # 只读打开，校验过程不会改动备份文件，也不会在路径错误时新建空库
    src = sqlite3.connect(f"{backup_path.resolve().as_uri()}?mode=ro", uri=True)
    try:
        valid = schema_objects(src) == _expected_schema() and integrity_ok(src)
    except sqlite3.DatabaseError:           # 文件不是 SQLite 数据库，或已损坏到无法读取
        valid = False
    if not valid:
        src.close()
        raise ValueError(NOT_A_BACKUP_MSG)
    return src


def restore_database(conn: sqlite3.Connection, backup_path: Path,
                     backup_dir: Path, now: datetime) -> Path:
    """用备份文件覆盖当前数据库，返回还原前自动做的那份备份的路径。

    顺序：先校验备份文件 → 再把当前数据备份一份（防止误还原后无法挽回）→ 最后还原。
    校验不通过时抛 ValueError，当前数据库和备份目录都不变。
    """
    src = _open_backup(backup_path)
    try:
        safety = backup_database(conn, backup_dir, now)
        src.backup(conn)
    finally:
        src.close()
    return safety
