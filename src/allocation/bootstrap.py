import inspect
from typing import Callable

from service_layer.unit_of_work import AbstractUnitOfWork, SqlAlchemyUnitOfWork
from service_layer.messagebus import MessageBus
from service_layer import handlers
from adapters.redis_eventpublisher import publish
import adapters.orm as orm
from src.allocation.adapters import email


def inject_dependencies(handler, dependencies):
    params = inspect.signature(handler).parameters
    deps = {
        name: dependency
        for name, dependency in dependencies.items()
        if name in params
    }
    return lambda message: handler(message, **deps)


def bootstrap(start_orm: bool = True,
              uow: AbstractUnitOfWork = SqlAlchemyUnitOfWork,
              send_mail: Callable = email.send,
              publish: Callable = publish) -> MessageBus:
    if start_orm:
        orm.start_mappers()

    dependencies = {"uow": uow, "send_mail": send_mail, "publish": publish}

    injected_event_handlers = {
        event_type: [
            inject_dependencies(handler, dependencies)
            for handler in event_handlers
        ]
        for event_type, event_handlers in handlers.EVENT_HANDLERS.items()
    }

    injected_command_handlers = {
        command_type: inject_dependencies(handler, dependencies)
        for command_type, handler in handlers.COMMAND_HANDLERS.items()
    }

    return MessageBus(uow=uow,
                      event_handlers=injected_event_handlers,
                      command_handlers=injected_command_handlers)
