from datetime import date, timedelta
import pytest

from src.allocation.adapters.repository import AbstractRepository
from src.allocation.service_layer import unit_of_work
from src.allocation.service_layer import services


class FakeRepository(AbstractRepository):

    def __init__(self, batches):
        self._batches = set(batches)

    def add(self, batch):
        self._batches.add(batch)

    def get(self, reference):
        return next(b for b in self._batches if b.reference == reference)

    def list(self):
        return list(self._batches)

    def get_by_orderid_and_sku(self, orderid, sku):
        return list(b for b in self._batches if b.sku == sku and b.is_allocated_for_order(orderid))


# spy?
class FakeUnitOfWork(unit_of_work.AbstractUnitOfWork):
    def __init__(self):
        self.batches = FakeRepository([])
        self.committed = False

    def commit(self):
        self.committed = True

    def rollback(self):
        pass


def test_add_batch():
    uow = FakeUnitOfWork()
    services.add_batch("b1", "CRUNCHY-ARMCHAIR", 100, None, uow)
    assert uow.batches.get("b1") is not None
    assert uow.committed


def test_returns_allocation():
    uow = FakeUnitOfWork()
    services.add_batch("b1", "COMPLICATED-LAMP", 100, None, uow)
    result = services.allocate("o1", "COMPLICATED-LAMP", 100, uow)
    assert result == "b1"


def test_error_for_invalid_sku():
    uow = FakeUnitOfWork()
    services.add_batch("b1", "AREALSKU", 100, None, uow)

    with pytest.raises(services.InvalidSku, match="Invalid sku NONEXISTENTSKU"):
        services.allocate("o1", "NONEXISTENTSKU", 10, uow)


def test_commits():
    uow = FakeUnitOfWork()
    services.add_batch("b1", "OMINOUS-MIRROR", 100, None, uow)
    services.allocate("o1", "OMINOUS-MIRROR", 10, uow)
    assert uow.committed is True

def test_returns_deallocation():
    uow = FakeUnitOfWork()
    # allocated batch
    services.add_batch("b1", "COMPLICATED-LAMP", 100, None, uow)
    # non-allocated batch
    services.add_batch("b2", "COMPLICATED-LAMP", 100, date.today(), uow)
    services.allocate("o1", "COMPLICATED-LAMP", 10, uow)

    results = services.deallocate("o1", "COMPLICATED-LAMP", uow)
    assert "b1" in results
    assert "b2" not in results


def test_deallocate_persists_decrement_to_the_available_quantity():
    uow = FakeUnitOfWork()
    services.add_batch("b1", "BLUE-PLINTH", 100, None, uow)
    services.allocate("o1", "BLUE-PLINTH", 10, uow)

    batch = uow.batches.get(reference="b1")
    assert batch.available_quantity == 90
    services.deallocate("o1", "BLUE-PLINTH", uow)
    assert batch.available_quantity == 100


def test_deallocate_decrements_correct_quantity():
    uow = FakeUnitOfWork()
    services.add_batch("b1", "BLUE-PLINTH", 100, None, uow)
    services.allocate("o1", "BLUE-PLINTH", 10, uow)
    batch = repo.get(reference="b1")
    services.add_batch("b2", "RED-PLINTH", 100, None, uow)
    other_batch = repo.get(reference="b2")

    assert batch.available_quantity == 90
    assert other_batch.available_quantity == 100
    services.deallocate("o1", "BLUE-PLINTH", uow)
    assert batch.available_quantity == 100
    assert other_batch.available_quantity == 100


def test_prefers_warehouse_batches_to_shipments():
    uow = FakeUnitOfWork()
    # in stock batch
    services.add_batch("in-stock-batch", "RETRO-CLOCK", 100, None, uow)
    # shipment batch
    services.add_batch("shipment-batch", "RETRO-CLOCK", 100, date.today() + timedelta(days=1), uow)

    services.allocate('oref', "RETRO-CLOCK", 10, uow)

    assert uow.batches.get("in-stock-batch").available_quantity == 90
    assert uow.batches.get("shipment-batch").available_quantity == 100
