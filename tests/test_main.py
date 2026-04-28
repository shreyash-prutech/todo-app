import main
import models
from database import Base
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

test_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

Base.metadata.create_all(bind=test_engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


main.app.dependency_overrides[main.get_db] = override_get_db
client = TestClient(main.app)


def get_test_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_todo_via_api(title="Test todo", description="Test description", completed=False):
    response = client.post(
        "/todos/",
        json={
            "title": title,
            "description": description,
            "completed": completed,
        },
    )
    assert response.status_code == 201
    return response


def test_root_endpoint_returns_expected_payload():
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "app": "Todo API", "version": "1.0.0"}


def test_create_todo_persists_and_returns_created_record():
    response = create_todo_via_api(
        title="Buy milk",
        description="Remember to buy milk",
        completed=False,
    )
    payload = response.json()

    assert payload["title"] == "Buy milk"
    assert payload["description"] == "Remember to buy milk"
    assert payload["completed"] is False
    assert "id" in payload

    with next(get_test_db()) as db:
        db_todo = db.query(models.Todo).filter(models.Todo.id == payload["id"]).first()
        assert db_todo is not None
        assert db_todo.title == "Buy milk"
        assert db_todo.description == "Remember to buy milk"
        assert db_todo.completed is False


def test_read_todos_returns_created_items():
    created = create_todo_via_api(
        title="Read books",
        description="Finish one chapter",
        completed=False,
    ).json()

    response = client.get("/todos/")

    assert response.status_code == 200
    todos = response.json()
    assert any(todo["id"] == created["id"] for todo in todos)
    assert any(todo["title"] == "Read books" for todo in todos)

    with next(get_test_db()) as db:
        db_todo = db.query(models.Todo).filter(models.Todo.id == created["id"]).first()
        assert db_todo is not None
        assert db_todo.title == "Read books"


def test_read_todo_returns_created_item_and_404_for_missing():
    created = create_todo_via_api(
        title="Walk dog",
        description="Evening walk",
        completed=True,
    ).json()

    response = client.get(f"/todos/{created['id']}")

    assert response.status_code == 200
    assert response.json()["id"] == created["id"]
    assert response.json()["title"] == "Walk dog"
    assert response.json()["description"] == "Evening walk"
    assert response.json()["completed"] is True

    with next(get_test_db()) as db:
        db_todo = db.query(models.Todo).filter(models.Todo.id == created["id"]).first()
        assert db_todo is not None
        assert db_todo.title == "Walk dog"

    missing_response = client.get("/todos/999999")

    assert missing_response.status_code == 404
    assert missing_response.json() == {"detail": "Todo not found"}


def test_update_todo_partially_updates_record_and_404_for_missing():
    created = create_todo_via_api(
        title="Original title",
        description="Original description",
        completed=False,
    ).json()

    response = client.put(
        f"/todos/{created['id']}",
        json={"title": "Updated title"},
    )

    assert response.status_code == 200
    updated = response.json()
    assert updated["id"] == created["id"]
    assert updated["title"] == "Updated title"
    assert updated["description"] == "Original description"
    assert updated["completed"] is False

    with next(get_test_db()) as db:
        db_todo = db.query(models.Todo).filter(models.Todo.id == created["id"]).first()
        assert db_todo is not None
        assert db_todo.title == "Updated title"
        assert db_todo.description == "Original description"
        assert db_todo.completed is False

    missing_response = client.put(
        "/todos/999999",
        json={"title": "Does not matter"},
    )

    assert missing_response.status_code == 404
    assert missing_response.json() == {"detail": "Todo not found"}


def test_delete_todo_removes_record_and_404_for_missing():
    created = create_todo_via_api(
        title="Delete me",
        description="Temporary task",
        completed=False,
    ).json()

    response = client.delete(f"/todos/{created['id']}")

    assert response.status_code == 204
    assert response.content == b""

    with next(get_test_db()) as db:
        db_todo = db.query(models.Todo).filter(models.Todo.id == created["id"]).first()
        assert db_todo is None

    missing_response = client.delete("/todos/999999")

    assert missing_response.status_code == 404
    assert missing_response.json() == {"detail": "Todo not found"}


def teardown_module(module):
    main.app.dependency_overrides.clear()
