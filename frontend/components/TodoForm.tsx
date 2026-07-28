import { FormEvent, useState } from 'react';

interface TodoFormProps {
  onSubmit: (title: string) => Promise<void>;
  isSubmitting: boolean;
}

export default function TodoForm({ onSubmit, isSubmitting }: TodoFormProps): JSX.Element {
  const [title, setTitle] = useState<string>('');
  const [validationError, setValidationError] = useState<string>('');

  const handleSubmit = async (event: FormEvent<HTMLFormElement>): Promise<void> => {
    event.preventDefault();
    const trimmedTitle = title.trim();
    if (!trimmedTitle) {
      setValidationError('Please enter a todo.');
      return;
    }
    setValidationError('');
    try {
      await onSubmit(trimmedTitle);
      setTitle('');
    } catch {
      // The parent displays the request error.
    }
  };

  return (
    <form onSubmit={handleSubmit} noValidate aria-label="Add todo form">
      <label htmlFor="todo-title" className="mb-2 block text-sm font-semibold text-slate-700">New todo</label>
      <div className="flex flex-col gap-3 sm:flex-row">
        <input
          id="todo-title"
          type="text"
          value={title}
          onChange={(event) => setTitle(event.target.value)}
          placeholder="What needs to be done?"
          maxLength={200}
          disabled={isSubmitting}
          aria-invalid={Boolean(validationError)}
          aria-describedby={validationError ? 'todo-title-error' : undefined}
          className="min-w-0 flex-1 rounded-md border border-slate-300 px-3 py-2 text-slate-900 placeholder:text-slate-500 focus:border-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-slate-100"
        />
        <button type="submit" disabled={isSubmitting} className="rounded-md bg-blue-600 px-5 py-2 font-semibold text-white transition hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-60">
          {isSubmitting ? 'Adding...' : 'Add todo'}
        </button>
      </div>
      {validationError && <p id="todo-title-error" className="mt-2 text-sm text-red-700" role="alert">{validationError}</p>}
    </form>
  );
}
