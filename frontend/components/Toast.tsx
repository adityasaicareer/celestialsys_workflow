interface ToastProps { message: string; type?: 'success' | 'error'; onClose: () => void }
export default function Toast({ message, type = 'success', onClose }: ToastProps): JSX.Element | null { if (!message) return null; return <div className={`toast ${type}`} role="status">{message}<button onClick={onClose} aria-label="Dismiss notification">×</button></div>; }
