"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Message, Agent } from "@/lib/types";
import { cn } from "@/lib/utils";
import { User, Bot } from "lucide-react";

interface MessageComponentProps {
  message: Message;
  agents: Record<string, Agent>;
}

export function MessageComponent({ message, agents }: MessageComponentProps) {
  const isUser = message.role === "user";
  const agent = message.name ? agents[message.name] : null;

  if (!message.content) return null;

  return (
    <div
      className={cn(
        "flex gap-4 py-4 animate-fade-in",
        isUser ? "flex-row-reverse" : "flex-row"
      )}
    >
      {/* Avatar */}
      <div className="flex-shrink-0">
        {isUser ? (
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary to-blue-600 flex items-center justify-center shadow-lg shadow-primary/20">
            <User className="w-5 h-5 text-primary-foreground" />
          </div>
        ) : agent ? (
          <div
            className="w-10 h-10 rounded-xl flex items-center justify-center text-lg shadow-lg"
            style={{
              background: `linear-gradient(135deg, ${agent.color}dd, ${agent.color})`,
              boxShadow: `0 4px 14px ${agent.color}40`,
            }}
          >
            {agent.emoji}
          </div>
        ) : (
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-slate-500 to-slate-700 flex items-center justify-center shadow-lg">
            <Bot className="w-5 h-5 text-white" />
          </div>
        )}
      </div>

      {/* Message Content */}
      <div
        className={cn(
          "flex-1 max-w-[85%] rounded-2xl px-5 py-4 shadow-sm transition-all",
          isUser
            ? "bg-gradient-to-br from-primary to-blue-600 text-primary-foreground shadow-lg shadow-primary/20"
            : "bg-card/80 backdrop-blur-sm border border-border/50"
        )}
        style={
          agent && !isUser
            ? { borderLeft: `3px solid ${agent.color}` }
            : undefined
        }
      >
        {agent && !isUser && (
          <div className="flex items-center gap-2 mb-2">
            <span className="text-lg">{agent.emoji}</span>
            <span className="text-sm font-semibold">{message.name}</span>
          </div>
        )}
        <div
          className={cn(
            "markdown-content prose prose-sm max-w-none dark:prose-invert",
            isUser && "prose-invert"
          )}
        >
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {message.content}
          </ReactMarkdown>
        </div>
      </div>
    </div>
  );
}
