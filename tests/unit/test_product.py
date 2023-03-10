from datetime import date, timedelta

import pytest

# inicialmente esse statement vai estar comentado para o teste falhar
# from model import ...
from src.allocation.domain.model import Product, Batch, OrderLine, OutOfStock

'''
"The name of our unit test describes the behavior that we want to see from the system, 
and the names of the classes and variables that we use are taken from the business jargon. 
We could show this code to our nontechnical coworkers, and they would agree that this 
correctly describes the behavior of the system."
'''

today = date.today()
tomorrow = today + timedelta(days=1)
later = tomorrow + timedelta(days=10)


def create_sample_batch_and_line(sku, batch_qty, line_qty):
    return (
        Batch("batch-001", sku, batch_qty, eta=date.today()),
        OrderLine("order-123", sku, line_qty),
    )


def test_is_allocated_for_false_if_order_not_allocated():
    product = Product("UNCOMFORTABLE-CHAIR", [Batch("batch-001", "UNCOMFORTABLE-CHAIR", 100, eta=None)])
    different_sku_line = OrderLine("order-123", "EXPENSIVE-TOASTER", 10)
    assert product.is_allocated_for_line(different_sku_line) is False
    assert product.is_allocated_for_order(different_sku_line.orderid) is False


def test_is_allocated_for_true_if_order_is_allocated():
    batch, line = create_sample_batch_and_line("ANGULAR-DESK", 20, 2)
    batch.allocate(line)
    product = Product(batch.sku, [batch])
    assert product.is_allocated_for_line(line)
    assert product.is_allocated_for_order(line.orderid)


def test_prefers_warehouse_batches_to_shipments():
    in_stock_batch = Batch("in-stock-batch", "RETRO-CLOCK", 100, eta=None)
    shipment_batch = Batch("shipment-batch", "RETRO-CLOCK", 100, eta=tomorrow)
    product = Product(sku="RETRO-CLOCK", batches=[in_stock_batch, shipment_batch])
    line = OrderLine("oref", "RETRO-CLOCK", 10)

    product.allocate(line)

    assert in_stock_batch.available_quantity == 90
    assert shipment_batch.available_quantity == 100
    assert product.available_quantity == 190


def test_prefers_earlier_batches():
    earliest = Batch("speedy-batch", "MINIMALIST-SPOON", 100, eta=today)
    medium = Batch("normal-batch", "MINIMALIST-SPOON", 100, eta=tomorrow)
    latest = Batch("slow-batch", "MINIMALIST-SPOON", 100, eta=later)
    product = Product(sku="MINIMALIST-SPOON", batches=[medium, earliest, latest])
    line = OrderLine("order1", "MINIMALIST-SPOON", 10)

    product.allocate(line)

    assert earliest.available_quantity == 90
    assert medium.available_quantity == 100
    assert latest.available_quantity == 100
    assert product.available_quantity == 290



def test_raises_out_of_stock_exception_if_cannot_allocate():
    batch = Batch("batch1", "SMALL-FORK", 10, eta=today)
    product = Product(sku="SMALL-FORK", batches=[batch])
    product.allocate(OrderLine("order1", "SMALL-FORK", 10))

    with pytest.raises(OutOfStock, match="SMALL-FORK"):
        product.allocate(OrderLine("order2", "SMALL-FORK", 1))


@pytest.mark.skip
def test_increments_version_number():
    line = OrderLine("oref", "SCANDI-PEN", 10)
    product = Product(
        sku="SCANDI-PEN", batches=[Batch("b1", "SCANDI-PEN", 100, eta=None)]
    )
    product.version_number = 7
    product.allocate(line)
    assert product.version_number == 8
