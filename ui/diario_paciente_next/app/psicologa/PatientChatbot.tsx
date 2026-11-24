"use client";

import { useEffect, useId, useRef, useState, type FormEvent, type MouseEvent } from "react";
import { requestPatientChatReply } from "./patientChatService";
import styles from "./patient-management.module.css";

type Message = {
  id: string;
  role: "psychologist" | "assistant";
  text: string;
};

type PatientChatbotProps = {
  patientId: string;
  patientName: string;
};

export default function PatientChatbot({ patientId, patientName }: PatientChatbotProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [draft, setDraft] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const dialogId = useId();
  const inputId = useId();
  const dialogRef = useRef<HTMLDialogElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const messagesRef = useRef<HTMLDivElement>(null);
  const messageSequence = useRef(0);

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;

    if (isOpen && !dialog.open) {
      dialog.showModal();
      inputRef.current?.focus();
    } else if (!isOpen && dialog.open) {
      dialog.close();
    }
  }, [isOpen]);

  useEffect(() => {
    if (isOpen && messagesRef.current) {
      messagesRef.current.scrollTop = messagesRef.current.scrollHeight;
    }
  }, [isOpen, isLoading, messages]);

  function createMessage(role: Message["role"], text: string): Message {
    messageSequence.current += 1;
    return { id: `${patientId}-${messageSequence.current}`, role, text };
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const question = draft.trim();
    if (!question || isLoading) return;

    setError("");
    setDraft("");
    setMessages((current) => [...current, createMessage("psychologist", question)]);
    setIsLoading(true);

    try {
      const reply = await requestPatientChatReply({ patientId, question });
      setMessages((current) => [...current, createMessage("assistant", reply)]);
    } catch (caughtError) {
      setError(
        caughtError instanceof Error
          ? caughtError.message
          : "Não foi possível responder agora. Tente novamente.",
      );
    } finally {
      setIsLoading(false);
    }
  }

  function handleDialogClick(event: MouseEvent<HTMLDialogElement>) {
    if (event.target === event.currentTarget) setIsOpen(false);
  }

  return (
    <>
      <section className={styles.patientChatLauncher} aria-labelledby={`${dialogId}-launcher-title`}>
        <div className={styles.patientChatLauncherCopy}>
          <h2 id={`${dialogId}-launcher-title`}>Converse sobre este paciente</h2>
          <p>Abra o chatbot para organizar perguntas sobre o acompanhamento.</p>
        </div>
        <button
          className={`${styles.secondaryButton} ${styles.patientChatLauncherButton}`}
          type="button"
          aria-haspopup="dialog"
          aria-expanded={isOpen}
          aria-controls={dialogId}
          onClick={() => setIsOpen(true)}
        >
          Abrir chatbot
        </button>
      </section>

      <dialog
        ref={dialogRef}
        id={dialogId}
        className={styles.patientChatDialog}
        aria-labelledby={`${dialogId}-title`}
        onClose={() => setIsOpen(false)}
        onClick={handleDialogClick}
      >
        <header className={styles.patientChatHeader}>
          <div>
            <p className={styles.patientChatEyebrow}>CHAT DO PACIENTE</p>
            <h2 id={`${dialogId}-title`}>Conversa sobre {patientName}</h2>
            <p className={styles.patientChatContext}>Contexto associado ao paciente selecionado.</p>
          </div>
          <button
            className={styles.patientChatCloseButton}
            type="button"
            aria-label="Fechar chatbot"
            onClick={() => setIsOpen(false)}
          >
            Fechar
          </button>
        </header>

        <div
          ref={messagesRef}
          className={styles.patientChatMessages}
          role="log"
          aria-label="Histórico da conversa"
          aria-live="polite"
          aria-relevant="additions text"
        >
          {messages.length === 0 ? (
            <div className={styles.patientChatEmpty}>
              <strong>Inicie uma conversa</strong>
              <p>Digite uma pergunta sobre {patientName} para começar.</p>
              <span>A integração com IA ainda não está conectada.</span>
            </div>
          ) : (
            messages.map((message) => (
              <article
                className={`${styles.patientChatBubble} ${
                  message.role === "psychologist"
                    ? styles.patientChatBubbleUser
                    : styles.patientChatBubbleAssistant
                }`}
                key={message.id}
              >
                <span className={styles.patientChatMessageAuthor}>
                  {message.role === "psychologist" ? "Você" : "Assistente"}
                </span>
                <p>{message.text}</p>
              </article>
            ))
          )}
          {isLoading ? (
            <p className={styles.patientChatLoading} role="status">
              <span className={styles.patientChatSpinner} aria-hidden="true" />
              Aguardando resposta…
            </p>
          ) : null}
        </div>

        <form className={styles.patientChatComposer} onSubmit={handleSubmit}>
          {error ? (
            <p className={styles.patientChatError} role="alert">{error}</p>
          ) : null}
          <label className={styles.screenReaderOnly} htmlFor={inputId}>
            Escreva uma pergunta sobre {patientName}
          </label>
          <div className={styles.patientChatInputRow}>
            <textarea
              ref={inputRef}
              id={inputId}
              className={styles.patientChatInput}
              value={draft}
              onChange={(event) => setDraft(event.currentTarget.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter" && !event.shiftKey) {
                  event.preventDefault();
                  event.currentTarget.form?.requestSubmit();
                }
              }}
              placeholder="Escreva sua pergunta…"
              rows={2}
              maxLength={2000}
              disabled={isLoading}
            />
            <button
              className={styles.patientChatSendButton}
              type="submit"
              disabled={isLoading || !draft.trim()}
            >
              {isLoading ? "Aguarde" : "Enviar"}
            </button>
          </div>
          <p className={styles.patientChatHint}>Enter envia · Shift + Enter quebra a linha</p>
        </form>
      </dialog>
    </>
  );
}
