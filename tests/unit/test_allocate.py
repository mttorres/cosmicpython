from datetime import date, timedelta
import pytest

from src.allocation.domain.model import Batch, OrderLine

today = date.today()
tomorrow = today + + timedelta(days=1)
later_ten_days = tomorrow + timedelta(days=10)


def test_allocating_to_a_batch_preferences_warehouse_stock():
    in_stock_batch = Batch("in-stock-batch", "RETRO-CLOCK", 100, eta=None)
    shipment_batch = Batch("shipment-batch", "RETRO-CLOCK", 100, eta=tomorrow)
    line = OrderLine("oref", "RETRO-CLOCK", 10)

    allocate(line, [in_stock_batch, shipment_batch])

    assert in_stock_batch.available_quantity == 90  # escolheu o que está em estoque
    assert shipment_batch.available_quantity == 100


def test_allocating_prefers_earlier_batches():
    earliest = Batch("speedy-batch", "MINIMALIST-SPOON", 100, eta=today)
    medium = Batch("normal-batch", "MINIMALIST-SPOON", 100, eta=tomorrow)
    latest = Batch("slow-batch", "MINIMALIST-SPOON", 100, eta=later_ten_days)
    line = OrderLine("order1", "MINIMALIST-SPOON", 10)

    allocate(line, [medium, earliest, latest])

    assert earliest.available_quantity == 90  # escolheu o que vai chegar mais cedo
    assert medium.available_quantity == 100
    assert latest.available_quantity == 100


def test_returns_allocated_batch_ref():
    in_stock_batch = Batch("in-stock-batch", "RETRO-CLOCK", 100, eta=None)
    shipment_batch = Batch("shipment-batch", "RETRO-CLOCK", 100, eta=tomorrow)
    line = OrderLine("oref", "RETRO-CLOCK", 10)

    allocation_batch_ref = allocate(line, [in_stock_batch, shipment_batch])

    assert allocation_batch_ref == in_stock_batch.reference
