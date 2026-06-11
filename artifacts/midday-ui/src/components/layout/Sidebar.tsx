import React from "react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Activity, ShieldCheck, Box, BarChart2 } from "lucide-react";

export default function Sidebar() {
  return (
    <div className="w-[280px] h-full bg-card border-r border-border flex flex-col flex-shrink-0 overflow-hidden">
      <div className="p-4 border-b border-border flex items-center gap-2">
        <Activity className="w-4 h-4 text-muted-foreground" />
        <span className="font-semibold text-sm">Dashboard</span>
      </div>
      <ScrollArea className="flex-1">
        <div className="p-4 space-y-6">
          
          <div className="space-y-2">
            <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Metrics</h3>
            <div className="grid grid-cols-2 gap-2">
              <div className="bg-background border border-border rounded p-2 flex flex-col">
                <span className="text-xs text-muted-foreground">Runs</span>
                <span className="text-lg font-mono">142</span>
              </div>
              <div className="bg-background border border-border rounded p-2 flex flex-col">
                <span className="text-xs text-muted-foreground">Commands</span>
                <span className="text-lg font-mono">1,023</span>
              </div>
              <div className="bg-background border border-border rounded p-2 flex flex-col">
                <span className="text-xs text-muted-foreground">Memory</span>
                <span className="text-lg font-mono">42%</span>
              </div>
              <div className="bg-background border border-border rounded p-2 flex flex-col">
                <span className="text-xs text-muted-foreground">Avg Time</span>
                <span className="text-lg font-mono">1.2s</span>
              </div>
            </div>
          </div>

          <div className="space-y-2">
            <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Agent Skills</h3>
            <div className="space-y-2">
              <div className="p-3 bg-background border border-border rounded text-sm flex items-start gap-3">
                <ShieldCheck className="w-4 h-4 text-primary shrink-0 mt-0.5" />
                <div>
                  <p className="font-medium">File System</p>
                  <p className="text-xs text-muted-foreground mt-1">Read/write access to project directory</p>
                </div>
              </div>
              <div className="p-3 bg-background border border-border rounded text-sm flex items-start gap-3">
                <Box className="w-4 h-4 text-chart-2 shrink-0 mt-0.5" />
                <div>
                  <p className="font-medium">Container Sandbox</p>
                  <p className="text-xs text-muted-foreground mt-1">Execute shell commands securely</p>
                </div>
              </div>
            </div>
          </div>

        </div>
      </ScrollArea>
    </div>
  );
}
