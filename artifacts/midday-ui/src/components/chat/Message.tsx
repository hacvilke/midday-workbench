import React from "react";
import { fetchApi } from "../../lib/api";

export default function Message({ role, content }: { role: "user" | "assistant", content: string }) {
  return (
    <div className={`flex ${role === "user" ? "justify-end" : "justify-start"}`}>
      <div className={`max-w-[85%] ${
        role === "user" 
          ? "bg-secondary text-secondary-foreground px-4 py-3 rounded-2xl rounded-tr-sm" 
          : "pl-4 border-l-2 border-primary py-1"
      }`}>
        <div className="text-sm leading-relaxed whitespace-pre-wrap">
          {content}
        </div>
      </div>
    </div>
  );
}
