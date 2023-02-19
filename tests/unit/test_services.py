from datetime import date

import pytest

from src.allocation.domain import model
from src.allocation.adapters.repository import FakeRepository
from src.allocation.service_layer import services


# spy?
class FakeSession:
    committed = False

    def commit(self):
        self.committed = True


def test_returns_allocation():
    line = model.OrderLine("o1", "COMPLICATED-LAMP", 10)
    batch = model.Batch("b1", "COMPLICATED-LAMP", 100, eta=None)
    repo = FakeRepository([batch])

    result = services.allocate(line, repo, FakeSession())
    assert result == "b1"


def test_error_for_invalid_sku():
    line = model.OrderLine("o1", "NONEXISTENTSKU", 10)
    batch = model.Batch("b1", "AREALSKU", 100, eta=None)
    repo = FakeRepository([batch])

    with pytest.raises(services.InvalidSku, match="Invalid sku NONEXISTENTSKU"):
        services.allocate(line, repo, FakeSession())


def test_commits():
    line = model.OrderLine("o1", "OMINOUS-MIRROR", 10)
    batch = model.Batch("b1", "OMINOUS-MIRROR", 100, eta=None)
    repo = FakeRepository([batch])
    session = FakeSession()

    services.allocate(line, repo, session)
    assert session.committed is True


def test_returns_deallocation():
    line = model.OrderLine("o1", "COMPLICATED-LAMP", 10)
    batch = model.Batch("b1", "COMPLICATED-LAMP", 100, eta=None)
    non_allocated_batch = model.Batch("b2", "COMPLICATED-LAMP", 100, eta=date.today())
    repo = FakeRepository([batch, non_allocated_batch])
    services.allocate(line, repo, FakeSession())

    results = services.deallocate(line.orderid, line.sku, repo, FakeSession())
    assert "b1" in results
    assert "b2" not in results


def test_deallocate_persists_decrements_to_available_quantity():
    repo = FakeRepository([])
    services.add_batch("b1", "BLUE-PLINTH", 100, None, repo, FakeSession())
    line = model.OrderLine("o1", "BLUE-PLINTH", 10)
    services.allocate(line, repo, FakeSession())

    batch = repo.get(reference="b1")
    assert batch.available_quantity == 90
    services.deallocate("o1", "BLUE-PLINTH", repo, FakeSession())
    assert batch.available_quantity == 100


def test_deallocate_decrements_correct_quantity():
    repo = FakeRepository([])
    services.add_batch("b1", "BLUE-PLINTH", 100, None, repo, FakeSession())
    line = model.OrderLine("o1", "BLUE-PLINTH", 10)
    services.allocate(line, repo, FakeSession())
    batch = repo.get(reference="b1")
    services.add_batch("b2", "RED-PLINTH", 100, None, repo, FakeSession())
    other_batch = repo.get(reference="b2")

    assert batch.available_quantity == 90
    assert other_batch.available_quantity == 100
    services.deallocate("o1", "BLUE-PLINTH", repo, FakeSession())
    assert batch.available_quantity == 100
    assert other_batch.available_quantity == 100
