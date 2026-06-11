import { useLocation } from "wouter";
import Rail from "./Rail";
import Sidebar from "./Sidebar";
import Inspector from "./Inspector";
import ChatPanel from "../chat/ChatPanel";
import FilesPage from "@/pages/FilesPage";
import ToolsPage from "@/pages/ToolsPage";
import RunsPage from "@/pages/RunsPage";
import MemoryPage from "@/pages/MemoryPage";
import SettingsPage from "@/pages/SettingsPage";

function CenterPanel() {
  const [location] = useLocation();
  if (location === "/files") return <FilesPage />;
  if (location === "/tools") return <ToolsPage />;
  if (location === "/runs") return <RunsPage />;
  if (location === "/memory") return <MemoryPage />;
  if (location === "/settings") return <SettingsPage />;
  return <ChatPanel />;
}

export default function Shell() {
  const [location] = useLocation();
  const isChat = location === "/" || location === "";

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-background text-foreground selection:bg-primary/30">
      <Rail />
      <Sidebar />
      <div className="flex-1 flex min-w-0 overflow-hidden border-r border-border">
        <CenterPanel />
      </div>
      {isChat && <Inspector />}
    </div>
  );
}
