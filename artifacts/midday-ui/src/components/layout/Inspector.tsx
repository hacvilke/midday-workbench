import { useState, useRef, useEffect } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ScrollArea } from "@/components/ui/scroll-area";
import { FileCode2, Terminal, Network, Send, Trash2, ExternalLink, Loader2, CheckCircle2, XCircle } from "lucide-react";
import { apiBase, getSessionId } from "@/lib/api";
import { useWorkbench } from "@/context/WorkbenchContext";

type ToolSchema = {
  function: { name: string; description: string };
};

function ArtifactsTab() {
  const { artifacts, clearArtifacts } = useWorkbench();

  if (artifacts.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-center p-6 gap-3">
        <FileCode2 className="w-8 h-8 text-muted-foreground/20" />
        <p className="text-xs text-muted-foreground">No files written yet. Ask the agent to create or edit files.</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between px-3 py-2 border-b border-border flex-shrink-0">
        <span className="text-[10px] text-muted-foreground uppercase tracking-wider font-medium">{artifacts.length} file{artifacts.length !== 1 ? "s" : ""}</span>
        <button onClick={clearArtifacts} className="p-1 rounded hover:bg-secondary/50 text-muted-foreground hover:text-destructive transition-colors" title="Clear">
          <Trash2 className="w-3 h-3" />
        </button>
      </div>
      <ScrollArea className="flex-1">
        <div className="p-2 space-y-1">
          {artifacts.map((a, i) => (
            <div key={i} className="flex items-center gap-2 p-2 rounded hover:bg-secondary/40 transition-colors group">
              <FileCode2 className="w-3.5 h-3.5 text-chart-2 flex-shrink-0" />
              <span className="font-mono text-[11px] text-foreground/80 truncate flex-1">{a.path}</span>
              <span className="text-[10px] text-muted-foreground flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
                {new Date(a.writtenAt).toLocaleTimeString()}
              </span>
            </div>
          ))}
        </div>
      </ScrollArea>
    </div>
  );
}

