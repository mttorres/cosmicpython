from src.allocation.domain.model import OrderLine
from src.allocation.domain import model
from src.allocation.adapters.repository import AbstractRepository
# from src.allocation.adapters.repository import SqlAlchemyRepository # testar sem abc.. funciona lindamente!
# mesmo que eu coloque ele como parâmetro da função!


class InvalidSku(Exception):
    pass


def is_valid_sku(sku, batches):
    return sku in {b.sku for b in batches}


def allocate(line: OrderLine, repo: AbstractRepository, session) -> str:
    batches = repo.list()
    if not is_valid_sku(line.sku, batches):
        raise InvalidSku(f"Invalid sku {line.sku}")
    batchref = model.allocate(line, batches)
    session.commit()
    return batchref