import functools
from typing import Set, Callable, Any, Iterable, Collection, Protocol

from src.allocation.adapters import orm
from src.allocation.domain import model


# Due to python is ducktype (Protocols: Structural subtyping (static duck typing))
# We don't need ABC's, we only use it for educational reasons and to make explicit.

class AbstractProductRepository(Protocol):
    tracked: Set[model.Product]

    def add(self, product: model.Product):
        ...

    def get(self, sku: str) -> model.Product:
        ...


# https://stackoverflow.com/questions/6307761/how-to-decorate-all-functions-of-a-class-without-typing-it-over-and-over-for-eac

def check_tracked_entity_in_args(tracker: set, args: Iterable):
    for arg in args:
        check_for_tracked_entity(tracker, arg)


def check_for_tracked_entity(tracker: set, arg: model.Product | Iterable[model.Product]):
    if isinstance(arg, model.Product):
        tracker.add(arg)
    if isinstance(arg, Collection) and all(isinstance(item, model.Product) for item in arg):
        tracker.update(arg)


def track_entity(func: Callable[[AbstractProductRepository, model.Product | Collection[model.Product]], None]
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


class SqlAlchemyProductRepository:
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

    @track_entity
    def get_by_batchref(self, batchref: str) -> model.Product:
        return (
            self.session.query(model.Product)
            .join(model.Batch)
            .filter(orm.batches.c.reference == batchref)
            .first()
        )
