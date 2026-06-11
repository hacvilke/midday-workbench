import React from "react";
import Rail from "./Rail";
import Sidebar from "./Sidebar";
import Inspector from "./Inspector";
import ChatPanel from "../chat/ChatPanel";

export default function Shell() {
  return (
    <div className="flex h-screen w-screen overflow-hidden bg-background text-foreground selection:bg-primary/30">
      <Rail />
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0 border-r border-border">
        <ChatPanel />
      </div>
      <Inspector />
    </div>
  );
}
