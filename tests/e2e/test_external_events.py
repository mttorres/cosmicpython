import json

import pytest
from tenacity import Retrying, stop_after_delay

from tests.e2e import redis_client
from tests.random_refs import random_sku, random_orderid, random_batchref
import api_client


@pytest.mark.usefixtures("postgres_db")
@pytest.mark.usefixtures("restart_api")
@pytest.mark.usefixtures("restart_redis_pubsub")
def check_allocated_event(batchref, orderid, subscription):
    messages = []
    for attempt in Retrying(stop=stop_after_delay(3), reraise=True):
        with attempt:
            message = subscription.get_message(timeout=1)
            if message:
                messages.append(message)
                print(messages)
            data = json.loads(messages[-1]["data"])
            assert data["orderid"] == orderid
            assert data["batchref"] == batchref


@pytest.mark.usefixtures("postgres_db")
@pytest.mark.usefixtures("restart_api")
@pytest.mark.usefixtures("restart_redis_pubsub")
def test_change_batch_quantity_leading_to_reallocation():
    # start with two batches and an order allocated to one of them
    orderid, sku = random_orderid(), random_sku()
    earlier_batch, later_batch = random_batchref("old"), random_batchref("newer")
    api_client.put_to_add_batch(earlier_batch, sku, qty=10, eta="2011-01-01")
    api_client.put_to_add_batch(later_batch, sku, qty=10, eta="2011-01-02")
    response = api_client.post_to_allocate(orderid, sku, 10)

    subscription = redis_client.subscribe_to("line_allocated")
    # change quantity on allocated batch so it's less than our order
    redis_client.publish_message(
        "change_batch_quantity",
        {"batchref": earlier_batch, "qty": 5},
    )

    # wait until we see a message saying the order has been reallocated
    check_allocated_event(later_batch, orderid, subscription)


def test_allocate_external_command_leads_to_allocation():
    # start with two batches a
    orderid, sku = random_orderid(), random_sku()
    earlier_batch, later_batch = random_batchref("old"), random_batchref("newer")
    api_client.put_to_add_batch(earlier_batch, sku, qty=10, eta="2011-01-01")
    api_client.put_to_add_batch(later_batch, sku, qty=10, eta="2011-01-02")

    subscription = redis_client.subscribe_to("line_allocated")
    # issue allocation
    redis_client.publish_message(
        "allocate_line",
        {"orderid": orderid,
         "sku": sku,
         "qty": 10},
    )

    # wait until we see a message...
    check_allocated_event(earlier_batch, orderid, subscription)
