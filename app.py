"""Catboard web app."""

import datetime as dt
import random
import time
import re
import pathlib
import subprocess
import shlex
import json
import os
import secrets

import argh
import flask
import humanize
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    logout_user,
    login_required,
    current_user,
)
from werkzeug.security import generate_password_hash, check_password_hash

import to_md

app = flask.Flask(__name__)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {"pool_pre_ping": True}
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = dt.timedelta(hours=12)
app.config["SECRET_KEY"] = secrets.token_urlsafe()
if os.getenv("CATBOARD_SQLALCHEMY_DATABASE_URI"):
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
        "CATBOARD_SQLALCHEMY_DATABASE_URI"
    )
else:
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///app.db"

db = SQLAlchemy(app)
migrate = Migrate(app, db)
login_manager = LoginManager(app)
login_manager.login_view = "login"


class Item(db.Model):
    """Board item (task) class."""

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
    """Class to store item events, such as moving between lanes."""

    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey("item.id"), nullable=False)
    item = db.relationship("Item", backref=db.backref("transitions"), lazy=True)
    from_column_id = db.Column(db.Integer, db.ForeignKey("column.id"))
    from_column = db.relationship("Column", foreign_keys=[from_column_id])
    to_column_id = db.Column(db.Integer, db.ForeignKey("column.id"), nullable=False)
    to_column = db.relationship("Column", foreign_keys=[to_column_id])
    epochtime = db.Column(db.Integer, nullable=False)


class ItemRelationship(db.Model):
    """Class to store item relationships, such as subtasks."""

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
        # TODO: is this used?
        return f"#{self.id} {self.item1.name} -> {self.item2.name}, type={self.type}"


class Column(db.Model):
    """Lane column class."""

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(256), nullable=False)
    closed = db.Column(db.Boolean, nullable=False, default=False)
    lane_id = db.Column(db.Integer, db.ForeignKey("lane.id"), nullable=False)
    lane = db.relationship("Lane", backref=db.backref("columns"), lazy=True)


class Lane(db.Model):
    """Board lane class."""

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(256), nullable=False)
    closed = db.Column(db.Boolean, nullable=False, default=False)
    board_id = db.Column(db.Integer, db.ForeignKey("board.id"), nullable=False)
    board = db.relationship("Board", backref=db.backref("lanes"), lazy=True)
    columns_sorted = db.Column(db.String(512), nullable=True)


# Association table
user_board = db.Table(
    "user_board",
    db.Column("user_id", db.Integer, db.ForeignKey("user.id"), primary_key=True),
    db.Column("board_id", db.Integer, db.ForeignKey("board.id"), primary_key=True),
)


class Board(db.Model):
    """Task board class."""

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(256), nullable=False)
    closed = db.Column(db.Boolean, nullable=False, default=False)
    lanes_sorted = db.Column(db.String(512), nullable=True)


class User(db.Model, UserMixin):
    """User model and flask-login mixin."""

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)

    boards = db.relationship(
        "Board",
        secondary=user_board,
        lazy="subquery",
        backref=db.backref("users", lazy=True),
    )

    def set_password(self, new_password):
        self.password_hash = generate_password_hash(new_password)

    def check_password(self, maybe_password):
        return check_password_hash(self.password_hash, maybe_password)


@app.route("/login", methods=["GET", "POST"])
def login():
    if flask.request.method == "POST":
        username = flask.request.form.get("username")
        maybe_password = flask.request.form.get("password")

        user = User.query.filter_by(username=username).first_or_404()

        if user.check_password(maybe_password):
            print("okay")
            login_user(user)
            return flask.redirect(flask.url_for("boards"))
        else:
            print("wrong password")
            flask.abort(403)
    if flask.request.method == "GET":
        return flask.render_template("login.jinja2")


@login_manager.user_loader
def load_user(user_id):
    """
    This is called by flask-login on every request to load the user
    """
    return User.query.filter_by(id=int(user_id)).first()


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
    """Show 404 page if arg is false."""
    if not arg:
        return flask.abort(404)
    return arg


