import type { FormEvent } from "react";
import type { ChatMessage } from "../../lib/types/assistant";

export interface AssistantPanelProps {
  messages: ChatMessage[];
  input: string;
  loading: boolean;
  error: string;
  onInput: (value: string) => void;
  onSubmit: (event: FormEvent) => void;
  onNewChat: () => void;
}

export function AssistantPanel({
  messages,
  input,
  loading,
  error,
  onInput,
  onSubmit,
  onNewChat,
}: AssistantPanelProps) {
  return (
    <section className="assistant-card">
      <div className="card-row">
        <div className="card-title">AI Assistant</div>
        <button onClick={onNewChat}>New Chat</button>
      </div>
      <div className="chat-thread">
        {messages.map((message, index) => (
          <div key={`${message.role}-${index}`} className={`chat-bubble ${message.role}`}>
            {message.text}
          </div>
        ))}
        {loading ? <div className="chat-bubble assistant">Thinking...</div> : null}
        {error ? <div className="chat-error">{error}</div> : null}
      </div>
      <form className="prompt-box" onSubmit={onSubmit}>
        <input
          value={input}
          onChange={(event) => onInput(event.target.value)}
          placeholder="Ask a question..."
          aria-label="Ask AI Assistant"
        />
        <button type="submit" disabled={loading}>
          Go
        </button>
      </form>
    </section>
  );
}
