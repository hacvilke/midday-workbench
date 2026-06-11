import { useState, useEffect, useCallback } from "react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { apiBase } from "@/lib/api";
import { FolderOpen, FileCode2, RefreshCw, ChevronRight, Copy, Check, Search } from "lucide-react";

type FileEntry = string;

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <button
      onClick={() => { navigator.clipboard.writeText(text); setCopied(true); setTimeout(() => setCopied(false), 1500); }}
      className="p-1.5 rounded hover:bg-white/10 text-muted-foreground hover:text-foreground transition-colors"
    >
      {copied ? <Check className="w-3.5 h-3.5 text-primary" /> : <Copy className="w-3.5 h-3.5" />}
    </button>
  );
}

const PATTERNS = ["**/*.py", "**/*.ts", "**/*.tsx", "**/*.js", "**/*.md", "**/*.json", "**/*.yaml", "**/*"];

export default function FilesPage() {
  const [pattern, setPattern] = useState("**/*.py");
  const [customPattern, setCustomPattern] = useState("");
  const [files, setFiles] = useState<FileEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [selected, setSelected] = useState<string | null>(null);
  const [fileContent, setFileContent] = useState<string | null>(null);
  const [fileLoading, setFileLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchFilter, setSearchFilter] = useState("");

  const loadFiles = useCallback(async (pat: string) => {
    setLoading(true);
    setError(null);
    try {
      const r = await fetch(`${apiBase}/api/files/list?pattern=${encodeURIComponent(pat)}`);
      const d = await r.json();
      setFiles(d.files || []);
    } catch {
      setError("Could not reach Midday server. Start the Python backend first.");
      setFiles([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadFiles(pattern); }, [pattern, loadFiles]);

  const openFile = async (path: string) => {
    setSelected(path);
    setFileContent(null);
    setFileLoading(true);
    try {
      const r = await fetch(`${apiBase}/api/files/read?path=${encodeURIComponent(path)}`);
      const d = await r.json();
      setFileContent(d.content ?? d.error ?? "");
    } catch {
      setFileContent("Error loading file.");
    } finally {
      setFileLoading(false);
    }
  };

  const filtered = files.filter((f) =>
    !searchFilter || f.toLowerCase().includes(searchFilter.toLowerCase())
  );

  return (
    <div className="flex-1 flex h-full overflow-hidden">
      {/* File list */}
      <div className="w-72 border-r border-border flex flex-col flex-shrink-0 bg-card">
        <div className="p-3 border-b border-border space-y-2">
          <div className="flex items-center gap-2">
            <FolderOpen className="w-4 h-4 text-primary flex-shrink-0" />
            <span className="font-semibold text-sm">File Browser</span>
            <button onClick={() => loadFiles(pattern)} className="ml-auto p-1 rounded hover:bg-secondary/50 text-muted-foreground hover:text-foreground transition-colors">
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
            </button>
          </div>
          <select
            value={pattern}
            onChange={(e) => setPattern(e.target.value)}
            className="w-full text-xs bg-background border border-border rounded px-2 py-1.5 text-foreground focus:outline-none focus:ring-1 focus:ring-primary/50"
          >
            {PATTERNS.map((p) => <option key={p} value={p}>{p}</option>)}
          </select>
          <div className="relative">
            <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-3 h-3 text-muted-foreground" />
            <input
              value={searchFilter}
              onChange={(e) => setSearchFilter(e.target.value)}
              placeholder="Filter files..."
              className="w-full pl-7 pr-3 py-1.5 text-xs bg-background border border-border rounded focus:outline-none focus:ring-1 focus:ring-primary/50 placeholder:text-muted-foreground"
            />
          </div>
        </div>
        <ScrollArea className="flex-1">
          {error ? (
            <div className="p-4 text-xs text-amber-400 bg-amber-500/5 m-3 rounded border border-amber-500/20">{error}</div>
          ) : loading ? (
            <div className="p-4 text-xs text-muted-foreground">Loading…</div>
          ) : filtered.length === 0 ? (
            <div className="p-4 text-xs text-muted-foreground">No files found.</div>
          ) : (
            <div className="py-1">
              {filtered.map((f) => (
                <button
                  key={f}
                  onClick={() => openFile(f)}
                  className={`w-full flex items-center gap-2 px-3 py-1.5 text-xs text-left transition-colors hover:bg-secondary/50 ${selected === f ? "bg-primary/10 text-primary" : "text-muted-foreground hover:text-foreground"}`}
                >
                  <FileCode2 className="w-3 h-3 flex-shrink-0" />
                  <span className="font-mono truncate">{f}</span>
                  {selected === f && <ChevronRight className="w-3 h-3 ml-auto flex-shrink-0" />}
                </button>
              ))}
            </div>
          )}
        </ScrollArea>
        <div className="px-3 py-2 border-t border-border text-[10px] text-muted-foreground">
          {filtered.length} file{filtered.length !== 1 ? "s" : ""}
        </div>
      </div>

      {/* File content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {selected ? (
          <>
            <div className="h-11 border-b border-border flex items-center justify-between px-4 flex-shrink-0 bg-background/80">
              <span className="text-xs font-mono text-foreground/70 truncate">{selected}</span>
              <div className="flex items-center gap-1 flex-shrink-0 ml-2">
                {fileContent && <CopyButton text={fileContent} />}
              </div>
            </div>
            <ScrollArea className="flex-1">
              {fileLoading ? (
                <div className="p-6 text-sm text-muted-foreground">Loading…</div>
              ) : (
                <pre className="p-6 text-xs font-mono leading-relaxed text-foreground/90 whitespace-pre-wrap break-all">
                  {fileContent}
                </pre>
              )}
            </ScrollArea>
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center text-sm text-muted-foreground">
            <div className="text-center space-y-2">
              <FolderOpen className="w-8 h-8 mx-auto text-muted-foreground/30" />
              <p>Select a file to view its contents</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
