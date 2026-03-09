# Todo App (FastAPI Backend)

A simple FastAPI backend for managing Todos, designed specifically for testing scenarios and workflows in the QIF platform.

## Features
- Complete CRUD operations (Create, Read, Update, Delete)
- SQLite database for easy setup and testing
- OpenAPI documentation out of the box using FastAPI

## Setup Instructions

1. **Install Dependencies:**
   Ensure you have Python installed. It is recommended to create a virtual environment first.
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the Application:**
   ```bash
   uvicorn main:app --reload
   ```

3. **View the API Documentation:**
   Open your browser and navigate to:
   - **Swagger UI:** `http://127.0.0.1:8000/docs`
   - **ReDoc:** `http://127.0.0.1:8000/redoc`

## API Endpoints

- `POST /todos/`: Create a new todo
- `GET /todos/`: Get a list of todos
- `GET /todos/{todo_id}`: Get a specific todo by ID
- `PUT /todos/{todo_id}`: Update a specific todo
- `DELETE /todos/{todo_id}`: Delete a specific todo
