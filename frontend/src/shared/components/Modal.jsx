import AnimatedModalShell from "./AnimatedModalShell";

function Modal({ children, onClose }) {
  return (
    <AnimatedModalShell
      ariaLabel="Modal"
      contentClassName="my-8 w-full max-w-4xl rounded-3xl border border-[var(--border)] bg-[var(--bg-card)] p-4 shadow-2xl sm:p-6"
      onBackdropClick={onClose}
    >
        {onClose && (
          <button
            type="button"
            onClick={onClose}
            className="float-right rounded-2xl border border-[var(--border)] bg-[var(--bg-surface)] px-3 py-2 text-sm font-semibold text-[var(--text-main)]"
          >
            Cerrar
          </button>
        )}
        {children}
    </AnimatedModalShell>
  );
}

export default Modal;
