import pytest


def test_root(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "app": "Todo API", "version": "1.0.0"}


def test_create_todo(client):
    payload = {"title": "Buy groceries", "description": "Milk, eggs, bread", "completed": False}
    response = client.post("/todos/", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert isinstance(data["id"], int)
    assert data["title"] == payload["title"]
    assert data["description"] == payload["description"]
    assert data["completed"] == payload["completed"]


def test_create_todo_minimal(client):
    response = client.post("/todos/", json={"title": "Just a title"})
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["title"] == "Just a title"
    assert data["description"] is None
    assert data["completed"] is False


def test_create_todo_invalid(client):
    response = client.post("/todos/", json={"description": "no title here"})
    assert response.status_code == 422


def test_read_todos_empty(client):
    response = client.get("/todos/")
    assert response.status_code == 200
    assert response.json() == []


def test_read_todos(client):
    client.post("/todos/", json={"title": "First task"})
    client.post("/todos/", json={"title": "Second task", "description": "second desc"})
    response = client.get("/todos/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    titles = [t["title"] for t in data]
    assert "First task" in titles
    assert "Second task" in titles


def test_read_todos_pagination(client):
    client.post("/todos/", json={"title": "Task 1"})
    client.post("/todos/", json={"title": "Task 2"})
    client.post("/todos/", json={"title": "Task 3"})

    response = client.get("/todos/?skip=1&limit=1")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1


def test_read_todo(client):
    create_resp = client.post(
        "/todos/",
        json={"title": "Read test", "description": "desc here", "completed": True},
    )
    todo_id = create_resp.json()["id"]

    response = client.get(f"/todos/{todo_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == todo_id
    assert data["title"] == "Read test"
    assert data["description"] == "desc here"
    assert data["completed"] is True


def test_read_todo_not_found(client):
    response = client.get("/todos/9999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Todo not found"


def test_update_todo(client):
    create_resp = client.post(
        "/todos/", json={"title": "Original", "description": "original desc", "completed": False}
    )
    todo_id = create_resp.json()["id"]

    update_resp = client.put(
        f"/todos/{todo_id}",
        json={"title": "Updated title", "completed": True},
    )
    assert update_resp.status_code == 200
    data = update_resp.json()
    assert data["id"] == todo_id
    assert data["title"] == "Updated title"
    assert data["completed"] is True
    assert data["description"] == "original desc"


def test_update_todo_partial(client):
    create_resp = client.post(
        "/todos/",
        json={"title": "Keep title", "description": "Keep desc", "completed": False},
    )
    todo_id = create_resp.json()["id"]

    update_resp = client.put(f"/todos/{todo_id}", json={"completed": True})
    assert update_resp.status_code == 200
    data = update_resp.json()
    assert data["title"] == "Keep title"
    assert data["description"] == "Keep desc"
    assert data["completed"] is True

    get_resp = client.get(f"/todos/{todo_id}")
    assert get_resp.json() == data


def test_update_todo_not_found(client):
    response = client.put("/todos/9999", json={"title": "Anything"})
    assert response.status_code == 404
    assert response.json()["detail"] == "Todo not found"


def test_delete_todo(client):
    create_resp = client.post("/todos/", json={"title": "To be deleted"})
    todo_id = create_resp.json()["id"]

    delete_resp = client.delete(f"/todos/{todo_id}")
    assert delete_resp.status_code == 204

    get_resp = client.get(f"/todos/{todo_id}")
    assert get_resp.status_code == 404
    assert get_resp.json()["detail"] == "Todo not found"


def test_delete_todo_not_found(client):
    response = client.delete("/todos/9999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Todo not found"
