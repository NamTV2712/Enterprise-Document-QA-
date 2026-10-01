import React, { type ReactNode } from "react";
import { useLocale } from "../../lib/i18n";
import { WORKBENCH_REGION_LABEL_KEYS } from "../../lib/workspace";

export interface ResearchWorkbenchProps {
  children: ReactNode;
  className?: string;
}

/**
 * Route-local research boundary. The route content remains the existing
 * semantic main element while the shared workbench composes Sources and
 * Document slots beside it without moving the application's request owners.
 */
export function ResearchWorkbench({ children, className }: ResearchWorkbenchProps) {
  const { t } = useLocale();

  return (
    <section
      className={`workbench-research${className ? ` ${className}` : ""}`}
      data-workbench-region="research"
      aria-label={t(WORKBENCH_REGION_LABEL_KEYS.research)}
    >
      <div className="workbench-research__surface">{children}</div>
    </section>
  );
}
