from typing import Set
import abc
from src.allocation.domain import model


# Due to python is ducktype (Protocols: Structural subtyping (static duck typing))
# We don't need ABC's, we only use it for educational reasons and to make explicit.
class AbstractProductRepository(abc.ABC):

    def __int__(self):
        self.seen = set()  # type: Set[model.Product]

    def add(self, product):
        self._add(product)
        self.seen.add(product)

    def get(self, sku) -> model.Product:
        product = self._get(sku)
        if product:
            self.seen.add(product)
        return product

    @abc.abstractmethod
    def _add(self, product: model.Product):
        raise NotImplementedError

    @abc.abstractmethod
    def _get(self, sku) -> model.Product:
        raise NotImplementedError


class SqlAlchemyProductRepository(AbstractProductRepository):
    def __init__(self, session):
        super().__init__()
        self.session = session

    def _add(self, product):
        self.session.add(product)

    def _get(self, sku):
        return self.session.query(model.Product).filter_by(sku=sku).first()

    def list(self):
        return self.session.query(model.Product).all()

