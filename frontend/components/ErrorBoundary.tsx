import React from 'react';

interface ErrorBoundaryProps {
  children: React.ReactNode;
  fallback?: React.ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error?: Error;
}

export default class ErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
  public state: ErrorBoundaryState = { hasError: false };

  public static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  public render() {
    if (this.state.hasError) {
      return this.props.fallback || (
        <main className="error-page">
          <div className="error-card">
            <span className="eyebrow">SYSTEM MESSAGE</span>
            <h1>Something went wrong</h1>
            <p>{this.state.error?.message || 'Please refresh and try again.'}</p>
            <button className="button primary" onClick={() => window.location.reload()}>Reload application</button>
          </div>
        </main>
      );
    }
    return this.props.children;
  }
}
