"""计费规则（负责人 D，REQ-012 至 REQ-015）。

全项目体现"面向对象"的核心：三类车用同一个方法名 calc，各自实现不同规则。
类设计见 docs/03-架构与接口.md 第五节。
"""
from abc import ABC, abstractmethod
from datetime import date, datetime

from app.models.entities import FeeRule


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
        raise NotImplementedError("REQ-012 待 D 实现")


class MonthlyFeePolicy(FeePolicy):
    """月租车：出场日期不晚于到期日则免费，否则交给 fallback 计费。"""

    def __init__(self, expire: date, fallback: FeePolicy):
        self.expire = expire
        self.fallback = fallback

    def calc(self, enter: datetime, exit: datetime) -> int:
        raise NotImplementedError("REQ-013 待 D 实现")


def make_policy(vehicle_type: str, monthly_expire: date | None,
                rules: dict[str, FeeRule]) -> FeePolicy:
    """根据车辆类型组装对应的计费策略。"""
    raise NotImplementedError("REQ-012 至 014 待 D 实现")
