from typing import Dict, List, Callable, Type

from src.allocation.domain import events
from src.allocation.service_layer import unit_of_work
from src.allocation.service_layer.handlers import send_out_of_stock_notification, allocate, add_batch, change_batch_quantity


def handle(event: events.Event, uow: unit_of_work.AbstractUnitOfWork):
    results = []
    queue = [event]
    while queue:
        event = queue.pop(0)
        for handler in HANDLERS[type(event)]:
            results.append(handler(event, uow))
            queue.extend(uow.collect_new_events())

    return results


HANDLERS = {
    events.OutOfStock: [send_out_of_stock_notification],
    events.AllocationRequired: [allocate],
    events.BatchCreated: [add_batch],
    events.BatchQuantityChanged: [change_batch_quantity]
}  # type: Dict[Type[events.Event], List[Callable]]
