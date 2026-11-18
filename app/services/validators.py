"""车牌、手机号等格式校验（负责人 B，REQ-003、REQ-005）。"""
import re

# 省份简称 + 发牌机关大写字母 + 5 位（普通车）或 6 位（新能源）大写字母/数字
_PROVINCES = "京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤青藏川宁琼"
_PLATE_RE = re.compile(rf"[{_PROVINCES}][A-Z][A-Z0-9]{{5,6}}")


def is_valid_plate(plate: str) -> bool:
    """REQ-005：豫A12345、豫AD12345 合法；A12345、豫A1234、豫a12345 不合法。"""
    return bool(plate) and _PLATE_RE.fullmatch(plate) is not None


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

