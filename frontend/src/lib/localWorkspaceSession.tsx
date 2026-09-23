import React, { createContext, useCallback, useContext, useMemo, useRef, useState } from "react";

import { pipelineApi } from "./pipelineApi";
import type { LocalWorkspaceConfigurationStatus } from "../types";

type SessionStatus = "disconnected" | "connecting" | "connected";

interface LocalWorkspaceSessionValue {
  status: SessionStatus;
  getToken: () => string | null;
  canExecute: boolean;
  generation: number;
  connect: (candidate: string) => Promise<void>;
  disconnect: () => void;
  invalidateIfCurrent: (token: string, generation: number) => void;
}

const emptySession: LocalWorkspaceSessionValue = {
  status: "disconnected",
  getToken: () => null,
  canExecute: false,
  generation: 0,
  connect: async () => { throw new Error("The local workspace session provider is unavailable."); },
  disconnect: () => {},
  invalidateIfCurrent: () => {},
};

const LocalWorkspaceSessionContext = createContext<LocalWorkspaceSessionValue>(emptySession);

export function LocalWorkspaceSessionProvider({ children }: { children: React.ReactNode }) {
  const [status, setStatus] = useState<SessionStatus>("disconnected");
  const tokenRef = useRef<string | null>(null);
  const [configuration, setConfiguration] = useState<LocalWorkspaceConfigurationStatus | null>(null);
  const [generation, setGeneration] = useState(0);
  const generationRef = useRef(0);
  const requestGeneration = useRef(0);
  const getToken = useCallback(() => tokenRef.current, []);

  const disconnect = useCallback(() => {
    requestGeneration.current += 1;
    tokenRef.current = null;
    setConfiguration(null);
    setStatus("disconnected");
    generationRef.current += 1;
    setGeneration(generationRef.current);
  }, []);

  const connect = useCallback(async (candidate: string) => {
    if (!candidate.trim()) throw new Error("Enter the local workspace token.");
    const requestId = ++requestGeneration.current;
    setStatus("connecting");
    try {
      const verified = await pipelineApi.verifyLocalWorkspaceToken(candidate);
      if (requestId !== requestGeneration.current) return;
      tokenRef.current = candidate;
      setConfiguration(verified);
      setStatus("connected");
      generationRef.current += 1;
      setGeneration(generationRef.current);
    } catch (error) {
      if (requestId === requestGeneration.current) {
        tokenRef.current = null;
        setConfiguration(null);
        setStatus("disconnected");
      }
      throw error;
    }
  }, []);

  const invalidateIfCurrent = useCallback((expectedToken: string, expectedGeneration: number) => {
    if (tokenRef.current !== expectedToken || generationRef.current !== expectedGeneration) return;
    disconnect();
  }, [disconnect]);

  const value = useMemo<LocalWorkspaceSessionValue>(() => ({
    status,
    getToken,
    canExecute: configuration?.capabilities.execution_jobs === true,
    generation,
    connect,
    disconnect,
    invalidateIfCurrent,
  }), [configuration?.capabilities.execution_jobs, connect, disconnect, generation, getToken, invalidateIfCurrent, status]);

  return (
    <LocalWorkspaceSessionContext.Provider value={value}>
      {children}
    </LocalWorkspaceSessionContext.Provider>
  );
}

export function useLocalWorkspaceSession(): LocalWorkspaceSessionValue {
  return useContext(LocalWorkspaceSessionContext);
}
