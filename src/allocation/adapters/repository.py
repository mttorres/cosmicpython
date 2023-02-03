import abc
from src.allocation.domain import model


class AbstractRepository(abc.ABC):
    @abc.abstractmethod  # (1)
    def add(self, batch: model.Batch):
        raise NotImplementedError  # (2)

    @abc.abstractmethod
    def get(self, reference) -> model.Batch:
        raise NotImplementedError
