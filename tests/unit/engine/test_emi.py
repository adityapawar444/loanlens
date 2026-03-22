from decimal import Decimal

import pytest

from loanlens.engine.emi import calculate_emi, calculate_monthly_rate


def test_calculate_monthly_rate() -> None:
    assert calculate_monthly_rate(Decimal("8.75")) == Decimal("0.007291666666666666666666666667")


def test_calculate_emi_known_value() -> None:
    # Independent calculators and the standard formula both yield 44,186 here.
    assert calculate_emi(Decimal("5000000"), Decimal("8.75"), 240, "rupee") == Decimal("44186")


def test_calculate_emi_ten_rounding() -> None:
    assert calculate_emi(Decimal("5000000"), Decimal("8.75"), 240, "ten") == Decimal("44186")


def test_calculate_emi_single_month() -> None:
    assert calculate_emi(Decimal("100000"), Decimal("12"), 1, "rupee") == Decimal("101000")


def test_calculate_emi_zero_roi() -> None:
    assert calculate_emi(Decimal("120000"), Decimal("0"), 12, "rupee") == Decimal("10000")


def test_calculate_emi_rejects_invalid_inputs() -> None:
    with pytest.raises(ValueError):
        calculate_emi(Decimal("-1"), Decimal("10"), 12, "rupee")


def test_calculate_emi_zero_principal_and_invalid_rounding() -> None:
    assert calculate_emi(Decimal("0"), Decimal("10"), 12, "rupee") == Decimal("0")
    with pytest.raises(ValueError):
        calculate_emi(Decimal("1000"), Decimal("10"), 12, "bad")  # type: ignore[arg-type]