function SourcesTab() {
  const [tools, setTools] = useState<ToolSchema[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${apiBase}/api/status`)
      .then((r) => r.json())
      .then((d) => setTools(d.tool_schemas || []))
      .catch(() => setTools([]))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (tools.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-center p-6 gap-3">
        <Network className="w-8 h-8 text-muted-foreground/20" />
        <p className="text-xs text-muted-foreground">No OSS tools loaded. Start the Midday Python server to see available tools.</p>
      </div>
    );
  }

  return (
    <ScrollArea className="flex-1">
      <div className="p-2 space-y-1">
        {tools.map((t, i) => (
          <div key={i} className="p-2.5 rounded border border-border/50 hover:border-primary/20 hover:bg-primary/3 transition-colors">
            <div className="font-mono text-[11px] text-primary font-medium truncate">{t.function.name}</div>
            <div className="text-[10px] text-muted-foreground mt-0.5 line-clamp-2 leading-relaxed">{t.function.description}</div>
          </div>
        ))}
      </div>
    </ScrollArea>
  );
}

type TerminalLine =
  | { type: "prompt"; text: string }
  | { type: "output"; text: string; exit?: number; duration_ms?: number; error?: string };

function TerminalTab() {
  const { terminalHistory, addTerminalEntry, clearTerminal } = useWorkbench();
  const [input, setInput] = useState("");
  const [running, setRunning] = useState(false);
  const [localLines, setLocalLines] = useState<TerminalLine[]>([
    { type: "output", text: "# Midday Workbench Sandbox\n# Type a command to run it via the sandboxed executor." },
  ]);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [localLines]);

  const runCommand = async () => {
    const cmd = input.trim();
    if (!cmd || running) return;
    setInput("");
    setRunning(true);

    setLocalLines((prev) => [...prev, { type: "prompt", text: cmd }]);

    try {
      const r = await fetch(`${apiBase}/api/sandbox/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ command: cmd, session_id: getSessionId() }),
      });
      const d = await r.json();
      const output = d.output ?? d.stdout ?? d.stderr ?? d.error ?? JSON.stringify(d);
      const exitCode = d.exit_code ?? d.returncode ?? null;
      const duration = d.duration_ms ?? null;

      setLocalLines((prev) => [
        ...prev,
        { type: "output", text: output, exit: exitCode, duration_ms: duration },
      ]);

      addTerminalEntry({
        id: crypto.randomUUID(),
        command: cmd,
        output,
        exitCode,
        duration_ms: duration ?? 0,
        timestamp: Date.now(),
      });
    } catch (err: any) {
      setLocalLines((prev) => [
        ...prev,
        { type: "output", text: `Error: ${err.message}`, error: "request_failed" },
      ]);
    } finally {
      setRunning(false);
    }
  };

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <div className="flex items-center justify-between px-3 py-1.5 border-b border-border flex-shrink-0">
        <span className="text-[10px] text-muted-foreground uppercase tracking-wider font-medium">Sandbox Terminal</span>
        <button
          onClick={() => { setLocalLines([{ type: "output", text: "# Terminal cleared." }]); clearTerminal(); }}
          className="p-1 rounded hover:bg-secondary/50 text-muted-foreground hover:text-foreground transition-colors"
        >
          <Trash2 className="w-3 h-3" />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto bg-[#0a0d10] p-3 font-mono text-[11px] leading-relaxed">
        {localLines.map((line, i) => (
          <div key={i}>
            {line.type === "prompt" ? (
              <div className="flex items-center gap-1.5 text-primary/90 mt-1">
                <span className="text-muted-foreground select-none">$</span>
                <span>{line.text}</span>
              </div>
            ) : (
              <div className="mt-0.5">
                {line.exit !== undefined && (
                  <div className="flex items-center gap-1 mb-0.5">
                    {line.exit === 0
                      ? <CheckCircle2 className="w-2.5 h-2.5 text-primary" />
                      : <XCircle className="w-2.5 h-2.5 text-destructive" />
                    }
                    <span className={`text-[9px] ${line.exit === 0 ? "text-primary/60" : "text-destructive/60"}`}>
                      exit {line.exit}{line.duration_ms != null ? ` · ${line.duration_ms}ms` : ""}
                    </span>
                  </div>
                )}
                <pre className={`whitespace-pre-wrap break-all ${line.error ? "text-destructive/80" : "text-green-400/80"}`}>
                  {line.text}
                </pre>
              </div>
            )}
          </div>
        ))}
        {running && (
          <div className="flex items-center gap-1.5 mt-1 text-muted-foreground">
            <Loader2 className="w-3 h-3 animate-spin" />
            <span>running…</span>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <div className="flex items-center gap-2 p-2 border-t border-border bg-[#0a0d10] flex-shrink-0">
        <span className="text-primary/60 font-mono text-[11px] select-none flex-shrink-0">$</span>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && runCommand()}
          placeholder="git status, ls, python …"
          disabled={running}
          className="flex-1 bg-transparent border-0 text-[11px] font-mono text-foreground/90 focus:outline-none placeholder:text-muted-foreground/40 disabled:opacity-50"
        />
        <button
          onClick={runCommand}
          disabled={!input.trim() || running}
          className="p-1.5 rounded bg-primary/10 hover:bg-primary/20 text-primary transition-colors disabled:opacity-40"
        >
          {running ? <Loader2 className="w-3 h-3 animate-spin" /> : <Send className="w-3 h-3" />}
        </button>
      </div>
    </div>
  );
}

export default function Inspector() {
  const { artifacts } = useWorkbench();

  return (
    <div className="w-[272px] h-full bg-card border-l border-border flex flex-col flex-shrink-0">
      <Tabs defaultValue="artifacts" className="flex-1 flex flex-col overflow-hidden">
        <div className="px-3 py-2.5 border-b border-border flex-shrink-0">
          <TabsList className="w-full grid grid-cols-3 bg-background h-8">
            <TabsTrigger value="artifacts" className="text-[11px] py-1 relative">
              <FileCode2 className="w-3 h-3 mr-1" />
              Artifacts
              {artifacts.length > 0 && (
                <span className="absolute -top-1 -right-1 w-3.5 h-3.5 rounded-full bg-primary text-[8px] text-primary-foreground flex items-center justify-center font-bold">
                  {artifacts.length > 9 ? "9+" : artifacts.length}
                </span>
              )}
            </TabsTrigger>
            <TabsTrigger value="sources" className="text-[11px] py-1">
              <Network className="w-3 h-3 mr-1" />
              Sources
            </TabsTrigger>
            <TabsTrigger value="terminal" className="text-[11px] py-1">
              <Terminal className="w-3 h-3 mr-1" />
              Terminal
            </TabsTrigger>
          </TabsList>
        </div>

        <TabsContent value="artifacts" className="flex-1 m-0 overflow-hidden">
          <ArtifactsTab />
        </TabsContent>

        <TabsContent value="sources" className="flex-1 m-0 overflow-hidden flex flex-col">
          <SourcesTab />
        </TabsContent>

        <TabsContent value="terminal" className="flex-1 m-0 overflow-hidden">
          <TerminalTab />
        </TabsContent>
      </Tabs>
    </div>
  );
}
