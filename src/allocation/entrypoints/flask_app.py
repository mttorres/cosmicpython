from datetime import datetime

from flask import Flask, request, jsonify

from src.allocation.domain import commands
from src.allocation.adapters import orm
from src.allocation.service_layer import handlers, unit_of_work, messagebus
from src.allocation.views import views

orm.start_mappers()
app = Flask(__name__)


@app.route("/batch", methods=["PUT"])
def add_batch_endpoint():
    eta = request.json["eta"]
    if eta is not None:
        eta = datetime.fromisoformat(eta).date()
    command = commands.CreateBatch(
        request.json["ref"],
        request.json["sku"],
        request.json["qty"],
        eta
    )

    messagebus.MessageBus(unit_of_work.SqlAlchemyUnitOfWork()).handle(command)
    return "OK", 201


@app.route("/allocate", methods=["POST"])
def allocate_endpoint():
    try:
        command = commands.Allocate(
            request.json["orderid"],
            request.json["sku"],
            request.json["qty"]
        )
        messagebus.MessageBus(unit_of_work.SqlAlchemyUnitOfWork()).handle(command)
    except handlers.InvalidSku as e:
        return {"message": str(e)}, 400

    return "OK", 202


@app.route("/allocations/<orderid>", methods=["GET"])
def allocations_view_endpoint(orderid):
    uow = unit_of_work.SqlAlchemyUnitOfWork()
    result = views.allocations(orderid, uow)
    if not result:
        return "not found", 404
    return jsonify(result), 200


@app.route("/allocations/<orderid>/<sku>", methods=["GET"])
def allocation_view_endpoint(orderid, sku):
    uow = unit_of_work.SqlAlchemyUnitOfWork()
    result = views.allocation(orderid, sku, uow)
    if not result:
        return "not found", 404
    return jsonify(result), 200

