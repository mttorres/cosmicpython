import abc
from src.allocation.domain import model


# Due to python is ducktype (Protocols: Structural subtyping (static duck typing))
# We don't need ABC's, we only use it for educational reasons and to make explicit.
class AbstractProductRepository(abc.ABC):
    @abc.abstractmethod
    def add(self, product):
        raise NotImplementedError

    @abc.abstractmethod
    def get(self, sku) -> model.Product:
        raise NotImplementedError


class AbstractBatchRepository(abc.ABC):
    @abc.abstractmethod
    def add(self, batch: model.Batch):
        raise NotImplementedError

    @abc.abstractmethod
    def get(self, reference) -> model.Batch:
        raise NotImplementedError


class SqlAlchemyBatchRepository(AbstractBatchRepository):
    def __init__(self, session):
        self.session = session

    def add(self, batch):
        self.session.add(batch)

    def get(self, reference):
        return self.session.query(model.Batch).filter_by(reference=reference).one()

    def list(self):
        return self.session.query(model.Batch).all()

    def get_by_orderid_and_sku(self, orderid, sku):
        # temp (should be filtered on the DB but the N:N join table is making things messy...)
        return sorted(b for b in self.session.query(model.Batch).filter_by(sku=sku).all()
                      if b.is_allocated_for_order(orderid)
                      )


