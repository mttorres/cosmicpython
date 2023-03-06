from __future__ import annotations
from datetime import date
from typing import Optional, List
from dataclasses import dataclass


class OutOfStock(Exception):
    pass


class SkuMismatch(Exception):
    pass


class Product:
    def __init__(self, sku: str, batches: Optional[List[Batch]] = None, version_number: int = 0):
        self.sku = sku
        self._batches = batches
        self.version_number = version_number

    def allocate(self, line: OrderLine) -> str:
        try:
            batch = next(b for b in sorted(self._batches) if b.can_allocate(line))
            batch.allocate(line)
            self.version_number += 1
            return batch.reference
        except StopIteration:
            raise OutOfStock(f"Out of stock for sku {line.sku}")

    def add_stock(self, batch: Batch):
        if self.sku != batch.sku:
            raise SkuMismatch(f"{batch.sku} sku mismatch with Product!")

        if self._batches is None:
            self._batches = [batch]
        else:
            self._batches.append(batch)

    def deallocate(self, orderid: str):
        batch_refs_deallocated = []
        for b in self._batches:
            if b.deallocate_for_order(orderid):
                batch_refs_deallocated.append(b.reference)
        return batch_refs_deallocated

    @property
    def available_quantity(self) -> int:
        return sum(line.available_quantity for line in self._batches)


@dataclass(unsafe_hash=True)
class OrderLine:
    orderid: str
    sku: str
    qty: int


class Batch:
    def __init__(self, ref: str, sku: str, qty: int, eta: Optional[date]):
        self.reference = ref
        self.sku = sku
        self.eta = eta
        self._purchased_quantity = qty
        self._allocations = set()

    def can_allocate(self, line: OrderLine) -> bool:
        return self.sku == line.sku and self.available_quantity >= line.qty

    def allocate(self, line: OrderLine):
        if self.can_allocate(line):
            self._allocations.add(line)

    def deallocate(self, line: OrderLine):
        if self.is_allocated_for_line(line):
            self._allocations.remove(line)

    def is_allocated_for_line(self, line: OrderLine):
        return line in self._allocations

    def is_allocated_for_order(self, orderid: str):
        return len([line for line in self._allocations if line.orderid == orderid]) > 0

    # can be optimized by those insane ideas that i had before... but that would have to be persisted
    # otherwise, the aux datastructure could be at in-memory concurrency mercy...?
    def deallocate_for_order(self, orderid) -> bool:
        prevsize = len(self._allocations)
        self._allocations = set(orderline for orderline in self._allocations if orderline.orderid != orderid)
        return prevsize > len(self._allocations)

    @property
    def allocated_quantity(self) -> int:
        return sum(line.qty for line in self._allocations)

    @property
    def available_quantity(self) -> int:
        return self._purchased_quantity - self.allocated_quantity

    def __eq__(self, other):
        if not isinstance(other, Batch):
            return False
        return other.reference == self.reference

    def __gt__(self, other):
        if self.eta is None:
            return False
        if other.eta is None:
            return True
        return self.eta > other.eta

    def __hash__(self):
        # note: it would be best if reference was read-only
        return hash(self.reference)
