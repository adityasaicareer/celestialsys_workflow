import { Todo } from '../lib/api';

interface TodoListProps {
  todos: Todo[];
  onDelete: (id: number | string) => Promise<void>;
  deletingId: number | string | null;
}

export default function TodoList({ todos, onDelete, deletingId }: TodoListProps): JSX.Element {
  if (todos.length === 0) {
    return <p className="py-8 text-center text-slate-600">No todos yet. Add one above to get started.</p>;
  }

  return (
    <ul className="divide-y divide-slate-200" aria-label="Todo items">
      {todos.map((todo) => (
        <li key={todo.id} className="flex items-center justify-between gap-4 py-4">
          <span className="break-words text-slate-800">{todo.title}</span>
          <button
            type="button"
            onClick={() => void onDelete(todo.id)}
            disabled={deletingId === todo.id}
            className="shrink-0 rounded-md border border-red-300 px-3 py-1.5 text-sm font-semibold text-red-700 hover:bg-red-50 focus:outline-none focus:ring-2 focus:ring-red-500 disabled:cursor-not-allowed disabled:opacity-60"
            aria-label={`Delete todo: ${todo.title}`}
          >
            {deletingId === todo.id ? 'Deleting...' : 'Delete'}
          </button>
        </li>
      ))}
    </ul>
  );
}
