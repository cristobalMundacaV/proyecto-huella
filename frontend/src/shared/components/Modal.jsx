import { useEffect, useRef } from "react";
import { X } from "lucide-react";

import IconButton from "./IconButton";

function Modal({
  children,
  title,
  description,
  footer,
  onClose,
  closeOnBackdrop = true,
  size = "md",
}) {
  const dialogRef = useRef(null);

  useEffect(() => {
    dialogRef.current?.focus();
  }, []);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center overflow-y-auto bg-slate-950/55 p-4 backdrop-blur-[3px]"
      onMouseDown={(event) => {
        if (
          closeOnBackdrop &&
          event.target === event.currentTarget
        ) {
          onClose?.();
        }
      }}
    >
      <section
        ref={dialogRef}
        tabIndex={-1}
        role="dialog"
        aria-modal="true"
        aria-labelledby="modal-title"
        className={`relative w-full overflow-hidden ${size === "sm"
            ? "max-w-md"
            : "max-w-3xl"
          } rounded-[28px] border border-emerald-900/10 bg-white shadow-[0_32px_100px_rgba(2,44,34,0.28)]`}
      >
        <div
          aria-hidden="true"
          className="absolute inset-x-0 top-0 h-1 bg-gradient-to-r from-emerald-800 via-emerald-500 to-teal-400"
        />

        <header className="relative flex items-start justify-between gap-4 border-b border-emerald-900/10 bg-[linear-gradient(135deg,rgba(236,253,245,0.90),rgba(255,255,255,0.98))] px-6 py-5">
          <div className="min-w-0">
            <p className="text-[10px] font-black uppercase tracking-[0.20em] text-emerald-700">
              Carbono Zero
            </p>

            <h2
              id="modal-title"
              className="mt-1 text-xl font-black tracking-tight text-slate-950"
            >
              {title}
            </h2>

            {description && (
              <p className="mt-1.5 max-w-2xl text-sm leading-6 text-slate-600">
                {description}
              </p>
            )}
          </div>

          {onClose && (
            <IconButton
              aria-label="Cerrar diálogo"
              icon={X}
              onClick={onClose}
              className="shrink-0 rounded-full bg-white/80 shadow-sm hover:bg-white"
            />
          )}
        </header>

        <div className="max-h-[70vh] overflow-y-auto px-6 py-6">
          {children}
        </div>

        {footer && (
          <footer className="border-t border-emerald-900/10 bg-slate-50/70 px-6 py-4">
            {footer}
          </footer>
        )}
      </section>
    </div>
  );
}

export default Modal;