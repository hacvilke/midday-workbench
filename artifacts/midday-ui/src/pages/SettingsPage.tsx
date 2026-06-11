import { useState, useEffect } from "react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { apiBase } from "@/lib/api";
import { Settings, Server, Key, ShieldCheck, GitBranch, RefreshCw, CheckCircle2, XCircle, ExternalLink } from "lucide-react";
import { useWorkbench } from "@/context/WorkbenchContext";

type StatusData = {
  provider?: string;
  provider_route?: string;
  has_groq_key?: boolean;
  has_openrouter_key?: boolean;
  provider_diagnostics?: Record<string, any>;
  tool_schemas?: any[];
  tools?: string[];
};

function StatusRow({ label, value, ok }: { label: string; value: string; ok?: boolean }) {
  return (
    <div className="flex items-center justify-between py-2.5 border-b border-border/50 last:border-0">
      <span className="text-xs text-muted-foreground">{label}</span>
      <div className="flex items-center gap-2">
        {ok !== undefined && (
          ok
            ? <CheckCircle2 className="w-3.5 h-3.5 text-primary flex-shrink-0" />
            : <XCircle className="w-3.5 h-3.5 text-muted-foreground/50 flex-shrink-0" />
        )}
        <span className="text-xs font-mono text-foreground/80">{value}</span>
      </div>
    </div>
  );
}

export default function SettingsPage() {
  const [status, setStatus] = useState<StatusData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { accessToken, setAccessToken } = useWorkbench();
  const [tokenInput, setTokenInput] = useState(accessToken);
  const [saved, setSaved] = useState(false);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const r = await fetch(`${apiBase}/api/status`);
      const d = await r.json();
      setStatus(d);
    } catch {
      setError("Could not reach Midday server at " + apiBase);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const saveToken = () => {
    setAccessToken(tokenInput);
    setSaved(true);
    setTimeout(() => setSaved(false), 1500);
  };

  const diag = status?.provider_diagnostics || {};

  return (
    <div className="flex-1 flex flex-col h-full overflow-hidden">
      <div className="h-14 border-b border-border flex items-center gap-3 px-6 flex-shrink-0">
        <Settings className="w-4 h-4 text-primary" />
        <h2 className="font-semibold text-sm">Settings</h2>
        <button onClick={load} className="ml-auto p-1.5 rounded hover:bg-secondary/50 text-muted-foreground hover:text-foreground transition-colors">
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
        </button>
      </div>

      <ScrollArea className="flex-1">
        <div className="p-6 max-w-2xl mx-auto space-y-6">

          {/* Connection */}
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <Server className="w-4 h-4 text-primary" />
              <h3 className="text-sm font-semibold">Midday Backend</h3>
            </div>
            <div className="rounded-lg border border-border bg-card p-4">
              {error ? (
                <div className="text-xs text-amber-400 bg-amber-500/5 border border-amber-500/20 rounded p-3 mb-3">{error}</div>
              ) : null}
              <StatusRow label="Server URL" value={apiBase} />
              {status && <>
                <StatusRow label="Active Provider" value={status.provider || "—"} ok={!!status.provider} />
                <StatusRow label="Route" value={status.provider_route || "—"} />
                <StatusRow label="Groq key" value={status.has_groq_key ? "configured" : "missing"} ok={status.has_groq_key} />
                <StatusRow label="OpenRouter key" value={status.has_openrouter_key ? "configured" : "missing"} ok={status.has_openrouter_key} />
                <StatusRow label="OSS tools loaded" value={String(status.tool_schemas?.length || 0)} ok={(status.tool_schemas?.length || 0) > 0} />
              </>}
              <div className="mt-3 pt-3 border-t border-border/50 flex items-center gap-2 text-xs text-muted-foreground">
                <span>Set <code className="font-mono bg-secondary/50 px-1 rounded">VITE_API_BASE</code> env var to point at your Midday server.</span>
                <a
                  href="https://github.com/hacvilke/midday-workbench"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="ml-auto flex items-center gap-1 text-primary hover:underline flex-shrink-0"
                >
                  <ExternalLink className="w-3 h-3" />
                  GitHub
                </a>
              </div>
            </div>
          </div>

          {/* Access Token */}
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <Key className="w-4 h-4 text-primary" />
              <h3 className="text-sm font-semibold">Access Token</h3>
            </div>
            <div className="rounded-lg border border-border bg-card p-4 space-y-3">
              <p className="text-xs text-muted-foreground leading-relaxed">
                If your Midday server requires a bearer token for authentication, enter it here.
                It will be stored in localStorage and sent with all API requests.
              </p>
              <div className="flex gap-2">
                <input
                  type="password"
                  value={tokenInput}
                  onChange={(e) => setTokenInput(e.target.value)}
                  placeholder="sk-… or your server token"
                  className="flex-1 px-3 py-2 text-xs bg-background border border-border rounded focus:outline-none focus:ring-1 focus:ring-primary/50 placeholder:text-muted-foreground font-mono"
                />
                <button
                  onClick={saveToken}
                  className={`px-4 py-2 text-xs rounded font-medium transition-colors ${saved ? "bg-primary/20 text-primary border border-primary/30" : "bg-primary hover:bg-primary/90 text-primary-foreground"}`}
                >
                  {saved ? "Saved ✓" : "Save"}
                </button>
              </div>
            </div>
          </div>

          {/* Security */}
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-primary" />
              <h3 className="text-sm font-semibold">Security &amp; Access Control</h3>
            </div>
            <div className="rounded-lg border border-border bg-card p-4 space-y-3">
              <p className="text-xs text-muted-foreground leading-relaxed">
                This workbench runs client-side and connects to your Midday Python server.
                For public deployment, protect access at the server layer:
              </p>
              <ul className="space-y-2 text-xs text-muted-foreground">
                {[
                  ["Replit Auth", "Enable Replit SSO on the Express API server to gate all frontend access"],
                  ["Network rules", "Restrict your Python server to a VPN or trusted IP range"],
                  ["API key header", "Add a required Authorization header check in server.py"],
                  ["Session isolation", "Each browser tab uses a unique session_id stored in localStorage"],
                ].map(([title, desc]) => (
                  <li key={title} className="flex items-start gap-2">
                    <span className="w-1.5 h-1.5 rounded-full bg-primary/50 mt-1.5 flex-shrink-0" />
                    <span><strong className="text-foreground/80">{title}</strong> — {desc}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>

          {/* Provider diagnostics */}
          {Object.keys(diag).length > 0 && (
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <GitBranch className="w-4 h-4 text-primary" />
                <h3 className="text-sm font-semibold">Provider Diagnostics</h3>
              </div>
              <div className="rounded-lg border border-border bg-card p-4">
                <pre className="text-[11px] font-mono text-foreground/70 whitespace-pre-wrap overflow-x-auto">
                  {JSON.stringify(diag, null, 2)}
                </pre>
              </div>
            </div>
          )}

        </div>
      </ScrollArea>
    </div>
  );
}
