"""车牌、手机号等格式校验（负责人 B，REQ-003、REQ-005）。"""


def is_valid_plate(plate: str) -> bool:
    """REQ-005：豫A12345、豫AD12345 合法；A12345、豫A1234、豫a12345 不合法。"""
    raise NotImplementedError("REQ-005 待 B 实现")


def is_valid_phone(phone: str) -> bool:
    """REQ-003：11 位数字且以 1 开头。"""
    if not phone:
        return False
    elif len(phone) != 11:
        return False
    elif phone[0] != '1':
        return False
    else:
        for x in phone:
            if '0' <= x <= '9':
                continue
            else:
                return False
        return True

