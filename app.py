import datetime as dt
import random
import time
import re
import pathlib
import subprocess
import shlex
import json
import logging

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
    public = db.Column(db.Boolean, nullable=False, default=False)
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


class ItemRelationship(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    item1_id = db.Column(db.Integer, db.ForeignKey("item.id"), nullable=False)
    item1 = db.relationship(
        "Item",
        foreign_keys=[item1_id],
        backref=db.backref("source_relationships"),
        lazy=True,
    )
    item2_id = db.Column(db.Integer, db.ForeignKey("item.id"), nullable=False)
    item2 = db.relationship(
        "Item",
        foreign_keys=[item2_id],
        backref=db.backref("destination_relationships"),
        lazy=True,
    )
    # 100 - item2 is subtask of item1
    type = db.Column(db.Integer, nullable=False)

    def __repr__(self):
        return f"#{self.id} {self.item1.name} -> {self.item2.name}, type={self.type}"


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

    for sorting lanes and columns
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


try:
    cmd = "git describe --tags --always --dirty"
    version = subprocess.check_output(shlex.split(cmd)).decode().strip()
except:
    version = None


@app.context_processor
def inject_globals():
    return {
        "version": version,
        "icon": icon,
        "list_reorder": list_reorder,
        "to_md": to_md.text_to_html,
    }


@app.route("/")
def index():
    return flask.redirect(flask.url_for("boards"))


def export_rows(cls):
    """Export sqlalchemy class table data to json."""
    rows = [x.__dict__ for x in cls.query.all()]
    for row in rows:
        del row["_sa_instance_state"]
    return rows


@app.route("/export_data")
def export_data():
    """Export all catboard data to json."""
    data = {
        "Item": export_rows(Item),
        "ItemTransition": export_rows(ItemTransition),
        "ItemRelationship": export_rows(ItemRelationship),
        "Column": export_rows(Column),
        "Lane": export_rows(Lane),
        "Board": export_rows(Board),
    }
    return "<pre>" + json.dumps(data, indent=4)


def import_rows(rows, cls):
    """Import json dict to sqlalchemy table."""
    for row in rows:
        obj = cls(**row)
        db.session.add(obj)


@app.route("/import_data", methods=["POST"])
def import_data():
    """Import all catboard data from json.

    To add data:

        curl -X POST -H "Content-Type: application/json" -d @data.json http://127.0.0.1:7777/import_data
    """
    data = flask.request.json
    import_rows(data["Board"], Board)
    import_rows(data["Lane"], Lane)
    import_rows(data["Column"], Column)
    import_rows(data["ItemRelationship"], ItemRelationship)
    import_rows(data["ItemTransition"], ItemTransition)
    import_rows(data["Item"], Item)
    db.session.commit()
    return "OK"


@app.route("/boards", methods=["GET", "POST"])
def boards():
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
        boards = Board.query.all()
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
            boards=boards,
            title=lane.name,
            column_names=column_names,
            columns_sorted=columns_sorted,
        )
    if flask.request.method == "POST":
        if flask.request.form.get("Submit") == "Submit_rename_lane":
            unsafe_new_lane_name = flask.request.form.get("new_lane_name")
            lane.name = unsafe_new_lane_name
            db.session.commit()
        if flask.request.form.get("Submit") == "Submit_move_board":
            unsafe_new_board_id = flask.request.form.get("new_board_id")
            or_404(Board.query.filter_by(id=unsafe_new_board_id).first())
            lane.board_id = unsafe_new_board_id
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
        rels = ItemRelationship.query.filter_by(item1_id=item.id, type=100).all()
        return flask.render_template(
            "item.jinja2",
            item=item,
            colors=colors,
            title=item.name,
            nice_time=nice_time,
            rels=rels,
        )
    if flask.request.method == "POST":
        unsafe_new_assign = flask.request.form.get("new_assign_name")
        item.assigned = unsafe_new_assign
        unsafe_new_name = flask.request.form.get("new_name")
        item.name = unsafe_new_name
        unsafe_new_description = flask.request.form.get("new_description")
        item.description = unsafe_new_description
        if item.description:
            ItemRelationship.query.filter_by(item1_id=item.id).delete()
            db.session.commit()
            subtask_ints = set()
            for subtask in re.findall(r"subtask #(\d+)", item.description):
                try:
                    subtask_int = int(subtask)
                except:
                    pass
                if subtask_int not in subtask_ints:
                    db.session.add(
                        ItemRelationship(
                            item1_id=item.id, item2_id=subtask_int, type=100
                        )
                    )
                    subtask_ints.add(subtask_int)

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


