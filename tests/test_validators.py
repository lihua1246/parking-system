"""REQ-003 验收条件 3：手机号 11 位数字且以 1 开头；REQ-005 车牌格式（负责人 B）。"""
import pytest

from app.services.validators import is_valid_phone, is_valid_plate


@pytest.mark.parametrize("plate", ["豫A12345", "豫AD12345"])
def test_req005_valid_plates_accepted(plate):
    assert is_valid_plate(plate) is True


@pytest.mark.parametrize("plate", ["A12345", "豫A1234", "豫a12345"])
def test_req005_invalid_plates_rejected(plate):
    assert is_valid_plate(plate) is False


def test_req005_empty_plate_rejected():
    assert is_valid_plate("") is False


def test_req003_valid_phone_accepted():
    assert is_valid_phone("13800000000") is True


def test_req003_phone_10_digits_rejected():
    assert is_valid_phone("1380000000") is False


def test_req003_phone_must_start_with_1():
    assert is_valid_phone("23800000000") is False


def test_req003_phone_with_space_rejected():
    assert is_valid_phone("138 0000 0000") is False


def test_req003_phone_with_letter_rejected():
    assert is_valid_phone("1380000000a") is False


def test_req003_empty_phone_rejected():
    assert is_valid_phone("") is False