from datetime import date
from typing import List, Optional

from src.allocation.domain.model import OrderLine
from src.allocation.domain import model
from src.allocation.adapters.repository import AbstractRepository


# from src.allocation.adapters.repository import SqlAlchemyRepository # testar sem abc.. funciona lindamente!
# mesmo que eu coloque ele como parâmetro da função!


class InvalidSku(Exception):
    pass


def is_valid_sku(sku, batches):
    return sku in {b.sku for b in batches}


def allocate(orderid: str, sku: str, qty: int, repo: AbstractRepository, session) -> str:
    line = model.OrderLine(
       orderid, sku, qty
    )
    batches = repo.list()
    if not is_valid_sku(line.sku, batches):
        raise InvalidSku(f"Invalid sku {line.sku}")
    batchref = model.allocate(line, batches)
    session.commit()
    return batchref


def deallocate(orderid: str, sku: str, repo: AbstractRepository, session) -> List[str]:
    batches = repo.get_by_orderid_and_sku(orderid, sku)
    if batches:
        deallocated_batch_refs = model.deallocate(orderid, batches)
        session.commit()
        return deallocated_batch_refs
    return []


def add_batch(batchref: str, sku: str, qty: int, eta: Optional[date], repo: AbstractRepository, session):
    repo.add(model.Batch(batchref, sku, qty, eta))
    session.commit()
    return batchref
