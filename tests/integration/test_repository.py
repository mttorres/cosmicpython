from sqlalchemy.sql import text

from src.allocation.domain import model


def test_repository_can_save_a_batch(session):
    batch = model.Batch("batch1", "RUSTY-SOAPDISH", 100, eta=None)

    repo = repository.SqlAlchemyRepository(session)
    repo.add(batch)
    session.commit() # não deveria ser parte do método add? (deixar o commit como responsabilidade externa me parece ruim

    rows = session.execute(
        text('SELECT reference, sku, _purchased_quantity, eta FROM "batches"')
    )

    assert list(rows) == [("batch1", "RUSTY-SOAPDISH", 100, None)]



