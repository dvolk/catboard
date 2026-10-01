"""Catboard command line interface."""

import getpass
import os
import sys
from json import dumps

import argh
import requests

from app import app, db, User, Board

DEFAULT_BASE_URL = "http://127.0.0.1:7777"


def _fail(message):
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(1)


def _session(base_url, user, password):
    if not user:
        _fail("missing --user")
    if not password:
        password = os.environ.get("CATBOARD_PASSWORD")
    if not password:
        if sys.stdin.isatty():
            password = getpass.getpass(f"password for {user}: ")
        else:
            _fail("no password (use --password or the CATBOARD_PASSWORD env var)")

    s = requests.Session()
    resp = s.post(
        base_url + "/login",
        data={"username": user, "password": password},
        allow_redirects=False,
    )
    if resp.status_code not in (301, 302):
        _fail(f"login failed (http {resp.status_code})")
    return s


def _index(s, base_url):
    resp = s.get(base_url + "/export_data")
    if resp.status_code != 200:
        _fail(f"could not fetch board data (http {resp.status_code})")
    data = resp.json()
    return {
        "boards": {b["id"]: b for b in data["Board"]},
        "lanes": {l["id"]: l for l in data["Lane"]},
        "columns": {c["id"]: c for c in data["Column"]},
        "items": {i["id"]: i for i in data["Item"]},
        "relationships": data["ItemRelationship"],
    }


def _resolve(ref, things, kind, scope=""):
    if str(ref).isdigit() and int(ref) in things:
        return things[int(ref)]
    matches = [t for t in things.values() if t["name"] == ref]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        _fail(f"ambiguous {kind} name '{ref}'{scope}")
    _fail(f"no {kind} named '{ref}'{scope}")


def _lanes_in(idx, board):
    return sorted(
        (l for l in idx["lanes"].values() if l["board_id"] == board["id"]),
        key=lambda l: l["id"],
    )


def _columns_in(idx, lane):
    return sorted(
        (c for c in idx["columns"].values() if c["lane_id"] == lane["id"]),
        key=lambda c: c["id"],
    )


def _item_location(idx, item):
    column = idx["columns"][item["column_id"]]
    lane = idx["lanes"][column["lane_id"]]
    board = idx["boards"][lane["board_id"]]
    return board, lane, column


def _emit(data, text, json_flag):
    if json_flag:
        print(dumps(data, indent=2))
    else:
        print(text)


def boards_list(base_url=DEFAULT_BASE_URL, user="", password=None, json=False):
    """List boards."""
    s = _session(base_url, user, password)
    idx = _index(s, base_url)
    boards = sorted(idx["boards"].values(), key=lambda b: b["id"])
    _emit(
        [{"id": b["id"], "name": b["name"], "closed": bool(b["closed"])} for b in boards],
        "\n".join(f"{b['id']}. {b['name']}" for b in boards),
        json,
    )


def boards_show(board, base_url=DEFAULT_BASE_URL, user="", password=None, json=False):
    """Show a board's lanes and columns."""
    s = _session(base_url, user, password)
    idx = _index(s, base_url)
    b = _resolve(board, idx["boards"], "board")
    lanes = []
    lines = [f"{b['id']}. {b['name']}"]
    for l in _lanes_in(idx, b):
        cols = []
        lines.append(f"  {l['id']}. {l['name']}")
        for c in _columns_in(idx, l):
            n = sum(1 for i in idx["items"].values() if i["column_id"] == c["id"])
            cols.append({"id": c["id"], "name": c["name"], "items": n})
            lines.append(f"    {c['id']}. {c['name']} ({n} items)")
        lanes.append({"id": l["id"], "name": l["name"], "columns": cols})
    _emit({"id": b["id"], "name": b["name"], "lanes": lanes}, "\n".join(lines), json)


