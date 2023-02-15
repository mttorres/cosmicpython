from datetime import date
import pytest

# inicialmente esse statement vai estar comentado para o teste falhar
# from model import ...
from src.allocation.domain.model import Batch, OrderLine

'''
"The name of our unit test describes the behavior that we want to see from the system, 
and the names of the classes and variables that we use are taken from the business jargon. 
We could show this code to our nontechnical coworkers, and they would agree that this 
correctly describes the behavior of the system."
'''


def create_sample_batch_and_line(sku, batch_qty, line_qty):
    return (
        Batch("batch-001", sku, batch_qty, eta=date.today()),
        OrderLine("order-123", sku, line_qty),
    )


def test_allocating_to_a_batch_reduces_the_available_quantity():
    # Batch(reference, sku, qtd, eta)
    batch = Batch('batch-001', 'SMALL-TABLE', qty=20, eta=date.today())
    # note que essa order reference possivelmente é da ordem pai (que deve ser o aggregate)
    # OrderLine(order-reference,   sku, qtd)
    line = OrderLine('order-ref', 'SMALL-TABLE', 2)

    batch.allocate(line)

    assert batch.available_quantity == 18


def test_allocating_for_a_line_creates_order_collection():
    batch = Batch('batch-001', 'SMALL-TABLE', qty=20, eta=date.today())
    line1 = OrderLine('order-ref1', 'SMALL-TABLE', 2)
    line2 = OrderLine('order-ref2', 'SMALL-TABLE', 4)

    batch.allocate(line1)
    batch.allocate(line2)

    assert 2 in batch.quantities_per_order(line1.orderid)
    assert 4 in batch.quantities_per_order(line2.orderid)


def test_allocating_to_a_batch_fails_if_available_quantity_is_less():
    batch, line = create_sample_batch_and_line("ELEGANT-LAMP", 2, 4)
    assert batch.can_allocate(line) is False


def test_allocating_fails_if_skus_do_not_match():
    batch = Batch("batch-001", "UNCOMFORTABLE-CHAIR", 100, eta=None)
    different_sku_line = OrderLine("order-123", "EXPENSIVE-TOASTER", 10)
    assert batch.can_allocate(different_sku_line) is False


def test_can_allocate_if_available_quantity_is_greater():
    batch, line = create_sample_batch_and_line("ELEGANT-LAMP", 20, 2)
    assert batch.can_allocate(line)


def test_can_allocate_if_available_quantity_is_equal():
    batch, line = create_sample_batch_and_line("ELEGANT-LAMP", 2, 2)
    assert batch.can_allocate(line)


def test_is_allocated_for_false_if_order_not_allocated():
    batch = Batch("batch-001", "UNCOMFORTABLE-CHAIR", 100, eta=None)
    different_sku_line = OrderLine("order-123", "EXPENSIVE-TOASTER", 10)
    assert batch.is_allocated_for_order(different_sku_line.orderid) is False


def test_is_allocated_for_true_if_order_is_allocated():
    batch, line = create_sample_batch_and_line("ANGULAR-DESK", 20, 2)
    batch.allocate(line)
    assert batch.is_allocated_for_order(line.orderid)


def test_can_deallocate_only_allocated_lines():
    batch, unallocated_line = create_sample_batch_and_line("DECORATIVE-TRINKET", 20, 2)
    batch.deallocate(unallocated_line)
    assert batch.available_quantity == 20


def test_allocation_for_same_line_keep_same_quantity():
    batch, line = create_sample_batch_and_line("ANGULAR-DESK", 20, 2)
    batch.allocate(line)
    batch.allocate(line)
    assert batch.available_quantity == 18


def test_allocating_for_same_line_maintains_order_collection():
    batch, line = create_sample_batch_and_line("ANGULAR-DESK", 20, 2)
    batch.allocate(line)
    batch.allocate(line)
    assert 2 in batch.quantities_per_order(line.orderid)

