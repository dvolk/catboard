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
    description = db.Column(db.Text)
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
    "w3-teal",
    "w3-green",
    "w3-deep-orange",
    "w3-blue-gray",
    "w3-brown",
]


@app.route("/boards", methods=["GET", "POST"])
def boards():
    boards = Board.query.all()
    if flask.request.method == "GET":
        return flask.render_template("boards.jinja2", boards=boards)
    if flask.request.method == "POST":
        unsafe_new_board_name = flask.request.form.get("new_board_name")
        b = Board(name=unsafe_new_board_name)
        l = Lane(name="Default")
        l.columns.append(Column(name="Backlog"))
        l.columns.append(Column(name="Ready"))
        c = Column(name="WIP")
        c.items.append(
            Item(
                name="Click column to add items",
                assigned="",
                color="w3-indigo",
                closed=False,
                description="",
            )
        )
        l.columns.append(c)
        l.columns.append(Column(name="Blocked"))
        l.columns.append(Column(name="QA"))
        l.columns.append(Column(name="Done"))
        b.lanes.append(l)

        db.session.add(b)
        db.session.commit()
        return flask.redirect(flask.url_for("boards"))


@app.route("/board/<board_id>")
def board(board_id):
    board = Board.query.filter_by(id=board_id).first()
    show_closed = flask.request.args.get("show_closed")
    return flask.render_template("board.jinja2", board=board, show_closed=show_closed)


@app.route("/board/<board_id>/edit", methods=["GET", "POST"])
def board_edit(board_id):
    board = Board.query.filter_by(id=board_id).first()
    if flask.request.method == "GET":
        return flask.render_template("board_edit.jinja2", board=board)
    if flask.request.method == "POST":
        if flask.request.form.get("Submit") == "Submit_rename_board":
            unsafe_new_board_name = flask.request.form.get("new_board_name")
            board.name = unsafe_new_board_name
            db.session.commit()
        if flask.request.form.get("Submit") == "Submit_new_lane":
            unsafe_new_lane_name = flask.request.form.get("new_lane_name")
            for x in unsafe_new_lane_name.split(","):
                board.lanes.append(Lane(name=x))
            db.session.commit()
        return flask.redirect(flask.url_for("board_edit", board_id=board_id))


@app.route("/lane/<lane_id>/edit", methods=["GET", "POST"])
def lane_edit(lane_id):
    lane = Lane.query.filter_by(id=lane_id).first()
    if flask.request.method == "GET":
        return flask.render_template("lane_edit.jinja2", lane=lane)
    if flask.request.method == "POST":
        if flask.request.form.get("Submit") == "Submit_rename_lane":
            unsafe_new_lane_name = flask.request.form.get("new_lane_name")
            lane.name = unsafe_new_lane_name
            db.session.commit()
        if flask.request.form.get("Submit") == "Submit_new_column":
            unsafe_new_column_name = flask.request.form.get("new_column_name")
            for x in unsafe_new_column_name.split(","):
                lane.columns.append(Column(name=x))
            db.session.commit()
        return flask.redirect(flask.url_for("lane_edit", lane_id=lane_id))


@app.route("/item/<item_id>", methods=["GET", "POST"])
def item(item_id):
    item = Item.query.filter_by(id=item_id).first()
    if flask.request.method == "GET":
        return flask.render_template("item.jinja2", item=item, colors=colors)
    if flask.request.method == "POST":
        unsafe_new_assign = flask.request.form.get("new_assign_name")
        item.assigned = unsafe_new_assign
        unsafe_new_name = flask.request.form.get("new_name")
        item.name = unsafe_new_name
        unsafe_new_description = flask.request.form.get("new_description")
        item.description = unsafe_new_description
        db.session.commit()
        return flask.redirect(flask.url_for("item", item_id=item_id))


@app.route("/item/move/<item_id>/<column_id>")
def item_move(item_id, column_id):
    item = Item.query.filter_by(id=item_id).first()
    column = Column.query.filter_by(id=column_id).first()
    item.column = column
    db.session.commit()
    return flask.redirect(flask.url_for("item", item_id=item_id))


@app.route("/item/color/<item_id>/<color>")
def item_color(item_id, color):
    item = Item.query.filter_by(id=item_id).first()
    item.color = color
    db.session.commit()
    return flask.redirect(flask.url_for("item", item_id=item_id))


@app.route("/item/toggle/<item_id>")
def item_close_toggle(item_id):
    item = Item.query.filter_by(id=item_id).first()
    item.closed = not item.closed
    db.session.commit()
    return flask.redirect(flask.url_for("item", item_id=item_id))


@app.route("/column/<column_id>/edit", methods=["GET", "POST"])
def column_edit(column_id):
    column = Column.query.filter_by(id=column_id).first()
    if flask.request.method == "GET":
        return flask.render_template("column_edit.jinja2", column=column, colors=colors)
    if flask.request.method == "POST":
        if flask.request.form.get("Submit") == "Submit_new_item":
            unsafe_new_item_name = flask.request.form.get("new_item_name")
            unsafe_new_item_assigned = flask.request.form.get("new_item_assigned")
            unsafe_new_item_color = flask.request.form.get("new_item_color")
            item = Item(
                name=unsafe_new_item_name,
                assigned=unsafe_new_item_assigned,
                color=unsafe_new_item_color,
                closed=False,
                column=column,
            )
            column.items.append(item)
            db.session.commit()
        if flask.request.form.get("Submit") == "Submit_rename_column":
            unsafe_new_column_name = flask.request.form.get("new_column_name")
            column.name = unsafe_new_column_name
            db.session.commit()
        return flask.redirect(flask.url_for("board", board_id=column.lane.board.id))


def main():
    app.run(debug=True)


if __name__ == "__main__":
    argh.dispatch_command(main)
