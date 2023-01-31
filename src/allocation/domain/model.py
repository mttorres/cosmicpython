import dataclasses
from datetime import date
from typing import Optional
from dataclasses import dataclass


@dataclass(frozen=True)  # ORDER LINE É IMUTÁVEL E SEM COMPORTAMENTOS (pelo menos por enquanto)
class OrderLine:
    orderid: str
    sku: str
    qty: int


class Batch:
    def __init__(self, ref: str, sku: str, qty: int, eta: Optional[date]):
        self.reference = ref
        self.sku = sku
        self.eta = eta
        self.available_quantity = qty
        self._allocations = set()

    def can_allocate(self, line: OrderLine) -> bool:
        return self.sku == line.sku and self.available_quantity >= line.qty

    def allocate(self, line: OrderLine):
        self.available_quantity -= line.qty

    def deallocate(self, line: OrderLine):
        if line in self._allocations:
            self._allocations.remove(line)
