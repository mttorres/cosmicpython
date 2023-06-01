import json
import os

import redis
import logging
from src.allocation import config, bootstrap
from src.allocation.domain import commands

r = redis.Redis(**config.get_redis_host_and_port())

logging.basicConfig(format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=os.environ.get('LOGLEVEL', 'INFO').upper()
)


commands_mappers = {
    'change_batch_quantity': lambda data: commands.ChangeBatchQuantity(ref=data["batchref"], qty=data["qty"]),
    'allocate_line': lambda data: commands.Allocate(orderid=data["orderid"], sku=data["sku"], qty=data["qty"])

}


def main():
    bus = bootstrap.bootstrap()
    pubsub = r.pubsub(ignore_subscribe_messages=True)
    pubsub.subscribe("change_batch_quantity", "allocate_line")

    for m in pubsub.listen():
        logger.debug("handling %s", m)
        channel_name = m["channel"].decode()
        if channel_name in commands_mappers:
            data = json.loads(m["data"])
            cmd = commands_mappers.get(channel_name)(data)
            bus.handle(cmd)

        else:
            logger.warning(f"Message incoming from {channel_name} was ignored")


if __name__ == "__main__":
    logger.info("Starting Event Listener")
    main()
