# pylint: disable=protected-access
import threading
import traceback
from typing import List
import pytest
import time
from sqlalchemy.sql import text

from src.allocation.service_layer import unit_of_work
from src.allocation.domain import model
from tests.random_refs import random_sku, random_batchref, random_orderid


def insert_batch(session, ref, sku, qty, eta, product_version=1):
    session.execute(text(
        "INSERT INTO products (sku, version_id_col) VALUES (:sku, :version)"),
        dict(sku=sku, version=product_version),
    )

    [[product_id]] = session.execute(
        text('SELECT id FROM products WHERE sku=:sku'),
        dict(ref=ref, sku=sku),
    )


    session.execute(text(
        "INSERT INTO batches (reference, sku, _purchased_quantity, eta)"
        " VALUES (:ref, :sku, :qty, :eta)"),
        dict(ref=ref, sku=sku, qty=qty, eta=eta),
    )

    [[batch_id]] = session.execute(
        text('SELECT id FROM batches WHERE reference=:ref AND sku=:sku'),
        dict(ref=ref, sku=sku),
    )

    session.execute(text(
        "INSERT INTO stocks (product_id, batch_id)"
        " VALUES (:pid, :bid)"),
        dict(pid=product_id, bid=batch_id)
    )

    return product_id, batch_id


def get_allocated_batch_ref(session, orderid, sku):
    [[orderlineid]] = session.execute(text(
        "SELECT id FROM order_lines WHERE orderid=:orderid AND sku=:sku"),
        dict(orderid=orderid, sku=sku),
    )
    [[batchref]] = session.execute(text(
        "SELECT b.reference FROM allocations JOIN batches AS b ON batch_id = b.id"
        " WHERE orderline_id=:orderlineid"),
        dict(orderlineid=orderlineid),
    )
    return batchref


def try_to_allocate(orderid, sku, num, exceptions):
    line = model.OrderLine(orderid, sku, 10)
    try:
        with unit_of_work.SqlAlchemyUnitOfWork() as uow:
            product = uow.products.get(sku=sku)
            product.allocate(line)
            time.sleep(0.2)
            uow.commit()
    except Exception as e:
        print(traceback.format_exc())
        print(f"Optimistic Concurrency failed for thread nº {num}")
        exceptions.append(e)


def uow_add_batch(sku, batchref, session_factory):
    with unit_of_work.SqlAlchemyUnitOfWork(session_factory) as uow:
        created_product = model.Product(sku)
        created_batch = model.Batch(batchref, sku, 100, None)
        created_product.add_stock(created_batch)
        uow.products.add(created_product)
        uow.commit()
        return created_product, created_batch


def uow_allocate(sku, line, session_factory):
    with unit_of_work.SqlAlchemyUnitOfWork(session_factory) as uow:
        product = uow.products.get(sku=sku)
        product.allocate(line)
        uow.commit()


def test_uow_can_add_a_batch(session_factory):
    expected_product = model.Product("HIPSTER-WORKBENCH")
    expected_batch = model.Batch("batch1", expected_product.sku, 100, None)

    uow_add_batch(expected_product.sku, expected_batch.reference, session_factory)

    session = session_factory()
    batches_rows = list(session.execute(text('SELECT * FROM "batches"')))
    product_rows = list(session.execute(text('SELECT * FROM "products"')))
    assert model.Batch(*batches_rows[0][1:]) == expected_batch
    assert model.Product(*product_rows[0][1:-1]) == expected_product


def test_uow_can_retrieve_a_product_and_allocate_to_it(session_factory):
    uow_add_batch("HIPSTER-WORKBENCH", "batch1", session_factory)

    uow_allocate("HIPSTER-WORKBENCH", model.OrderLine("o1", "HIPSTER-WORKBENCH", 10), session_factory)

    session = session_factory()
    batchref = get_allocated_batch_ref(session, "o1", "HIPSTER-WORKBENCH")
    assert batchref == "batch1"


def test_uow_can_retrieve_a_product_with_allocations(session_factory):
    uow_add_batch("HIPSTER-WORKBENCH", "batch1", session_factory)

    uow_allocate("HIPSTER-WORKBENCH", model.OrderLine("o1", "HIPSTER-WORKBENCH", 10), session_factory)

    session = session_factory()
    product_with_alllocation = session.query(model.Product).filter_by(sku="HIPSTER-WORKBENCH").one()
    assert product_with_alllocation.is_allocated_for_line(model.OrderLine("o1", "HIPSTER-WORKBENCH", 10))


def test_rolls_back_uncommitted_work_by_default(session_factory):
    uow = unit_of_work.SqlAlchemyUnitOfWork(session_factory)
    with uow:
        insert_batch(uow.session, "batch1", "MEDIUM-PLINTH", 100, None)

    new_session = session_factory()
    batches_rows = list(new_session.execute(text('SELECT * FROM "batches"')))
    product_rows = list(new_session.execute(text('SELECT * FROM "products"')))
    assert batches_rows == []
    assert product_rows == []


def test_rolls_back_on_error(session_factory):
    class MyException(Exception):
        pass

    uow = unit_of_work.SqlAlchemyUnitOfWork(session_factory)
    with pytest.raises(MyException):
        with uow:
            insert_batch(uow.session, "batch1", "LARGE-FORK", 100, None)
            raise MyException()

    new_session = session_factory()
    batches_rows = list(new_session.execute(text('SELECT * FROM "batches"')))
    product_rows = list(new_session.execute(text('SELECT * FROM "products"')))
    assert batches_rows == []
    assert product_rows == []


def test_concurrent_updates_to_version_are_not_allowed(postgres_session_factory):
    sku, batch = random_sku(), random_batchref()
    session = postgres_session_factory()
    insert_batch(session, batch, sku, 100, eta=None, product_version=1)
    session.commit()

    order1, order2 = random_orderid(1), random_orderid(2)
    exceptions = []  # type: List[Exception]
    # https://stackoverflow.com/questions/25010167/e731-do-not-assign-a-lambda-expression-use-a-def
    thread1 = threading.Thread(target=lambda: try_to_allocate(order1, sku, 1, exceptions))
    thread2 = threading.Thread(target=lambda: try_to_allocate(order2, sku, 2, exceptions))
    thread1.start()
    thread2.start()
    thread1.join()
    thread2.join()

    [[version]] = session.execute(text(
        "SELECT version_id_col FROM products WHERE sku=:sku"),
        dict(sku=sku),
    )
    assert version == 2
    [exception] = exceptions
    assert "could not serialize access due to concurrent update" in str(exception)

    orders = session.execute(text(
        "SELECT orderid FROM allocations"
        " JOIN batches ON allocations.batch_id = batches.id"
        " JOIN order_lines ON allocations.orderline_id = order_lines.id"
        " WHERE order_lines.sku=:sku"),
        dict(sku=sku),
    )
    assert orders.rowcount == 1
