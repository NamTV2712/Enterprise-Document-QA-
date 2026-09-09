import React from "react";
import { useLocale } from "../lib/i18n";

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
  const { locale } = useLocale();
  const isChecking = isBackendConnected === null || isPipelineReady === null;
  const isReady = isBackendConnected === true && isPipelineReady === true;
  const label = isChecking
    ? locale === "vi" ? "Đang kết nối" : "Connecting"
    : !isBackendConnected
      ? locale === "vi" ? "API ngoại tuyến" : "API offline"
      : isPipelineReady
      ? locale === "vi" ? "Pipeline: Sẵn sàng" : "Pipeline: Ready"
        : locale === "vi" ? "Đang tải pipeline" : "Pipeline loading";

  return (
    <div
      role="status"
      aria-live="polite"
      aria-label={`${locale === "vi" ? "Trạng thái kết nối backend" : "Backend connection status"}: ${label}`}
      title={label}
      className={`connection-status connection-status--${
        isChecking ? "checking" : isReady ? "ready" : !isBackendConnected ? "offline" : "loading"
      }`}
    >
      <span
        aria-hidden="true"
        className={`connection-dot ${
          isChecking
            ? "connection-dot--checking"
            : isReady
              ? "connection-dot--ready"
              : !isBackendConnected
                ? "connection-dot--offline"
                : "connection-dot--loading"
        }`}
      />
        <span className="hidden whitespace-nowrap sm:inline">{label}</span>
      {isReady && companyCount ? (
        <span className="hidden sm:inline connection-status__meta">
          · {companyCount} {locale === "vi" ? "công ty đã lập chỉ mục" : "indexed"}
        </span>
      ) : null}
    </div>
  );
};

ConnectionStatus.displayName = "ConnectionStatus";
