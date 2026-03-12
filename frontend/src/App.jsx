import { useState, useEffect } from 'react'
import './App.css'

const API_URL = 'http://localhost:8000/todos/';

function App() {
  const [todos, setTodos] = useState([])
  const [newTitle, setNewTitle] = useState('')
  const [newDescription, setNewDescription] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchTodos()
  }, [])

  const fetchTodos = async () => {
    try {
      const response = await fetch(API_URL)
      if (response.ok) {
        const data = await response.json()
        setTodos(data)
      }
    } catch (error) {
      console.error('Error fetching todos:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleAddTodo = async (e) => {
    e.preventDefault()
    if (!newTitle.trim()) return

    try {
      const response = await fetch(API_URL, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          title: newTitle,
          description: newDescription || null,
          completed: false
        }),
      })

      if (response.ok) {
        const newTodo = await response.json()
        setTodos([...todos, newTodo])
        setNewTitle('')
        setNewDescription('')
      }
    } catch (error) {
      console.error('Error adding todo:', error)
    }
  }

  const toggleTodo = async (id, currentStatus) => {
    try {
      const response = await fetch(`${API_URL}${id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          completed: !currentStatus
        }),
      })

      if (response.ok) {
        setTodos(todos.map(todo => 
          todo.id === id ? { ...todo, completed: !currentStatus } : todo
        ))
      }
    } catch (error) {
      console.error('Error toggling todo:', error)
    }
  }

  const deleteTodo = async (id) => {
    try {
      const response = await fetch(`${API_URL}${id}`, {
        method: 'DELETE',
      })

      if (response.ok || response.status === 204) {
        setTodos(todos.filter(todo => todo.id !== id))
      }
    } catch (error) {
      console.error('Error deleting todo:', error)
    }
  }

  return (
    <div className="app-container">
      <header className="header">
        <h1>Tasks</h1>
        <p>Stay organized, stay focused.</p>
      </header>

      <form className="todo-form" onSubmit={handleAddTodo}>
        <div className="input-group">
          <input
            type="text"
            className="input-field"
            placeholder="What needs to be done?"
            value={newTitle}
            onChange={(e) => setNewTitle(e.target.value)}
          />
          <button type="submit" className="add-btn">Add Task</button>
        </div>
        <textarea
          className="textarea-field"
          placeholder="Notes or description (optional)"
          value={newDescription}
          onChange={(e) => setNewDescription(e.target.value)}
          rows="2"
        />
      </form>

      <div className="todo-list">
        {loading ? (
          <div className="empty-state">Loading tasks...</div>
        ) : todos.length === 0 ? (
          <div className="empty-state">No tasks yet. Add one above!</div>
        ) : (
          todos.map((todo) => (
            <div key={todo.id} className={`todo-item ${todo.completed ? 'completed' : ''}`}>
              <div className="checkbox-wrapper">
                <input
                  type="checkbox"
                  className="checkbox"
                  checked={todo.completed}
                  onChange={() => toggleTodo(todo.id, todo.completed)}
                />
              </div>
              <div className="todo-content">
                <span className="todo-title">{todo.title}</span>
                {todo.description && <span className="todo-desc">{todo.description}</span>}
              </div>
              <button 
                className="delete-btn" 
                onClick={() => deleteTodo(todo.id)}
                title="Delete task"
              >
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0" />
                </svg>
              </button>
            </div>
          ))
        )}
      </div>
    </div>
  )
}

export default App
