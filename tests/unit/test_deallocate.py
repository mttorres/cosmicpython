from src.allocation.domain.model import Batch, OrderLine, deallocate


def test_deallocating_for_a_orderid_clear_all_orderlines():
    batch = Batch("in-stock-batch", "RETRO-CLOCK", 100, eta=None)
    batch_non_allocated = Batch("in-stock-batch", "RETRO-CLOCK", 100, eta=None)
    line1 = OrderLine("oref", "RETRO-CLOCK", 10)
    line2 = OrderLine("oref", "RETRO-CLOCK", 3)
    batch.allocate(line1)
    batch.allocate(line2)

    deallocate("oref", [batch, batch_non_allocated])

    assert batch.is_allocated_for_line(line1) is False
    assert batch.is_allocated_for_line(line2) is False
    assert batch_non_allocated.is_allocated_for_line(line1) is False
    assert batch_non_allocated.is_allocated_for_line(line2) is False
