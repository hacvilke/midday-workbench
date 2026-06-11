import { useState, useEffect } from "react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { apiBase } from "@/lib/api";
import { Wrench, Play, ChevronDown, ChevronRight, Package, Loader2, CheckCircle2, XCircle } from "lucide-react";

type ToolSchema = {
  type: string;
  function: {
    name: string;
    description: string;
    parameters?: any;
  };
};

type RunResult = {
  name: string;
  summary: string;
  content: string;
  error?: string;
};

const OSS_REPO_MAP: Record<string, { repo: string; color: string }> = {
  erpnext: { repo: "frappe/erpnext", color: "text-orange-400" },
  julia: { repo: "JuliaLang/julia", color: "text-purple-400" },
  cugraph: { repo: "rapidsai/cugraph", color: "text-green-400" },
  system_design: { repo: "donnemartin/system-design-primer", color: "text-blue-400" },
  aider: { repo: "paul-gauthier/aider", color: "text-yellow-400" },
  repomix: { repo: "yamadashy/repomix", color: "text-pink-400" },
  gitingest: { repo: "cyclotruc/gitingest", color: "text-cyan-400" },
  last30days: { repo: "last30days-skill", color: "text-indigo-400" },
  rich_output: { repo: "rich-output-template", color: "text-emerald-400" },
  file_edit: { repo: "file-edit-tool", color: "text-primary" },
  web_search: { repo: "web-search-tool", color: "text-sky-400" },
  command_runner: { repo: "command-runner-tool", color: "text-rose-400" },
};

function repoInfo(name: string) {
  const key = Object.keys(OSS_REPO_MAP).find((k) => name.toLowerCase().includes(k));
  return key ? OSS_REPO_MAP[key] : { repo: name, color: "text-muted-foreground" };
}

export default function ToolsPage() {
  const [tools, setTools] = useState<ToolSchema[]>([]);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [running, setRunning] = useState<string | null>(null);
  const [results, setResults] = useState<Record<string, RunResult>>({});
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${apiBase}/api/status`)
      .then((r) => r.json())
      .then((d) => {
        setTools(d.tool_schemas || []);
        setError(null);
      })
      .catch(() => setError("Midday server offline. Start the Python backend to load OSS tools."))
      .finally(() => setLoading(false));
  }, []);

  const runTool = async (name: string) => {
    if (!query.trim()) return;
    setRunning(name);
    try {
      const r = await fetch(`${apiBase}/api/tools/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ tool: name, query }),
      });
      const d = await r.json();
      setResults((prev) => ({ ...prev, [name]: d }));
    } catch {
      setResults((prev) => ({ ...prev, [name]: { name, summary: "Error", content: "", error: "Request failed" } }));
    } finally {
      setRunning(null);
    }
  };

  return (
    <div className="flex-1 flex flex-col h-full overflow-hidden">
      <div className="h-14 border-b border-border flex items-center gap-3 px-6 flex-shrink-0">
        <Wrench className="w-4 h-4 text-primary" />
        <h2 className="font-semibold text-sm">OSS Tool Registry</h2>
        {!loading && <span className="text-xs text-muted-foreground ml-1">{tools.length} tools loaded</span>}
        <div className="ml-auto flex items-center gap-2">
          <Package className="w-3.5 h-3.5 text-muted-foreground" />
          <span className="text-xs text-muted-foreground">Query all tools:</span>
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Enter a query to run a tool…"
            className="w-64 px-3 py-1.5 text-xs bg-background border border-border rounded focus:outline-none focus:ring-1 focus:ring-primary/50 placeholder:text-muted-foreground"
          />
        </div>
      </div>

      {error && (
        <div className="mx-6 mt-4 p-3 bg-amber-500/5 border border-amber-500/20 rounded text-xs text-amber-400">{error}</div>
      )}

      <ScrollArea className="flex-1">
        <div className="p-6 space-y-3 max-w-4xl mx-auto">
          {loading ? (
            <div className="flex items-center gap-2 text-sm text-muted-foreground py-8 justify-center">
              <Loader2 className="w-4 h-4 animate-spin" />
              <span>Loading OSS tools…</span>
            </div>
          ) : tools.map((t) => {
            const fn = t.function;
            const info = repoInfo(fn.name);
            const isExpanded = expanded === fn.name;
            const result = results[fn.name];
            const isRunning = running === fn.name;

            return (
              <div key={fn.name} className="border border-border rounded-lg overflow-hidden bg-card hover:border-primary/20 transition-colors">
                <button
                  onClick={() => setExpanded(isExpanded ? null : fn.name)}
                  className="w-full flex items-center gap-3 p-4 text-left"
                >
                  {isExpanded
                    ? <ChevronDown className="w-4 h-4 text-muted-foreground flex-shrink-0" />
                    : <ChevronRight className="w-4 h-4 text-muted-foreground flex-shrink-0" />
                  }
                  <span className={`font-mono font-medium text-sm flex-shrink-0 ${info.color}`}>{fn.name}</span>
                  <span className="text-xs text-muted-foreground truncate">{fn.description}</span>
                  <span className={`ml-auto text-[10px] font-mono px-2 py-0.5 rounded bg-secondary/40 flex-shrink-0 ${info.color}`}>
                    {info.repo}
                  </span>
                </button>

                {isExpanded && (
                  <div className="border-t border-border">
                    <div className="p-4 space-y-3">
                      <p className="text-sm text-muted-foreground leading-relaxed">{fn.description}</p>

                      <div className="flex gap-2">
                        <input
                          value={query}
                          onChange={(e) => setQuery(e.target.value)}
                          onKeyDown={(e) => e.key === "Enter" && runTool(fn.name)}
                          placeholder="Enter query…"
                          className="flex-1 px-3 py-2 text-xs bg-background border border-border rounded focus:outline-none focus:ring-1 focus:ring-primary/50 placeholder:text-muted-foreground"
                        />
                        <button
                          onClick={() => runTool(fn.name)}
                          disabled={!query.trim() || isRunning}
                          className="flex items-center gap-1.5 px-3 py-2 bg-primary hover:bg-primary/90 text-primary-foreground text-xs rounded transition-colors disabled:opacity-50 font-medium"
                        >
                          {isRunning ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5" />}
                          Run
                        </button>
                      </div>

                      {result && (
                        <div className="space-y-2">
                          <div className="flex items-center gap-1.5 text-xs">
                            {result.error
                              ? <XCircle className="w-3.5 h-3.5 text-destructive" />
                              : <CheckCircle2 className="w-3.5 h-3.5 text-primary" />
                            }
                            <span className="font-medium">{result.summary || result.error}</span>
                          </div>
                          {result.content && (
                            <pre className="text-xs font-mono bg-background border border-border rounded p-3 overflow-x-auto max-h-48 leading-relaxed text-foreground/80 whitespace-pre-wrap">
                              {result.content.slice(0, 2000)}{result.content.length > 2000 ? "\n…(truncated)" : ""}
                            </pre>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </ScrollArea>
    </div>
  );
}
