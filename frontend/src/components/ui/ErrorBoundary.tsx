import { Component, ErrorInfo, ReactNode } from "react";
import { AlertOctagon, RotateCcw } from "lucide-react";
import { Button } from "./Button";

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("ErrorBoundary caught an unhandled error:", error, errorInfo);
  }

  public handleReset = () => {
    this.setState({ hasError: false, error: null });
    window.location.reload();
  };

  public render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div className="flex min-h-[400px] flex-col items-center justify-center rounded-xl border border-red-500/30 bg-red-950/20 p-8 text-center">
          <div className="flex h-12 w-12 items-center justify-center rounded-full bg-red-900/40 text-red-400 mb-4">
            <AlertOctagon className="h-6 w-6" />
          </div>
          <h2 className="text-lg font-bold text-white">Something went wrong</h2>
          <p className="mt-1 text-xs text-red-300/80 max-w-md">
            {this.state.error?.message || "An unexpected runtime error occurred in this view."}
          </p>
          <div className="mt-5">
            <Button
              variant="secondary"
              size="sm"
              onClick={this.handleReset}
              leftIcon={<RotateCcw className="h-4 w-4" />}
            >
              Reload View
            </Button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
