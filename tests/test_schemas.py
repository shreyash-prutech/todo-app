import pytest
from pydantic import ValidationError
from schemas import Todo, TodoBase, TodoCreate, TodoUpdate


def test_todo_base_defaults():
    todo = TodoBase(title="Sample task")
    assert todo.title == "Sample task"
    assert todo.description is None
    assert todo.completed is False


def test_todo_base_requires_title():
    with pytest.raises(ValidationError):
        TodoBase()


def test_todo_create_inherits_fields():
    todo = TodoCreate(title="New", description="desc", completed=True)
    assert todo.title == "New"
    assert todo.description == "desc"
    assert todo.completed is True

    minimal = TodoCreate(title="Only title")
    assert minimal.title == "Only title"
    assert minimal.description is None
    assert minimal.completed is False

    with pytest.raises(ValidationError):
        TodoCreate()


def test_todo_update_all_optional():
    update = TodoUpdate()
    assert update.title is None
    assert update.description is None
    assert update.completed is None


def test_todo_update_partial():
    update = TodoUpdate(completed=True)
    dumped = update.model_dump(exclude_unset=True)
    assert dumped == {"completed": True}

    update2 = TodoUpdate(title="Changed", description="d")
    dumped2 = update2.model_dump(exclude_unset=True)
    assert dumped2 == {"title": "Changed", "description": "d"}


def test_todo_response_schema():
    todo = Todo(id=1, title="Task", description="desc", completed=True)
    assert todo.id == 1
    assert todo.title == "Task"
    assert todo.description == "desc"
    assert todo.completed is True

    minimal = Todo(id=2, title="Bare")
    assert minimal.id == 2
    assert minimal.title == "Bare"
    assert minimal.description is None
    assert minimal.completed is False

    with pytest.raises(ValidationError):
        Todo(title="No id")
