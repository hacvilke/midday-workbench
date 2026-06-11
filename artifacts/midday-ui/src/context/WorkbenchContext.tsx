import { createContext, useContext, useState, useCallback, ReactNode } from "react";

export type ArtifactEntry = {
  path: string;
  writtenAt: number;
  runId?: string;
};

export type TerminalEntry = {
  id: string;
  command: string;
  output: string;
  exitCode: number | null;
  duration_ms: number;
  timestamp: number;
  error?: string;
};

type WorkbenchCtx = {
  artifacts: ArtifactEntry[];
  addArtifact: (path: string, runId?: string) => void;
  clearArtifacts: () => void;
  terminalHistory: TerminalEntry[];
  addTerminalEntry: (entry: TerminalEntry) => void;
  clearTerminal: () => void;
  accessToken: string;
  setAccessToken: (token: string) => void;
};

const WorkbenchContext = createContext<WorkbenchCtx | null>(null);

export function WorkbenchProvider({ children }: { children: ReactNode }) {
  const [artifacts, setArtifacts] = useState<ArtifactEntry[]>([]);
  const [terminalHistory, setTerminalHistory] = useState<TerminalEntry[]>([]);
  const [accessToken, setAccessTokenState] = useState<string>(
    () => localStorage.getItem("mw-access-token") || ""
  );

  const addArtifact = useCallback((path: string, runId?: string) => {
    setArtifacts((prev) => {
      if (prev.some((a) => a.path === path)) return prev;
      return [{ path, writtenAt: Date.now(), runId }, ...prev];
    });
  }, []);

  const clearArtifacts = useCallback(() => setArtifacts([]), []);

  const addTerminalEntry = useCallback((entry: TerminalEntry) => {
    setTerminalHistory((prev) => [...prev.slice(-99), entry]);
  }, []);

  const clearTerminal = useCallback(() => setTerminalHistory([]), []);

  const setAccessToken = useCallback((token: string) => {
    localStorage.setItem("mw-access-token", token);
    setAccessTokenState(token);
  }, []);

  return (
    <WorkbenchContext.Provider value={{
      artifacts, addArtifact, clearArtifacts,
      terminalHistory, addTerminalEntry, clearTerminal,
      accessToken, setAccessToken,
    }}>
      {children}
    </WorkbenchContext.Provider>
  );
}

export function useWorkbench() {
  const ctx = useContext(WorkbenchContext);
  if (!ctx) throw new Error("useWorkbench must be used inside WorkbenchProvider");
  return ctx;
}
