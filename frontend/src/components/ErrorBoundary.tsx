/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React from "react";
import { AlertTriangle, RefreshCw } from "lucide-react";

interface ErrorBoundaryProps {
  children: React.ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends React.Component<
  ErrorBoundaryProps,
  ErrorBoundaryState
> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error("ErrorBoundary caught:", error, errorInfo);
  }

  handleReload = () => {
    window.location.reload();
  };

  render() {
    if (this.state.hasError) {
      return (
        <main className="flex items-center justify-center min-h-screen bg-[#FCFBF8] dark:bg-[#171D2B] p-4">
          <div className="max-w-md w-full bg-white dark:bg-[#1E2738] border border-slate-200 dark:border-slate-700 rounded-2xl p-6 text-center space-y-4 shadow-lg">
            <div className="w-12 h-12 mx-auto bg-rose-100 dark:bg-rose-950/30 rounded-full flex items-center justify-center">
              <AlertTriangle className="w-6 h-6 text-rose-600 dark:text-rose-400" />
            </div>
            <h1 className="text-lg font-bold text-[#26324A] dark:text-[#FCFBF8]">
              Something went wrong
            </h1>
            <p className="text-sm text-slate-600 dark:text-slate-400">
              The application encountered an unexpected error. Please reload to
              try again.
            </p>
            <button
              type="button"
              onClick={this.handleReload}
              className="inline-flex items-center gap-2 min-h-11 px-4 py-2 bg-[#26324A] dark:bg-[#FCFBF8] text-[#FCFBF8] dark:text-[#26324A] rounded-lg font-semibold text-sm hover:opacity-95 transition-opacity cursor-pointer"
            >
              <RefreshCw className="w-4 h-4" />
              Reload
            </button>
          </div>
        </main>
      );
    }

    return this.props.children;
  }
}
