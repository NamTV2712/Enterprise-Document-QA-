import type { ReactNode } from "react";
import { MemoryRouter, useLocation } from "react-router-dom";
import { LocaleProvider } from "../lib/i18n";
import { LocalWorkspaceSessionProvider, useLocalWorkspaceSession } from "../lib/localWorkspaceSession";
import { operationalToken } from "./operationalFixtures";
function HarnessState() {
  const session = useLocalWorkspaceSession(), location = useLocation();
  return <><button onClick={() => void session.connect(operationalToken)}>Test connect</button><button onClick={session.disconnect}>Test disconnect</button><output data-testid="test-location">{location.search}</output></>;
}
export function OperationalHarness({ children, route = "/analytics" }: { children: ReactNode; route?: string }) {
  return <LocaleProvider><MemoryRouter initialEntries={[route]}><LocalWorkspaceSessionProvider><HarnessState />{children}</LocalWorkspaceSessionProvider></MemoryRouter></LocaleProvider>;
}
