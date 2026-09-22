/**
 * Compatibility entry point for the existing App and tests.
 * ContextPanel now composes the first-class SourcesPane with the existing
 * reader lifecycle, so callers keep the established selection contract.
 */
export { ContextPanel as EvidenceWorkspaceRail } from "./ContextPanel";
export type { ContextPanelProps as EvidenceWorkspaceRailProps } from "./ContextPanel";