@app.route("/lane/<lane_id>/move/<board_id>")
def lane_move(lane_id, board_id):
    lane = or_404(Lane.query.filter_by(id=lane_id).first())
    or_404(Board.query.filter_by(id=board_id).first())
    lane.board_id = board_id
    db.session.commit()
    return flask.redirect(flask.url_for("lane_edit", lane_id=lane_id))


@app.route("/item/color/<item_id>/<color>")
def item_color(item_id, color):
    or_404(color in colors)
    item = or_404(Item.query.filter_by(id=item_id).first())
    item.color = color
    db.session.commit()
    return flask.redirect(flask.url_for("item", item_id=item_id))


@app.route("/item/<item_id>/toggle")
def item_close_toggle(item_id):
    item = or_404(Item.query.filter_by(id=item_id).first())
    item.closed = not item.closed
    db.session.commit()
    return flask.redirect(flask.url_for("item", item_id=item_id))


@app.route("/column/<column_id>/toggle")
def column_close_toggle(column_id):
    column = or_404(Column.query.filter_by(id=column_id).first())
    column.closed = not column.closed
    db.session.commit()
    return flask.redirect(flask.url_for("lane_edit", lane_id=column.lane.id))


@app.route("/lane/<lane_id>/toggle")
def lane_close_toggle(lane_id):
    lane = or_404(Lane.query.filter_by(id=lane_id).first())
    lane.closed = not lane.closed
    db.session.commit()
    return flask.redirect(flask.url_for("board_edit", board_id=lane.board.id))


@app.route("/board/<board_id>/toggle")
def board_close_toggle(board_id):
    board = or_404(Board.query.filter_by(id=board_id).first())
    board.closed = not board.closed
    db.session.commit()
    return flask.redirect(flask.url_for("boards"))


@app.route("/column/<column_id>/edit", methods=["GET", "POST"])
def column_edit(column_id):
    column = or_404(Column.query.filter_by(id=column_id).first())
    templates_dir = pathlib.Path("./item_templates")
    templates = [x.name for x in templates_dir.glob("*.txt")]
    if flask.request.method == "GET":
        random_color = random.choice(colors)

        return flask.render_template(
            "column_edit.jinja2",
            column=column,
            colors=colors,
            name=column.name,
            templates=templates,
            random_color=random_color,
        )
    if flask.request.method == "POST":
        if flask.request.form.get("Submit") == "Submit_new_item":
            unsafe_new_item_name = flask.request.form.get("new_item_name")
            unsafe_new_item_assigned = flask.request.form.get("new_item_assigned")
            unsafe_new_item_color = flask.request.form.get("new_item_color")
            unsafe_new_item_template = flask.request.form.get("new_item_template")
            item = Item(
                name=unsafe_new_item_name,
                assigned=unsafe_new_item_assigned,
                color=unsafe_new_item_color,
                closed=False,
                column=column,
            )
            if unsafe_new_item_template in templates:
                with open(templates_dir / unsafe_new_item_template) as f:
                    item.description = f.read()

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
        return flask.redirect(flask.url_for("item", item_id=item.id))


@app.route("/board/<board_id>/graph")
def board_graph(board_id):
    board = or_404(Board.query.filter_by(id=board_id).first())
    return flask.render_template("graph.jinja2", board=board)


def main(host="127.0.0.1", port=7777, debug=False):
    app.run(host=host, port=port, debug=debug)


if __name__ == "__main__":
    argh.dispatch_command(main)
