import functools
from typing import Set, Callable, Any, Iterable, Collection, Protocol
from src.allocation.domain import model


def check_tracked_entity_in_args(tracker: set, args: Iterable):
    for arg in args:
        check_for_tracked_entity(tracker, arg)


def check_for_tracked_entity(tracker: set, arg: model.Product | Iterable[model.Product]):
    if isinstance(arg, model.Product):
        tracker.add(arg)
    if isinstance(arg, Collection) and all(isinstance(item, model.Product) for item in arg):
        tracker.update(arg)


def track_entity(func: Callable[[model.Product | Collection[model.Product]], None]
                       | Callable[[Any], model.Product | Collection[model.Product]]) -> Callable:
    @functools.wraps(func)
    def wrapper_track_entity(self, *args, **kwargs):
        check_tracked_entity_in_args(self.tracked, args)
        check_tracked_entity_in_args(self.tracked, kwargs.values())
        result = func(self, *args, **kwargs)
        if result:
            check_for_tracked_entity(self.tracked, result)
        return result

    return wrapper_track_entity


# Due to python is ducktype (Protocols: Structural subtyping (static duck typing))
# We don't need ABC's, we only use it for educational reasons and to make explicit.

class AbstractProductRepository(Protocol):
    tracked: Set[model.Product]

    def add(self, product: model.Product):
        ...

    def get(self, sku: str) -> model.Product:
        ...


class SqlAlchemyProductRepository(AbstractProductRepository):
    def __init__(self, session):
        self.session = session
        self.tracked = set()  # type: Set[model.Product]

    @track_entity
    def add(self, product: model.Product):
        self.session.add(product)

    @track_entity
    def get(self, sku: str) -> model.Product:
        return self.session.query(model.Product).filter_by(sku=sku).first()

    @track_entity
    def list(self) -> Collection[model.Product]:
        return self.session.query(model.Product).all()


class TrackingProductRepository:
    seen: Set[model.Product]

    def __init__(self, repo: AbstractProductRepository):
        self.seen = set()  # type: Set[model.Product]
        self._repo = repo

    def add(self, product: model.Product):
        self._repo.add(product)
        self.seen.add(product)

    def get(self, sku) -> model.Product:
        product = self._repo.get(sku)
        if product:
            self.seen.add(product)
        return product
