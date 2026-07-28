import React from 'react';
interface Props { children: React.ReactNode; fallback?: React.ReactNode; }
interface State { hasError: boolean; error?: Error; }
export default class ErrorBoundary extends React.Component<Props, State> {
  public state: State = { hasError: false };
  static getDerivedStateFromError(error: Error): State { return { hasError: true, error }; }
  render(): React.ReactNode { if (this.state.hasError) return this.props.fallback || <main className="p-8"><h1 className="text-xl font-bold">Something went wrong</h1><p className="mt-2 text-slate-600">Please refresh and try again.</p></main>; return this.props.children; }
}