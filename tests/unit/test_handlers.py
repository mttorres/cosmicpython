import pytest
from datetime import date

from src.allocation.adapters.repository import AbstractProductRepository, track_entity
from src.allocation.domain import events, commands
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

    @track_entity
    def get_by_batchref(self, batchref: str):
        return next(
            (p for p in self._products for b in p.batches if b.reference == batchref),
            None
        )


# spy?
class FakeUnitOfWork(unit_of_work.AbstractUnitOfWork):
    def __init__(self, storage=None):
        self.products = FakeProductRepository(storage if storage is not None else [])
        self.committed = False

    def commit(self):
        self.committed = True

    def rollback(self):
        pass


class FakeMessageBus(messagebus.AbstractMessageBus):
    def __init__(self, uow: unit_of_work.AbstractUnitOfWork):
        self.uow = uow
        self.messages_published = []
        default_fake_handle = self.messages_published.append
        self.EVENT_HANDLERS = {
            events.OutOfStock: [default_fake_handle],
            events.Allocated: [default_fake_handle],
            events.Deallocated: [default_fake_handle, handlers.reallocate]
        }
        self.COMMAND_HANDLERS = {
            commands.Allocate: handlers.allocate,
            commands.CreateBatch: handlers.add_batch,
            commands.ChangeBatchQuantity: handlers.change_batch_quantity
        }

    def handle(self, message: messagebus.Message):
        if isinstance(message, events.Event):
            for handler in self.EVENT_HANDLERS[type(message)]:
                handler(message, self.uow)
        if isinstance(message, commands.Command):
            self.COMMAND_HANDLERS[type(message)](message, self.uow)

        for product in self.uow.products.tracked:
            while product.messages:
                self.messages_published.append(product.messages.pop(0))


class TestAddBatch:
    def test_add_batch_new_product(self):
        uow = FakeUnitOfWork()
        msbus = FakeMessageBus(uow)
        msbus.handle(commands.CreateBatch("b1", "CRUNCHY-ARMCHAIR", 100, None))
        assert uow.products.get("CRUNCHY-ARMCHAIR") is not None
        assert uow.committed

    def test_add_batch_existing_product(self):
        uow = FakeUnitOfWork()
        msbus = FakeMessageBus(uow)
        msbus.handle(commands.CreateBatch("b1", "CRUNCHY-ARMCHAIR", 100, None))
        msbus.handle(commands.CreateBatch("b2", "GARISH-RUG", 99, None, ))
        retrieved_product = uow.products.get("CRUNCHY-ARMCHAIR")
        assert retrieved_product is not None
        assert "b2" in [b.reference for b in uow.products.get("GARISH-RUG").batches]


class TestAllocate:
    def test_returns_allocation(self):
        msbus = FakeMessageBus(FakeUnitOfWork())
        msbus.handle(
            commands.CreateBatch("b1", "COMPLICATED-LAMP", 100, None)
        )

        msbus.handle(
            commands.Allocate("o1", "COMPLICATED-LAMP", 100)
        )
        allocation_event = msbus.messages_published[-1]
        assert isinstance(allocation_event, events.Allocated)
        assert allocation_event.batchref == "b1"
        assert allocation_event.sku == "COMPLICATED-LAMP"

    def test_allocate_errors_for_invalid_sku(self):
        msbus = FakeMessageBus(FakeUnitOfWork())
        msbus.handle(commands.CreateBatch("b1", "AREALSKU", 100, None, ))

        with pytest.raises(handlers.InvalidSku, match="Invalid sku NONEXISTENTSKU"):
            msbus.handle(
                commands.Allocate("o1", "NONEXISTENTSKU", 10)
            )

    def test_commits(self):
        uow_trans_1 = FakeUnitOfWork()
        msbus = FakeMessageBus(uow_trans_1)
        msbus.handle(commands.CreateBatch("b1", "OMINOUS-MIRROR", 100, None))
        assert uow_trans_1.committed
        uow_trans_2 = FakeUnitOfWork(msbus.uow.products.list())
        msbus.uow = uow_trans_2
        msbus.handle(commands.Allocate("o1", "OMINOUS-MIRROR", 10))
        assert uow_trans_2.committed


class TestChangeBatchQuantity:
    def test_changes_available_quantity(self):
        uow = FakeUnitOfWork()
        msbus = FakeMessageBus(uow)
        msbus.handle(
            commands.CreateBatch("batch1", "ADORABLE-SETTEE", 100, None),
        )
        [batch] = uow.products.get(sku="ADORABLE-SETTEE").batches
        assert batch.available_quantity == 100

        msbus.handle(commands.ChangeBatchQuantity("batch1", 50))

        assert batch.available_quantity == 50

    def test_issues_reallocation_if_necessary(self):
        uow = FakeUnitOfWork()
        msbus = FakeMessageBus(uow)
        event_history = [
            commands.CreateBatch("batch1", "INDIFFERENT-TABLE", 50, None),
            commands.CreateBatch("batch2", "INDIFFERENT-TABLE", 50, date.today()),
            commands.Allocate("order1", "INDIFFERENT-TABLE", 20),
            commands.Allocate("order2", "INDIFFERENT-TABLE", 20),
        ]
        for e in event_history:
            msbus.handle(e)
        [batch1, batch2] = uow.products.get(sku="INDIFFERENT-TABLE").batches
        assert batch1.available_quantity == 10
        assert batch2.available_quantity == 50

        msbus.handle(commands.ChangeBatchQuantity("batch1", 25))

        '''
        # order1 ou order 2 serão desalocadas, assim temos 25 - 20
        assert batch1.available_quantity == 5
        # e 20 será realocado para a próxima batch
        assert batch2.available_quantity == 30
        '''
        # ao invés de verificar todos os sideeffects agora verificamos só se o evento foi emitido!
        # assert on new events emitted rather than downstream side-effects
        reallocation_event = msbus.messages_published[-1]
        assert isinstance(reallocation_event, events.Deallocated)
        assert reallocation_event.orderid in {"order1", "order2"}
        assert reallocation_event.sku == "INDIFFERENT-TABLE"


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
