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
        deallocated_batch_refs = product.deallocate(orderid, sku)
        uow.commit()
    return deallocated_batch_refs


def add_batch(batchref: str, sku: str, qty: int, eta: Optional[date], uow: AbstractUnitOfWork):
    with uow:
        product = uow.products.get(sku=sku)
        if product is None:
            product = model.Product(sku, batches=[])
            uow.products.add(product)
        product.batches.append(model.Batch(batchref, sku, qty, eta))
        uow.commit()
    return batchref
