import { postJson } from "./client";
import type { AssistantChatRequest, AssistantChatResponse } from "../types/assistant";

export function sendAssistantMessage(payload: AssistantChatRequest): Promise<AssistantChatResponse> {
  return postJson<AssistantChatResponse>("/api/assistant/chat", payload);
}

