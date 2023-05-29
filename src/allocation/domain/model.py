from __future__ import annotations
from datetime import date
from typing import Optional, List, Union
from dataclasses import dataclass

from src.allocation.domain import events, commands

Message = Union[commands.Command, events.Event]


class Product:
    def __init__(self, sku: str, batches: Optional[List[Batch]] = None, version_id_col: int = 0):
        self.sku = sku
        self.batches = batches if batches else []
        self.version_id_col = version_id_col
        self.messages = []  # type: List[Message]

    def allocate(self, line: OrderLine):
        try:
            batch = next(b for b in sorted(self.batches) if b.can_allocate(line))
            batch.allocate(line)
            self.version_id_col += 1
            self.messages.append(
                events.Allocated(
                    orderid=line.orderid,
                    sku=line.sku,
                    qty=line.qty,
                    batchref=batch.reference,
                )
            )
            return batch.reference
        except StopIteration:
            self.messages.append(events.OutOfStock(line.sku))
            return None

    def add_stock(self, batch: Batch):
        self.batches.append(batch)
        self.version_id_col += 1

    def is_allocated_for_line(self, line: OrderLine) -> bool:
        return len([batch for batch in self.batches if batch.is_allocated_for_line(line)]) > 0

    def is_allocated_for_order(self, orderid: str) -> bool:
        return len([batch for batch in self.batches if batch.is_allocated_for_order(orderid)]) > 0

    def change_batch_quantity(self, ref: str, qty: int):
        # sanity check
        batch = next(b for b in self.batches if b.reference == ref)
        batch._purchased_quantity = qty
        while batch.available_quantity < 0:
            line = batch.deallocate_one()
            self.messages.append(
                events.Deallocated(line.orderid, line.sku, line.qty)
            )

    @property
    def available_quantity(self) -> int:
        return sum(line.available_quantity for line in self.batches)

    def __eq__(self, other):
        if not isinstance(other, Product):
            return False
        return other.sku == self.sku

    def __hash__(self):
        return hash(self.sku)


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

    def deallocate_one(self) -> OrderLine:
        return self._allocations.pop()

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

    def __repr__(self):
        return f"<Batch {self.reference}>"
