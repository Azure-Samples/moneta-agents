"use client";

import { useState, useRef, useEffect } from "react";
import { Conversation, UseCase } from "@/lib/types";
import {
  getPredefinedQuestionsByUseCase,
  getAgentsByUseCase,
} from "@/lib/constants";
import { MessageComponent } from "./message";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Send,
  PanelLeftOpen,
  Sparkles,
  Zap,
  MessageSquarePlus,
  Bot,
  Lock,
} from "lucide-react";
import { cn } from "@/lib/utils";

interface ChatAreaProps {
  conversation: Conversation | null;
  useCase: UseCase;
  isLoading: boolean;
  isDeepResearch: boolean;
  sidebarOpen: boolean;
  onSendMessage: (message: string) => Promise<void>;
  onToggleSidebar: () => void;
  onDeepResearchChange: (isDeepResearch: boolean) => void;
}

export function ChatArea({
  conversation,
  useCase,
  isLoading,
  isDeepResearch,
  sidebarOpen,
  onSendMessage,
  onToggleSidebar,
  onDeepResearchChange,
}: ChatAreaProps) {
  const [input, setInput] = useState("");
  const [selectedQuestion, setSelectedQuestion] = useState<string>("");
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const predefinedQuestions = getPredefinedQuestionsByUseCase(useCase);
  const agents = getAgentsByUseCase(useCase);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [conversation?.messages]);

  // Auto-resize textarea
  useEffect(() => {
    if (inputRef.current) {
      inputRef.current.style.height = "auto";
      inputRef.current.style.height = `${Math.min(inputRef.current.scrollHeight, 150)}px`;
    }
  }, [input]);

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;
    const message = input.trim();
    setInput("");
    if (inputRef.current) {
      inputRef.current.style.height = "auto";
    }
    await onSendMessage(message);
  };

  const handleQuestionSelect = async (question: string) => {
    if (question === "placeholder" || isLoading) return;
    setSelectedQuestion("");
    await onSendMessage(question);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const deepResearchLocked = conversation?.deepResearchUsed ?? false;

  if (!conversation) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-8 relative overflow-hidden">
        {/* Background decoration */}
        <div className="absolute inset-0 overflow-hidden pointer-events-none">
          <div className="absolute -top-40 -right-40 w-80 h-80 bg-primary/5 rounded-full blur-3xl" />
          <div className="absolute -bottom-40 -left-40 w-80 h-80 bg-primary/5 rounded-full blur-3xl" />
        </div>

        <div className="text-center space-y-6 animate-fade-in relative z-10">
          <div className="relative inline-block">
            <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-primary to-blue-600 flex items-center justify-center shadow-lg glow-primary animate-float">
              <Bot className="w-10 h-10 text-white" />
            </div>
            <div className="absolute -bottom-1 -right-1 w-6 h-6 bg-green-500 rounded-full border-4 border-background flex items-center justify-center">
              <Zap className="w-3 h-3 text-white" />
            </div>
          </div>

          <div className="space-y-2">
            <h2 className="text-3xl font-bold bg-gradient-to-r from-foreground to-foreground/70 bg-clip-text">
              Welcome to Moneta
            </h2>
            <p className="text-muted-foreground max-w-md text-lg">
              Your AI-powered assistant for financial advisory services
            </p>
          </div>

          <div className="flex flex-col sm:flex-row gap-3 justify-center">
            <Button
              onClick={onToggleSidebar}
              variant="outline"
              size="lg"
              className="gap-2 group hover:border-primary/50 transition-all"
            >
              <PanelLeftOpen className="w-4 h-4 group-hover:text-primary transition-colors" />
              View Conversations
            </Button>
          </div>

          <div className="pt-8 flex items-center gap-4 text-sm text-muted-foreground justify-center">
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
              <span>{Object.keys(agents).length} agents online</span>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col h-full bg-gradient-to-b from-background to-muted/20">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b bg-background/80 backdrop-blur-sm">
        <div className="flex items-center gap-3">
          <Button
            variant="ghost"
            size="icon"
            onClick={onToggleSidebar}
            className="md:hidden hover:bg-primary/10 transition-colors"
          >
            <PanelLeftOpen className="w-5 h-5" />
          </Button>
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary to-blue-600 flex items-center justify-center">
              <MessageSquarePlus className="w-4 h-4 text-white" />
            </div>
            <div>
              <h2 className="font-semibold text-sm truncate max-w-[200px] md:max-w-none">
                {conversation.name === "New Conversation"
                  ? "New Conversation"
                  : conversation.name}
              </h2>
              <p className="text-xs text-muted-foreground">
                {conversation.messages.length} messages
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Messages */}
      <ScrollArea className="flex-1 px-4">
        <div className="max-w-4xl mx-auto py-6">
          {conversation.messages.length === 0 && (
            <div className="text-center py-12 animate-fade-in">
              <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-muted flex items-center justify-center">
                <MessageSquarePlus className="w-8 h-8 text-muted-foreground" />
              </div>
              <p className="text-muted-foreground">
                Start the conversation by typing a message or selecting a
                predefined question below.
              </p>
            </div>
          )}
          {conversation.messages.map((message, index) => (
            <div
              key={message.id}
              className="animate-fade-in"
              style={{ animationDelay: `${index * 0.05}s` }}
            >
              <MessageComponent message={message} agents={agents} />
            </div>
          ))}
          {isLoading && (
            <div className="flex items-center gap-3 py-4 animate-fade-in">
              <div className="w-8 h-8 rounded-full bg-gradient-to-br from-primary to-blue-600 flex items-center justify-center">
                <Bot className="w-4 h-4 text-white" />
              </div>
              <div className="bg-muted rounded-2xl px-4 py-3">
                <div className="typing-indicator">
                  <span></span>
                  <span></span>
                  <span></span>
                </div>
              </div>
              <span className="text-sm text-muted-foreground">
                Agents collaborating...
              </span>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
      </ScrollArea>

      {/* Input Area */}
      <div className="border-t bg-background/80 backdrop-blur-sm p-4">
        <div className="max-w-4xl mx-auto space-y-3">
          {/* Predefined Questions */}
          <Select value={selectedQuestion} onValueChange={handleQuestionSelect}>
            <SelectTrigger className="w-full bg-muted/50 border-muted hover:bg-muted transition-colors">
              <SelectValue placeholder="💡 Select a predefined question or type your own below" />
            </SelectTrigger>
            <SelectContent>
              {predefinedQuestions.map((question, index) => (
                <SelectItem key={index} value={question}>
                  {question}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          {/* Message Input with Deep Research Toggle */}
          <div className="relative">
            <div className="flex items-end gap-2 p-2 bg-muted/30 rounded-2xl border border-border/50 focus-within:border-primary/50 focus-within:ring-2 focus-within:ring-primary/20 transition-all">
              {/* Deep Research Toggle */}
              <div className="flex-shrink-0 pb-1">
                {deepResearchLocked ? (
                  <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-muted text-muted-foreground text-xs">
                    <Lock className="w-3 h-3" />
                    <span>Deep used</span>
                  </div>
                ) : (
                  <button
                    onClick={() => onDeepResearchChange(!isDeepResearch)}
                    className={cn(
                      "flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all",
                      isDeepResearch
                        ? "bg-gradient-to-r from-purple-500 to-pink-500 text-white shadow-lg shadow-purple-500/25"
                        : "bg-muted hover:bg-muted/80 text-muted-foreground hover:text-foreground"
                    )}
                  >
                    <Sparkles
                      className={cn(
                        "w-3.5 h-3.5",
                        isDeepResearch && "animate-pulse"
                      )}
                    />
                    <span>Deep Research</span>
                  </button>
                )}
              </div>

              {/* Text Input */}
              <textarea
                ref={inputRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask Moneta anything..."
                disabled={isLoading}
                rows={1}
                className="flex-1 bg-transparent border-0 resize-none focus:outline-none focus:ring-0 text-sm py-2 px-2 max-h-[150px] placeholder:text-muted-foreground/60"
              />

              {/* Send Button */}
              <Button
                onClick={handleSend}
                disabled={!input.trim() || isLoading}
                size="icon"
                className={cn(
                  "flex-shrink-0 rounded-xl h-10 w-10 transition-all",
                  input.trim()
                    ? "bg-gradient-to-r from-primary to-blue-600 hover:shadow-lg hover:shadow-primary/25 hover:scale-105"
                    : ""
                )}
              >
                <Send className="w-4 h-4" />
              </Button>
            </div>
          </div>

          {/* Helper text */}
          <p className="text-xs text-center text-muted-foreground">
            Press{" "}
            <kbd className="px-1.5 py-0.5 rounded bg-muted text-[10px] font-mono">
              Enter
            </kbd>{" "}
            to send •{" "}
            <kbd className="px-1.5 py-0.5 rounded bg-muted text-[10px] font-mono">
              Shift + Enter
            </kbd>{" "}
            for new line
          </p>
        </div>
      </div>
    </div>
  );
}
