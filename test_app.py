import json

from markupsafe import Markup

import app as app_module
import to_md


def _new_item(name, description=None):
    with app_module.app.app_context():
        lane = app_module.Lane.query.first()
        item = app_module.Item(
            name=name,
            assigned="",
            color="w3-indigo",
            closed=False,
            description=description,
        )
        lane.columns[0].items.append(item)
        app_module.db.session.commit()
        return item.id


def test_item_view_with_none_description(client):
    item_id = _new_item("view-none-desc")
    assert client.get(f"/item/{item_id}/view").status_code == 200


def test_item_view_renders_markdown(client):
    item_id = _new_item("md-render", description="# Heading\n- [x] done\n**bold**")
    body = client.get(f"/item/{item_id}/view").get_data(as_text=True)
    assert "<h1>" in body
    assert "<strong>bold</strong>" in body


def test_item_name_html_escaped_on_board_page(client):
    _new_item("<script>alert('xss')</script>")
    body = client.get("/board/1").get_data(as_text=True)
    assert "<script>alert('xss')</script>" not in body
    assert "&lt;script&gt;alert" in body
    assert '<i class="fa' in body


def test_lane_edit_column_sort_button_value(client):
    body = client.get("/lane/1/edit").get_data(as_text=True)
    assert 'value="Submit_columns_sorted"' in body


def test_column_sort_is_persisted(client):
    with app_module.app.app_context():
        lane = app_module.Lane.query.first()
        cols = {c.name: c.id for c in lane.columns}
        expected = ",".join(str(cols[n]) for n in ("Done", "QA", "WIP", "Ready", "Backlog", "Blocked"))
    resp = client.post(
        "/lane/1/edit",
        data={
            "columns_sorted": "Done, QA, WIP, Ready, Backlog, Blocked",
            "Submit": "Submit_columns_sorted",
        },
    )
    assert resp.status_code == 302
    with app_module.app.app_context():
        assert app_module.Lane.query.first().columns_sorted == expected


def test_subtask_links_removed_when_description_cleared(client):
    target_id = _new_item("subtask-target")
    parent_id = _new_item("subtask-parent")

    client.post(
        f"/item/{parent_id}",
        data={
            "new_name": "subtask-parent",
            "new_assign_name": "",
            "new_description": f"see subtask #{target_id}",
            "Submit": "Submit_save",
        },
    )
    with app_module.app.app_context():
        assert app_module.ItemRelationship.query.filter_by(
            item1_id=parent_id, item2_id=target_id
        ).first() is not None

    client.post(
        f"/item/{parent_id}",
        data={
            "new_name": "subtask-parent",
            "new_assign_name": "",
            "new_description": "no more subtasks",
            "Submit": "Submit_save",
        },
    )
    with app_module.app.app_context():
        assert app_module.ItemRelationship.query.filter_by(
            item1_id=parent_id
        ).first() is None


def test_url_is_image():
    assert app_module.url_is_image("http://x.com/photo.png")
    assert app_module.url_is_image("http://x.com/a.JPG")
    assert app_module.url_is_image("http://x.com/p.jpeg")
    assert not app_module.url_is_image("http://x.com/jp")
    assert not app_module.url_is_image("http://x.com/photograph")


def test_to_md_handles_none_and_escapes():
    assert to_md.text_to_html(None) == ""
    assert to_md.text_to_html("") == ""
    out = to_md.text_to_html("<script>alert(1)</script>")
    assert "<script>" not in out
    assert "&lt;script&gt;" in out


def test_login_wrong_password_returns_404(client):
    assert (
        client.post("/login", data={"username": "tester", "password": "wrong"})
        .status_code
        == 404
    )


def test_export_data_route(client):
    resp = client.get("/export_data")
    assert resp.status_code == 200
    data = json.loads(resp.get_data(as_text=True))
    assert set(data) == {
        "Item", "ItemTransition", "ItemRelationship", "Column", "Lane", "Board"
    }
    assert len(data["Board"]) >= 1


def test_graph_labels_are_js_safe(client):
    _new_item('We"ird\nname')
    body = client.get("/board/1/graph").get_data(as_text=True)
    assert "We\\\"ird\\nname (Backlog)" in body


def test_instance_import_rejects_non_http_urls(client):
    for bad in ("ftp://x.com", "file:///etc/passwd", "not a url"):
        resp = client.post(
            "/import_data_from_instance", data={"instance_url": bad}
        )
        assert resp.status_code == 400


def test_icon_helper_returns_safe_markup():
    assert isinstance(app_module.icon("cog"), Markup)
    assert "<i class=\"fa fa-cog fa-fw\"></i>" in str(app_module.icon("cog"))
