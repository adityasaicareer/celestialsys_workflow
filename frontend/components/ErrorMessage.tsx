interface ErrorMessageProps { message: string; onRetry?: () => void; }
export default function ErrorMessage({ message, onRetry }: ErrorMessageProps): JSX.Element { return <div className="error-box" role="alert"><strong>Something went wrong</strong><p>{message}</p>{onRetry && <button className="button button-outline" onClick={onRetry}>Try again</button>}</div>; }
