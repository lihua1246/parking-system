"""全部数据类与类型常量。

这里只描述"数据长什么样"，不写业务逻辑，不访问数据库（见 docs/03-架构与接口.md 第三节）。
其他文件使用类型值时，从这里导入常量，不要手写字符串。
"""
from dataclasses import dataclass
from datetime import date, datetime

# ---- 用户角色 ----
ROLE_ADMIN = "admin"        # 管理员
ROLE_GUARD = "guard"        # 门卫
ROLES = (ROLE_ADMIN, ROLE_GUARD)

# ---- 车辆类型 ----
VEHICLE_MONTHLY = "monthly"  # 月租车
VEHICLE_TEMP = "temp"        # 临时车
VEHICLE_VISITOR = "visitor"  # 访客车
VEHICLE_TYPES = (VEHICLE_MONTHLY, VEHICLE_TEMP, VEHICLE_VISITOR)

# ---- 车位状态 ----
SPACE_FREE = "free"            # 空闲
SPACE_OCCUPIED = "occupied"    # 占用
SPACE_RESERVED = "reserved"    # 预约
SPACE_STATUSES = (SPACE_FREE, SPACE_OCCUPIED, SPACE_RESERVED)


@dataclass
class User:
    id: int | None
    username: str
    password_hash: str
    role: str                      # ROLE_ADMIN / ROLE_GUARD


@dataclass
class Resident:
    id: int | None
    name: str
    building: str                  # 楼栋，如 "3号楼"
    room: str                      # 房号，如 "2-501"
    phone: str


@dataclass
class Vehicle:
    id: int | None
    plate: str                     # 车牌号，唯一
    vehicle_type: str              # VEHICLE_MONTHLY / VEHICLE_TEMP / VEHICLE_VISITOR
    resident_id: int | None        # 月租车必填；访客车填被访住户；临时车为空
    monthly_expire: date | None    # 月租到期日，仅月租车有
    note: str = ""


@dataclass
class ParkingSpace:
    id: int | None
    code: str                      # 车位编号，唯一，如 "A-012"
    zone: str                      # 区域，如 "A区"
    status: str                    # SPACE_FREE / SPACE_OCCUPIED / SPACE_RESERVED
    fixed_vehicle_id: int | None   # 固定车位绑定的月租车，可空


@dataclass
class ParkingRecord:
    id: int | None
    plate: str
    vehicle_type: str              # 入场时的车辆类型，之后不随车辆资料变化
    enter_time: datetime
    exit_time: datetime | None     # 为空表示仍在场
    fee: int | None                # 应收金额（元），出场时写入
    space_id: int | None
    operator: str                  # 操作员用户名


@dataclass
class FeeRule:
    vehicle_type: str              # VEHICLE_TEMP / VEHICLE_VISITOR
    free_minutes: int
    hourly_rate: int               # 元
    daily_cap: int                 # 每 24 小时封顶，元


@dataclass
class Reservation:
    id: int | None
    space_id: int
    plate: str
    start_time: datetime
    end_time: datetime
