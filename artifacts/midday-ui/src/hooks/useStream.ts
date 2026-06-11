import { useState, useCallback, useRef } from "react";
import { apiBase, getSessionId } from "../lib/api";

type StreamEvent =
  | { type: "token"; token: string }
  | { type: "tool"; tool: string; summary: string }
  | { type: "file_written"; path: string }
  | { type: "done"; metadata: any };

export function useStream() {
  const [streaming, setStreaming] = useState(false);
  const [content, setContent] = useState("");
  const abortControllerRef = useRef<AbortController | null>(null);

  const stream = useCallback(async (message: string, onEvent: (event: StreamEvent) => void) => {
    setStreaming(true);
    setContent("");
    
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    
    abortControllerRef.current = new AbortController();
    
    try {
      const response = await fetch(`${apiBase}/api/chat/stream?session_id=${getSessionId()}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ message }),
        signal: abortControllerRef.current.signal,
      });

      if (!response.body) throw new Error("No body in response");
      
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";
        
        for (const line of lines) {
          if (line.startsWith("data: ")) {
            try {
              const data = JSON.parse(line.slice(6)) as StreamEvent;
              if (data.type === "token") {
                setContent((prev) => prev + data.token);
              }
              onEvent(data);
            } catch (e) {
              console.error("Failed to parse SSE event", e);
            }
          }
        }
      }
    } catch (err: any) {
      if (err.name !== "AbortError") {
        console.error("Stream error", err);
      }
    } finally {
      setStreaming(false);
    }
  }, []);

  const abort = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      setStreaming(false);
    }
  }, []);

  return { stream, abort, streaming, content };
}
