import pytest
import time
import requests
from sqlite3 import OperationalError
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, clear_mappers
from pathlib import Path

import src.allocation.config as config
from src.allocation.adapters.orm import metadata, start_mappers


@pytest.fixture
def in_memory_db():
    engine = create_engine("sqlite:///:memory:")
    metadata.create_all(engine)
    return engine


@pytest.fixture
def session(in_memory_db):
    start_mappers()
    yield sessionmaker(bind=in_memory_db)()
    clear_mappers()


def wait_for_postgres_to_come_up(engine):
    deadline = time.time() + 10
    while time.time() < deadline:
        try:
            return engine.connect()
        except OperationalError:
            time.sleep(0.5)
    pytest.fail("Postgres never came up")


@pytest.fixture(scope="session")
def postgres_db():
    engine = create_engine(config.get_postgres_uri())
    wait_for_postgres_to_come_up(engine)
    metadata.create_all(engine)
    return engine


@pytest.fixture
def postgres_session(postgres_db):
    start_mappers()
    yield sessionmaker(bind=postgres_db)()
    clear_mappers()


@pytest.fixture
def add_stock(postgres_session):
    batches_added = set()
    skus_added = set()

    def _add_stock(lines):
        for ref, sku, qty, eta in lines:
            postgres_session.execute(text(
                "INSERT INTO batches (reference, sku, _purchased_quantity, eta)"
                " VALUES (:ref, :sku, :qty, :eta)"),
                dict(ref=ref, sku=sku, qty=qty, eta=eta),
            )
            [[batch_id]] = postgres_session.execute(text(
                "SELECT id FROM batches WHERE reference=:ref AND sku=:sku"),
                dict(ref=ref, sku=sku),
            )
            batches_added.add(batch_id)
            skus_added.add(sku)
        postgres_session.commit()

    yield _add_stock
    # We should use yield when we want to iterate over a sequence, but don't want to store
    # the entire sequence in memory. Yield are used in Python generators.
    # A generator function is defined like a normal function, but whenever it
    # needs to generate a value, it does so with the yield keyword rather than return.

    for batch_id in batches_added:
        postgres_session.execute(text(
            "DELETE FROM allocations WHERE batch_id=:batch_id"),
            dict(batch_id=batch_id),
        )
        postgres_session.execute(text(
            "DELETE FROM batches WHERE id=:batch_id"), dict(batch_id=batch_id),
        )
    for sku in skus_added:
        postgres_session.execute(text(
            "DELETE FROM order_lines WHERE sku=:sku"), dict(sku=sku),
        )
        postgres_session.commit()


def wait_for_webapp_to_come_up():
    deadline = time.time() + 10
    url = config.get_api_url()
    while time.time() < deadline:
        try:
            return requests.get(url)
        except ConnectionError:
            time.sleep(0.5)
    pytest.fail("API never came up")


@pytest.fixture
def restart_api():
    (Path(__file__).parent / "../src/allocation/entrypoints/flask_app.py").touch()
    time.sleep(0.5)
    wait_for_webapp_to_come_up()

