from datetime import date

import pytest

from src.allocation.adapters.repository import AbstractProductRepository, track_entity
from src.allocation.service_layer import unit_of_work
from src.allocation.service_layer import handlers


class FakeProductRepository(AbstractProductRepository):

    def __init__(self, products):
        self._products = set(products)
        self.tracked = set()

    @track_entity
    def add(self, product):
        self._products.add(product)

    @track_entity
    def get(self, sku: str):
        return next((p for p in self._products if p.sku == sku), None)

    @track_entity
    def list(self):
        return list(self._products)


# spy?
class FakeUnitOfWork(unit_of_work.AbstractUnitOfWork):
    def __init__(self, storage=None):
        self.products = FakeProductRepository(storage if storage is not None else [])
        self.committed = False

    def commit(self):
        self.committed = True

    def rollback(self):
        pass


def test_add_batch_new_product():
    uow = FakeUnitOfWork()
    services.add_batch("b1", "CRUNCHY-ARMCHAIR", 100, None, uow)
    assert uow.products.get("CRUNCHY-ARMCHAIR") is not None
    assert uow.committed


def test_add_batch_existing_product():
    uow = FakeUnitOfWork()
    services.add_batch("b1", "CRUNCHY-ARMCHAIR", 100, None, uow)
    services.add_batch("b2", "GARISH-RUG", 99, None, uow)
    retrieved_product = uow.products.get("CRUNCHY-ARMCHAIR")
    assert retrieved_product is not None
    assert "b2" in [b.reference for b in uow.products.get("GARISH-RUG").batches]


def test_returns_allocation():
    uow = FakeUnitOfWork()
    services.add_batch("b1", "COMPLICATED-LAMP", 100, None, uow)
    result = services.allocate("o1", "COMPLICATED-LAMP", 100, uow)
    assert result == "b1"


def test_allocate_errors_for_invalid_sku():
    uow = FakeUnitOfWork()
    services.add_batch("b1", "AREALSKU", 100, None, uow)

    with pytest.raises(services.InvalidSku, match="Invalid sku NONEXISTENTSKU"):
        services.allocate("o1", "NONEXISTENTSKU", 10, uow)


def test_commits():
    uow_trans_1 = FakeUnitOfWork()
    services.add_batch("b1", "OMINOUS-MIRROR", 100, None, uow_trans_1)
    assert uow_trans_1.committed
    uow_trans_2 = FakeUnitOfWork(uow_trans_1.products.list())
    services.allocate("o1", "OMINOUS-MIRROR", 10, uow_trans_2)
    assert uow_trans_2.committed


def test_returns_deallocation():
    uow = FakeUnitOfWork()
    # allocated batch for o1
    services.add_batch("b1", "COMPLICATED-LAMP", 100, None, uow)
    services.allocate("o1", "COMPLICATED-LAMP", 10, uow)

    # non-allocated for o1 batch
    services.add_batch("b2", "COMPLICATED-LAMP", 100, date.today(), uow)
    services.allocate("o2", "COMPLICATED-LAMP", 10, uow)

    results = services.deallocate("o1", "COMPLICATED-LAMP", uow)
    assert "b1" in results
    assert "b2" not in results


def test_deallocation_returns_empty_if_not_allocated():
    uow = FakeUnitOfWork()
    # allocated batch for o1
    services.add_batch("b1", "COMPLICATED-LAMP", 100, None, uow)

    results = services.deallocate("o1", "COMPLICATED-LAMP", uow)
    assert results == []


def test_deallocate_persists_decrement_to_the_available_quantity():
    uow = FakeUnitOfWork()
    services.add_batch("b1", "BLUE-PLINTH", 100, None, uow)
    services.allocate("o1", "BLUE-PLINTH", 10, uow)

    product = uow.products.get(sku="BLUE-PLINTH")
    assert product.available_quantity == 90
    services.deallocate("o1", "BLUE-PLINTH", uow)
    assert product.available_quantity == 100


def test_deallocate_errors_for_invalid_sku():
    uow = FakeUnitOfWork()

    with pytest.raises(services.InvalidSku, match="Invalid sku NONEXISTENTSKU"):
        services.allocate("o1", "NONEXISTENTSKU", 10, uow)


def test_deallocating_for_a_orderid_clear_all_orderlines():
    uow = FakeUnitOfWork()
    services.add_batch("in-stock-batch", "RETRO-CLOCK", 100, None, uow=uow)
    services.add_batch("almost-arriving-batch", "RETRO-CLOCK", 100, None, uow=uow)
    services.allocate("oref", "RETRO-CLOCK", 10, uow)
    services.allocate("oref", "RETRO-CLOCK", 3, uow)

    product = uow.products.get(sku="RETRO-CLOCK")
    assert product.available_quantity == 187

    services.deallocate("oref", "RETRO-CLOCK", uow)

    assert product.is_allocated_for_order("oref") is False
    assert product.available_quantity == 200


def test_can_handle_events():
    pytest.fail("Next chapter")