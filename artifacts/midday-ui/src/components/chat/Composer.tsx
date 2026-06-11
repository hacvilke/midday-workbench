import React, { useState } from "react";
import { Send, TerminalSquare } from "lucide-react";

export default function Composer({ onSend, disabled }: { onSend: (msg: string) => void, disabled?: boolean }) {
  const [input, setInput] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || disabled) return;
    onSend(input);
    setInput("");
  };

  return (
    <form onSubmit={handleSubmit} className="relative shadow-2xl rounded-xl border border-border bg-card/95 backdrop-blur overflow-hidden focus-within:ring-1 focus-within:ring-primary/50 transition-all">
      <textarea 
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
            e.preventDefault();
            handleSubmit(e);
          }
        }}
        placeholder="Instruct the agent... (Cmd+Enter to send)"
        className="w-full bg-transparent border-0 resize-none p-4 pb-12 text-sm focus:ring-0 placeholder:text-muted-foreground outline-none min-h-[100px]"
      />
      <div className="absolute bottom-3 left-4 flex items-center gap-2">
        <button type="button" className="p-1.5 text-muted-foreground hover:text-foreground rounded transition-colors" title="Tools">
          <TerminalSquare className="w-4 h-4" />
        </button>
      </div>
      <div className="absolute bottom-3 right-4">
        <button 
          type="submit"
          disabled={!input.trim() || disabled}
          className="bg-primary hover:bg-primary/90 text-primary-foreground p-2 rounded-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <Send className="w-4 h-4" />
        </button>
      </div>
    </form>
  );
}
