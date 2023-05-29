from sqlalchemy import text

from src.allocation.service_layer import unit_of_work


def allocations(orderid: str, uow: unit_of_work.SqlAlchemyUnitOfWork):
    with uow:
        results = uow.session.execute(text(
            """
                SELECT sku, batchref FROM allocations_view WHERE orderid = :orderid
            """),
            dict(orderid=orderid),
        )
    return [{"sku": sku, "batchref": batchref} for sku, batchref in results]


def allocation(orderid: str, sku: str, uow: unit_of_work.SqlAlchemyUnitOfWork):
    with uow:
        results = uow.session.execute(text(
            """
                SELECT sku, batchref FROM allocations_view WHERE orderid = :orderid AND sku = :sku
            """),
            dict(orderid=orderid, sku=sku),
        )
        return dict(results.mappings().one_or_none())
