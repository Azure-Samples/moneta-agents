export type UseCase = "fsi_banking" | "fsi_insurance" | "energy";

export interface Message {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  name?: string;
  timestamp: Date;
}

export interface Conversation {
  id: string;
  name: string;
  messages: Message[];
  useCase: UseCase;
  deepResearchUsed: boolean;
  createdAt: Date;
  updatedAt: Date;
}

export interface Agent {
  emoji: string;
  color: string;
  description: string;
}
