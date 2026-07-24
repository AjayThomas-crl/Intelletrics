"use client";

import { ScrollArea } from "@/components/ui/scroll-area";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/separator";
import { cn } from "@/lib/utils";
import { Loader2Icon, SendIcon, BotIcon, UserIcon } from "lucide-react";
import { useRef, useState, useCallback, useEffect } from "react";

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
}

interface ChatPanelProps {
  datasetId: string | null;
  className?: string;
}

export function ChatPanel({ datasetId, className }: ChatPanelProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: "welcome",
      role: "assistant",
      content:
        "Upload a dataset to get started. Ask questions about your data — trends, outliers, summaries, or specific columns — and I'll analyse them for you.",
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    if (scrollRef.current) {
      const viewport = scrollRef.current.querySelector(
        "[data-slot=scroll-area-viewport]"
      );
      if (viewport) {
        viewport.scrollTop = viewport.scrollHeight;
      }
    }
  }, [messages]);

  const handleSend = useCallback(async () => {
    const text = input.trim();
    if (!text || !datasetId || loading) return;

    const userMsg: ChatMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content: text,
    };

    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const res = await fetch("http://127.0.0.1:8000/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ dataset_id: datasetId, question: text }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Request failed" }));
        throw new Error(err.detail || `HTTP ${res.status}`);
      }

      const data = await res.json();
      const assistantMsg: ChatMessage = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: data.answer,
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err) {
      const errorMsg: ChatMessage = {
        id: crypto.randomUUID(),
        role: "assistant",
        content:
          err instanceof Error
            ? `Error: ${err.message}`
            : "Error: Something went wrong. Please try again.",
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setLoading(false);
      // Re-focus input after send
      inputRef.current?.focus();
    }
  }, [input, datasetId, loading]);

  // Clear messages when dataset changes
  useEffect(() => {
    if (datasetId) {
      setMessages([
        {
          id: "context-ready",
          role: "assistant",
          content: "Dataset loaded! Ask me anything about your data.",
        },
      ]);
    }
  }, [datasetId]);

  return (
    <div
      className={cn(
        "flex h-full flex-col bg-background border-l",
        className
      )}
    >
      {/* Header */}
      <div className="flex h-14 shrink-0 items-center gap-2 border-b px-4">
        <BotIcon className="size-5 text-primary" />
        <span className="text-sm font-semibold">AI Chat</span>
      </div>

      {/* Messages */}
      <ScrollArea ref={scrollRef} className="flex-1">
        <div className="flex flex-col gap-3 p-4">
          {messages.map((msg) => (
            <div
              key={msg.id}
              className={cn(
                "flex gap-3",
                msg.role === "user" ? "flex-row-reverse" : "flex-row"
              )}
            >
              <Avatar
                size={msg.role === "user" ? "sm" : "default"}
                className={cn(
                  "mt-0.5 shrink-0",
                  msg.role === "user" && "bg-primary text-primary-foreground"
                )}
              >
                <AvatarFallback>
                  {msg.role === "user" ? (
                    <UserIcon className="size-4" />
                  ) : (
                    <BotIcon className="size-4" />
                  )}
                </AvatarFallback>
              </Avatar>
              <div
                className={cn(
                  "max-w-[80%] rounded-xl px-3.5 py-2 text-sm leading-relaxed whitespace-pre-wrap",
                  msg.role === "user"
                    ? "bg-primary text-primary-foreground rounded-tr-sm"
                    : "bg-muted text-foreground rounded-tl-sm"
                )}
              >
                {msg.content}
              </div>
            </div>
          ))}
          {loading && (
            <div className="flex gap-3 flex-row">
              <Avatar size="default" className="mt-0.5 shrink-0">
                <AvatarFallback>
                  <BotIcon className="size-4" />
                </AvatarFallback>
              </Avatar>
              <div className="max-w-[80%] rounded-xl rounded-tl-sm bg-muted px-3.5 py-2 text-sm">
                <Loader2Icon className="size-4 animate-spin text-muted-foreground" />
              </div>
            </div>
          )}
        </div>
      </ScrollArea>

      {/* Input bar */}
      <div className="shrink-0 border-t p-4">
        <div className="flex items-center gap-2">
          <Input
            ref={inputRef}
            placeholder={
              datasetId
                ? "Ask a question about your data..."
                : "Upload a dataset first..."
            }
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleSend();
              }
            }}
            disabled={!datasetId || loading}
            className="h-10 text-sm"
          />
          <Button
            size="icon"
            onClick={handleSend}
            disabled={!input.trim() || !datasetId || loading}
            className="shrink-0"
          >
            {loading ? (
              <Loader2Icon className="size-4 animate-spin" />
            ) : (
              <SendIcon className="size-4" />
            )}
          </Button>
        </div>
      </div>
    </div>
  );
}
