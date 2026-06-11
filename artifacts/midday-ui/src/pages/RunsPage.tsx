import { useState, useEffect } from "react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { apiBase, getSessionId } from "@/lib/api";
import { Activity, Terminal, FileCode2, RefreshCw, ChevronDown, ChevronRight, Clock, Zap, GitMerge } from "lucide-react";

type Run = {
  run_id: string;
  session_id?: string;
  started_at?: string;
  ended_at?: string;
  tool_count?: number;
  model?: string;
  status?: string;
  summary?: string;
  duration_ms?: number;
};

type CommandRun = {
  id?: string;
  session_id?: string;
  command: string;
  exit_code?: number;
  output?: string;
  duration_ms?: number;
  started_at?: string;
};

type FileEvent = {
  id?: string;
  path: string;
  operation?: string;
  session_id?: string;
  occurred_at?: string;
};

type TabId = "runs" | "commands" | "files";

function timeAgo(ts?: string) {
  if (!ts) return "—";
  const d = Date.now() - new Date(ts).getTime();
  if (d < 60000) return `${Math.round(d / 1000)}s ago`;
  if (d < 3600000) return `${Math.round(d / 60000)}m ago`;
  return `${Math.round(d / 3600000)}h ago`;
}

export default function RunsPage() {
  const [tab, setTab] = useState<TabId>("runs");
  const [runs, setRuns] = useState<Run[]>([]);
  const [commands, setCommands] = useState<CommandRun[]>([]);
  const [fileEvents, setFileEvents] = useState<FileEvent[]>([]);
  const [loading, setLoading] = useState(false);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const sessionId = getSessionId();

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const [r, c, f] = await Promise.allSettled([
        fetch(`${apiBase}/api/runs?session_id=${sessionId}`).then((x) => x.json()),
        fetch(`${apiBase}/api/commands?session_id=${sessionId}`).then((x) => x.json()),
        fetch(`${apiBase}/api/files/events?session_id=${sessionId}`).then((x) => x.json()),
      ]);
      if (r.status === "fulfilled") setRuns(r.value.runs || r.value || []);
      if (c.status === "fulfilled") setCommands(c.value.commands || c.value || []);
      if (f.status === "fulfilled") setFileEvents(f.value.events || f.value || []);
    } catch {
      setError("Could not reach Midday server.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const TABS: { id: TabId; label: string; icon: React.ReactNode; count: number }[] = [
    { id: "runs", label: "Agent Runs", icon: <Zap className="w-3.5 h-3.5" />, count: runs.length },
    { id: "commands", label: "Commands", icon: <Terminal className="w-3.5 h-3.5" />, count: commands.length },
    { id: "files", label: "File Events", icon: <FileCode2 className="w-3.5 h-3.5" />, count: fileEvents.length },
  ];

  return (
    <div className="flex-1 flex flex-col h-full overflow-hidden">
      <div className="h-14 border-b border-border flex items-center gap-3 px-6 flex-shrink-0">
        <Activity className="w-4 h-4 text-primary" />
        <h2 className="font-semibold text-sm">Run History</h2>
        <button onClick={load} className="ml-auto p-1.5 rounded hover:bg-secondary/50 text-muted-foreground hover:text-foreground transition-colors">
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
        </button>
      </div>

      <div className="flex items-center gap-1 px-6 py-2.5 border-b border-border flex-shrink-0">
        {TABS.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-full transition-colors ${
              tab === t.id
                ? "bg-primary/15 text-primary border border-primary/25"
                : "text-muted-foreground hover:text-foreground hover:bg-secondary/50 border border-transparent"
            }`}
          >
            {t.icon}
            {t.label}
            {t.count > 0 && <span className="ml-1 bg-secondary px-1.5 py-0.5 rounded-full text-[10px]">{t.count}</span>}
          </button>
        ))}
      </div>

      {error && (
        <div className="mx-6 mt-4 p-3 bg-amber-500/5 border border-amber-500/20 rounded text-xs text-amber-400">{error}</div>
      )}

      <ScrollArea className="flex-1">
        <div className="p-6 space-y-2 max-w-4xl mx-auto">

          {tab === "runs" && (
            runs.length === 0
              ? <div className="text-sm text-muted-foreground py-12 text-center">No agent runs recorded yet.</div>
              : runs.map((run) => {
                const id = run.run_id;
                const isOpen = expanded === id;
                return (
                  <div key={id} className="border border-border rounded-lg overflow-hidden bg-card">
                    <button
                      onClick={() => setExpanded(isOpen ? null : id)}
                      className="w-full flex items-center gap-3 p-3 text-left hover:bg-secondary/20 transition-colors"
                    >
                      {isOpen ? <ChevronDown className="w-3.5 h-3.5 text-muted-foreground flex-shrink-0" /> : <ChevronRight className="w-3.5 h-3.5 text-muted-foreground flex-shrink-0" />}
                      <span className="font-mono text-xs text-foreground/60">{id?.slice(0, 8)}</span>
                      {run.status && (
                        <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${run.status === "ok" ? "bg-primary/10 text-primary" : "bg-destructive/10 text-destructive"}`}>
                          {run.status}
                        </span>
                      )}
                      {run.model && <span className="text-xs text-muted-foreground">{run.model}</span>}
                      {run.tool_count !== undefined && (
                        <span className="flex items-center gap-1 text-xs text-muted-foreground">
                          <Wrench className="w-3 h-3" />{run.tool_count}
                        </span>
                      )}
                      <div className="ml-auto flex items-center gap-3 text-xs text-muted-foreground">
                        {run.duration_ms !== undefined && (
                          <span className="flex items-center gap-1"><Clock className="w-3 h-3" />{run.duration_ms < 1000 ? `${run.duration_ms}ms` : `${(run.duration_ms / 1000).toFixed(1)}s`}</span>
                        )}
                        <span>{timeAgo(run.started_at)}</span>
                      </div>
                    </button>
                    {isOpen && run.summary && (
                      <div className="border-t border-border p-3 text-xs text-muted-foreground bg-background/50">
                        {run.summary}
                      </div>
                    )}
                  </div>
                );
              })
          )}

          {tab === "commands" && (
            commands.length === 0
              ? <div className="text-sm text-muted-foreground py-12 text-center">No commands run yet.</div>
              : commands.map((cmd, i) => (
                <div key={i} className="border border-border rounded-lg overflow-hidden bg-card">
                  <div className="flex items-center gap-3 p-3">
                    <Terminal className="w-3.5 h-3.5 text-muted-foreground flex-shrink-0" />
                    <code className="font-mono text-xs text-foreground/90 flex-1 truncate">{cmd.command}</code>
                    <span className={`text-[10px] px-2 py-0.5 rounded font-mono ${cmd.exit_code === 0 ? "bg-primary/10 text-primary" : "bg-destructive/10 text-destructive"}`}>
                      exit {cmd.exit_code ?? "?"}
                    </span>
                    {cmd.duration_ms !== undefined && (
                      <span className="text-[10px] text-muted-foreground">{cmd.duration_ms}ms</span>
                    )}
                    <span className="text-[10px] text-muted-foreground flex-shrink-0">{timeAgo(cmd.started_at)}</span>
                  </div>
                  {cmd.output && (
                    <pre className="border-t border-border p-3 text-[11px] font-mono text-foreground/70 bg-background/50 overflow-x-auto max-h-32 whitespace-pre-wrap">
                      {cmd.output.slice(0, 500)}
                    </pre>
                  )}
                </div>
              ))
          )}

          {tab === "files" && (
            fileEvents.length === 0
              ? <div className="text-sm text-muted-foreground py-12 text-center">No file events recorded yet.</div>
              : fileEvents.map((fe, i) => (
                <div key={i} className="flex items-center gap-3 p-3 border border-border rounded-lg bg-card hover:bg-secondary/10 transition-colors">
                  <FileCode2 className="w-3.5 h-3.5 text-chart-2 flex-shrink-0" />
                  <span className="font-mono text-xs text-foreground/80 flex-1 truncate">{fe.path}</span>
                  {fe.operation && (
                    <span className="text-[10px] px-2 py-0.5 rounded bg-chart-2/10 text-chart-2 font-medium">{fe.operation}</span>
                  )}
                  <span className="text-[10px] text-muted-foreground flex-shrink-0">{timeAgo(fe.occurred_at)}</span>
                </div>
              ))
          )}
        </div>
      </ScrollArea>
    </div>
  );
}

function Wrench({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z" />
    </svg>
  );
}
