import pytest

from tests.random_refs import random_sku, random_batchref, random_orderid
from api_client import put_to_add_batch, post_to_allocate, get_allocations, get_allocation


@pytest.mark.usefixtures("postgres_db")
@pytest.mark.usefixtures("restart_api")
def test_happy_path_returns_202_and_batch_is_allocated():
    orderid = random_orderid()
    sku, othersku = random_sku(), random_sku("other")
    earlybatch = random_batchref("1")
    laterbatch = random_batchref("2")
    otherbatch = random_batchref("3")
    put_to_add_batch(laterbatch, sku, 100, "2011-01-02")
    put_to_add_batch(earlybatch, sku, 100, "2011-01-01")
    put_to_add_batch(otherbatch, othersku, 100, None)

    r = post_to_allocate(orderid, sku, qty=3)

    r = get_allocation(orderid, sku)
    assert r.ok
    assert r.json() == {"sku": sku, "batchref": earlybatch}


@pytest.mark.usefixtures("postgres_db")
@pytest.mark.usefixtures("restart_api")
def test_unhappy_path_returns_400_and_error_message():
    unknown_sku, orderid = random_sku(), random_orderid()
    r = post_to_allocate(orderid, unknown_sku, qty=20, expect_success=False)
    assert r.status_code == 400
    assert r.json()["message"] == f"Invalid sku {unknown_sku}"

    r = get_allocations(orderid)
    assert r.status_code == 404

