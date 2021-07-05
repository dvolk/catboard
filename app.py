import base64
import datetime as dt
import random
import time

import argh
import flask
import humanize
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

import to_md

app = flask.Flask(__name__)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
# app.config["SQLALCHEMY_ECHO"] = True
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///app.db"

db = SQLAlchemy(app)
migrate = Migrate(app, db)


class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(256), nullable=False)
    assigned = db.Column(db.String(64), nullable=False)
    color = db.Column(db.String(64), nullable=False)
    closed = db.Column(db.Boolean, nullable=False, default=False)
    description = db.Column(db.Text)
    column_id = db.Column(db.Integer, db.ForeignKey("column.id"), nullable=False)
    column = db.relationship("Column", backref=db.backref("items"), lazy=True)


class ItemTransition(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey("item.id"), nullable=False)
    item = db.relationship("Item", backref=db.backref("transitions"), lazy=True)
    from_column_id = db.Column(db.Integer, db.ForeignKey("column.id"))
    from_column = db.relationship("Column", foreign_keys=[from_column_id])
    to_column_id = db.Column(db.Integer, db.ForeignKey("column.id"), nullable=False)
    to_column = db.relationship("Column", foreign_keys=[to_column_id])
    epochtime = db.Column(db.Integer, nullable=False)


class Column(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(256), nullable=False)
    closed = db.Column(db.Boolean, nullable=False, default=False)
    lane_id = db.Column(db.Integer, db.ForeignKey("lane.id"), nullable=False)
    lane = db.relationship("Lane", backref=db.backref("columns"), lazy=True)


class Lane(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(256), nullable=False)
    closed = db.Column(db.Boolean, nullable=False, default=False)
    board_id = db.Column(db.Integer, db.ForeignKey("board.id"), nullable=False)
    board = db.relationship("Board", backref=db.backref("lanes"), lazy=True)
    columns_sorted = db.Column(db.String(512), nullable=True)


class Board(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(256), nullable=False)
    closed = db.Column(db.Boolean, nullable=False, default=False)
    lanes_sorted = db.Column(db.String(512), nullable=True)


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


def or_404(arg):
    if not arg:
        return flask.abort(404)
    return arg


def icon(name):
    return f'<i class="fa fa-{name} fa-fw"></i>'


def list_reorder(list1, list2):
    """
    reorder list1 based on comma separated ids in list2

    for sorting lanes and columnsa
    """
    if list2:
        list2 = list2.split(",")
        for l2 in list2:
            for x in list1:
                if x.id == int(l2):
                    yield x
    else:
        for l1 in list1:
            yield l1


@app.context_processor
def inject_globals():
    return {"icon": icon, "list_reorder": list_reorder, "to_md": to_md.text_to_html}


@app.route("/")
def index():
    return flask.redirect(flask.url_for("boards"))


@app.route("/boards", methods=["GET", "POST"])
def boards():
    print(flask.request.authorization)

    boards = Board.query.all()
    if flask.request.method == "GET":
        return flask.render_template(
            "boards.jinja2", boards=boards, title="Board index"
        )
    if flask.request.method == "POST":
        unsafe_new_board_name = flask.request.form.get("new_board_name")
        # make new board with some defaults
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
    board = or_404(Board.query.filter_by(id=board_id).first())
    show_closed = flask.request.args.get("show_closed")

    return flask.render_template(
        "board.jinja2",
        board=board,
        show_closed=show_closed,
        title=board.name,
    )


@app.route("/board/<board_id>/history")
def board_history(board_id):
    board = or_404(Board.query.filter_by(id=board_id).first())
    time_now = int(time.time())

    def nice_time(t2):
        return humanize.naturaltime(dt.timedelta(seconds=(time_now - t2))).capitalize()

    if flask.request.method == "GET":
        board_transitions = list()
        for lane in board.lanes:
            for column in lane.columns:
                for item in column.items:
                    board_transitions += item.transitions
        board_transitions = sorted(
            board_transitions, key=lambda x: x.epochtime, reverse=True
        )
        return flask.render_template(
            "board_history.jinja2",
            board=board,
            title=board.name,
            board_transitions=board_transitions,
            nice_time=nice_time,
            time_now=time_now,
        )


@app.route("/board/<board_id>/edit", methods=["GET", "POST"])
def board_edit(board_id):
    board = or_404(Board.query.filter_by(id=board_id).first())
    if flask.request.method == "GET":
        lane_id_to_name = {lane.id: lane.name for lane in board.lanes}
        lane_names = [lane.name for lane in board.lanes]
        lanes_sorted = None
        if board.lanes_sorted:
            lanes_sorted = [
                lane_id_to_name[int(lane_id)]
                for lane_id in board.lanes_sorted.split(",")
            ]

        return flask.render_template(
            "board_edit.jinja2",
            board=board,
            title=board.name,
            lane_names=lane_names,
            lane_id_to_name=lane_id_to_name,
            lanes_sorted=lanes_sorted,
        )
    if flask.request.method == "POST":
        if flask.request.form.get("Submit") == "Submit_rename_board":
            unsafe_new_board_name = flask.request.form.get("new_board_name")
            board.name = unsafe_new_board_name
            db.session.commit()
        if flask.request.form.get("Submit") == "Submit_new_lane":
            unsafe_new_lane_name = flask.request.form.get("new_lane_name")
            for x in unsafe_new_lane_name.split(","):
                board.lanes.append(Lane(name=x.strip()))
            db.session.commit()
        if flask.request.form.get("Submit") == "Submit_lanes_sorted":
            unsafe_lanes_sorted = flask.request.form.get("lanes_sorted")
            lane_name_to_id = {lane.name: lane.id for lane in board.lanes}
            try:
                board.lanes_sorted = ",".join(
                    [
                        str(lane_name_to_id[unsafe_lane_name.strip()])
                        for unsafe_lane_name in unsafe_lanes_sorted.split(",")
                    ]
                )
            except:
                return flask.redirect(flask.url_for("board_edit", board_id=board_id))
            db.session.commit()
        return flask.redirect(flask.url_for("board_edit", board_id=board_id))


