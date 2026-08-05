import type { FormEvent } from "react";
import type { ChatMessage } from "../../lib/types/assistant";
import { useI18n } from "../../i18n/useI18n";
import styles from "./AssistantPanel.module.css";

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
    <section className={styles.panel}>
      <div className={styles.header}>
        <div>{t("assistant.panel.title")}</div>
        <button onClick={onNewChat}>{t("assistant.panel.newChat")}</button>
      </div>
      <div className={styles.thread}>
        {messages.map((message, index) => (
          <div
            key={`${message.role}-${index}`}
            className={`${styles.bubble} ${
              message.role === "user" ? styles.user : styles.assistant
            }`}
          >
            {message.text}
          </div>
        ))}
        {loading ? (
          <div className={`${styles.bubble} ${styles.assistant}`}>
            {t("assistant.panel.thinking")}
          </div>
        ) : null}
        {error ? <div className={styles.error}>{error}</div> : null}
      </div>
      <form className={styles.prompt} onSubmit={onSubmit}>
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
