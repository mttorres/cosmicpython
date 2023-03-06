from datetime import date

import pytest

# inicialmente esse statement vai estar comentado para o teste falhar
# from model import ...
from src.allocation.domain.model import Product, Batch, OrderLine, SkuMismatch

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


def test_add_product_stock_succeed_for_same_sku():
    product = Product('GAMER-MAGAZINE')
    batch_to_stock = Batch('batch-001', 'GAMER-MAGAZINE', 20, eta=None)

    product.add_stock(batch_to_stock)

    assert product.available_quantity == 20


def test_raises_sku_mismatch_exception_if_cannot_stock():
    product = Product('GAMER-MAGAZINE')
    batch_to_stock = Batch('batch-001', 'G-MAGAZINE', 20, eta=None)

    with pytest.raises(SkuMismatch, match="G-MAGAZINE"):
        product.add_stock(batch_to_stock)


def test_add_product_stock_succeed_for_same_sku():
    product = Product('GAMER-MAGAZINE')
    batch_to_stock = Batch('batch-001', 'GAMER-MAGAZINE', 20, eta=None)

    product.add_stock(batch_to_stock)

    assert product.available_quantity == 20


def test_allocating_to_a_batch_reduces_the_available_quantity():
    # Batch(reference, sku, qtd, eta)
    product = Product('SMALL-TABLE',
                      [Batch('batch-001', 'SMALL-TABLE', qty=20, eta=date.today())])
    # OrderLine(order-reference,   sku, qtd)
    line = OrderLine('order-ref', 'SMALL-TABLE', 2)

    product.allocate(line)

    assert product.available_quantity == 18


def test_allocating_to_a_batch_fails_if_available_quantity_is_less():
    # we won't use product cause can_allocate looks like something "very internal"
    batch, line = create_sample_batch_and_line('ELEGANT-LAMP', 2, 4)
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
    assert batch.is_allocated_for_line(different_sku_line) is False
    assert batch.is_allocated_for_order(different_sku_line.orderid) is False


def test_is_allocated_for_true_if_order_is_allocated():
    batch, line = create_sample_batch_and_line("ANGULAR-DESK", 20, 2)
    batch.allocate(line)
    assert batch.is_allocated_for_line(line)
    assert batch.is_allocated_for_order(line.orderid)


def test_can_deallocate_only_allocated_lines():
    unallocated_line = OrderLine("order-123", 'DECORATIVE-TRINKET', 10)
    product = Product('DECORATIVE-TRINKET', [
        Batch("batch-001", 'DECORATIVE-TRINKET', 20, eta=None),
        Batch("batch-002", 'DECORATIVE-TRINKET', 20, eta=date.today())
    ])
    product.deallocate(unallocated_line)
    assert product.available_quantity == 40


def test_allocation_for_same_line_keep_same_quantity():
    line = OrderLine("order-123", 'ANGULAR-DESK', 2)
    product = Product('DECORATIVE-TRINKET', [
        Batch("batch-001", 'ANGULAR-DESK', 20, eta=None),
        Batch("batch-002", 'ANGULAR-DESK', 20, eta=date.today())
    ])
    product.allocate(line)
    product.allocate(line)
    assert product.available_quantity == 38
