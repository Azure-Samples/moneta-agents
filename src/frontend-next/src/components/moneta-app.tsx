"use client";

import { useState, useEffect, useCallback } from "react";
import { Conversation, Message, UseCase } from "@/lib/types";
import { apiClient, transformApiMessages } from "@/lib/api";
import { generateId } from "@/lib/utils";
import { Sidebar } from "@/components/sidebar/sidebar";
import { ChatArea } from "@/components/chat/chat-area";

export function MonetaApp() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [currentConversation, setCurrentConversation] =
    useState<Conversation | null>(null);
  const [useCase, setUseCase] = useState<UseCase>("fsi_banking");
  const [isDeepResearch, setIsDeepResearch] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [displayName, setDisplayName] = useState("Default User");
  const [userId, setUserId] = useState("default_user_id");

  // Fetch user info from headers (set by Azure Container Apps auth)
  useEffect(() => {
    // In production, these would come from the x-ms-client-principal header
    // For local development, we use defaults
    setDisplayName("Default User");
    setUserId("default_user_id");
  }, []);

  // Fetch conversations when use case changes
  const fetchConversations = useCallback(async () => {
    try {
      const convs = await apiClient.fetchConversations({
        user_id: userId,
        load_history: true,
        use_case: useCase,
      });
      setConversations(convs);
      setCurrentConversation(null);
    } catch (error) {
      console.error("Error fetching conversations:", error);
      setConversations([]);
    }
  }, [userId, useCase]);

  useEffect(() => {
    fetchConversations();
  }, [fetchConversations]);

  const handleNewConversation = () => {
    const newConversation: Conversation = {
      id: generateId(),
      name: "New Conversation",
      messages: [],
      useCase,
      deepResearchUsed: false,
      createdAt: new Date(),
      updatedAt: new Date(),
    };

    setConversations((prev) => [...prev, newConversation]);
    setCurrentConversation(newConversation);
    setIsDeepResearch(false);
  };

  const handleSelectConversation = (conversation: Conversation) => {
    setCurrentConversation(conversation);
    setIsDeepResearch(false);
    setSidebarOpen(false);
  };

  const handleUseCaseChange = async (newUseCase: UseCase) => {
    setUseCase(newUseCase);
    setCurrentConversation(null);
    setIsDeepResearch(false);
  };

  const handleSendMessage = async (content: string) => {
    if (!currentConversation || !content.trim()) return;

    setIsLoading(true);

    // Add user message
    const userMessage: Message = {
      id: generateId(),
      role: "user",
      content: content.trim(),
      timestamp: new Date(),
    };

    const updatedConversation: Conversation = {
      ...currentConversation,
      messages: [...currentConversation.messages, userMessage],
      updatedAt: new Date(),
    };

    // If deep research is enabled, mark it as used
    if (isDeepResearch) {
      updatedConversation.deepResearchUsed = true;
    }

    setCurrentConversation(updatedConversation);
    setConversations((prev) =>
      prev.map((c) => (c.id === updatedConversation.id ? updatedConversation : c))
    );

    try {
      const response = await apiClient.sendMessage({
        user_id: userId,
        message: content.trim(),
        use_case: useCase,
        is_deep_research: isDeepResearch,
        chat_id:
          currentConversation.name !== "New Conversation"
            ? currentConversation.name
            : undefined,
      });

      // Transform and add assistant messages
      const assistantMessages = transformApiMessages(response.reply);

      const finalConversation: Conversation = {
        ...updatedConversation,
        name: response.chat_id || updatedConversation.name,
        messages: [...updatedConversation.messages, ...assistantMessages],
        updatedAt: new Date(),
      };

      setCurrentConversation(finalConversation);
      setConversations((prev) =>
        prev.map((c) => (c.id === finalConversation.id ? finalConversation : c))
      );
    } catch (error) {
      console.error("Error sending message:", error);

      // Add error message
      const errorMessage: Message = {
        id: generateId(),
        role: "assistant",
        content: "Sorry, an error occurred while processing your request.",
        name: "System",
        timestamp: new Date(),
      };

      const errorConversation: Conversation = {
        ...updatedConversation,
        messages: [...updatedConversation.messages, errorMessage],
        updatedAt: new Date(),
      };

      setCurrentConversation(errorConversation);
      setConversations((prev) =>
        prev.map((c) => (c.id === errorConversation.id ? errorConversation : c))
      );
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex h-screen bg-background overflow-hidden">
      {/* Decorative gradient background */}
      <div className="fixed inset-0 -z-10 overflow-hidden">
        <div className="absolute top-0 left-1/4 w-96 h-96 bg-primary/5 rounded-full blur-3xl animate-float" />
        <div
          className="absolute bottom-0 right-1/4 w-96 h-96 bg-blue-500/5 rounded-full blur-3xl animate-float"
          style={{ animationDelay: "-3s" }}
        />
      </div>

      <Sidebar
        conversations={conversations}
        currentConversation={currentConversation}
        useCase={useCase}
        displayName={displayName}
        isLoading={isLoading}
        open={sidebarOpen}
        onNewConversation={handleNewConversation}
        onSelectConversation={handleSelectConversation}
        onUseCaseChange={handleUseCaseChange}
        onClose={() => setSidebarOpen(false)}
      />

      <ChatArea
        conversation={currentConversation}
        useCase={useCase}
        isLoading={isLoading}
        isDeepResearch={isDeepResearch}
        sidebarOpen={sidebarOpen}
        onSendMessage={handleSendMessage}
        onToggleSidebar={() => setSidebarOpen(true)}
        onDeepResearchChange={setIsDeepResearch}
      />
    </div>
  );
}
