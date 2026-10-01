import os
import tempfile

import pytest

_scratch_db = os.path.join(tempfile.mkdtemp(prefix="catboard-test-"), "test.db")
os.environ["CATBOARD_SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{_scratch_db}"
os.environ["CATBOARD_SECRET_KEY"] = "test-secret-key"

import app as app_module  # noqa: E402


@pytest.fixture(scope="session")
def app():
    app_module.app.config["TESTING"] = True
    with app_module.app.app_context():
        app_module.db.create_all()
        user = app_module.User(username="tester")
        user.set_password("testpass")
        app_module.db.session.add(user)

        board = app_module.Board(name="TestBoard")
        lane = app_module.Lane(name="Default")
        for name in ("Backlog", "Ready", "WIP", "Blocked", "QA", "Done"):
            lane.columns.append(app_module.Column(name=name))
        board.lanes.append(lane)
        user.boards.append(board)

        lane.columns[0].items.append(
            app_module.Item(
                name="NoDescription", assigned="", color="w3-indigo", closed=False
            )
        )
        lane.columns[1].items.append(
            app_module.Item(
                name="WithDescription",
                assigned="",
                color="w3-indigo",
                closed=False,
                description="hello *world*",
            )
        )
        app_module.db.session.commit()
    yield app_module.app


@pytest.fixture
def client(app):
    with app.test_client() as c:
        c.post("/login", data={"username": "tester", "password": "testpass"})
        yield c
