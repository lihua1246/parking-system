"""计费规则（REQ-012 至 REQ-014；原属 D，见任务卡 A-5）。

全项目体现"面向对象"的核心：三类车用同一个方法名 calc，各自实现不同规则。
类设计见 docs/03-架构与接口.md 第五节；算法和验收示例见 docs/02-需求清单.md「计费规则」。

- 抽象类与抽象方法：FeePolicy.calc 只规定"怎么调用"，不规定"怎么算"
- 继承与多态：HourlyFeePolicy、MonthlyFeePolicy 各自实现 calc，调用方不写 if 车辆类型
- 组合：MonthlyFeePolicy 内部持有一个 fallback 策略，过期后交给它计费
"""
from abc import ABC, abstractmethod
from datetime import date, datetime

from app.models.entities import FeeRule, VEHICLE_MONTHLY, VEHICLE_TEMP, VEHICLE_VISITOR

MINUTES_PER_HOUR = 60
MINUTES_PER_PERIOD = 24 * MINUTES_PER_HOUR      # 每 24 小时为一个封顶周期
EXIT_BEFORE_ENTER_MSG = "出场时间不能早于入场时间"
UNKNOWN_TYPE_MSG = "未知的车辆类型"
NO_RULE_MSG = "缺少该车辆类型的收费规则"


def parked_minutes(enter: datetime, exit: datetime) -> int:
    """停车时长（分钟），不足 1 分钟的秒数舍去。exit 早于 enter 时抛 ValueError。"""
    if exit < enter:
        raise ValueError(EXIT_BEFORE_ENTER_MSG)
    return int((exit - enter).total_seconds()) // MINUTES_PER_HOUR


class FeePolicy(ABC):
    """计费策略的抽象基类。"""

    @abstractmethod
    def calc(self, enter: datetime, exit: datetime) -> int:
        """返回应收金额（元）。exit 早于 enter 时抛出 ValueError。"""


class HourlyFeePolicy(FeePolicy):
    """按小时计费，带免费时长和每 24 小时封顶。临时车和访客车使用。"""

    def __init__(self, rule: FeeRule):
        self.rule = rule

    def calc(self, enter: datetime, exit: datetime) -> int:
        minutes = parked_minutes(enter, exit)
        if minutes <= self.rule.free_minutes:          # 不超过免费时长（含恰好等于）：0 元
            return 0
        # 超过免费时长：按全部时长计费，不扣除免费时长；每 24 小时一个周期
        full_periods, rest = divmod(minutes, MINUTES_PER_PERIOD)
        fee = full_periods * self._period_fee(MINUTES_PER_PERIOD)
        if rest:
            fee += self._period_fee(rest)
        return fee

    def _period_fee(self, minutes: int) -> int:
        """一个周期的费用：小时数向上取整 × 单价，不超过封顶。"""
        hours = -(-minutes // MINUTES_PER_HOUR)          # 向上取整，不足 1 小时按 1 小时
        return min(hours * self.rule.hourly_rate, self.rule.daily_cap)


class MonthlyFeePolicy(FeePolicy):
    """月租车：出场日期不晚于到期日则免费，否则交给 fallback 计费。"""

    def __init__(self, expire: date, fallback: FeePolicy):
        self.expire = expire
        self.fallback = fallback

    def calc(self, enter: datetime, exit: datetime) -> int:
        parked_minutes(enter, exit)                     # 先校验时间顺序
        if exit.date() <= self.expire:                  # 到期日当天出场仍免费
            return 0
        return self.fallback.calc(enter, exit)


def make_policy(vehicle_type: str, monthly_expire: date | None,
                rules: dict[str, FeeRule]) -> FeePolicy:
    """根据车辆类型组装对应的计费策略。

    月租车过期后按临时车计费；没有到期日的月租车（例如车辆资料已被删除）直接按临时车计费。
    """
    if vehicle_type not in (VEHICLE_MONTHLY, VEHICLE_TEMP, VEHICLE_VISITOR):
        raise ValueError(UNKNOWN_TYPE_MSG)
    rule_type = VEHICLE_TEMP if vehicle_type == VEHICLE_MONTHLY else vehicle_type
    if rule_type not in rules:
        raise ValueError(NO_RULE_MSG)
    hourly = HourlyFeePolicy(rules[rule_type])
    if vehicle_type == VEHICLE_MONTHLY and monthly_expire is not None:
        return MonthlyFeePolicy(monthly_expire, hourly)
    return hourly