def items_add(
    board,
    lane,
    column,
    name,
    description=None,
    assigned="",
    color="w3-indigo",
    base_url=DEFAULT_BASE_URL,
    user="",
    password=None,
    json=False,
):
    """Add an item to a column (board/lane/column by name or id)."""
    s = _session(base_url, user, password)
    idx = _index(s, base_url)
    b = _resolve(board, idx["boards"], "board")
    l = _resolve(lane, {i: x for i, x in idx["lanes"].items() if x["board_id"] == b["id"]}, "lane", f" in board '{b['name']}'")
    c = _resolve(column, {i: x for i, x in idx["columns"].items() if x["lane_id"] == l["id"]}, "column", f" in lane '{l['name']}'")

    resp = s.post(
        f"{base_url}/column/{c['id']}/edit",
        data={
            "Submit": "Submit_new_item",
            "new_item_name": name,
            "new_item_assigned": assigned,
            "new_item_color": color,
            "new_item_template": "",
        },
        headers={"Accept": "application/json"},
        allow_redirects=False,
    )
    if resp.status_code != 200:
        _fail(f"item creation failed (http {resp.status_code})")
    item_id = resp.json()["id"]

    if description is not None:
        resp = s.post(
            f"{base_url}/item/{item_id}",
            data={
                "new_name": name,
                "new_assign_name": assigned,
                "new_description": description,
                "Submit": "Submit_save",
            },
            allow_redirects=False,
        )
        if resp.status_code != 302:
            _fail(f"setting description failed (http {resp.status_code})")

    _emit(
        {
            "id": item_id,
            "name": name,
            "board": b["name"],
            "lane": l["name"],
            "column": c["name"],
        },
        f"created item {item_id}: {name} ({b['name']} / {l['name']} / {c['name']})",
        json,
    )


def items_list(
    board,
    lane=None,
    column=None,
    base_url=DEFAULT_BASE_URL,
    user="",
    password=None,
    json=False,
):
    """List a board's items (optionally one lane or one column)."""
    s = _session(base_url, user, password)
    idx = _index(s, base_url)
    b = _resolve(board, idx["boards"], "board")
    if lane is not None:
        l = _resolve(lane, {i: x for i, x in idx["lanes"].items() if x["board_id"] == b["id"]}, "lane", f" in board '{b['name']}'")
        lane_ids = {l["id"]}
    else:
        lane_ids = {l["id"] for l in _lanes_in(idx, b)}
    if column is not None:
        c = _resolve(column, {i: x for i, x in idx["columns"].items() if x["lane_id"] in lane_ids}, "column", f" in board '{b['name']}'")
        column_ids = {c["id"]}
    else:
        column_ids = {i for i, x in idx["columns"].items() if x["lane_id"] in lane_ids}

    items = sorted(
        (i for i in idx["items"].values() if i["column_id"] in column_ids),
        key=lambda i: i["id"],
    )
    out = []
    lines = []
    for i in items:
        bb, ll, cc = _item_location(idx, i)
        suffix = " (closed)" if i["closed"] else ""
        lines.append(f"{i['id']}. {i['name']}  [{ll['name']} / {cc['name']}]{suffix}")
        out.append(
            {
                "id": i["id"],
                "name": i["name"],
                "closed": bool(i["closed"]),
                "assigned": i["assigned"],
                "board": bb["name"],
                "lane": ll["name"],
                "column": cc["name"],
            }
        )
    _emit(out, "\n".join(lines), json)


def items_get(item_id, base_url=DEFAULT_BASE_URL, user="", password=None, json=False):
    """Show one item by id."""
    s = _session(base_url, user, password)
    idx = _index(s, base_url)
    i = _resolve(item_id, idx["items"], "item")
    b, l, c = _item_location(idx, i)
    subtasks = [
        idx["items"][r["item2_id"]]["name"]
        for r in idx["relationships"]
        if r["item1_id"] == i["id"] and r["type"] == 100 and r["item2_id"] in idx["items"]
    ]
    data = {
        "id": i["id"],
        "name": i["name"],
        "closed": bool(i["closed"]),
        "public": bool(i["public"]),
        "color": i["color"],
        "assigned": i["assigned"],
        "description": i["description"],
        "board": b["name"],
        "lane": l["name"],
        "column": c["name"],
        "subtasks": subtasks,
    }
    lines = [
        f"{i['id']}. {i['name']}  [{b['name']} / {l['name']} / {c['name']}]"
        + (" (closed)" if i["closed"] else ""),
        f"assigned: {i['assigned']}",
        f"color: {i['color']}",
        f"subtasks: {', '.join(subtasks) if subtasks else '-'}",
        "",
        i["description"] or "",
    ]
    _emit(data, "\n".join(lines), json)


