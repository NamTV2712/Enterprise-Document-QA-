import { createContext, useContext } from "react";
import type { WorkbenchController } from "../../hooks/useWorkbenchController";
import type { WorkbenchPreferencesController } from "../../hooks/useWorkbenchPreferences";

export interface WorkbenchContextValue {
  controller: WorkbenchController;
  preferences: WorkbenchPreferencesController;
}

const WorkbenchContext = createContext<WorkbenchContextValue | null>(null);

export const WorkbenchContextProvider = WorkbenchContext.Provider;

export function useOptionalWorkbenchContext(): WorkbenchContextValue | null {
  return useContext(WorkbenchContext);
}

export function useWorkbenchContext(): WorkbenchContextValue {
  const context = useOptionalWorkbenchContext();
  if (!context) {
    throw new Error("useWorkbenchContext must be used inside ApplicationWorkspace");
  }
  return context;
}
