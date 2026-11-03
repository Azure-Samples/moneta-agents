import { Agent, UseCase } from "./types";

export const USE_CASE_LABELS: Record<UseCase, string> = {
  fsi_banking: "Banking",
  fsi_insurance: "Insurance",
  energy: "Energy",
};

const BANKING_AGENTS: Record<string, Agent> = {
  CRM: {
    emoji: "👤",
    color: "#3b82f6",
    description: "Customer Relationship Management agent handling client data and interactions",
  },
  CIO: {
    emoji: "📊",
    color: "#8b5cf6",
    description: "Chief Investment Officer agent providing market insights and investment guidance",
  },
  Funds: {
    emoji: "💰",
    color: "#10b981",
    description: "Funds agent managing investment portfolios and fund recommendations",
  },
  News: {
    emoji: "📰",
    color: "#f59e0b",
    description: "News agent providing latest market news and financial updates",
  },
  Orchestrator: {
    emoji: "🎯",
    color: "#6366f1",
    description: "Main orchestrator coordinating between all banking agents",
  },
};

const INSURANCE_AGENTS: Record<string, Agent> = {
  CRM: {
    emoji: "👤",
    color: "#3b82f6",
    description: "Customer Relationship Management agent handling policyholder data",
  },
  Policies: {
    emoji: "📋",
    color: "#10b981",
    description: "Policies agent managing insurance policies and coverage details",
  },
  Orchestrator: {
    emoji: "🎯",
    color: "#6366f1",
    description: "Main orchestrator coordinating between all insurance agents",
  },
};

const ENERGY_AGENTS: Record<string, Agent> = {
  Analyst: {
    emoji: "⚡",
    color: "#f59e0b",
    description: "Energy analyst providing market analysis and forecasts",
  },
  Orchestrator: {
    emoji: "🎯",
    color: "#6366f1",
    description: "Main orchestrator coordinating energy sector queries",
  },
};

export function getAgentsByUseCase(useCase: UseCase): Record<string, Agent> {
  switch (useCase) {
    case "fsi_banking":
      return BANKING_AGENTS;
    case "fsi_insurance":
      return INSURANCE_AGENTS;
    case "energy":
      return ENERGY_AGENTS;
    default:
      return BANKING_AGENTS;
  }
}

const BANKING_QUESTIONS = [
  "What is the current market outlook for tech stocks?",
  "Can you provide an overview of my portfolio performance?",
  "What are the top performing mutual funds this quarter?",
  "Show me the latest financial news affecting my investments",
  "What investment strategies do you recommend based on my risk profile?",
];

const INSURANCE_QUESTIONS = [
  "What are my current active insurance policies?",
  "Can you explain my coverage details?",
  "What claims have I filed recently?",
  "How can I update my policy beneficiaries?",
  "What additional coverage options are available to me?",
];

const ENERGY_QUESTIONS = [
  "What is the current energy market outlook?",
  "Provide an analysis of renewable energy trends",
  "What are the key factors affecting energy prices?",
  "Show me the latest developments in sustainable energy",
  "What investment opportunities exist in the energy sector?",
];

export function getPredefinedQuestionsByUseCase(useCase: UseCase): string[] {
  switch (useCase) {
    case "fsi_banking":
      return BANKING_QUESTIONS;
    case "fsi_insurance":
      return INSURANCE_QUESTIONS;
    case "energy":
      return ENERGY_QUESTIONS;
    default:
      return BANKING_QUESTIONS;
  }
}
