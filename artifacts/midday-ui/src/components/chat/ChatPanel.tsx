import { useState, useRef, useEffect, useCallback } from "react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { apiBase, getSessionId } from "@/lib/api";
import Message, { ChatMessage } from "./Message";
import Composer from "./Composer";
import { WifiOff, Zap, GitBranch, Archive } from "lucide-react";

const QUICK_ACTIONS = [
  { label: "Run status", prompt: "run git status" },
  { label: "Check UI", prompt: "run frontend syntax check" },
  { label: "Draw diagram", prompt: "show graph of Midday Workbench agent architecture" },
  { label: "Pack context", prompt: "pack repo context for agent_core/router.py and agent_core/agent.py" },
];

type StreamEvent =
  | { type: "token"; token: string }
  | { type: "tool"; tool: string; summary: string }
  | { type: "file_written"; path: string }
  | { type: "done"; metadata: any };

export default function ChatPanel() {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: "welcome",
      role: "assistant",
      content: "Hi. I am Midday Workbench, ready to help.",
      metadata: null,
      toolBadges: [],
      fileWrites: [],
      streaming: false,
    },
  ]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [providerInfo, setProviderInfo] = useState<{ provider?: string; model?: string; offline?: boolean } | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const bottomRef = useRef<HTMLDivElement | null>(null);
  const scrollRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    fetch(`${apiBase}/api/status`)
      .then((r) => r.json())
      .then((d) => {
        setProviderInfo({
          provider: d.provider || d.active_provider || "Local",
          model: d.model || d.active_model || "OpenAI",
          offline: d.offline || false,
        });
      })
      .catch(() => setProviderInfo({ provider: "Local", model: "—", offline: true }));
  }, []);

  const scrollToBottom = useCallback(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  const handleSend = useCallback(async (text: string) => {
    if (isStreaming) return;

    const userMsg: ChatMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content: text,
      metadata: null,
      toolBadges: [],
      fileWrites: [],
      streaming: false,
    };

    const agentId = crypto.randomUUID();
    const agentMsg: ChatMessage = {
      id: agentId,
      role: "assistant",
      content: "",
      metadata: null,
      toolBadges: [],
      fileWrites: [],
      streaming: true,
    };

    setMessages((prev) => [...prev, userMsg, agentMsg]);
    setIsStreaming(true);

    abortRef.current = new AbortController();

    try {
      const response = await fetch(`${apiBase}/api/chat/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text, session_id: getSessionId() }),
        signal: abortRef.current.signal,
      });

      if (!response.body) throw new Error("No response body");

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          let event: StreamEvent;
          try {
            event = JSON.parse(line.slice(6));
          } catch {
            continue;
          }

          if (event.type === "token") {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === agentId ? { ...m, content: m.content + event.token } : m
              )
            );
            scrollToBottom();
          } else if (event.type === "tool") {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === agentId
                  ? { ...m, toolBadges: [...m.toolBadges, { tool: event.tool, summary: event.summary }] }
                  : m
              )
            );
          } else if (event.type === "file_written") {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === agentId
                  ? { ...m, fileWrites: [...m.fileWrites, event.path] }
                  : m
              )
            );
          } else if (event.type === "done") {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === agentId
                  ? { ...m, streaming: false, metadata: event.metadata || null }
                  : m
              )
            );
          }
        }
      }
    } catch (err: any) {
      if (err.name !== "AbortError") {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === agentId
              ? { ...m, streaming: false, content: m.content || "Connection failed. Is the Midday server running at " + apiBase + "?" }
              : m
          )
        );
      }
    } finally {
      setIsStreaming(false);
      setMessages((prev) =>
        prev.map((m) => (m.id === agentId ? { ...m, streaming: false } : m))
      );
      scrollToBottom();
    }
  }, [isStreaming, scrollToBottom]);

  const handleQuickAction = useCallback(
    (prompt: string) => handleSend(prompt),
    [handleSend]
  );

  const isOffline = providerInfo?.offline;

  return (
    <div className="flex-1 flex flex-col h-full bg-background relative overflow-hidden">
      {/* Topbar */}
      <div className="h-14 border-b border-border flex items-center justify-between px-6 flex-shrink-0 bg-background/95 backdrop-blur-sm z-10">
        <div className="flex items-center gap-3">
          <h2 className="font-semibold tracking-tight text-sm">Workbench</h2>
          {providerInfo && (
            <div className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full border text-xs font-medium ${
              isOffline
                ? "bg-amber-500/10 border-amber-500/30 text-amber-400"
                : "bg-primary/10 border-primary/20 text-primary"
            }`}>
              {isOffline
                ? <WifiOff className="w-3 h-3" />
                : <div className="w-1.5 h-1.5 rounded-full bg-primary animate-pulse" />
              }
              <span>{isOffline ? "Offline" : `${providerInfo.provider} / ${providerInfo.model}`}</span>
            </div>
          )}
        </div>
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <Zap className="w-3 h-3" />
          <span>ReAct</span>
          <span className="w-px h-3 bg-border mx-1" />
          <GitBranch className="w-3 h-3" />
          <span>Verified</span>
          <span className="w-px h-3 bg-border mx-1" />
          <Archive className="w-3 h-3" />
          <span>SQLite</span>
        </div>
      </div>

      {/* Offline banner */}
      {isOffline && (
        <div className="px-6 py-2 bg-amber-500/5 border-b border-amber-500/20 flex items-center gap-2 text-xs text-amber-400/80">
          <WifiOff className="w-3 h-3 flex-shrink-0" />
          <span>Offline mode — no model provider active. Local tools and repo context still available.</span>
        </div>
      )}

      {/* Quick actions */}
      <div className="flex items-center gap-2 px-6 py-2.5 border-b border-border overflow-x-auto scrollbar-none flex-shrink-0">
        {QUICK_ACTIONS.map((a) => (
          <button
            key={a.label}
            onClick={() => handleQuickAction(a.prompt)}
            disabled={isStreaming}
            className="flex-shrink-0 text-xs px-3 py-1.5 rounded-full border border-border bg-card hover:bg-secondary/50 hover:border-primary/30 text-muted-foreground hover:text-foreground transition-all disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {a.label}
          </button>
        ))}
      </div>

      {/* Messages */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto">
        <div className="max-w-3xl mx-auto px-6 py-6 space-y-5 pb-36">
          {messages.map((msg) => (
            <Message key={msg.id} message={msg} />
          ))}
          <div ref={bottomRef} />
        </div>
      </div>

      {/* Composer */}
      <div className="absolute bottom-0 left-0 right-0 px-6 pb-6 pt-3 bg-gradient-to-t from-background via-background/95 to-transparent">
        <div className="max-w-3xl mx-auto">
          <Composer onSend={handleSend} disabled={isStreaming} />
        </div>
      </div>
    </div>
  );
}
