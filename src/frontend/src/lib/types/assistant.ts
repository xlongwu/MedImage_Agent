export interface AssistantChatRequest {
  project_id: string;
  message: string;
}

export interface AssistantChatResponse {
  reply: string;
}

export interface ChatMessage {
  role: "assistant" | "user" | "system";
  text: string;
}

