from typing import List

from src.allocation.domain import model, events, commands
from src.allocation.service_layer.unit_of_work import AbstractUnitOfWork


# from src.allocation.adapters.repository import SqlAlchemyRepository # testar sem abc.. funciona lindamente!
# mesmo que eu coloque ele como parâmetro da função!


class InvalidSku(Exception):
    pass


def allocate(command: commands.Allocate, uow: AbstractUnitOfWork) -> str:
    line = model.OrderLine(
        command.orderid, command.sku, command.qty
    )
    with uow:
        product = uow.products.get(sku=line.sku)
        if product is None:
            raise InvalidSku(f"Invalid sku {line.sku}")
        batchref = product.allocate(line)
        uow.commit()
    return batchref


def deallocate(orderid: str, sku: str, uow: AbstractUnitOfWork) -> List[str]:
    with uow:
        product = uow.products.get(sku=sku)
        if product is None:
            raise InvalidSku(f"Invalid sku {sku}")
        deallocated_batch_refs = product.deallocate(orderid)
        uow.commit()
    return deallocated_batch_refs


def add_batch(command: commands.CreateBatch, uow: AbstractUnitOfWork):
    with uow:
        product = uow.products.get(sku=command.sku)
        if product is None:
            product = model.Product(command.sku)
            uow.products.add(product)
        product.add_stock(model.Batch(command.ref, command.sku, command.qty, command.eta))
        uow.commit()
    return command.ref


def send_out_of_stock_notification(event: events.OutOfStock, uow: AbstractUnitOfWork):
    email.send_mail(
        "stock@made.com",
        f"Out of stock for {event.sku}",
    )


def change_batch_quantity(command: commands.ChangeBatchQuantity, uow: AbstractUnitOfWork):
    with uow:
        product = uow.products.get_by_batchref(batchref=command.ref)
        product.change_batch_quantity(ref=command.ref, qty=command.qty)
        uow.commit()
