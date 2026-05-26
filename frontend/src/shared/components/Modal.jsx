import AnimatedModalShell from "./AnimatedModalShell";

function Modal({ children, onClose }) {
  return (
    <AnimatedModalShell
      ariaLabel="Modal"
      className="premium-modal-overlay"
      contentClassName="premium-modal-shell my-8 w-full max-w-4xl p-4 sm:p-6 slide-up"
      onBackdropClick={onClose}
    >
      {onClose && (
        <button
          type="button"
          onClick={onClose}
          className="float-right rounded-2xl border border-[var(--border)] bg-[var(--bg-surface)] px-3 py-2 text-sm font-semibold text-[var(--text-main)] premium-button-secondary"
        >
          Cerrar
        </button>
      )}
      {children}
    </AnimatedModalShell>
  );
}

export default Modal;
