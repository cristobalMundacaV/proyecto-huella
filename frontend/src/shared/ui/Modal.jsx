import { useEffect, useId, useRef } from "react";
import { X } from "lucide-react";
import { IconButton } from "./Button";

const widths = { sm: "max-w-md", lg: "max-w-3xl", xl: "max-w-5xl" };

export default function Modal({ open = true, eyebrow, icon: Icon, title = "Diálogo", description, children, footer, onClose, closeOnBackdrop = true, size = "lg" }) {
  const dialogRef = useRef(null);
  const onCloseRef = useRef(onClose);
  const titleId = useId();
  const descriptionId = useId();

  useEffect(() => { onCloseRef.current = onClose; }, [onClose]);
  useEffect(() => {
    if (!open) return undefined;
    const previous = document.activeElement;
    const dialog = dialogRef.current;
    const selector = 'button:not([disabled]), [href], input:not([disabled]):not([type="hidden"]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';
    const focusable = () => Array.from(dialog?.querySelectorAll(selector) || []).filter((element) => element.getAttribute("aria-hidden") !== "true" && element.offsetParent !== null);
    const elements = focusable();
    (elements.find((element) => element.hasAttribute("data-autofocus")) || elements.find((element) => ["INPUT", "SELECT", "TEXTAREA"].includes(element.tagName)) || elements[0] || dialog)?.focus();
    const handleKeyDown = (event) => {
      if (event.key === "Escape") { onCloseRef.current?.(); return; }
      if (event.key !== "Tab" || !dialog) return;
      const current = focusable();
      if (!current.length) { event.preventDefault(); dialog.focus(); return; }
      const first = current[0];
      const last = current[current.length - 1];
      if (event.shiftKey && (document.activeElement === first || !dialog.contains(document.activeElement))) { event.preventDefault(); last.focus(); }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => { document.removeEventListener("keydown", handleKeyDown); previous?.focus?.(); };
  }, [open]);

  if (!open) return null;
  return <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-3 backdrop-blur-[2px] sm:p-6" onMouseDown={(event) => { if (closeOnBackdrop && event.target === event.currentTarget) onClose?.(); }}>
    <section ref={dialogRef} tabIndex={-1} role="dialog" aria-modal="true" aria-labelledby={titleId} aria-describedby={description ? descriptionId : undefined} className={`flex max-h-[calc(100dvh-1.5rem)] w-full flex-col overflow-hidden rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--bg-elevated)] shadow-[var(--shadow-lg)] sm:max-h-[calc(100dvh-3rem)] ${widths[size] || widths.lg}`}>
      <header className="flex shrink-0 items-center justify-between gap-4 border-b border-[var(--border-subtle)] bg-[var(--bg-surface-subtle)] px-5 py-4 sm:px-6 sm:py-5">
        <div className="flex min-w-0 items-center gap-3">
          {Icon && <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-[var(--radius-md)] bg-[var(--brand-soft)] text-[var(--brand-primary)]"><Icon aria-hidden="true" size={20} /></span>}
          <div className="min-w-0">
            {eyebrow && <p className="mb-1 text-[0.68rem] font-black uppercase tracking-[0.16em] text-[var(--brand-primary)]">{eyebrow}</p>}
            <h2 id={titleId} className="text-lg font-black leading-tight text-[var(--text-primary)] sm:text-xl">{title}</h2>
            {description && <p id={descriptionId} className="mt-1 max-w-2xl text-sm leading-5 text-[var(--text-muted)]">{description}</p>}
          </div>
        </div>
        {onClose && <IconButton aria-label="Cerrar diálogo" title="Cerrar" icon={X} onClick={onClose} className="h-10 w-10 shrink-0 rounded-full border border-[var(--border-default)] bg-white p-0 shadow-sm hover:bg-white" />}
      </header>
      <div className="min-h-0 flex-1 overflow-y-auto px-5 py-5 sm:px-6 sm:py-6">{children}</div>
      {footer && <footer className="shrink-0 border-t border-[var(--border-subtle)] bg-[var(--bg-surface-subtle)] px-5 py-4 sm:px-6">{footer}</footer>}
    </section>
  </div>;
}
