import { useEffect, useRef } from "react";
import { X } from "lucide-react";

export function Drawer({ open, onClose, title, children }) {
  const closeRef = useRef(null);
  useEffect(() => {
    if (!open) return undefined;
    const previous = document.activeElement;
    closeRef.current?.focus();
    const onKeyDown = (event) => event.key === "Escape" && onClose();
    document.addEventListener("keydown", onKeyDown);
    return () => { document.removeEventListener("keydown", onKeyDown); previous?.focus?.(); };
  }, [onClose, open]);
  if (!open) return null;
  return <div className="fixed inset-0 z-50" role="presentation"><button aria-label="Cerrar panel" className="absolute inset-0 bg-slate-950/35" onClick={onClose} /><aside aria-label={title} aria-modal="true" role="dialog" className="absolute inset-y-0 right-0 w-full overflow-y-auto border-l border-[var(--border-default)] bg-[var(--bg-surface)] p-5 shadow-2xl sm:max-w-xl"><header className="mb-5 flex items-center justify-between gap-3"><h2 className="text-xl font-bold">{title}</h2><button ref={closeRef} aria-label="Cerrar" className="rounded-lg p-2 hover:bg-[var(--bg-surface-subtle)]" onClick={onClose}><X /></button></header>{children}</aside></div>;
}
