import { useState, memo } from "react";
import { ChevronDown, ChevronRight, Wrench, FileCode2, WifiOff, Terminal, Copy, Check } from "lucide-react";

export type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  metadata: {
    run_id?: string;
    tool_count?: number;
    duration_ms?: number;
    offline?: boolean;
  } | null;
  toolBadges: { tool: string; summary: string }[];
  fileWrites: string[];
  streaming: boolean;
};

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  const handleCopy = () => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };
  return (
    <button
      onClick={handleCopy}
      className="absolute top-2 right-2 p-1.5 rounded bg-white/5 hover:bg-white/10 text-muted-foreground hover:text-foreground transition-colors opacity-0 group-hover:opacity-100"
    >
      {copied ? <Check className="w-3 h-3 text-primary" /> : <Copy className="w-3 h-3" />}
    </button>
  );
}

function CodeBlock({ code, lang }: { code: string; lang?: string }) {
  return (
    <div className="relative group my-3 rounded-lg overflow-hidden border border-border">
      {lang && (
        <div className="flex items-center justify-between px-4 py-1.5 bg-secondary/40 border-b border-border">
          <span className="text-[11px] font-mono text-muted-foreground">{lang}</span>
        </div>
      )}
      <CopyButton text={code} />
      <pre className="overflow-x-auto p-4 text-xs font-mono leading-relaxed text-foreground/90 bg-[#0d1117]">
        <code>{code}</code>
      </pre>
    </div>
  );
}

function MermaidBlock({ code }: { code: string }) {
  return (
    <div className="my-3 rounded-lg border border-primary/20 bg-primary/5 overflow-hidden">
      <div className="flex items-center gap-2 px-4 py-1.5 border-b border-primary/10">
        <div className="w-1.5 h-1.5 rounded-full bg-primary" />
        <span className="text-[11px] font-mono text-primary/70">mermaid diagram</span>
      </div>
      <pre className="p-4 text-xs font-mono leading-relaxed text-primary/80 overflow-x-auto">
        <code>{code}</code>
      </pre>
    </div>
  );
}

