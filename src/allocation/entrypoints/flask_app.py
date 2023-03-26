from datetime import datetime

from flask import Flask, request


from src.allocation.domain import events
from src.allocation.adapters import orm
from src.allocation.service_layer import handlers, unit_of_work, messagebus

orm.start_mappers()
app = Flask(__name__)


@app.route("/batch", methods=["PUT"])
def add_batch_endpoint():
    eta = request.json["eta"]
    if eta is not None:
        eta = datetime.fromisoformat(eta).date()
    event = events.BatchCreated(
        request.json["ref"],
        request.json["sku"],
        request.json["qty"],
        eta
    )

    messagebus.MessageBus(unit_of_work.SqlAlchemyUnitOfWork()).handle(event)
    return "OK", 201


@app.route("/allocate", methods=["POST"])
def allocate_endpoint():

    try:
        event = events.AllocationRequired(
            request.json["orderid"],
            request.json["sku"],
            request.json["qty"]
        )
        results = messagebus.MessageBus(unit_of_work.SqlAlchemyUnitOfWork()).handle(event)
        batchref = results.pop(0)
    except handlers.InvalidSku as e:
        return {"message": str(e)}, 400

    return {"batchref": batchref}, 201


@app.route("/deallocate", methods=["POST"])
def deallocate_endpoint():

    return {"deallocated_batches": services.deallocate(
        request.json["orderid"], request.json["sku"], unit_of_work.SqlAlchemyUnitOfWork()
    )}, 200
