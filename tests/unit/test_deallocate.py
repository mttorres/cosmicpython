from datetime import date, timedelta
import pytest

from src.allocation.domain.model import Batch, OrderLine, deallocate, NotAllocated

today = date.today()
tomorrow = today + + timedelta(days=1)
later_ten_days = tomorrow + timedelta(days=10)


def test_deallocating_for_a_orderid_clear_all_orderlines():
    batch = Batch("in-stock-batch", "RETRO-CLOCK", 100, eta=None)
    line1 = OrderLine("oref", "RETRO-CLOCK", 10)
    line2 = OrderLine("oref", "RETRO-CLOCK", 3)
    batch.allocate(line1)
    batch.allocate(line2)

    deallocate("oref", batch)

    assert batch.is_allocated_for_line(line1) is False
    assert batch.is_allocated_for_line(line2) is False
    assert batch.is_allocated_for_order("oref") is False


def test_raises_not_allocated_exception_if_not_found_by_orderid():
    batch = Batch("batch1", "SMALL-FORK", 10, eta=today)
    batch.allocate(OrderLine("order1", "SMALL-FORK", 10))

    with pytest.raises(NotAllocated, match="order1"):
        deallocate("order1", batch)
