from typing import Dict, List, Callable, Type, Protocol

from src.allocation.domain import events
from src.allocation.service_layer import unit_of_work
from src.allocation.service_layer.handlers import send_out_of_stock_notification, allocate, add_batch, \
    change_batch_quantity


class AbstractMessageBus:
    HANDLERS: Dict[Type[events.Event], List[Callable]]
    uow: unit_of_work.AbstractUnitOfWork

    def handle(self, event: events.Event):
        results = []
        for handler in self.HANDLERS[type(event)]:
            results.append(handler(event, self.uow))

        return results


class MessageBus(AbstractMessageBus):

    def __init__(self, uow: unit_of_work.AbstractUnitOfWork):
        self.HANDLERS = {
            events.OutOfStock: [send_out_of_stock_notification],
            events.AllocationRequired: [allocate],
            events.BatchCreated: [add_batch],
            events.BatchQuantityChanged: [change_batch_quantity]
        }  # type: Dict[Type[events.Event], List[Callable]]
        self.uow = uow

    def handle(self, event: events.Event):
        results = []
        queue = [event]
        while queue:
            event = queue.pop(0)
            for handler in self.HANDLERS[type(event)]:
                results.append(handler(event, self.uow))
                queue.extend(self.uow.collect_new_events())

        return results


