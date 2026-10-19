import { Component, type ErrorInfo, type ReactNode } from "react";
import { captureFrontendException } from "@/shared/telemetry/sentry";

export interface ErrorBoundaryProps {
  readonly children: ReactNode;
  readonly fallback?: ReactNode;
}

interface ErrorBoundaryState {
  readonly hasError: boolean;
  readonly errorMessage: string;
}

export class ErrorBoundary extends Component<
  ErrorBoundaryProps,
  ErrorBoundaryState
> {
  public constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, errorMessage: "" };
  }

  public static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, errorMessage: error.message };
  }

  public override componentDidCatch(error: Error, info: ErrorInfo): void {
    captureFrontendException(error, {
      componentStack: info.componentStack ?? "unknown",
    });
  }

  public override render(): ReactNode {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }
      return (
        <div
          role="alert"
          data-testid="error-boundary-fallback"
          className="rounded-xl border border-destructive/40 bg-destructive/10 p-4 text-xs text-destructive"
        >
          {`UI Boundary Protected: ${this.state.errorMessage}`}
        </div>
      );
    }
    return this.props.children;
  }
}
