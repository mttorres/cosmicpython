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

    def allocate(self, line: OrderLine):
        self.available_quantity -= line.qty
