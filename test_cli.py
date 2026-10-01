import json
import os
import socket
import subprocess
import sys
import time
import urllib.request

import argh
import pytest

import app as app_module
import cli


@pytest.fixture(scope="session")
def base_url(app):
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    proc = subprocess.Popen(
        [sys.executable, "app.py", "--port", str(port)],
        cwd=os.path.dirname(os.path.abspath(app_module.__file__)),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    base = f"http://127.0.0.1:{port}"
    deadline = time.time() + 15
    while time.time() < deadline:
        try:
            urllib.request.urlopen(base + "/login", timeout=1)
            break
        except Exception:
            if proc.poll() is not None:
                proc.terminate()
                raise RuntimeError("catboard server exited early")
            time.sleep(0.1)
    else:
        proc.terminate()
        raise RuntimeError("catboard server did not start")
    yield base
    proc.terminate()
    proc.wait()


def _auth(base_url):
    return {"base_url": base_url, "user": "tester", "password": "testpass"}


def test_boards_list(base_url, capsys):
    cli.boards_list(json=True, **_auth(base_url))
    out = json.loads(capsys.readouterr().out)
    assert {"id": 1, "name": "TestBoard", "closed": False} in out


def test_boards_show(base_url, capsys):
    cli.boards_show("TestBoard", json=True, **_auth(base_url))
    out = json.loads(capsys.readouterr().out)
    assert out["name"] == "TestBoard"
    assert out["lanes"][0]["name"] == "Default"
    assert [c["name"] for c in out["lanes"][0]["columns"]] == [
        "Backlog", "Ready", "WIP", "Blocked", "QA", "Done",
    ]


def test_items_add_returns_id_and_persists(base_url, capsys):
    cli.items_add(
        "TestBoard", "Default", "Backlog", "cli item",
        description="from cli",
        json=True, **_auth(base_url),
    )
    out = json.loads(capsys.readouterr().out)
    assert out["name"] == "cli item"
    assert isinstance(out["id"], int)
    with app_module.app.app_context():
        item = app_module.Item.query.filter_by(name="cli item").first()
        assert item is not None
        assert item.description == "from cli"
        assert item.column.name == "Backlog"
        assert item.column.lane.name == "Default"


def test_items_list_contains_new_item(base_url, capsys):
    cli.items_list("TestBoard", json=True, **_auth(base_url))
    out = json.loads(capsys.readouterr().out)
    assert any(i["name"] == "cli item" and i["column"] == "Backlog" for i in out)


def test_items_list_lane_filter(base_url, capsys):
    cli.items_list("TestBoard", lane="Default", json=True, **_auth(base_url))
    out = json.loads(capsys.readouterr().out)
    assert all(i["lane"] == "Default" for i in out)


def test_items_get(base_url, capsys):
    with app_module.app.app_context():
        item_id = app_module.Item.query.filter_by(name="cli item").first().id
    cli.items_get(item_id, json=True, **_auth(base_url))
    out = json.loads(capsys.readouterr().out)
    assert out["description"] == "from cli"
    assert out["board"] == "TestBoard"
    assert out["closed"] is False


def test_items_edit(base_url, capsys):
    with app_module.app.app_context():
        item_id = app_module.Item.query.filter_by(name="cli item").first().id
    cli.items_edit(
        item_id, name="cli item renamed", state="closed",
        json=True, **_auth(base_url),
    )
    out = json.loads(capsys.readouterr().out)
    assert out["name"] == "cli item renamed"
    assert out["closed"] is True
    with app_module.app.app_context():
        item = app_module.Item.query.filter_by(id=item_id).first()
        assert item.name == "cli item renamed"
        assert item.closed is True
        assert item.description == "from cli"
    cli.items_edit(item_id, state="open", json=True, **_auth(base_url))
    with app_module.app.app_context():
        assert app_module.Item.query.filter_by(id=item_id).first().closed is False


def test_items_move_records_transition(base_url, capsys):
    with app_module.app.app_context():
        item_id = app_module.Item.query.filter_by(name="cli item renamed").first().id
        from_id = app_module.Item.query.filter_by(id=item_id).first().column_id
    cli.items_move(item_id, "Default", "Done", json=True, **_auth(base_url))
    out = json.loads(capsys.readouterr().out)
    assert out["moved"] is True
    assert out["to"]["column"] == "Done"
    with app_module.app.app_context():
        item = app_module.Item.query.filter_by(id=item_id).first()
        assert item.column.name == "Done"
        transition = app_module.ItemTransition.query.filter_by(
            item_id=item_id, from_column_id=from_id, to_column_id=item.column_id
        ).first()
        assert transition is not None


def test_items_move_same_column_is_noop(base_url, capsys):
    with app_module.app.app_context():
        item_id = app_module.Item.query.filter_by(name="cli item renamed").first().id
    cli.items_move(item_id, "Default", "Done", json=True, **_auth(base_url))
    out = json.loads(capsys.readouterr().out)
    assert out["moved"] is False


def test_bad_board_exits_nonzero(base_url, capsys):
    with pytest.raises(SystemExit) as e:
        cli.items_add("Nope", "Default", "Backlog", "x", **_auth(base_url))
    assert e.value.code == 1
    assert "no board named 'Nope'" in capsys.readouterr().err


def test_wrong_password_exits_nonzero(base_url, capsys):
    with pytest.raises(SystemExit) as e:
        cli.boards_list(base_url=base_url, user="tester", password="wrong")
    assert e.value.code == 1
    assert "login failed" in capsys.readouterr().err


def test_users_list(base_url, capsys):
    cli.users_list()
    assert "tester" in capsys.readouterr().out


def test_argh_dispatch_end_to_end(base_url, monkeypatch, capsys):
    monkeypatch.setattr(
        "sys.argv",
        [
            "cli.py", "items-add", "TestBoard", "Default", "Backlog",
            "dispatched item", "--json",
            "--base-url", base_url, "--user", "tester", "--password", "testpass",
        ],
    )
    argh.dispatch_commands([cli.boards_list, cli.items_add])
    out = json.loads(capsys.readouterr().out)
    assert out["name"] == "dispatched item"
