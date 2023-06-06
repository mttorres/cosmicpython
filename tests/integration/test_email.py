import requests

from src.allocation import config
from src.allocation.domain import commands
from tests.random_refs import random_sku


def get_email_from_mailhog(sku):
    host, port = map(config.get_email_host_and_port().get, ["host", "http_port"])
    all_emails = requests.get(f"http://{host}:{port}/api/v2/messages").json()
    return next(m for m in all_emails["items"] if sku in str(m))


def test_out_of_stock_email(sqlite_bus):
    sku = random_sku()
    sqlite_bus.handle(commands.CreateBatch("batch1", sku, 9, None))
    sqlite_bus.handle(commands.Allocate("order1", sku, 10))
    email = get_email_from_mailhog(sku)
    assert email["Raw"]["From"] == "allocations@example.com"
    assert email["Raw"]["To"] == ["stock@made.com"]
    assert f"Out of stock for {sku}" in email["Raw"]["Data"]
