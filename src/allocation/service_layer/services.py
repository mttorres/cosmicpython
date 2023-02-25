from datetime import date
from typing import List, Optional

from src.allocation.domain import model
from src.allocation.service_layer.unit_of_work import AbstractUnitOfWork


# from src.allocation.adapters.repository import SqlAlchemyRepository # testar sem abc.. funciona lindamente!
# mesmo que eu coloque ele como parâmetro da função!


class InvalidSku(Exception):
    pass


def is_valid_sku(sku, batches):
    return sku in {b.sku for b in batches}


def allocate(orderid: str, sku: str, qty: int, uow: AbstractUnitOfWork) -> str:
    line = model.OrderLine(
       orderid, sku, qty
    )
    with uow:
        batches = uow.batches.list()
        if not is_valid_sku(line.sku, batches):
            raise InvalidSku(f"Invalid sku {line.sku}")
        batchref = model.allocate(line, batches)
        uow.commit()
    return batchref


def deallocate(orderid: str, sku: str, uow: AbstractUnitOfWork) -> List[str]:
    with uow:
        batches = uow.batches.get_by_orderid_and_sku(orderid, sku)
        if batches:
            deallocated_batch_refs = model.deallocate(orderid, batches)
            uow.commit()
            return deallocated_batch_refs
    return []


def add_batch(batchref: str, sku: str, qty: int, eta: Optional[date], uow: AbstractUnitOfWork):
    with uow:
        uow.batches.add(model.Batch(batchref, sku, qty, eta))
        uow.commit()
    return batchref
