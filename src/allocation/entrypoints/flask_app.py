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

    try:
        batchref = services.allocate(
            request.json["orderid"], request.json["sku"], request.json["qty"], repo, db_session
        )
    except (model.OutOfStock, services.InvalidSku) as e:
        return {"message": str(e)}, 400

    return {"batchref": batchref}, 201


@app.route("/deallocate", methods=["POST"])
def deallocate_endpoint():
    db_session = get_session()
    repo = repository.SqlAlchemyRepository(db_session)
    return {"deallocated_batches": services.deallocate(
        request.json["orderid"], request.json["sku"], repo, db_session
    )}, 200
