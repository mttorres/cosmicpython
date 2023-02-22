from datetime import date, timedelta
import pytest

from src.allocation.adapters.repository import FakeRepository
from src.allocation.service_layer import services


# spy?
class FakeSession:
    committed = False

    def commit(self):
        self.committed = True


def test_add_batch():
    repo, session = FakeRepository([]), FakeSession()
    services.add_batch("b1", "CRUNCHY-ARMCHAIR", 100, None, repo, session)
    assert repo.get("b1") is not None
    assert session.committed


def test_returns_allocation():
    repo, session = FakeRepository([]), FakeSession()
    services.add_batch("b1", "COMPLICATED-LAMP", 100, None, repo, session)
    result = services.allocate("o1", "COMPLICATED-LAMP", 100, repo, FakeSession())
    assert result == "b1"


def test_error_for_invalid_sku():
    repo, session = FakeRepository([]), FakeSession()
    services.add_batch("b1", "AREALSKU", 100, None, repo, session)

    with pytest.raises(services.InvalidSku, match="Invalid sku NONEXISTENTSKU"):
        services.allocate("o1", "NONEXISTENTSKU", 10,  repo, FakeSession())


def test_commits():
    repo, session = FakeRepository([]), FakeSession()
    services.add_batch("b1", "OMINOUS-MIRROR", 100, None, repo, session)
    services.allocate("o1", "OMINOUS-MIRROR", 10, repo, session)
    assert session.committed is True


def test_returns_deallocation():
    repo = FakeRepository([])
    # allocated batch
    services.add_batch("b1", "COMPLICATED-LAMP", 100, None, repo, FakeSession())
    # non-allocated batch
    services.add_batch("b2", "COMPLICATED-LAMP", 100, date.today(), repo, FakeSession())
    services.allocate("o1", "COMPLICATED-LAMP", 10, repo, FakeSession())

    results = services.deallocate("o1", "COMPLICATED-LAMP", repo, FakeSession())
    assert "b1" in results
    assert "b2" not in results


def test_deallocate_persists_decrement_to_the_available_quantity():
    repo = FakeRepository([])
    services.add_batch("b1", "BLUE-PLINTH", 100, None, repo, FakeSession())
    services.allocate("o1", "BLUE-PLINTH", 10, repo, FakeSession())

    batch = repo.get(reference="b1")
    assert batch.available_quantity == 90
    services.deallocate("o1", "BLUE-PLINTH", repo, FakeSession())
    assert batch.available_quantity == 100


def test_deallocate_decrements_correct_quantity():
    repo = FakeRepository([])
    services.add_batch("b1", "BLUE-PLINTH", 100, None, repo, FakeSession())
    services.allocate("o1", "BLUE-PLINTH", 10, repo, FakeSession())
    batch = repo.get(reference="b1")
    services.add_batch("b2", "RED-PLINTH", 100, None, repo, FakeSession())
    other_batch = repo.get(reference="b2")

    assert batch.available_quantity == 90
    assert other_batch.available_quantity == 100
    services.deallocate("o1", "BLUE-PLINTH", repo, FakeSession())
    assert batch.available_quantity == 100
    assert other_batch.available_quantity == 100


def test_prefers_warehouse_batches_to_shipments():
    repo = FakeRepository([])
    session = FakeSession()
    # in stock batch
    services.add_batch("in-stock-batch", "RETRO-CLOCK", 100, None, repo, session)
    # shipment batch
    services.add_batch("shipment-batch", "RETRO-CLOCK", 100, date.today() + timedelta(days=1), repo, session)

    services.allocate('oref', "RETRO-CLOCK", 10, repo, session)

    assert repo.get("in-stock-batch").available_quantity == 90
    assert repo.get("shipment-batch").available_quantity == 100

