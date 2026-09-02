import React from "react";

interface ConnectionStatusProps {
  isBackendConnected: boolean | null;
  isPipelineReady: boolean | null;
  companyCount?: number;
}

export const ConnectionStatus: React.FC<ConnectionStatusProps> = ({
  isBackendConnected,
  isPipelineReady,
  companyCount,
}) => {
  const isChecking = isBackendConnected === null || isPipelineReady === null;
  const isReady = isBackendConnected === true && isPipelineReady === true;
  const label = isChecking
    ? "Connecting"
    : !isBackendConnected
      ? "API offline"
      : isPipelineReady
      ? "Pipeline: Ready"
        : "Pipeline loading";

  return (
    <div
      role="status"
      aria-live="polite"
      aria-label={`Backend connection status: ${label}`}
      className="inline-flex min-h-8 items-center gap-2 rounded-lg border border-slate-200 bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-600 dark:border-slate-800 dark:bg-slate-800 dark:text-slate-300"
    >
      <span
        aria-hidden="true"
        className={`h-2 w-2 rounded-full ${
          isChecking
            ? "bg-slate-400"
            : isReady
              ? "bg-verified-green dark:bg-[#53B89A]"
              : !isBackendConnected
                ? "bg-rose-500"
                : "bg-amber-500"
        }`}
      />
      <span>{label}</span>
      {isReady && companyCount ? (
        <span className="hidden sm:inline text-slate-400 dark:text-slate-500">
          · {companyCount} indexed
        </span>
      ) : null}
    </div>
  );
};

ConnectionStatus.displayName = "ConnectionStatus";
