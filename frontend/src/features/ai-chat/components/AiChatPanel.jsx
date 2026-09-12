import { useEffect, useRef, useState } from "react";
import { AlertTriangle, Bot, RotateCcw, Send, Sparkles, User, X } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import { Button } from "@/shared/ui/Button";
import { humanizeApiError } from "@/shared/utils/apiErrors";
import { useOrganizacionActiva } from "@/features/organizaciones/context/OrganizacionActivaContext";
import { createConversation, getConversation, listConversations, sendMessage } from "../services/aiChatApi";

const SUGGESTED_QUESTIONS = [
  "¿Cuál es la obra con mayor impacto ambiental?",
  "¿Qué material representa el mayor hotspot?",
  "¿Cuáles son las principales alertas abiertas?",
  "¿Qué datos tienen mala calidad?",
];

function formatTime(value) {
  if (!value) return "";
  try {
    return new Date(value).toLocaleTimeString("es-CL", { hour: "2-digit", minute: "2-digit" });
  } catch {
    return "";
  }
}

const SAFE_URL_SCHEME = /^(https?:|\/|#)/i;

// react-markdown never renders raw HTML by default (no rehype-raw plugin
// is used), so this is defense-in-depth rather than the primary guard: it
// only prevents an unsafe-scheme href (e.g. "javascript:") from rendering
// as a clickable link, and opens real links in a new tab safely.
const MARKDOWN_COMPONENTS = {
  a: ({ href, children, ...props }) => {
    if (!href || !SAFE_URL_SCHEME.test(href)) return <span>{children}</span>;
    return (
      <a href={href} target="_blank" rel="noopener noreferrer" {...props}>
        {children}
      </a>
    );
  },
};

function ToolBadge({ name }) {
  return (
    <span className="rounded-full border border-[var(--border-default)] bg-[var(--bg-surface-subtle)] px-2 py-0.5 text-[11px] font-semibold text-[var(--text-muted)]">
      {name}
    </span>
  );
}

function MessageBubble({ message }) {
  const isUser = message.role === "user";
  const isAssistant = message.role === "assistant";
  if (!isUser && !isAssistant) return null;
  return (
    <div className={`flex gap-2.5 ${isUser ? "flex-row-reverse" : ""}`}>
      <span
        className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full ${
          isUser ? "bg-[var(--brand-primary)] text-white" : "bg-emerald-50 text-emerald-700 ring-1 ring-emerald-100"
        }`}
      >
        {isUser ? <User size={16} /> : <Bot size={16} />}
      </span>
      <div className={`max-w-[80%] ${isUser ? "items-end" : "items-start"} flex flex-col gap-1`}>
        <div
          className={`rounded-[var(--radius-lg)] px-3.5 py-2.5 text-sm leading-relaxed ${
            isUser
              ? "bg-[var(--brand-primary)] text-white"
              : "border border-[var(--border-default)] bg-[var(--bg-surface)] text-[var(--text-primary)]"
          }`}
        >
          {isUser ? (
            <p className="whitespace-pre-wrap">{message.content}</p>
          ) : (
            <div className="prose prose-sm max-w-none prose-p:my-1.5 prose-ul:my-1.5 prose-table:my-2 [&_table]:w-full [&_th]:text-left [&_td]:align-top">
              <ReactMarkdown remarkPlugins={[remarkGfm]} components={MARKDOWN_COMPONENTS}>
                {message.content || ""}
              </ReactMarkdown>
            </div>
          )}
        </div>
        {isAssistant && message.provenance?.length > 0 && (
          <details className="w-full text-xs text-[var(--text-muted)]">
            <summary className="cursor-pointer font-semibold">Fuentes utilizadas</summary>
            <div className="mt-1.5 flex flex-wrap gap-1.5">
              {message.provenance.map((item, index) => (
                <ToolBadge key={`${item.tool}-${index}`} name={item.tool} />
              ))}
            </div>
          </details>
        )}
        <span className="text-[11px] text-[var(--text-muted)]">{formatTime(message.created_at)}</span>
      </div>
    </div>
  );
}

function TypingIndicator() {
  return (
    <div className="flex items-center gap-2 text-sm text-[var(--text-muted)]" role="status" aria-label="El asistente está escribiendo">
      <span className="flex h-8 w-8 items-center justify-center rounded-full bg-emerald-50 text-emerald-700 ring-1 ring-emerald-100">
        <Bot size={16} />
      </span>
      <span className="flex gap-1">
        <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-[var(--text-muted)] [animation-delay:-0.2s]" />
        <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-[var(--text-muted)] [animation-delay:-0.1s]" />
        <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-[var(--text-muted)]" />
      </span>
    </div>
  );
}

export default function AiChatPanel({ onClose }) {
  const { activeOrganizacionId } = useOrganizacionActiva();
  const [conversation, setConversation] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [loadingConversation, setLoadingConversation] = useState(true);
  const [error, setError] = useState(null);
  const [pendingRetryText, setPendingRetryText] = useState(null);
  const scrollRef = useRef(null);

  useEffect(() => {
    let cancelled = false;
    if (!activeOrganizacionId) return undefined;
    setLoadingConversation(true);
    setError(null);
    listConversations(activeOrganizacionId)
      .then((existing) =>
        existing?.length
          ? getConversation(activeOrganizacionId, existing[0].id)
          : createConversation(activeOrganizacionId),
      )
      .then((data) => {
        if (cancelled) return;
        setConversation(data);
        setMessages(data.messages || []);
      })
      .catch((err) => {
        if (cancelled) return;
        setError(humanizeApiError(err, "No pudimos iniciar la conversación con el asistente."));
      })
      .finally(() => !cancelled && setLoadingConversation(false));
    return () => {
      cancelled = true;
    };
  }, [activeOrganizacionId]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, sending]);

  async function submit(text) {
    const content = text.trim();
    if (!content || !conversation || sending) return;
    setSending(true);
    setError(null);
    setPendingRetryText(null);
    setMessages((prev) => [
      ...prev,
      { id: `local-${Date.now()}`, role: "user", content, created_at: new Date().toISOString() },
    ]);
    setInput("");
    try {
      const assistantMessage = await sendMessage(activeOrganizacionId, conversation.id, content);
      setMessages((prev) => [...prev, assistantMessage]);
    } catch (err) {
      setError(humanizeApiError(err, "No pudimos obtener una respuesta del asistente."));
      setPendingRetryText(content);
    } finally {
      setSending(false);
    }
  }

  function handleSubmit(event) {
    event.preventDefault();
    submit(input);
  }

  function handleRetry() {
    if (pendingRetryText) submit(pendingRetryText);
  }

  return (
    <div className="fixed inset-0 z-50" role="presentation">
      <button aria-label="Cerrar asistente" className="absolute inset-0 bg-slate-950/35" onClick={onClose} />
      <aside
        aria-label="Carbono Zero Intelligence"
        aria-modal="true"
        role="dialog"
        className="absolute inset-y-0 right-0 flex w-full flex-col border-l border-[var(--border-default)] bg-[var(--bg-surface)] shadow-2xl sm:max-w-md"
      >
        <header className="flex shrink-0 items-center justify-between gap-3 border-b border-[var(--border-default)] px-4 py-3.5">
          <div className="flex items-center gap-2">
            <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-emerald-50 text-emerald-700 ring-1 ring-emerald-100">
              <Sparkles size={18} />
            </span>
            <div>
              <h2 className="text-sm font-bold leading-tight">Carbono Zero Intelligence</h2>
              <p className="text-xs text-[var(--text-muted)]">Asistente de inteligencia ambiental</p>
            </div>
          </div>
          <button
            aria-label="Cerrar"
            className="rounded-lg p-2 hover:bg-[var(--bg-surface-subtle)]"
            onClick={onClose}
          >
            <X size={18} />
          </button>
        </header>

        <div ref={scrollRef} className="flex-1 space-y-4 overflow-y-auto px-4 py-4">
          {loadingConversation && (
            <div className="flex items-center gap-2 text-sm text-[var(--text-muted)]" role="status">
              Iniciando conversación…
            </div>
          )}
          {messages.map((message) => (
            <MessageBubble key={message.id} message={message} />
          ))}
          {sending && <TypingIndicator />}
          {error && (
            <div className="flex items-start gap-2 rounded-[var(--radius-md)] border border-[var(--status-danger)]/25 bg-[var(--danger-bg)] p-3 text-sm text-[var(--text-secondary)]">
              <AlertTriangle size={16} className="mt-0.5 shrink-0 text-[var(--status-danger)]" />
              <div className="flex-1">
                <p>{error}</p>
                {pendingRetryText && (
                  <Button size="sm" variant="secondary" className="mt-2" leftIcon={RotateCcw} onClick={handleRetry}>
                    Reintentar
                  </Button>
                )}
              </div>
            </div>
          )}
          {!loadingConversation && messages.length <= 1 && !sending && (
            <div className="flex flex-wrap gap-2 pt-2">
              {SUGGESTED_QUESTIONS.map((question) => (
                <button
                  key={question}
                  type="button"
                  onClick={() => submit(question)}
                  className="rounded-full border border-[var(--border-default)] bg-[var(--bg-surface-subtle)] px-3 py-1.5 text-xs font-semibold text-[var(--text-secondary)] hover:bg-[var(--bg-surface)]"
                >
                  {question}
                </button>
              ))}
            </div>
          )}
        </div>

        <form onSubmit={handleSubmit} className="shrink-0 border-t border-[var(--border-default)] p-3">
          <div className="flex items-end gap-2">
            <textarea
              value={input}
              onChange={(event) => setInput(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter" && !event.shiftKey) {
                  event.preventDefault();
                  submit(input);
                }
              }}
              rows={1}
              placeholder="Pregunta sobre tus obras, materiales, indicadores o evidencias…"
              disabled={loadingConversation || !conversation}
              className="max-h-32 flex-1 resize-none rounded-[var(--radius-md)] border border-[var(--border-default)] bg-[var(--bg-surface)] px-3 py-2 text-sm outline-none focus-visible:shadow-[var(--focus-ring)]"
            />
            <Button
              type="submit"
              size="sm"
              disabled={!input.trim() || sending || loadingConversation}
              leftIcon={Send}
              aria-label="Enviar"
            >
              Enviar
            </Button>
          </div>
          <p className="mt-1.5 text-[11px] text-[var(--text-muted)]">
            El asistente sólo lee información de tu organización actual y nunca ejecuta acciones por sí solo.
          </p>
        </form>
      </aside>
    </div>
  );
}
