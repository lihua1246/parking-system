"""收费规则修改（负责人 A，REQ-015，任务卡 A-4）。

规则（任务卡 A-4 规则 2 至 4）：
- 免费时长（分钟）、每小时单价、封顶金额（元）都是整数，且不能为负数
- 封顶金额不能小于每小时单价，否则停 1 小时就封顶，规则自相矛盾
- 只能修改已有的规则（临时车、访客车），不新增车辆类型

任何一条不通过都抛 ValueError（消息可直接显示在界面上），且数据库不变。
"""
from app.models.entities import FeeRule

RULE_NOT_FOUND_MSG = "该车辆类型没有收费规则"
NOT_INTEGER_MSG = "免费时长、每小时单价、封顶金额必须是整数"
NEGATIVE_MSG = "免费时长、每小时单价、封顶金额不能为负数"
CAP_BELOW_RATE_MSG = "封顶金额不能小于每小时单价"


def update_rule(fee_rule_repo, vehicle_type: str, free_minutes: int,
                hourly_rate: int, daily_cap: int) -> None:
    """校验通过后保存新规则；不通过时抛 ValueError，数据库不变。"""
    if fee_rule_repo.get(vehicle_type) is None:
        raise ValueError(RULE_NOT_FOUND_MSG)
    values = (free_minutes, hourly_rate, daily_cap)
    # bool 是 int 的子类（True == 1），单独排除，避免 True 被当成 1 元存进去
    if any(not isinstance(v, int) or isinstance(v, bool) for v in values):
        raise ValueError(NOT_INTEGER_MSG)
    if any(v < 0 for v in values):
        raise ValueError(NEGATIVE_MSG)
    if daily_cap < hourly_rate:
        raise ValueError(CAP_BELOW_RATE_MSG)
    fee_rule_repo.update(FeeRule(vehicle_type, free_minutes, hourly_rate, daily_cap))