def icon(name):
    """Format html for fontawesome icons."""
    return f'<i class="fa fa-{name} fa-fw"></i>'


def list_reorder(list1, list2):
    """
    Reorder list1 based on comma separated ids in list2.

    for sorting lanes and columns.
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
except Exception:
    version = ""

try:
    cmd = "hostname"
    hostname = subprocess.check_output(shlex.split(cmd)).decode().strip()
except Exception:
    hostname = ""


@app.context_processor
def inject_globals():
    """Add some stuff into all templates."""
    return {
        "version": version,
        "hostname": hostname,
        "icon": icon,
        "list_reorder": list_reorder,
        "to_md": to_md.text_to_html,
    }


@app.route("/")
@login_required
def index():
    """Index page."""
    return flask.redirect(flask.url_for("boards"))


def export_rows(cls):
    """Export sqlalchemy class table data to json."""
    rows = [x.__dict__ for x in cls.query.all()]
    for row in rows:
        del row["_sa_instance_state"]
    return rows


@app.route("/export_data")
@login_required
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
    return json.dumps(data, indent=4)


def import_rows(rows, cls):
    """Import json dict to sqlalchemy table."""
    for row in rows:
        obj = cls(**row)
        db.session.add(obj)


@app.route("/import_data_from_instance", methods=["POST"])
@login_required
def import_data_from_instance():
    """Import data from a different instance."""
    catboard_url = flask.request.form.get("instance_url")
    catboard_export_url = catboard_url.rstrip("/") + "/export_data"
    print(catboard_export_url)
    import requests

    data = requests.get(catboard_export_url).json()
    import_data(data)

    return flask.redirect(flask.url_for("index"))


def import_data(data):
    """Import data from json."""
    import_rows(data["Board"], Board)
    import_rows(data["Lane"], Lane)
    import_rows(data["Column"], Column)
    import_rows(data["ItemRelationship"], ItemRelationship)
    import_rows(data["ItemTransition"], ItemTransition)
    import_rows(data["Item"], Item)
    db.session.commit()


@app.route("/import_data", methods=["POST"])
@login_required
def app_import_data():
    """Import all catboard data from json.

    To add data:

        curl -X POST -H "Content-Type: application/json" -d @data.json http://127.0.0.1:7777/import_data
    """
    data = flask.request.json
    import_data(data)
    return "OK"


@app.route("/boards", methods=["GET", "POST"])
@login_required
def boards():
    """Return boards template."""
    boards = current_user.boards
    if flask.request.method == "GET":
        return flask.render_template(
            "boards.jinja2", boards=boards, title="Board index"
        )
    if flask.request.method == "POST":
        unsafe_new_board_name = flask.request.form.get("new_board_name")
        # make new board with some defaults
        b = Board(name=unsafe_new_board_name)
        lane = Lane(name="Default")
        lane.columns.append(Column(name="Backlog"))
        lane.columns.append(Column(name="Ready"))
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
        lane.columns.append(c)
        lane.columns.append(Column(name="Blocked"))
        lane.columns.append(Column(name="QA"))
        lane.columns.append(Column(name="Done"))
        b.lanes.append(lane)

        db.session.add(b)
        current_user.boards.append(b)
        db.session.commit()
        return flask.redirect(flask.url_for("boards"))


def prev_and_next_elems(elems, elem):
    """Given a list element, return the elements right before and after."""
    if not elems or elem not in elems:
        return None, None
    if type(elems) == str:
        elems = elems.split(",")
    idx = elems.index(elem)
    prev_elem = None
    if idx > 0:
        prev_elem = elems[idx - 1]
    next_elem = None
    if idx < len(elems) - 1:
        next_elem = elems[idx + 1]
    return prev_elem, next_elem


@app.route("/board/<board_id>")
@login_required
def board(board_id):
    """Return board template."""
    board = or_404(Board.query.filter_by(id=board_id).first())
    show_closed = flask.request.args.get("show_closed")

    if board not in current_user.boards:
        flask.abort(403)

    return flask.render_template(
        "board.jinja2",
        board=board,
        show_closed=show_closed,
        title=board.name,
        prev_and_next_elems=prev_and_next_elems,
    )


@app.route("/board/<board_id>/history")
@login_required
def board_history(board_id):
    """Return board history template."""
    board = or_404(Board.query.filter_by(id=board_id).first())

    if board not in current_user.boards:
        flask.abort(403)

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
@login_required
def board_edit(board_id):
    """Return board edit template.

    Here the user can rename the board, add a new lane, and sort lanes.

    The sorting can also be used to hide lanes.
    """
    board = or_404(Board.query.filter_by(id=board_id).first())

    if board not in current_user.boards:
        flask.abort(403)

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
            except Exception:
                return flask.redirect(flask.url_for("board_edit", board_id=board_id))
            db.session.commit()
        return flask.redirect(flask.url_for("board_edit", board_id=board_id))


@app.route("/lane/<lane_id>/edit", methods=["GET", "POST"])
@login_required
def lane_edit(lane_id):
    """Return edit lane template.

    Here the user can rename the lane, move the lane to a different board,
    create a new column, and sort columns (which can also be used to hide columns.)
    """
    lane = or_404(Lane.query.filter_by(id=lane_id).first())

    if lane.board not in current_user.boards:
        flask.abort(403)

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
            except Exception:
                return flask.redirect(flask.url_for("lane_edit", lane_id=lane_id))
            db.session.commit()
    return flask.redirect(flask.url_for("lane_edit", lane_id=lane_id))


def extract_links(md_text):
    """Extract links from text."""
    if not md_text:
        return []
    links = []
    for group in to_md.link_patterns[0][0].findall(md_text):
        links.append(group[0])
    return links


def url_is_image(link: str):
    """Check if url is an image."""
    return re.match(r".*(jpe?g?|png|gif)$", link.lower())


def extract_checkboxes(text):
    """Get all the checkboxes out of a item description.

    Format:
    - [ ] not finished
    - [x] finished

    Allow any kind of character in []? empty [] means not finished?
    multiple characters allowed?
    """
    if not text:
        return []
    ret = list()
    checkbox_line_re = re.compile(r"- \[(.?)\] (.*)")
    for line in text.split("\n"):
        m = checkbox_line_re.match(line)
        if m:
            checkbox_sym = m.group(1)
            checkbox_text = m.group(2)
            checkbox_done = checkbox_sym == "x"
            ret.append(
                {
                    "done": checkbox_done,
                    "text": checkbox_text,
                }
            )
    return ret


@app.route("/item/<item_id>", methods=["GET", "POST"])
@login_required
def item(item_id):
    """Return page showing item/task details."""
    item = or_404(Item.query.filter_by(id=item_id).first())

    if item.column.lane.board not in current_user.boards:
        flask.abort(403)

    time_now = int(time.time())

    def nice_time(t2):
        return humanize.naturaltime(dt.timedelta(seconds=(time_now - t2))).capitalize()

    if flask.request.method == "GET":
        rels = ItemRelationship.query.filter_by(item1_id=item.id, type=100).all()
        links = extract_links(item.description)
        images = [link for link in links if url_is_image(link)]
        checkboxes = extract_checkboxes(item.description)
        print(images)
        return flask.render_template(
            "item.jinja2",
            item=item,
            colors=colors,
            title=item.name,
            nice_time=nice_time,
            rels=rels,
            links=links,
            images=images,
            checkboxes=checkboxes,
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
                except Exception:
                    pass
                # check if item exists
                item2 = Item.query.filter_by(id=subtask_int).first()
                if not item2:
                    continue
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
@login_required
def item_view(item_id):
    """Return page showing item/task description as rendered markdown."""
    item = or_404(Item.query.filter_by(id=item_id).first())

    if item.column.lane.board not in current_user.boards:
        flask.abort(403)

    return flask.render_template("item_view.jinja2", title=item.name, item=item)


@app.route("/item/move/<item_id>/<column_id>")
@login_required
def item_move(item_id, column_id):
    """Move item to different column and redirect back to item page."""
    item = or_404(Item.query.filter_by(id=item_id).first())

    if item.column.lane.board not in current_user.boards:
        flask.abort(403)

    if item.column.id == column_id:
        return flask.redirect(flask.url_for("item", item_id=item_id))
    column = or_404(Column.query.filter_by(id=column_id).first())

    if column.lane.board not in current_user.boards:
        flask.abort(403)

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
@login_required
def lane_move(lane_id, board_id):
    """Move lane to diferent board and redirect back to lane page."""
    lane = or_404(Lane.query.filter_by(id=lane_id).first())
    or_404(Board.query.filter_by(id=board_id).first())

    if lane.board not in current_user.boards:
        flask.abort(403)
    if board not in current_user.boards:
        flask.abort(403)

    lane.board_id = board_id
    db.session.commit()
    return flask.redirect(flask.url_for("lane_edit", lane_id=lane_id))


@app.route("/item/color/<item_id>/<color>")
@login_required
def item_color(item_id, color):
    """Change item color."""
    or_404(color in colors)
    item = or_404(Item.query.filter_by(id=item_id).first())

    if item.column.lane.board not in current_user.boards:
        flask.abort(403)

    item.color = color
    db.session.commit()
    return flask.redirect(flask.url_for("item", item_id=item_id))


@app.route("/item/<item_id>/toggle")
@login_required
def item_close_toggle(item_id):
    """Toggle item open/close state."""
    item = or_404(Item.query.filter_by(id=item_id).first())

    if item.column.lane.board not in current_user.boards:
        flask.abort(403)

    item.closed = not item.closed
    db.session.commit()
    return flask.redirect(flask.url_for("item", item_id=item_id))


@app.route("/column/<column_id>/toggle")
@login_required
def column_close_toggle(column_id):
    """Toggle column open/close state."""
    column = or_404(Column.query.filter_by(id=column_id).first())

    if column.lane.board not in current_user.boards:
        flask.abort(403)

    column.closed = not column.closed
    db.session.commit()
    return flask.redirect(flask.url_for("lane_edit", lane_id=column.lane.id))


@app.route("/lane/<lane_id>/toggle")
@login_required
def lane_close_toggle(lane_id):
    """Toggle lane open/close state."""
    lane = or_404(Lane.query.filter_by(id=lane_id).first())

    if lane.board not in current_user.boards:
        flask.abort(403)

    lane.closed = not lane.closed
    db.session.commit()
    return flask.redirect(flask.url_for("board_edit", board_id=lane.board.id))


@app.route("/board/<board_id>/toggle")
@login_required
def board_close_toggle(board_id):
    """Toggle board open/close state."""
    board = or_404(Board.query.filter_by(id=board_id).first())

    if board not in current_user.boards:
        flask.abort(403)

    board.closed = not board.closed
    db.session.commit()
    return flask.redirect(flask.url_for("boards"))


@app.route("/column/<column_id>/edit", methods=["GET", "POST"])
@login_required
def column_edit(column_id):
    """Return column edit page."""
    column = or_404(Column.query.filter_by(id=column_id).first())

    if column.lane.board not in current_user.boards:
        flask.abort(403)

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
            return flask.redirect(
                flask.url_for("board", board_id=item.column.lane.board.id)
                + f"#lane_{item.column.lane.id}"
            )
        if flask.request.form.get("Submit") == "Submit_rename_column":
            unsafe_new_column_name = flask.request.form.get("new_column_name")
            column.name = unsafe_new_column_name
            db.session.commit()
            return flask.redirect(
                flask.url_for("board", board_id=column.lane.board.id)
                + f"#lane_{column.lane.id}"
            )


@app.route("/board/<board_id>/graph")
@login_required
def board_graph(board_id):
    """Return board graph page."""
    board = or_404(Board.query.filter_by(id=board_id).first())

    if board not in current_user.boards:
        flask.abort(403)

    return flask.render_template("graph.jinja2", board=board)


def main(host="127.0.0.1", port=7777, debug=False):
    """Run flask app."""
    app.run(host=host, port=port, debug=debug)


if __name__ == "__main__":
    argh.dispatch_command(main)
