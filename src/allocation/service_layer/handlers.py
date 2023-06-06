from dataclasses import asdict
from typing import List, Dict, Type, Callable

from sqlalchemy import text

from src.allocation.adapters import redis_eventpublisher
from src.allocation.domain import model, events, commands
from src.allocation.service_layer.unit_of_work import AbstractUnitOfWork, SqlAlchemyUnitOfWork


# from src.allocation.adapters.repository import SqlAlchemyRepository # testar sem abc.. funciona lindamente!
# mesmo que eu coloque ele como parâmetro da função!


class InvalidSku(Exception):
    pass


def allocate(command: commands.Allocate, uow: AbstractUnitOfWork):
    line = model.OrderLine(
        command.orderid, command.sku, command.qty
    )
    with uow:
        product = uow.products.get(sku=line.sku)
        if product is None:
            raise InvalidSku(f"Invalid sku {line.sku}")
        product.allocate(line)
        uow.commit()


def add_batch(command: commands.CreateBatch, uow: AbstractUnitOfWork):
    with uow:
        product = uow.products.get(sku=command.sku)
        if product is None:
            product = model.Product(command.sku)
            uow.products.add(product)
        product.add_stock(model.Batch(command.ref, command.sku, command.qty, command.eta))
        uow.commit()


def send_out_of_stock_notification(event: events.OutOfStock, notifications: Callable):
    notifications(
        "stock@made.com",
        f"Out of stock for {event.sku}",
    )


def change_batch_quantity(command: commands.ChangeBatchQuantity, uow: AbstractUnitOfWork):
    with uow:
        product = uow.products.get_by_batchref(batchref=command.ref)
        product.change_batch_quantity(ref=command.ref, qty=command.qty)
        uow.commit()


def reallocate(event: events.Deallocated, uow: AbstractUnitOfWork):
    with uow:
        product = uow.products.get(sku=event.sku)
        product.messages.append(commands.Allocate(**asdict(event)))
        uow.commit()


def publish_allocated_event(
        event: events.Allocated,
        uow: AbstractUnitOfWork,
):
    redis_eventpublisher.publish("line_allocated", event)


def add_allocation_to_read_model(event: events.Allocated, uow: SqlAlchemyUnitOfWork):
    with uow:
        uow.session.execute(text(
            """
            INSERT INTO allocations_view (orderid, sku, batchref)
            VALUES (:orderid, :sku, :batchref)
            """),
            dict(orderid=event.orderid, sku=event.sku, batchref=event.batchref),
        )
        uow.commit()


def remove_allocation_from_read_model(
        event: events.Deallocated,
        uow: SqlAlchemyUnitOfWork,
):
    with uow:
        uow.session.execute(text(
            """
            DELETE FROM allocations_view
            WHERE orderid = :orderid AND sku = :sku
            """),
            dict(orderid=event.orderid, sku=event.sku),
        )
        uow.commit()


EVENT_HANDLERS = {
    events.Allocated: [publish_allocated_event, add_allocation_to_read_model],
    events.Deallocated: [remove_allocation_from_read_model, reallocate],
    events.OutOfStock: [send_out_of_stock_notification],
}  # type: Dict[Type[events.Event], List[Callable]]

COMMAND_HANDLERS = {
    commands.Allocate: allocate,
    commands.CreateBatch: add_batch,
    commands.ChangeBatchQuantity: change_batch_quantity,
}  # type: Dict[Type[commands.Command], Callable]
