"""车牌、手机号等格式校验（负责人 B，REQ-003、REQ-005）。"""


def is_valid_plate(plate: str) -> bool:
    """REQ-005：豫A12345、豫AD12345 合法；A12345、豫A1234、豫a12345 不合法。"""
    raise NotImplementedError("REQ-005 待 B 实现")


def is_valid_phone(phone: str) -> bool:
    """REQ-003：11 位数字且以 1 开头。"""
    raise NotImplementedError("REQ-003 待 B 实现")
