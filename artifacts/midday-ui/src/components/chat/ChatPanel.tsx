import React, { useState } from "react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { useHealthCheck } from "@workspace/api-client-react";
import Message from "./Message";
import Composer from "./Composer";

export default function ChatPanel() {
  const { data: health } = useHealthCheck();
  const [messages, setMessages] = useState<{role: "user" | "assistant", content: string}[]>([
    { role: "assistant", content: "I am ready. How can I help you build today?" }
  ]);

  const handleSend = (msg: string) => {
    setMessages(prev => [...prev, { role: "user", content: msg }]);
    setTimeout(() => {
      setMessages(prev => [...prev, { role: "assistant", content: "Processing your request..." }]);
    }, 500);
  };

  return (
    <div className="flex-1 flex flex-col h-full bg-background relative">
      {/* Topbar */}
      <div className="h-14 border-b border-border flex items-center justify-between px-6 flex-shrink-0 bg-background/95 backdrop-blur z-10">
        <div className="flex items-center gap-3">
          <h2 className="font-semibold tracking-tight">Workbench</h2>
          <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-secondary/50 border border-border text-xs">
            <div className={`w-2 h-2 rounded-full ${health?.status === "ok" ? "bg-primary" : "bg-amber-500"}`} />
            <span className="text-muted-foreground">Provider:</span>
            <span className="font-medium">Local / OpenAI</span>
          </div>
        </div>
      </div>

      {/* Messages */}
      <ScrollArea className="flex-1 p-6">
        <div className="max-w-3xl mx-auto space-y-6 pb-32">
          {messages.map((msg, i) => (
            <Message key={i} role={msg.role} content={msg.content} />
          ))}
        </div>
      </ScrollArea>

      {/* Composer */}
      <div className="absolute bottom-6 left-1/2 -translate-x-1/2 w-full max-w-3xl px-6">
        <Composer onSend={handleSend} />
      </div>
    </div>
  );
}