function parseMarkdown(text: string): React.ReactNode[] {
  const nodes: React.ReactNode[] = [];
  const lines = text.split("\n");
  let i = 0;
  let key = 0;

  while (i < lines.length) {
    const line = lines[i];

    // Fenced code block
    const fenceMatch = line.match(/^```(\w*)$/);
    if (fenceMatch) {
      const lang = fenceMatch[1].toLowerCase();
      const codeLines: string[] = [];
      i++;
      while (i < lines.length && !lines[i].startsWith("```")) {
        codeLines.push(lines[i]);
        i++;
      }
      i++; // skip closing ```
      const code = codeLines.join("\n");
      if (lang === "mermaid") {
        nodes.push(<MermaidBlock key={key++} code={code} />);
      } else {
        nodes.push(<CodeBlock key={key++} code={code} lang={lang || undefined} />);
      }
      continue;
    }

    // Headings
    const h3 = line.match(/^### (.+)/);
    const h2 = line.match(/^## (.+)/);
    const h1 = line.match(/^# (.+)/);
    if (h3) { nodes.push(<h3 key={key++} className="text-sm font-semibold mt-4 mb-1">{h3[1]}</h3>); i++; continue; }
    if (h2) { nodes.push(<h2 key={key++} className="text-sm font-semibold mt-4 mb-1 text-foreground/90">{h2[1]}</h2>); i++; continue; }
    if (h1) { nodes.push(<h1 key={key++} className="text-base font-bold mt-4 mb-2">{h1[1]}</h1>); i++; continue; }

    // Horizontal rule
    if (line.match(/^---+$/) || line.match(/^\*\*\*+$/) || line.match(/^___+$/)) {
      nodes.push(<hr key={key++} className="border-border my-3" />);
      i++;
      continue;
    }

    // Unordered list
    if (line.match(/^[-*+] /)) {
      const items: string[] = [];
      while (i < lines.length && lines[i].match(/^[-*+] /)) {
        items.push(lines[i].replace(/^[-*+] /, ""));
        i++;
      }
      nodes.push(
        <ul key={key++} className="list-disc list-inside space-y-0.5 my-1.5 pl-2">
          {items.map((item, idx) => (
            <li key={idx} className="text-sm leading-relaxed">{inlineFormat(item)}</li>
          ))}
        </ul>
      );
      continue;
    }

    // Ordered list
    if (line.match(/^\d+\. /)) {
      const items: string[] = [];
      while (i < lines.length && lines[i].match(/^\d+\. /)) {
        items.push(lines[i].replace(/^\d+\. /, ""));
        i++;
      }
      nodes.push(
        <ol key={key++} className="list-decimal list-inside space-y-0.5 my-1.5 pl-2">
          {items.map((item, idx) => (
            <li key={idx} className="text-sm leading-relaxed">{inlineFormat(item)}</li>
          ))}
        </ol>
      );
      continue;
    }

    // Blockquote
    if (line.startsWith("> ")) {
      const qlines: string[] = [];
      while (i < lines.length && lines[i].startsWith("> ")) {
        qlines.push(lines[i].slice(2));
        i++;
      }
      nodes.push(
        <blockquote key={key++} className="border-l-2 border-primary/40 pl-3 my-2 text-sm text-muted-foreground italic">
          {qlines.join(" ")}
        </blockquote>
      );
      continue;
    }

    // Empty line — spacer
    if (line.trim() === "") {
      i++;
      continue;
    }

    // Paragraph
    nodes.push(
      <p key={key++} className="text-sm leading-relaxed">
        {inlineFormat(line)}
      </p>
    );
    i++;
  }
  return nodes;
}

function inlineFormat(text: string): React.ReactNode {
  const parts = text.split(/(`[^`]+`|\*\*[^*]+\*\*|\*[^*]+\*|__[^_]+__|_[^_]+_)/);
  return parts.map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return <strong key={i} className="font-semibold">{part.slice(2, -2)}</strong>;
    }
    if (part.startsWith("__") && part.endsWith("__")) {
      return <strong key={i} className="font-semibold">{part.slice(2, -2)}</strong>;
    }
    if (part.startsWith("*") && part.endsWith("*") && part.length > 2) {
      return <em key={i}>{part.slice(1, -1)}</em>;
    }
    if (part.startsWith("_") && part.endsWith("_") && part.length > 2) {
      return <em key={i}>{part.slice(1, -1)}</em>;
    }
    if (part.startsWith("`") && part.endsWith("`")) {
      return <code key={i} className="px-1.5 py-0.5 rounded bg-secondary/50 font-mono text-xs text-primary/90">{part.slice(1, -1)}</code>;
    }
    return part;
  });
}

function RunMeta({ metadata, toolBadges }: { metadata: ChatMessage["metadata"]; toolBadges: ChatMessage["toolBadges"] }) {
  const [open, setOpen] = useState(false);
  if (!metadata && toolBadges.length === 0) return null;

  const runId = metadata?.run_id;
  const toolCount = metadata?.tool_count ?? toolBadges.length;
  const duration = metadata?.duration_ms;

  return (
    <div className="mt-3 border border-border/60 rounded-lg overflow-hidden text-xs">
      <button
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center gap-2 px-3 py-2 bg-secondary/20 hover:bg-secondary/40 transition-colors text-left"
      >
        {open ? <ChevronDown className="w-3 h-3 text-muted-foreground flex-shrink-0" /> : <ChevronRight className="w-3 h-3 text-muted-foreground flex-shrink-0" />}
        {runId && (
          <span className="font-mono text-muted-foreground">
            Run <span className="text-foreground/60">{runId.slice(0, 8)}</span>
          </span>
        )}
        {toolCount > 0 && (
          <span className="px-1.5 py-0.5 rounded bg-primary/10 text-primary font-medium">
            {toolCount} tool{toolCount !== 1 ? "s" : ""}
          </span>
        )}
        {duration !== undefined && (
          <span className="text-muted-foreground ml-auto">{duration < 1000 ? `${duration}ms` : `${(duration / 1000).toFixed(1)}s`}</span>
        )}
      </button>

      {open && toolBadges.length > 0 && (
        <div className="px-3 py-2 space-y-1.5 border-t border-border/40 bg-background/50">
          {toolBadges.map((b, i) => (
            <div key={i} className="flex items-start gap-2">
              <Wrench className="w-3 h-3 text-primary/60 flex-shrink-0 mt-0.5" />
              <span className="font-mono text-primary/80">{b.tool}</span>
              {b.summary && <span className="text-muted-foreground truncate">{b.summary}</span>}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function ToolBadges({ toolBadges, streaming }: { toolBadges: ChatMessage["toolBadges"]; streaming: boolean }) {
  if (toolBadges.length === 0 && !streaming) return null;
  return (
    <div className="flex flex-wrap gap-1.5 mt-2">
      {toolBadges.map((b, i) => (
        <span key={i} className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-primary/10 border border-primary/20 text-xs text-primary font-medium">
          <Wrench className="w-2.5 h-2.5" />
          {b.tool}
        </span>
      ))}
      {streaming && (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-secondary/50 border border-border text-xs text-muted-foreground">
          <span className="w-1.5 h-1.5 rounded-full bg-primary animate-pulse" />
          thinking…
        </span>
      )}
    </div>
  );
}

function FileWriteBadges({ paths }: { paths: string[] }) {
  if (paths.length === 0) return null;
  return (
    <div className="flex flex-wrap gap-1.5 mt-2">
      {paths.map((p, i) => (
        <span key={i} className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-chart-2/10 border border-chart-2/20 text-xs text-chart-2 font-mono">
          <FileCode2 className="w-2.5 h-2.5" />
          {p}
        </span>
      ))}
    </div>
  );
}

function OfflineNotice() {
  return (
    <div className="flex items-center gap-1.5 mt-2 text-xs text-amber-400/70">
      <WifiOff className="w-3 h-3 flex-shrink-0" />
      <span>Offline mode — no model provider active. Local tools still available.</span>
    </div>
  );
}

const Message = memo(function Message({ message }: { message: ChatMessage }) {
  const { role, content, metadata, toolBadges, fileWrites, streaming } = message;
  const isOffline = metadata?.offline;

  if (role === "user") {
    return (
      <div className="flex justify-end">
        <div className="max-w-[80%] bg-secondary border border-border rounded-2xl rounded-tr-sm px-4 py-3">
          <p className="text-sm leading-relaxed">{content}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex justify-start">
      <div className="flex-1 min-w-0">
        {/* Agent icon + line */}
        <div className="flex items-start gap-3">
          <div className="flex-shrink-0 w-6 h-6 rounded-full border border-primary/30 bg-primary/10 flex items-center justify-center mt-0.5">
            <Terminal className="w-3 h-3 text-primary" />
          </div>

          <div className="flex-1 min-w-0">
            {/* Tool use badges above content */}
            <ToolBadges toolBadges={toolBadges} streaming={streaming && content === ""} />

            {/* Content */}
            {content ? (
              <div className="prose-sm text-foreground space-y-0.5">
                {parseMarkdown(content)}
                {streaming && (
                  <span className="inline-block w-2 h-4 bg-primary/70 ml-0.5 animate-pulse rounded-sm" />
                )}
              </div>
            ) : streaming ? (
              <div className="flex items-center gap-1.5 text-xs text-muted-foreground py-1">
                <span className="w-1.5 h-1.5 rounded-full bg-primary animate-bounce [animation-delay:0ms]" />
                <span className="w-1.5 h-1.5 rounded-full bg-primary animate-bounce [animation-delay:150ms]" />
                <span className="w-1.5 h-1.5 rounded-full bg-primary animate-bounce [animation-delay:300ms]" />
              </div>
            ) : null}

            {isOffline && <OfflineNotice />}
            <FileWriteBadges paths={fileWrites} />
            {!streaming && <RunMeta metadata={metadata} toolBadges={toolBadges} />}
          </div>
        </div>
      </div>
    </div>
  );
});

export default Message;
