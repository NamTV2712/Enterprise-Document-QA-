import type { Message } from "../types";

export type AgentMessage = Message & { assistantExecution: { kind: "agent_research"; runId: string; createdAt: number } };

export function isAgentMessage(message: Message): message is AgentMessage {
  return message.sender === "assistant" && message.assistantExecution?.kind === "agent_research";
}

export function validAssistantExecution(value: unknown): boolean {
  if (!value || typeof value !== "object") return false;
  const ref = value as Record<string, unknown>;
  if (ref.kind === "quick_answer") return true;
  return ref.kind === "agent_research" && typeof ref.runId === "string"
    && /^agent_[A-Za-z0-9_-]{1,122}$/.test(ref.runId)
    && typeof ref.createdAt === "number" && Number.isFinite(ref.createdAt) && ref.createdAt >= 0;
}

/** Browser persistence never becomes an authority for private Agent payloads. */
export function agentReference(message: AgentMessage): AgentMessage {
  const { runId, createdAt } = message.assistantExecution;
  return { id: message.id, sender: "assistant", text: "", assistantExecution: { kind: "agent_research", runId, createdAt } };
}
