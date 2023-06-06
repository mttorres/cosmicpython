from typing import Protocol

from src.allocation import config


class NotificationsService(Protocol):
    def send(self, destination, message):
        ...


class EmailNotifications:
    def __init__(self):
        ...
        # TODO

    def send(self, destination, message):
        raise NotImplementedError

