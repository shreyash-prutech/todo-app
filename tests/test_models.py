from models import Todo


def test_create_todo_model(db_session):
    todo = Todo(title="x", description="y", completed=False)
    db_session.add(todo)
    db_session.commit()
    db_session.refresh(todo)

    assert todo.id is not None
    assert isinstance(todo.id, int)
    assert todo.title == "x"
    assert todo.description == "y"
    assert todo.completed is False
    assert Todo.__tablename__ == "todos"


def test_todo_default_completed(db_session):
    todo = Todo(title="x")
    db_session.add(todo)
    db_session.commit()
    db_session.refresh(todo)

    fetched = db_session.query(Todo).filter(Todo.id == todo.id).first()
    assert fetched is not None
    assert fetched.title == "x"
    assert fetched.description is None
    assert fetched.completed is False or fetched.completed is None


def test_query_todo_by_id(db_session):
    todo = Todo(title="findme", description="desc", completed=True)
    db_session.add(todo)
    db_session.commit()
    db_session.refresh(todo)

    fetched = db_session.query(Todo).filter(Todo.id == todo.id).first()
    assert fetched is not None
    assert fetched.id == todo.id
    assert fetched.title == "findme"
    assert fetched.description == "desc"
    assert fetched.completed is True
