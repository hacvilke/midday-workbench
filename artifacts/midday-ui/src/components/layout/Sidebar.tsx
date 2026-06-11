import { useEffect, useState } from "react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Activity, ShieldCheck, Box, Globe, GitBranch, BarChart2, Database, Cpu, Zap, BookOpen } from "lucide-react";
import { apiBase } from "@/lib/api";

type Skill = {
  name: string;
  description: string;
  icon?: string;
};

type Metrics = {
  runs?: number;
  commands?: number;
  memory_pct?: number;
  avg_time_ms?: number;
};

type Status = {
  skills?: Skill[];
  workspace?: string[];
  metrics?: Metrics;
};

const SKILL_ICONS: Record<string, React.ReactNode> = {
  file: <ShieldCheck className="w-4 h-4 text-primary" />,
  command: <Box className="w-4 h-4 text-chart-2" />,
  web: <Globe className="w-4 h-4 text-chart-3" />,
  git: <GitBranch className="w-4 h-4 text-chart-4" />,
  graph: <BarChart2 className="w-4 h-4 text-chart-5" />,
  db: <Database className="w-4 h-4 text-primary" />,
};

function skillIcon(name: string | undefined): React.ReactNode {
  const lower = (name ?? "").toLowerCase();
  if (lower.includes("file")) return SKILL_ICONS.file;
  if (lower.includes("command") || lower.includes("container") || lower.includes("sandbox")) return SKILL_ICONS.command;
  if (lower.includes("web") || lower.includes("search")) return SKILL_ICONS.web;
  if (lower.includes("git") || lower.includes("aider")) return SKILL_ICONS.git;
  if (lower.includes("graph") || lower.includes("cugraph")) return SKILL_ICONS.graph;
  if (lower.includes("db") || lower.includes("data")) return SKILL_ICONS.db;
  return <Cpu className="w-4 h-4 text-muted-foreground" />;
}

const FALLBACK_SKILLS: Skill[] = [
  { name: "File System", description: "Read/write access to project directory" },
  { name: "Container Sandbox", description: "Execute shell commands securely" },
  { name: "Web Search", description: "DuckDuckGo instant search" },
  { name: "Git Native", description: "Aider-inspired git-native workflow" },
];

const FALLBACK_METRICS: Metrics = {};

function MetricCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-background border border-border rounded-lg p-3 flex flex-col gap-0.5">
      <span className="text-[10px] font-medium text-muted-foreground uppercase tracking-wider">{label}</span>
      <span className="text-xl font-mono font-semibold tabular-nums leading-none">{value}</span>
    </div>
  );
}

export default function Sidebar() {
  const [status, setStatus] = useState<Status | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const [statusRes, metricsRes] = await Promise.allSettled([
          fetch(`${apiBase}/api/status`).then((r) => (r.ok ? r.json() : null)),
          fetch(`${apiBase}/api/metrics`).then((r) => (r.ok ? r.json() : null)),
        ]);
        const s = statusRes.status === "fulfilled" ? statusRes.value : null;
        const m = metricsRes.status === "fulfilled" ? metricsRes.value : null;
        const rawSkills = s?.skills ?? s?.tool_schemas ?? null;
        const normalizedSkills: Skill[] | undefined = rawSkills
          ? rawSkills
              .map((sk: any): Skill | null => {
                if (sk?.name) return { name: sk.name, description: sk.description ?? "" };
                if (sk?.function?.name) return { name: sk.function.name, description: sk.function.description ?? "" };
                return null;
              })
              .filter(Boolean) as Skill[]
          : undefined;
        setStatus({
          skills: normalizedSkills,
          workspace: s?.workspace ?? null,
          metrics: m ?? s?.metrics ?? null,
        });
      } catch {
        setStatus(null);
      } finally {
        setLoading(false);
      }
    };

    load();
    const interval = setInterval(load, 15000);
    return () => clearInterval(interval);
  }, []);

  const skills = status?.skills ?? FALLBACK_SKILLS;
  const metrics = status?.metrics ?? FALLBACK_METRICS;
  const workspace = status?.workspace ?? [];

  const metricsRows = [
    { label: "Runs", value: metrics.runs !== undefined ? String(metrics.runs) : "—" },
    { label: "Commands", value: metrics.commands !== undefined ? metrics.commands.toLocaleString() : "—" },
    { label: "Memory", value: metrics.memory_pct !== undefined ? `${metrics.memory_pct}%` : "—" },
    { label: "Avg Time", value: metrics.avg_time_ms !== undefined
      ? metrics.avg_time_ms < 1000 ? `${metrics.avg_time_ms}ms` : `${(metrics.avg_time_ms / 1000).toFixed(1)}s`
      : "—" },
  ];

  return (
    <div className="w-[268px] h-full bg-card border-r border-border flex flex-col flex-shrink-0 overflow-hidden">
      <div className="h-14 px-4 border-b border-border flex items-center gap-2 flex-shrink-0">
        <Activity className="w-4 h-4 text-muted-foreground" />
        <span className="font-semibold text-sm">Dashboard</span>
        {loading && <span className="ml-auto w-1.5 h-1.5 rounded-full bg-primary/50 animate-pulse" />}
      </div>

      <ScrollArea className="flex-1">
        <div className="p-4 space-y-6">

          {/* Metrics */}
          <div className="space-y-2">
            <h3 className="text-[10px] font-semibold text-muted-foreground uppercase tracking-widest">Metrics</h3>
            <div className="grid grid-cols-2 gap-2">
              {metricsRows.map((r) => (
                <MetricCard key={r.label} label={r.label} value={r.value} />
              ))}
            </div>
          </div>

          {/* Workspace map */}
          {workspace.length > 0 && (
            <div className="space-y-2">
              <h3 className="text-[10px] font-semibold text-muted-foreground uppercase tracking-widest flex items-center gap-1.5">
                <BookOpen className="w-3 h-3" />
                Workspace
              </h3>
              <div className="space-y-1">
                {workspace.map((dir, i) => (
                  <div key={i} className="flex items-center gap-2 text-xs text-muted-foreground hover:text-foreground transition-colors px-1 py-0.5 rounded cursor-default">
                    <span className="w-1 h-1 rounded-full bg-primary/40 flex-shrink-0" />
                    <span className="font-mono truncate">{dir}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Agent skills */}
          <div className="space-y-2">
            <h3 className="text-[10px] font-semibold text-muted-foreground uppercase tracking-widest flex items-center gap-1.5">
              <Zap className="w-3 h-3" />
              Agent Skills
            </h3>
            <div className="space-y-2">
              {skills.map((skill, i) => (
                <div key={i} className="p-3 bg-background border border-border rounded-lg text-sm flex items-start gap-3 hover:border-primary/20 transition-colors">
                  <span className="flex-shrink-0 mt-0.5">{skillIcon(skill.name)}</span>
                  <div className="min-w-0">
                    <p className="font-medium text-sm leading-tight truncate">{skill.name}</p>
                    {skill.description && (
                      <p className="text-xs text-muted-foreground mt-0.5 leading-relaxed line-clamp-2">{skill.description}</p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>

        </div>
      </ScrollArea>
    </div>
  );
}