def items_edit(
    item_id,
    name=None,
    description=None,
    assigned=None,
    state=None,
    base_url=DEFAULT_BASE_URL,
    user="",
    password=None,
    json=False,
):
    """Edit an item: --name, --description, --assigned, --state open|closed."""
    s = _session(base_url, user, password)
    idx = _index(s, base_url)
    i = _resolve(item_id, idx["items"], "item")
    if state is not None and state not in ("open", "closed"):
        _fail("--state must be 'open' or 'closed'")

    resp = s.post(
        f"{base_url}/item/{i['id']}",
        data={
            "new_name": name if name is not None else i["name"],
            "new_assign_name": assigned if assigned is not None else (i["assigned"] or ""),
            "new_description": description if description is not None else (i["description"] or ""),
            "Submit": "Submit_save",
        },
        allow_redirects=False,
    )
    if resp.status_code != 302:
        _fail(f"item edit failed (http {resp.status_code})")

    closed = bool(i["closed"])
    if state is not None and (state == "closed") != closed:
        resp = s.get(f"{base_url}/item/{i['id']}/toggle", allow_redirects=False)
        if resp.status_code != 302:
            _fail(f"item toggle failed (http {resp.status_code})")
        closed = state == "closed"

    b, l, c = _item_location(idx, i)
    _emit(
        {
            "id": i["id"],
            "name": name if name is not None else i["name"],
            "closed": closed,
            "board": b["name"],
            "lane": l["name"],
            "column": c["name"],
        },
        f"updated item {i['id']}: {name if name is not None else i['name']}"
        f" ({b['name']} / {l['name']} / {c['name']}, {'closed' if closed else 'open'})",
        json,
    )


def items_move(
    item_id,
    lane,
    column,
    base_url=DEFAULT_BASE_URL,
    user="",
    password=None,
    json=False,
):
    """Move an item to a column (lane/column by name or id)."""
    s = _session(base_url, user, password)
    idx = _index(s, base_url)
    i = _resolve(item_id, idx["items"], "item")
    from_board, from_lane, from_column = _item_location(idx, i)

    lane_matches = [x for x in idx["lanes"].values() if x["name"] == lane]
    if str(lane).isdigit() and int(lane) in idx["lanes"]:
        lane_matches = [idx["lanes"][int(lane)]]
    if not lane_matches:
        _fail(f"no lane named '{lane}'")
    if len(lane_matches) > 1:
        own = [x for x in lane_matches if x["board_id"] == from_board["id"]]
        if len(own) == 1:
            lane_matches = own
        else:
            _fail(f"ambiguous lane name '{lane}'")
    l = lane_matches[0]
    c = _resolve(
        column,
        {x["id"]: x for x in idx["columns"].values() if x["lane_id"] == l["id"]},
        "column",
        f" in lane '{l['name']}'",
    )

    if c["id"] == i["column_id"]:
        _emit(
            {"id": i["id"], "lane": l["name"], "column": c["name"], "moved": False},
            f"item {i['id']} is already in {l['name']} / {c['name']}",
            json,
        )
        return

    resp = s.get(f"{base_url}/item/move/{i['id']}/{c['id']}", allow_redirects=False)
    if resp.status_code != 302:
        _fail(f"item move failed (http {resp.status_code})")
    _emit(
        {
            "id": i["id"],
            "moved": True,
            "from": {"lane": from_lane["name"], "column": from_column["name"]},
            "to": {"lane": l["name"], "column": c["name"]},
        },
        f"moved item {i['id']}: {from_lane['name']} / {from_column['name']}"
        f" -> {l['name']} / {c['name']}",
        json,
    )


def users_list():
    """List users and their boards."""
    with app.app_context():
        for u in User.query.all():
            print(f"{u.id}. {u.username} (boards: {u.boards})")


def users_add(username, password):
    """Create a user."""
    with app.app_context():
        u = User(username=username, password_hash="")
        u.set_password(password)
        db.session.add(u)
        db.session.commit()


def users_remove(username):
    """Remove a user."""
    with app.app_context():
        user = User.query.filter_by(username=username).first()
        if user:
            db.session.delete(user)
            db.session.commit()
        else:
            print(f"No user found with username: {username}")


def users_set_password(username, new_password):
    """Set a user's password."""
    with app.app_context():
        user = User.query.filter_by(username=username).first()
        if user:
            user.set_password(new_password)
            db.session.commit()
        else:
            print(f"No user found with username: {username}")


def users_add_board(username, board_id):
    """Grant a user a board."""
    with app.app_context():
        user = User.query.filter_by(username=username).first()
        if user:
            board = Board.query.filter_by(id=board_id).first()
            user.boards.append(board)
            db.session.commit()
        else:
            print(f"No user found with username: {username}")


def users_remove_board(username, board_id):
    """Revoke a user's board."""
    with app.app_context():
        user = User.query.filter_by(username=username).first()
        if user:
            board = Board.query.filter_by(id=board_id).first()
            if board in user.boards:
                user.boards.remove(board)
                db.session.commit()
            else:
                print(f"No board found with name: {board_id}")
        else:
            print(f"No user found with username: {username}")


if __name__ == "__main__":
    argh.dispatch_commands(
        [
            boards_list,
            boards_show,
            items_add,
            items_list,
            items_get,
            items_edit,
            items_move,
            users_list,
            users_add,
            users_remove,
            users_set_password,
            users_add_board,
            users_remove_board,
        ]
    )
