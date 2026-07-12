import type { FormEvent } from "react";
import type { ChatMessage } from "../../lib/types/assistant";
import { useI18n } from "../../i18n/useI18n";

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
  const { t } = useI18n();
  return (
    <section className="assistant-card">
      <div className="card-row">
        <div className="card-title">{t("assistant.panel.title")}</div>
        <button onClick={onNewChat}>{t("assistant.panel.newChat")}</button>
      </div>
      <div className="chat-thread">
        {messages.map((message, index) => (
          <div key={`${message.role}-${index}`} className={`chat-bubble ${message.role}`}>
            {message.text}
          </div>
        ))}
        {loading ? (
          <div className="chat-bubble assistant">{t("assistant.panel.thinking")}</div>
        ) : null}
        {error ? <div className="chat-error">{error}</div> : null}
      </div>
      <form className="prompt-box" onSubmit={onSubmit}>
        <input
          value={input}
          onChange={(event) => onInput(event.target.value)}
          placeholder={t("assistant.panel.placeholder")}
          aria-label={t("assistant.panel.inputAria")}
        />
        <button type="submit" disabled={loading}>
          {t("assistant.panel.submit")}
        </button>
      </form>
    </section>
  );
}
