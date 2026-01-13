"use client";

import { Conversation, UseCase } from "@/lib/types";
import { getAgentsByUseCase, USE_CASE_LABELS } from "@/lib/constants";
import { AgentItem } from "@/components/chat/agent-item";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { TooltipProvider } from "@/components/ui/tooltip";
import { ThemeToggle } from "@/components/ui/theme-toggle";
import {
  Plus,
  X,
  MessageSquare,
  LogOut,
  Landmark,
  Shield,
  Sparkles,
} from "lucide-react";
import { cn, truncateText } from "@/lib/utils";

interface SidebarProps {
  conversations: Conversation[];
  currentConversation: Conversation | null;
  useCase: UseCase;
  displayName: string;
  isLoading: boolean;
  open: boolean;
  onNewConversation: () => void;
  onSelectConversation: (conversation: Conversation) => void;
  onUseCaseChange: (useCase: UseCase) => void;
  onClose: () => void;
}

export function Sidebar({
  conversations,
  currentConversation,
  useCase,
  displayName,
  isLoading,
  open,
  onNewConversation,
  onSelectConversation,
  onUseCaseChange,
  onClose,
}: SidebarProps) {
  const agents = getAgentsByUseCase(useCase);

  const getConversationTitle = (conv: Conversation): string => {
    const firstUserMessage = conv.messages.find((m) => m.role === "user");
    if (firstUserMessage) {
      return truncateText(firstUserMessage.content, 40);
    }
    return "New Conversation";
  };

  return (
    <TooltipProvider>
      <div
        className={cn(
          "fixed inset-y-0 left-0 z-50 w-80 bg-card backdrop-blur-xl border-r border-border transform transition-transform duration-300 ease-out md:relative md:translate-x-0",
          open ? "translate-x-0" : "-translate-x-full"
        )}
      >
        <div className="flex flex-col h-full">
          {/* Header */}
          <div className="p-5 border-b border-border">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary to-blue-600 flex items-center justify-center shadow-lg shadow-primary/20">
                  <Sparkles className="w-5 h-5 text-white" />
                </div>
                <div>
                  <h1 className="text-lg font-bold">Moneta</h1>
                  <p className="text-xs text-muted-foreground">
                    AI Advisory Assistant
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-1">
                <ThemeToggle />
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={onClose}
                  className="md:hidden hover:bg-destructive/10 hover:text-destructive transition-colors"
                >
                  <X className="w-5 h-5" />
                </Button>
              </div>
            </div>
            <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-muted">
              <div className="w-8 h-8 rounded-full bg-gradient-to-br from-green-400 to-emerald-600 flex items-center justify-center text-white text-sm font-medium">
                {displayName.charAt(0).toUpperCase()}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium truncate text-foreground">{displayName}</p>
                <p className="text-xs text-muted-foreground">Advisor</p>
              </div>
            </div>
          </div>

          {/* Use Case Selector */}
          <div className="p-4 border-b border-border">
            <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-2 block">
              Industry
            </label>
            <Select
              value={useCase}
              onValueChange={(value) => onUseCaseChange(value as UseCase)}
            >
              <SelectTrigger className="bg-muted border-border hover:bg-accent transition-colors">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="fsi_banking">
                  <div className="flex items-center gap-2">
                    <Landmark className="w-4 h-4 text-blue-500" />
                    <span>{USE_CASE_LABELS.fsi_banking}</span>
                  </div>
                </SelectItem>
                <SelectItem value="fsi_insurance">
                  <div className="flex items-center gap-2">
                    <Shield className="w-4 h-4 text-amber-500" />
                    <span>{USE_CASE_LABELS.fsi_insurance}</span>
                  </div>
                </SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Agents Online */}
          <div className="p-4 border-b border-border">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                Active Agents
              </h3>
              <span className="text-xs bg-green-500/10 text-green-500 px-2 py-0.5 rounded-full font-medium">
                {Object.keys(agents).length} online
              </span>
            </div>
            <div className="space-y-1">
              {Object.entries(agents).map(([key, agent], index) => (
                <div
                  key={key}
                  className="animate-fade-in"
                  style={{ animationDelay: `${index * 0.1}s` }}
                >
                  <AgentItem agentKey={key} agent={agent} />
                </div>
              ))}
            </div>
          </div>

          {/* New Conversation Button */}
          <div className="p-4">
            <Button
              onClick={onNewConversation}
              className="w-full bg-gradient-to-r from-primary to-blue-600 hover:from-primary/90 hover:to-blue-600/90 shadow-lg shadow-primary/20 transition-all hover:shadow-xl hover:shadow-primary/30 hover:scale-[1.02]"
              disabled={isLoading}
            >
              <Plus className="w-4 h-4 mr-2" />
              New Conversation
            </Button>
          </div>

          {/* Conversation History */}
          <div className="flex-1 flex flex-col min-h-0">
            <div className="px-4 pb-2">
              <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                Conversations
              </h3>
            </div>
            <ScrollArea className="flex-1 px-4">
              <div className="space-y-1 pb-4">
                {conversations.length === 0 ? (
                  <div className="text-center py-8">
                    <MessageSquare className="w-8 h-8 mx-auto mb-2 text-muted-foreground/50" />
                    <p className="text-sm text-muted-foreground">
                      No conversations yet
                    </p>
                    <p className="text-xs text-muted-foreground/70">
                      Start a new conversation above
                    </p>
                  </div>
                ) : (
                  conversations.map((conv, index) => (
                    <button
                      key={conv.id}
                      onClick={() => onSelectConversation(conv)}
                      className={cn(
                        "w-full text-left p-3 rounded-xl transition-all group animate-fade-in",
                        currentConversation?.id === conv.id
                          ? "bg-primary/10 border border-primary/20"
                          : "hover:bg-muted/50 border border-transparent"
                      )}
                      style={{ animationDelay: `${index * 0.05}s` }}
                    >
                      <div className="flex items-start gap-3">
                        <div
                          className={cn(
                            "w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 transition-colors",
                            currentConversation?.id === conv.id
                              ? "bg-primary text-primary-foreground"
                              : "bg-muted text-muted-foreground group-hover:bg-muted-foreground/20"
                          )}
                        >
                          <MessageSquare className="w-4 h-4" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <p
                            className={cn(
                              "text-sm truncate font-medium",
                              currentConversation?.id === conv.id
                                ? "text-primary"
                                : ""
                            )}
                          >
                            {getConversationTitle(conv)}
                          </p>
                          <p className="text-xs text-muted-foreground mt-0.5">
                            {conv.messages.length > 0
                              ? `${conv.messages.length} messages`
                              : "Empty"}
                          </p>
                        </div>
                      </div>
                    </button>
                  ))
                )}
              </div>
            </ScrollArea>
          </div>

          {/* Footer */}
          <div className="p-4 border-t border-border">
            <a
              href="/.auth/logout"
              className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-muted-foreground hover:text-destructive hover:bg-destructive/10 transition-all"
            >
              <LogOut className="w-4 h-4" />
              Sign Out
            </a>
          </div>
        </div>
      </div>

      {/* Overlay for mobile */}
      {open && (
        <div
          className="fixed inset-0 bg-black/50 z-40 md:hidden"
          onClick={onClose}
        />
      )}
    </TooltipProvider>
  );
}
