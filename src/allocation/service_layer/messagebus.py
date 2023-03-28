from __future__ import annotations
import logging
from typing import Dict, List, Callable, Type, Protocol, Union, TYPE_CHECKING
from tenacity import Retrying, RetryError, stop_after_attempt, wait_exponential

from src.allocation.domain import events, commands
from src.allocation.domain.model import Message
from src.allocation.service_layer.handlers import send_out_of_stock_notification, allocate, add_batch, \
    change_batch_quantity, publish_allocated_event

if TYPE_CHECKING:
    from . import unit_of_work

logger = logging.getLogger(__name__)


class AbstractMessageBus(Protocol):
    EVENT_HANDLERS: Dict[Type[events.Event], List[Callable]]
    COMMAND_HANDLERS: Dict[Type[commands.Command], Callable]
    uow: unit_of_work.AbstractUnitOfWork

    def handle(self, message: Message):
        results = []
        if isinstance(message, events.Event):
            for handler in self.EVENT_HANDLERS[type(message)]:
                handler(message, self.uow)
        if isinstance(message, commands.Command):
            results.append(self.COMMAND_HANDLERS[type(message)](message, self.uow))
        return results


class MessageBus(AbstractMessageBus):

    def __init__(self, uow: unit_of_work.AbstractUnitOfWork):
        self.EVENT_HANDLERS = {
            events.Allocated: [publish_allocated_event],
            events.OutOfStock: [send_out_of_stock_notification],
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
                self.handle_event(message)
            elif isinstance(message, commands.Command):
                results.append(self.handle_command(message))
            else:
                raise Exception(f"{message} was not an Event or Command")
            queue.extend(self.uow.collect_new_events())

        return results

    def handle_command(self, command: commands.Command):
        logger.debug("handling command %s", command)
        try:
            handler = self.COMMAND_HANDLERS[type(command)]
            return handler(command, self.uow)
        except Exception:
            logger.exception("Exception handling command %s", command)
            raise

    def handle_event(self, event: events.Event):
        for handler in self.EVENT_HANDLERS[type(event)]:
            try:
                for attempt in Retrying(
                    stop=stop_after_attempt(3),
                    wait=wait_exponential
                ):
                    with attempt:
                        logger.debug("handling event %s with handler %s", event, handler)
                        handler(event, self.uow)
            except RetryError as retry_failure:
                logger.error(
                    "Failed to handle event %s times, giving up!",
                    retry_failure.last_attempt.attempt_number
                )
                continue
