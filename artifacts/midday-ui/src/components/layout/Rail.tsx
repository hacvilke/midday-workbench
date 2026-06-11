import React from "react";
import { MessageSquare, FolderOpen, Wrench, Clock, Brain, Settings, Terminal, Activity } from "lucide-react";
import { Link, useLocation } from "wouter";

export default function Rail() {
  const [location] = useLocation();

  const items = [
    { icon: MessageSquare, id: "chat", title: "Chat" },
    { icon: FolderOpen, id: "files", title: "Files" },
    { icon: Wrench, id: "tools", title: "Tools" },
    { icon: Clock, id: "runs", title: "Runs" },
    { icon: Brain, id: "memory", title: "Memory" },
    { icon: Settings, id: "settings", title: "Settings" }
  ];

  return (
    <div className="w-[52px] h-full bg-sidebar border-r border-sidebar-border flex flex-col items-center py-4 gap-4 flex-shrink-0 z-20 relative">
      <div className="w-8 h-8 rounded bg-primary/20 flex items-center justify-center mb-4">
        <Terminal className="w-5 h-5 text-primary" />
      </div>
      
      <div className="flex flex-col gap-2 w-full px-2">
        {items.map((item) => {
          const Icon = item.icon;
          const isActive = location === `/${item.id}` || (location === "/" && item.id === "chat");
          return (
            <Link 
              key={item.id} 
              href={item.id === "chat" ? "/" : `/${item.id}`}
              className={`w-full aspect-square rounded flex items-center justify-center transition-colors relative ${isActive ? "text-primary bg-primary/10" : "text-muted-foreground hover:text-foreground hover:bg-white/5"}`}
              title={item.title}
            >
              {isActive && (
                <div className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-1/2 bg-primary rounded-r-full" />
              )}
              <Icon className="w-5 h-5" />
            </Link>
          );
        })}
      </div>
    </div>
  );
}
