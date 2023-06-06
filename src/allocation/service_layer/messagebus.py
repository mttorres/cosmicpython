from __future__ import annotations
import logging
from typing import Dict, List, Callable, Type, Protocol, Union, TYPE_CHECKING
from tenacity import Retrying, RetryError, stop_after_attempt, wait_exponential

from src.allocation.domain import events, commands
from src.allocation.domain.model import Message

if TYPE_CHECKING:
    from . import unit_of_work

logger = logging.getLogger(__name__)


class AbstractMessageBus(Protocol):
    EVENT_HANDLERS: Dict[Type[events.Event], List[Callable]]
    COMMAND_HANDLERS: Dict[Type[commands.Command], Callable]
    uow: unit_of_work.AbstractUnitOfWork

    def handle(self, message: Message):
        ...


class MessageBus:

    def __init__(
            self,
            uow: unit_of_work.AbstractUnitOfWork,
            event_handlers: Dict[Type[events.Event], List[Callable]],
            command_handlers: Dict[Type[commands.Command], Callable]
    ):
        self.queue = []
        self.EVENT_HANDLERS = event_handlers
        self.COMMAND_HANDLERS = command_handlers
        self.uow = uow

    def handle(self, message: Message):
        self.queue.append(message) # Not thread safe?
        while self.queue:
            message = self.queue.pop(0)
            if isinstance(message, events.Event):
                self.handle_event(message)
            elif isinstance(message, commands.Command):
                self.handle_command(message)
            else:
                raise Exception(f"{message} was not an Event or Command")

    def handle_command(self, command: commands.Command):
        logger.debug("handling command %s", command)
        try:
            handler = self.COMMAND_HANDLERS[type(command)]
            handler(command)
            self.queue.extend(self.uow.collect_new_events())
        except Exception as e:
            logger.exception("Exception %s  while handling command %s", e, command)
            raise

    def handle_event(self, event: events.Event):
        for handler in self.EVENT_HANDLERS[type(event)]:
            try:
                for attempt in Retrying(
                    stop=stop_after_attempt(3),
                    wait=wait_exponential()
                ):
                    with attempt:
                        logger.debug("handling event %s with handler %s", event, handler)
                        handler(event)
                        self.queue.extend(self.uow.collect_new_events())  # only collected if has not failed
            except RetryError as retry_failure:
                logger.error(
                    "Failed to handle event %s times, giving up!",
                    retry_failure.last_attempt.attempt_number
                )
                continue
