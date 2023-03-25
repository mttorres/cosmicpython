import pytest
from datetime import date

from src.allocation.adapters.repository import AbstractProductRepository, track_entity
from src.allocation.domain import events
from src.allocation.service_layer import unit_of_work, messagebus
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


class TestAddBatch:
    def test_add_batch_new_product(self):
        uow = FakeUnitOfWork()
        messagebus.handle(events.BatchCreated("b1", "CRUNCHY-ARMCHAIR", 100, None), uow)
        assert uow.products.get("CRUNCHY-ARMCHAIR") is not None
        assert uow.committed

    def test_add_batch_existing_product(self):
        uow = FakeUnitOfWork()
        messagebus.handle(events.BatchCreated("b1", "CRUNCHY-ARMCHAIR", 100, None), uow)
        messagebus.handle(events.BatchCreated("b2", "GARISH-RUG", 99, None,), uow)
        retrieved_product = uow.products.get("CRUNCHY-ARMCHAIR")
        assert retrieved_product is not None
        assert "b2" in [b.reference for b in uow.products.get("GARISH-RUG").batches]


class TestAllocate:
    def test_returns_allocation(self):
        uow = FakeUnitOfWork()
        messagebus.handle(
            events.BatchCreated("b1", "COMPLICATED-LAMP", 100, None), uow
        )
        results = messagebus.handle(
            events.AllocationRequired("o1", "COMPLICATED-LAMP", 100), uow
        )
        assert results.pop(0) == "b1"

    def test_allocate_errors_for_invalid_sku(self):
        uow = FakeUnitOfWork()
        messagebus.handle(events.BatchCreated("b1", "AREALSKU", 100, None,), uow)

        with pytest.raises(handlers.InvalidSku, match="Invalid sku NONEXISTENTSKU"):
            messagebus.handle(
                events.AllocationRequired("o1", "NONEXISTENTSKU", 10), uow
            )

    def test_commits(self):
        uow_trans_1 = FakeUnitOfWork()
        messagebus.handle(events.BatchCreated("b1", "OMINOUS-MIRROR", 100, None), uow_trans_1)
        assert uow_trans_1.committed
        uow_trans_2 = FakeUnitOfWork(uow_trans_1.products.list())
        messagebus.handle(events.AllocationRequired("o1", "OMINOUS-MIRROR", 10), uow_trans_2)
        assert uow_trans_2.committed


class TestChangeBatchQuantity:
    def test_changes_available_quantity(self):
        uow = FakeUnitOfWork()
        messagebus.handle(
            events.BatchCreated("batch1", "ADORABLE-SETTEE", 100, None),
            uow
        )
        [batch] = uow.products.get(sku="ADORABLE-SETTEE").batches
        assert batch.available_quantity == 100

        messagebus.handle(events.BatchQuantityChanged("batch1", 50), FakeUnitOfWork(uow.products.list()))

        assert batch.available_quantity == 50

    def test_reallocates_if_necessary(self):
        uow = FakeUnitOfWork()
        event_history = [
            events.BatchCreated("batch1", "INDIFFERENT-TABLE", 50, None),
            events.BatchCreated("batch2", "INDIFFERENT-TABLE", 50, date.today()),
            events.AllocationRequired("order1", "INDIFFERENT-TABLE", 20),
            events.AllocationRequired("order2", "INDIFFERENT-TABLE", 20),
        ]
        for e in event_history:
            messagebus.handle(e, uow)
        [batch1, batch2] = uow.products.get(sku="INDIFFERENT-TABLE").batches
        assert batch1.available_quantity == 10
        assert batch2.available_quantity == 50

        messagebus.handle(events.BatchQuantityChanged("batch1", 25), uow)

        # order1 ou order 2 serão desalocadas, assim temos 25 - 20
        assert batch1.available_quantity == 5
        # e 20 será realocado para a próxima batch
        assert batch2.available_quantity == 30


class TestDeallocate:
    pass
    # dunno what to do with Deallocation yet


'''
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

'''