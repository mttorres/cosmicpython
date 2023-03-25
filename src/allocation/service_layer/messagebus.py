from typing import Dict, List, Callable, Type

from src.allocation.domain import events
from src.allocation.service_layer import unit_of_work
from src.allocation.service_layer.handlers import send_out_of_stock_notification


def handle(event: events.Event, uow: unit_of_work.AbstractUnitOfWork):
    queue = [event]
    while queue:
        event = queue.pop(0)
        for handler in HANDLERS[type(event)]:
            handler(event, uow)
            queue.extend(uow.collect_new_events())


HANDLERS = {
    events.OutOfStock: [send_out_of_stock_notification]
}  # type: Dict[Type[events.Event], List[Callable]]
