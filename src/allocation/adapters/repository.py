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


class SqlAlchemyProductRepository(AbstractProductRepository):
    def __init__(self, session):
        self.session = session

    def add(self, product):
        self.session.add(product)

    def get(self, sku):
        return self.session.query(model.Product).filter_by(sku=sku).first()

    def list(self):
        return self.session.query(model.Product).all()

