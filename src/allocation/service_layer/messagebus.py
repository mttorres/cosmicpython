from __future__ import annotations
import logging
from typing import Dict, List, Callable, Type, Protocol, Union, TYPE_CHECKING
from src.allocation.domain import events, commands
from src.allocation.service_layer.handlers import send_out_of_stock_notification, allocate, add_batch, \
    change_batch_quantity

if TYPE_CHECKING:
    from . import unit_of_work

logger = logging.getLogger(__name__)
Message = Union[commands.Command, events.Event]


class AbstractMessageBus:
    HANDLERS: Dict[Type[events.Event], List[Callable]]
    uow: unit_of_work.AbstractUnitOfWork

    def handle(self, event: Message):
        results = []
        for handler in self.HANDLERS[type(event)]:
            results.append(handler(event, self.uow))

        return results


class MessageBus(AbstractMessageBus):

    def __init__(self, uow: unit_of_work.AbstractUnitOfWork):
        self.EVENT_HANDLERS = {
            events.OutOfStock: [send_out_of_stock_notification],
            events.AllocationRequired: [allocate],
            events.BatchCreated: [add_batch],
            events.BatchQuantityChanged: [change_batch_quantity]
        }  # type: Dict[Type[events.Event], List[Callable]]
        self.COMMAND_HANDLERS = {
            commands.Allocate: allocate,
            commands.CreateBatch: add_batch,
            commands.ChangeBatchQuantity: change_batch_quantity
        }  # type: Dict[Type[commands.Command], Callable]
        self.uow = uow

    def handle(self, message: Message):
        results = []
        queue = [message]
        while queue:
            message = queue.pop(0)
            if isinstance(message, events.Event):
                self.handle_event(message, queue)
            elif isinstance(message, commands.Command):
                results.append(self.handle_command(message, queue))
            else:
                raise Exception(f"{message} was not an Event or Command")
            queue.extend(self.uow.collect_new_events())

        return results

    def handle_command(self, command: commands.Command, queue: List[Message]):
        logger.debug("handling command %s", command)
        try:
            handler = self.COMMAND_HANDLERS[type(command)]
            return handler(command, self.uow)
        except:
            logger.exception("Exception handling command %s", command)
            raise

    def handle_event(self, event: events.Event, queue: List[Message]):
        for handler in self.EVENT_HANDLERS[type(event)]:
            try:
                logger.debug("handling event %s with handler %s", event, handler)
                handler(event, self.uow)
                queue.extend(self.uow.collect_new_events())
            except Exception:
                logger.exception("Exception handling event %s", event)
                continue
