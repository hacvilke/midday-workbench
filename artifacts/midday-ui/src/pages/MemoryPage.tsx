import { useState, useEffect } from "react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { apiBase, getSessionId } from "@/lib/api";
import { Brain, RefreshCw, Trash2, Clock, ChevronDown, ChevronRight } from "lucide-react";

type MemoryMessage = {
  role: string;
  content: string;
  timestamp?: string;
};

type MemoryData = {
  session_id: string;
  messages: MemoryMessage[];
  summary?: string;
  total_messages?: number;
};

function timeAgo(ts?: string) {
  if (!ts) return "";
  const d = Date.now() - new Date(ts).getTime();
  if (d < 60000) return `${Math.round(d / 1000)}s ago`;
  if (d < 3600000) return `${Math.round(d / 60000)}m ago`;
  return new Date(ts).toLocaleTimeString();
}

export default function MemoryPage() {
  const [data, setData] = useState<MemoryData | null>(null);
  const [loading, setLoading] = useState(false);
  const [clearing, setClearing] = useState(false);
  const [expanded, setExpanded] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const sessionId = getSessionId();

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const r = await fetch(`${apiBase}/api/memory?session_id=${sessionId}`);
      const d = await r.json();
      setData(d);
    } catch {
      setError("Could not reach Midday server.");
    } finally {
      setLoading(false);
    }
  };

  const clearMemory = async () => {
    if (!confirm("Clear all conversation memory for this session?")) return;
    setClearing(true);
    try {
      await fetch(`${apiBase}/api/memory/clear`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId }),
      });
      await load();
    } catch {
      setError("Failed to clear memory.");
    } finally {
      setClearing(false);
    }
  };

  useEffect(() => { load(); }, []);

  const messages = data?.messages || [];

  return (
    <div className="flex-1 flex flex-col h-full overflow-hidden">
      <div className="h-14 border-b border-border flex items-center gap-3 px-6 flex-shrink-0">
        <Brain className="w-4 h-4 text-primary" />
        <h2 className="font-semibold text-sm">Session Memory</h2>
        {data && (
          <span className="text-xs text-muted-foreground">
            {messages.length} message{messages.length !== 1 ? "s" : ""}
            {data.total_messages ? ` (${data.total_messages} total)` : ""}
          </span>
        )}
        <div className="ml-auto flex items-center gap-2">
          <button
            onClick={clearMemory}
            disabled={clearing || messages.length === 0}
            className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded border border-destructive/30 text-destructive hover:bg-destructive/10 transition-colors disabled:opacity-40"
          >
            <Trash2 className="w-3.5 h-3.5" />
            Clear
          </button>
          <button onClick={load} className="p-1.5 rounded hover:bg-secondary/50 text-muted-foreground hover:text-foreground transition-colors">
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
          </button>
        </div>
      </div>

      {error && (
        <div className="mx-6 mt-4 p-3 bg-amber-500/5 border border-amber-500/20 rounded text-xs text-amber-400">{error}</div>
      )}

      {data?.summary && (
        <div className="mx-6 mt-4 p-3 bg-primary/5 border border-primary/15 rounded-lg">
          <div className="text-[10px] font-semibold text-primary/70 uppercase tracking-wider mb-1.5">Session Summary</div>
          <p className="text-xs text-foreground/80 leading-relaxed">{data.summary}</p>
        </div>
      )}

      <ScrollArea className="flex-1">
        <div className="p-6 space-y-2 max-w-3xl mx-auto">
          {loading ? (
            <div className="text-sm text-muted-foreground py-12 text-center">Loading memory…</div>
          ) : messages.length === 0 ? (
            <div className="text-sm text-muted-foreground py-12 text-center">
              <Brain className="w-8 h-8 mx-auto mb-2 opacity-20" />
              No messages in memory for this session.
            </div>
          ) : (
            messages.map((msg, i) => {
              const isUser = msg.role === "user";
              const isOpen = expanded === i;
              const preview = msg.content?.slice(0, 120) || "";
              const long = msg.content?.length > 120;

              return (
                <div key={i} className={`border rounded-lg overflow-hidden ${isUser ? "border-border bg-card" : "border-primary/10 bg-primary/3"}`}>
                  <div
                    className="flex items-start gap-3 p-3 cursor-pointer hover:bg-secondary/10 transition-colors"
                    onClick={() => long && setExpanded(isOpen ? null : i)}
                  >
                    <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full flex-shrink-0 mt-0.5 ${isUser ? "bg-secondary text-muted-foreground" : "bg-primary/15 text-primary"}`}>
                      {msg.role}
                    </span>
                    <span className="text-xs text-foreground/80 leading-relaxed flex-1 min-w-0">
                      {isOpen ? msg.content : preview}{!isOpen && long ? "…" : ""}
                    </span>
                    <div className="flex items-center gap-1.5 flex-shrink-0 ml-2 text-[10px] text-muted-foreground">
                      {msg.timestamp && <span className="flex items-center gap-1"><Clock className="w-2.5 h-2.5" />{timeAgo(msg.timestamp)}</span>}
                      {long && (isOpen ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />)}
                    </div>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </ScrollArea>
    </div>
  );
}
