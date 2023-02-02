from sqlalchemy.sql import text

from src.allocation.domain import model
'''
Como o session funciona? Você não precisa se preocupar sobre pytest e fixtures
durante esse estudo... Porém, explicando brevemente, VOCÊ PODE DEFINIR DEPENDÊNCIAS
COMUNS AOS SEUS TESTES POR MEIO DE FIXTURES, e o pytest vai injetar elas magicamente
aos testes que usam essas como argumentos! Nesse caso, um SQLAlchemy database session.
'''


def test_orderline_mapper_can_load_lines(session):
    session.execute(text(
        "INSERT INTO order_lines (orderid, sku, qty) VALUES "
        '("order1", "RED-CHAIR", 12),'
        '("order1", "RED-TABLE", 13),'
        '("order2", "BLUE-LIPSTICK", 14)')
    )
    expected = [
        model.OrderLine("order1", "RED-CHAIR", 12),
        model.OrderLine("order1", "RED-TABLE", 13),
        model.OrderLine("order2", "BLUE-LIPSTICK", 14),
    ]
    assert session.query(model.OrderLine).all() == expected


def test_orderline_mapper_can_save_lines(session):
    new_line = model.OrderLine("order1", "DECORATIVE-WIDGET", 12)
    session.add(new_line)
    session.commit()

    rows = list(session.execute(text('SELECT orderid, sku, qty FROM "order_lines"')))
    assert rows == [("order1", "DECORATIVE-WIDGET", 12)]
