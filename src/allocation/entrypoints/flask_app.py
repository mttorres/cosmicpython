from flask import Flask, request
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.allocation import config
from src.allocation.domain import model
from src.allocation.adapters import orm
from src.allocation.adapters import repository
from src.allocation.service_layer import services

orm.start_mappers()
get_session = sessionmaker(bind=create_engine(config.get_postgres_uri()))
app = Flask(__name__)


@app.route("/allocate", methods=["POST"])
def allocate_endpoint():
    db_session = get_session()
    repo = repository.SqlAlchemyRepository(db_session)
    line = model.OrderLine(
        request.json["orderid"], request.json["sku"], request.json["qty"],
    )

    try:
        batchref = services.allocate(line, repo, db_session)
    except (model.OutOfStock, services.InvalidSku) as e:
        return {"message": str(e)}, 400

    return {"batchref": batchref}, 201


@app.route("/deallocate", methods=["POST"])
def deallocate_endpoint():
    db_session = get_session()
    batches = repository.SqlAlchemyRepository(db_session).get_by_orderid_and_sku(
        request.json["orderid"], request.json["sku"]
    )

    deallocated_batches = model.deallocate(request.json["orderid"], batches)

    db_session.commit()

    return {"deallocated_batches": deallocated_batches}, 200
