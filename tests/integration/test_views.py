from datetime import date

from src.allocation.domain import commands
from src.allocation.service_layer import unit_of_work
from src.allocation.service_layer.messagebus import MessageBus
from src.allocation.views import views

today = date.today()


def test_allocations_view(session_factory):
    uow = unit_of_work.SqlAlchemyUnitOfWork(session_factory)
    msbus = MessageBus(uow)
    msbus.handle(commands.CreateBatch("sku1batch", "sku1", 50, None))
    msbus.handle(commands.CreateBatch("sku2batch", "sku2", 50, today))
    msbus.handle(commands.Allocate("order1", "sku1", 20))
    msbus.handle(commands.Allocate("order1", "sku2", 20))

    msbus.handle(commands.CreateBatch("sku1batch-later", "sku1", 50, today))
    msbus.handle(commands.Allocate("otherorder", "sku1", 30))
    msbus.handle(commands.Allocate("otherorder", "sku2", 10))

    assert views.allocations("order1", uow) == [
        {"sku": "sku1", "batchref": "sku1batch"},
        {"sku": "sku2", "batchref": "sku2batch"},
    ]