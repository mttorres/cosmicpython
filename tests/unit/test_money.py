import pytest

from src.commons.money import Money


def test_can_add_money_values_for_same_currency():
    fiver = Money('gbp', 5)
    tenner = Money('gbp', 10)
    assert fiver + fiver == tenner


def test_can_subtract_money_values():
    fiver = Money('gbp', 5)
    tenner = Money('gbp', 10)
    assert tenner - fiver == fiver


def test_subtracting_results_negative_fails():
    with pytest.raises(ValueError):
        fiver = Money('gbp', 5)
        tenner = Money('gbp', 10)
        fiver - tenner


def test_adding_different_currencies_fails():
    with pytest.raises(ValueError):
        Money('usd', 10) + Money('gbp', 10)


def test_can_multiply_money_by_a_number():
    assert Money('gbp', 5) * 5 == Money('gbp', 25)


def test_multiplying_two_money_values_is_an_error():
    with pytest.raises(TypeError):
        fiver = Money('gbp', 5)
        tenner = Money('gbp', 10)
        tenner * fiver
