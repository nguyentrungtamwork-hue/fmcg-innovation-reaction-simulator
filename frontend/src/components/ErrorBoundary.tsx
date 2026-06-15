import { Component, type ErrorInfo, type ReactNode } from "react";

interface Props {
  children: ReactNode;
}
interface State {
  hasError: boolean;
  message: string;
}

export default class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, message: "" };

  static getDerivedStateFromError(err: unknown): State {
    return { hasError: true, message: err instanceof Error ? err.message : "Unknown error" };
  }

  componentDidCatch(err: unknown, info: ErrorInfo) {
    // dev-only console logging; never surface stack traces in the UI
    if (import.meta.env.DEV) {
      // eslint-disable-next-line no-console
      console.error("ErrorBoundary caught:", err, info);
    }
  }

  private reset = () => this.setState({ hasError: false, message: "" });

  render() {
    if (!this.state.hasError) return this.props.children;
    return (
      <div className="mx-auto max-w-2xl px-4 py-12 text-center" role="alert">
        <h1 className="text-xl font-semibold text-slate-900">Something went wrong while rendering this page.</h1>
        <p className="mt-2 text-sm text-slate-600">
          The dashboard hit an unexpected error. You can retry this view or go back to your projects.
        </p>
        <div className="mt-4 flex justify-center gap-2">
          <button className="btn-primary" onClick={this.reset}>Retry</button>
          <a className="btn-secondary" href="/">Go home</a>
        </div>
        {import.meta.env.DEV && this.state.message && (
          <pre className="mt-4 overflow-auto rounded bg-slate-900 p-3 text-left text-xs text-slate-100">{this.state.message}</pre>
        )}
      </div>
    );
  }
}
