import random

import flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import argh


app = flask.Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///app.db"
db = SQLAlchemy(app)
migrate = Migrate(app, db)

class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(256), nullable=False)
    assigned = db.Column(db.String(64), nullable=False)
    color = db.Column(db.String(64), nullable=False)
    closed = db.Column(db.Boolean, nullable=False)
    column_id = db.Column(db.Integer, db.ForeignKey("column.id"), nullable=False)
    column = db.relationship("Column", backref=db.backref("items"), lazy=True)


class Column(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(256), nullable=False)
    lane_id = db.Column(db.Integer, db.ForeignKey("lane.id"), nullable=False)
    lane = db.relationship("Lane", backref=db.backref("columns"), lazy=True)


class Lane(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(256), nullable=False)
    board_id = db.Column(db.Integer, db.ForeignKey("board.id"), nullable=False)
    board = db.relationship("Board", backref=db.backref("lanes"), lazy=True)


class Board(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(256), nullable=False)


colors = [
    "w3-red",
    "w3-pink",
    "w3-purple",
    "w3-deep-purple",
    "w3-indigo",
    "w3-blue",
    "w3-light-blue",
    "w3-cyan",
    "w3-aqua",
    "w3-teal",
    "w3-green",
    "w3-light-green",
    "w3-lime",
    "w3-sand",
    "w3-khaki",
    "w3-yellow",
    "w3-amber",
    "w3-orange",
    "w3-deep-orange",
    "w3-blue-gray",
    "w3-brown",
    "w3-light-gray",
    "w3-gray",
    "w3-dark-gray",
    "w3-pale-red",
    "w3-pale-yellow",
    "w3-pale-green",
    "w3-pale-blue",
]


@app.route("/board/<board_id>")
def board(board_id):
    board = Board.query.filter_by(id=board_id).first()
    return flask.render_template("board.jinja2", board=board)


@app.route("/item/<item_id>")
def item(item_id):
    item = Item.query.filter_by(id=item_id).first()
    return flask.render_template("item.jinja2", item=item)


@app.route("/item/new", methods=["GET", "POST"])
def item_new():
    pass


@app.route("/item/move/<item_id>/<column_id>")
def item_move(item_id, column_id):
    item = Item.query.filter_by(id=item_id).first()
    column = Column.query.filter_by(id=column_id).first()
    item.column = column
    db.session.commit()
    return flask.redirect(flask.url_for("item", item_id=item_id))

def main():
    app.run(debug=True)


if __name__ == "__main__":
    argh.dispatch_command(main)
