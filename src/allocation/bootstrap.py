import inspect
from typing import Callable

from src.allocation.service_layer.unit_of_work import AbstractUnitOfWork, SqlAlchemyUnitOfWork
from src.allocation.service_layer.messagebus import AbstractMessageBus, MessageBus
from src.allocation.service_layer import handlers
import src.allocation.adapters.orm as orm
from src.allocation.adapters import notifications, redis_eventpublisher


def inject_dependencies(handler, dependencies):
    params = inspect.signature(handler).parameters
    deps = {
        name: dependency
        for name, dependency in dependencies.items()
        if name in params
    }
    return lambda message: handler(message, **deps)


def bootstrap(start_orm: bool = True,
              uow: AbstractUnitOfWork = SqlAlchemyUnitOfWork(),
              notifications: Callable = notifications.EmailNotifications(),
              publish: Callable = redis_eventpublisher.publish,
              messagebus_init: Callable = MessageBus) -> AbstractMessageBus:
    if start_orm:
        orm.start_mappers()

    dependencies = {"uow": uow, "notifications": notifications, "publish": publish}

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

    return messagebus_init(uow=uow,
                           event_handlers=injected_event_handlers,
                           command_handlers=injected_command_handlers)
