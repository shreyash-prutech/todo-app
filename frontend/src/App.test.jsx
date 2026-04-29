import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { beforeEach, afterEach, describe, it, vi } from 'vitest'
import App from './App.jsx'

const getApiUrl = () => {
  const host = window.location.hostname
  const port = window.location.port === '5173' ? '8000' : window.location.port
  return `http://${host}:${port}/todos/`
}

const mockFetch = (responses) => {
  const fetchMock = vi.fn()
  responses.forEach((response) => {
    fetchMock.mockImplementationOnce(response)
  })
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

const jsonResponse = (data, ok = true, status = 200) =>
  Promise.resolve({
    ok,
    status,
    json: () => Promise.resolve(data),
  })

describe('App', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    vi.clearAllMocks()
  })

  it('replaces the loading state with an empty state after fetching no todos', async () => {
    const fetchMock = mockFetch([
      () => jsonResponse([]),
    ])

    render(<App />)

    expect(screen.getByText('Loading tasks...')).toBeInTheDocument()

    await waitFor(() => {
      expect(screen.getByText('No tasks yet. Add one above!')).toBeInTheDocument()
    })

    expect(fetchMock).toHaveBeenCalledTimes(1)
    expect(fetchMock).toHaveBeenCalledWith(getApiUrl())
  })

  it('adds a todo through the form and renders the new item', async () => {
    const newTodo = {
      id: 101,
      title: 'Write tests',
      description: 'Cover the main flows',
      completed: false,
    }

    const fetchMock = vi.fn()
    fetchMock.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: () => Promise.resolve([]),
    })
    fetchMock.mockResolvedValueOnce({
      ok: true,
      status: 201,
      json: () => Promise.resolve(newTodo),
    })
    vi.stubGlobal('fetch', fetchMock)

    render(<App />)

    await waitFor(() => {
      expect(screen.getByText('No tasks yet. Add one above!')).toBeInTheDocument()
    })

    fireEvent.change(screen.getByPlaceholderText('What needs to be done?'), {
      target: { value: newTodo.title },
    })
    fireEvent.change(screen.getByPlaceholderText('Notes or description (optional)'), {
      target: { value: newTodo.description },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Add Task' }))

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        getApiUrl(),
        expect.objectContaining({
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            title: newTodo.title,
            description: newTodo.description,
            completed: false,
          }),
        }),
      )
    })

    expect(screen.getByText(newTodo.title)).toBeInTheDocument()
    expect(screen.getByText(newTodo.description)).toBeInTheDocument()
    expect(screen.getByPlaceholderText('What needs to be done?')).toHaveValue('')
    expect(screen.getByPlaceholderText('Notes or description (optional)')).toHaveValue('')
  })

  it('toggles a todo completion state and updates the DOM', async () => {
    const todo = {
      id: 7,
      title: 'Complete task',
      description: 'Mark me done',
      completed: false,
    }

    const fetchMock = vi.fn()
    fetchMock.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: () => Promise.resolve([todo]),
    })
    fetchMock.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: () => Promise.resolve({ ...todo, completed: true }),
    })
    vi.stubGlobal('fetch', fetchMock)

    render(<App />)

    const todoTitle = await screen.findByText(todo.title)
    const todoItem = todoTitle.closest('.todo-item')
    expect(todoItem).not.toBeNull()

    const checkbox = todoItem.querySelector('input[type="checkbox"]')
    expect(checkbox).toBeInTheDocument()
    expect(checkbox).not.toBeChecked()

    fireEvent.click(checkbox)

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        `${getApiUrl()}${todo.id}`,
        expect.objectContaining({
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ completed: true }),
        }),
      )
    })

    await waitFor(() => {
      expect(todoItem).toHaveClass('completed')
    })
    expect(checkbox).toBeChecked()
  })

  it('deletes a todo and removes it from the list', async () => {
    const todo = {
      id: 9,
      title: 'Delete me',
      description: 'This item should disappear',
      completed: false,
    }

    const fetchMock = vi.fn()
    fetchMock.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: () => Promise.resolve([todo]),
    })
    fetchMock.mockResolvedValueOnce({
      ok: true,
      status: 204,
      json: () => Promise.resolve(),
    })
    vi.stubGlobal('fetch', fetchMock)

    render(<App />)

    const todoTitle = await screen.findByText(todo.title)
    const todoItem = todoTitle.closest('.todo-item')
    expect(todoItem).not.toBeNull()

    fireEvent.click(screen.getByTitle('Delete task'))

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(`${getApiUrl()}${todo.id}`, {
        method: 'DELETE',
      })
    })

    await waitFor(() => {
      expect(screen.queryByText(todo.title)).not.toBeInTheDocument()
    })

    expect(screen.getByText('No tasks yet. Add one above!')).toBeInTheDocument()
  })

  it('logs fetch errors and exits the loading state', async () => {
    const error = new Error('network down')
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

    const fetchMock = vi.fn().mockRejectedValueOnce(error)
    vi.stubGlobal('fetch', fetchMock)

    render(<App />)

    await waitFor(() => {
      expect(screen.getByText('No tasks yet. Add one above!')).toBeInTheDocument()
    })

    expect(screen.queryByText('Loading tasks...')).not.toBeInTheDocument()
    expect(consoleSpy).toHaveBeenCalledWith('Error fetching todos:', error)
  })
})
