from datetime import datetime

from flask import Flask, request


from src.allocation.domain import model
from src.allocation.adapters import orm
from src.allocation.service_layer import services, unit_of_work

orm.start_mappers()
app = Flask(__name__)


@app.route("/batch", methods=["PUT"])
def add_batch_endpoint():
    eta = request.json["eta"]
    if eta is not None:
        eta = datetime.fromisoformat(eta).date()
    services.add_batch(
        request.json["ref"],
        request.json["sku"],
        request.json["qty"],
        eta,
        unit_of_work.SqlAlchemyUnitOfWork()
    )
    return "OK", 201


@app.route("/allocate", methods=["POST"])
def allocate_endpoint():

    try:
        batchref = services.allocate(
            request.json["orderid"],
            request.json["sku"],
            request.json["qty"],
            unit_of_work.SqlAlchemyUnitOfWork()
        )
    except (model.OutOfStock, services.InvalidSku) as e:
        return {"message": str(e)}, 400

    return {"batchref": batchref}, 201


@app.route("/deallocate", methods=["POST"])
def deallocate_endpoint():

    return {"deallocated_batches": services.deallocate(
        request.json["orderid"], request.json["sku"], unit_of_work.SqlAlchemyUnitOfWork()
    )}, 200