@app.route("/lane/<lane_id>/edit", methods=["GET", "POST"])
def lane_edit(lane_id):
    lane = or_404(Lane.query.filter_by(id=lane_id).first())
    if flask.request.method == "GET":
        column_id_to_name = {column.id: column.name for column in lane.columns}
        column_names = [column.name for column in lane.columns]
        columns_sorted = None
        if lane.columns_sorted:
            columns_sorted = [
                column_id_to_name[int(column_id)]
                for column_id in lane.columns_sorted.split(",")
            ]
        return flask.render_template(
            "lane_edit.jinja2",
            lane=lane,
            title=lane.name,
            column_names=column_names,
            columns_sorted=columns_sorted,
        )
    if flask.request.method == "POST":
        if flask.request.form.get("Submit") == "Submit_rename_lane":
            unsafe_new_lane_name = flask.request.form.get("new_lane_name")
            lane.name = unsafe_new_lane_name
            db.session.commit()
        if flask.request.form.get("Submit") == "Submit_new_column":
            unsafe_new_column_name = flask.request.form.get("new_column_name")
            for x in unsafe_new_column_name.split(","):
                lane.columns.append(Column(name=x.strip()))
            db.session.commit()
        if flask.request.form.get("Submit") == "Submit_columns_sorted":
            unsafe_columns_sorted = flask.request.form.get("columns_sorted")
            column_name_to_id = {column.name: column.id for column in lane.columns}
            try:
                lane.columns_sorted = ",".join(
                    [
                        str(column_name_to_id[unsafe_column_name.strip()])
                        for unsafe_column_name in unsafe_columns_sorted.split(",")
                    ]
                )
            except:
                return flask.redirect(flask.url_for("lane_edit", lane_id=lane_id))
            db.session.commit()
    return flask.redirect(flask.url_for("lane_edit", lane_id=lane_id))


@app.route("/item/<item_id>", methods=["GET", "POST"])
def item(item_id):
    item = or_404(Item.query.filter_by(id=item_id).first())
    time_now = int(time.time())

    def nice_time(t2):
        return humanize.naturaltime(dt.timedelta(seconds=(time_now - t2))).capitalize()

    if flask.request.method == "GET":
        return flask.render_template(
            "item.jinja2",
            item=item,
            colors=colors,
            title=item.name,
            nice_time=nice_time,
        )
    if flask.request.method == "POST":
        unsafe_new_assign = flask.request.form.get("new_assign_name")
        item.assigned = unsafe_new_assign
        unsafe_new_name = flask.request.form.get("new_name")
        item.name = unsafe_new_name
        unsafe_new_description = flask.request.form.get("new_description")
        item.description = unsafe_new_description
        db.session.commit()
        if flask.request.form.get("Submit") == "Submit_print":
            return flask.redirect(flask.url_for("item_view", item_id=item_id))
        return flask.redirect(flask.url_for("item", item_id=item_id))


@app.route("/item/<item_id>/view")
def item_view(item_id):
    item = or_404(Item.query.filter_by(id=item_id).first())
    return flask.render_template("item_view.jinja2", title=item.name, item=item)


@app.route("/item/move/<item_id>/<column_id>")
def item_move(item_id, column_id):
    item = or_404(Item.query.filter_by(id=item_id).first())
    if item.column.id == column_id:
        return flask.redirect(flask.url_for("item", item_id=item_id))
    column = or_404(Column.query.filter_by(id=column_id).first())
    transition = ItemTransition(
        item_id=item.id,
        from_column_id=item.column.id,
        to_column_id=column.id,
        epochtime=int(time.time()),
    )
    item.column = column
    db.session.add(transition)
    db.session.commit()
    return flask.redirect(flask.url_for("item", item_id=item_id))


@app.route("/item/color/<item_id>/<color>")
def item_color(item_id, color):
    item = or_404(Item.query.filter_by(id=item_id).first())
    item.color = color
    db.session.commit()
    return flask.redirect(flask.url_for("item", item_id=item_id))


@app.route("/item/toggle/<item_id>")
def item_close_toggle(item_id):
    item = or_404(Item.query.filter_by(id=item_id).first())
    item.closed = not item.closed
    db.session.commit()
    return flask.redirect(flask.url_for("item", item_id=item_id))


@app.route("/column/<column_id>/edit", methods=["GET", "POST"])
def column_edit(column_id):
    column = or_404(Column.query.filter_by(id=column_id).first())
    if flask.request.method == "GET":
        return flask.render_template(
            "column_edit.jinja2", column=column, colors=colors, name=column.name
        )
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
            t = ItemTransition(
                item_id=item.id, to_column_id=column.id, epochtime=int(time.time())
            )
            db.session.add(t)
            db.session.commit()
        if flask.request.form.get("Submit") == "Submit_rename_column":
            unsafe_new_column_name = flask.request.form.get("new_column_name")
            column.name = unsafe_new_column_name
            db.session.commit()
        return flask.redirect(flask.url_for("board", board_id=column.lane.board.id))


def main():
    app.run(host="0.0.0.0", port=7777, debug=True)


if __name__ == "__main__":
    argh.dispatch_command(main)
