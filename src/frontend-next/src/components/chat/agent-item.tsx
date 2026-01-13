"use client";

import { Agent } from "@/lib/types";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";

interface AgentItemProps {
  agent: Agent;
  agentKey: string;
}

export function AgentItem({ agent, agentKey }: AgentItemProps) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <div className="flex items-center gap-3 py-2.5 px-3 rounded-xl hover:bg-muted/50 transition-all cursor-pointer group">
          <div className="relative">
            <div
              className={cn(
                "flex items-center justify-center w-9 h-9 rounded-xl text-lg shadow-md transition-transform group-hover:scale-110"
              )}
              style={{
                background: `linear-gradient(135deg, ${agent.color}dd, ${agent.color})`,
              }}
            >
              {agent.emoji}
            </div>
            <span className="absolute -bottom-0.5 -right-0.5 w-3 h-3 bg-green-500 rounded-full border-2 border-card animate-pulse" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium truncate group-hover:text-primary transition-colors">
              {agentKey}
            </p>
            <p className="text-xs text-muted-foreground">Ready</p>
          </div>
        </div>
      </TooltipTrigger>
      <TooltipContent
        side="right"
        className="max-w-[300px] bg-card/95 backdrop-blur-xl border-border/50"
      >
        <div className="flex items-center gap-2 mb-1.5">
          <span className="text-lg">{agent.emoji}</span>
          <span className="font-semibold">{agentKey}</span>
        </div>
        <p className="text-sm text-muted-foreground">{agent.description}</p>
      </TooltipContent>
    </Tooltip>
  );
}
