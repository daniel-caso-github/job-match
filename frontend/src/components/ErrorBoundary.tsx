import { Component, type ErrorInfo, type ReactNode } from "react";

interface ErrorBoundaryProps {
  children: ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
}

export default class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = { hasError: false };

  static getDerivedStateFromError(): ErrorBoundaryState {
    return { hasError: true };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("Error no capturado en la UI:", error, info);
  }

  render() {
    if (this.state.hasError) {
      return (
        <main className="max-w-[560px] mx-auto px-6 py-24 animate-fade-in">
          <div className="bg-neg-soft border border-neg-line rounded-2xl p-10 text-center">
            <h2 className="m-0 text-lg font-semibold text-fg">Algo salió mal</h2>
            <p className="mt-2 text-sm text-sub">Recargá la página para continuar.</p>
            <button
              type="button"
              onClick={() => window.location.reload()}
              className="mt-5 h-9 px-4 bg-accent rounded-lg text-accent-ink text-sm font-semibold"
            >
              Recargar
            </button>
          </div>
        </main>
      );
    }
    return this.props.children;
  }
}
