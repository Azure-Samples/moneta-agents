import { Message, Conversation, UseCase } from "./types";
import { generateId } from "./utils";

interface FetchConversationsParams {
  user_id: string;
  load_history: boolean;
  use_case: UseCase;
}

interface SendMessageParams {
  user_id: string;
  message: string;
  use_case: UseCase;
  is_deep_research: boolean;
  chat_id?: string;
}

interface SendMessageResponse {
  chat_id: string;
  reply: ApiMessage[];
}

interface ApiMessage {
  role: string;
  content: string;
  name?: string;
}

interface ApiConversation {
  chat_id: string;
  messages: ApiMessage[];
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "";

async function fetchWithError(url: string, options: RequestInit) {
  const response = await fetch(url, options);
  
  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`API Error: ${response.status} - ${errorText}`);
  }
  
  return response.json();
}

export const apiClient = {
  async fetchConversations(params: FetchConversationsParams): Promise<Conversation[]> {
    const response = await fetchWithError(`${API_BASE_URL}/http_trigger`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(params),
    });

    // API returns array of conversations when load_history is true
    if (!Array.isArray(response)) {
      return [];
    }

    return response.map((conv: ApiConversation) => ({
      id: conv.chat_id || generateId(),
      name: conv.chat_id || "Conversation",
      messages: transformApiMessages(conv.messages || []),
      useCase: params.use_case,
      deepResearchUsed: false,
      createdAt: new Date(),
      updatedAt: new Date(),
    }));
  },

  async sendMessage(params: SendMessageParams): Promise<SendMessageResponse> {
    const response = await fetchWithError(`${API_BASE_URL}/http_trigger`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(params),
    });

    return response as SendMessageResponse;
  },
};

export function transformApiMessages(messages: ApiMessage[]): Message[] {
  if (!Array.isArray(messages)) {
    return [];
  }

  return messages.map((msg) => ({
    id: generateId(),
    role: msg.role as Message["role"],
    content: msg.content || "",
    name: msg.name,
    timestamp: new Date(),
  }));
}
