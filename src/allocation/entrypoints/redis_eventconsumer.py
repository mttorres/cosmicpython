import json

import redis
import logging
from src.allocation import config
from src.allocation.adapters import orm
from src.allocation.domain import commands
from src.allocation.service_layer import messagebus, unit_of_work

r = redis.Redis(**config.get_redis_host_and_port())

logger = logging.getLogger(__name__)


def main():
    orm.start_mappers()
    pubsub = r.pubsub(ignore_subscribe_messages=True)
    pubsub.subscribe("change_batch_quantity")

    for m in pubsub.listen():
        handle_change_batch_quantity(m)


def handle_change_batch_quantity(m):
    logger.debug("handling %s", m)
    data = json.loads(m["data"])
    cmd = commands.ChangeBatchQuantity(ref=data["batchref"], qty=data["qty"])
    messagebus.MessageBus(unit_of_work.SqlAlchemyUnitOfWork()).handle(cmd)
