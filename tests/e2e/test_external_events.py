import json
from tenacity import Retrying, stop_after_delay

from tests.e2e import redis_client
from tests.random_refs import random_sku, random_orderid, random_batchref
import api_client


def test_change_batch_quantity_leading_to_reallocation():
    # start with two batches and an order allocated to one of them
    orderid, sku = random_orderid(), random_sku()
    earlier_batch, later_batch = random_batchref("old"), random_batchref("newer")
    api_client.put_to_add_batch(earlier_batch, sku, qty=10, eta="2011-01-01")
    api_client.put_to_add_batch(later_batch, sku, qty=10, eta="2011-01-02")
    response = api_client.post_to_allocate(orderid, sku, 10)
    assert response.json()["batchref"] == earlier_batch

    subscription = redis_client.subscribe_to("line_allocated")
    # change quantity on allocated batch so it's less than our order
    redis_client.publish_message(
        "change_batch_quantity",
        {"batchref": earlier_batch, "qty": 5},
    )

    # wait until we see a message saying the order has been reallocated
    messages = []
    for attempt in Retrying(stop=stop_after_delay(3), reraise=True):
        with attempt:
            message = subscription.get_message(timeout=1)
            if message:
                messages.append(message)
                print(messages)
                data = json.loads(messages[-1]["data"])
                assert data["orderid"] == orderid
                assert data["batchref"] == later_batch
