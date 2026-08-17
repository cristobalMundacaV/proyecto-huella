import { useEffect, useRef } from "react";
import { X } from "lucide-react";

import { IconButton } from "./Button";

export default function Modal({
  open = true,
  title = "Diálogo",
  description,
  children,
  footer,
  onClose,
  closeOnBackdrop = true,
  size = "lg",
}) {
  const dialogRef = useRef(null);
  const onCloseRef = useRef(onClose);

  useEffect(() => {
    onCloseRef.current = onClose;
  }, [onClose]);

  useEffect(() => {
    if (!open) return undefined;

    const previous = document.activeElement;
    const dialog = dialogRef.current;

    const focusableSelector =
      'button:not([disabled]), [href], input:not([disabled]):not([type="hidden"]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

    const getFocusableElements = () =>
      Array.from(dialog?.querySelectorAll(focusableSelector) || []).filter(
        (element) =>
          element.getAttribute("aria-hidden") !== "true" &&
          element.offsetParent !== null,
      );

    const focusableElements = getFocusableElements();

    const firstFocusable =
      focusableElements.find((element) =>
        element.hasAttribute("data-autofocus"),
      ) ||
      focusableElements.find((element) =>
        ["INPUT", "SELECT", "TEXTAREA"].includes(element.tagName),
      ) ||
      focusableElements[0] ||
      dialog;

    firstFocusable?.focus();

    const handleKeyDown = (event) => {
      if (event.key === "Escape") {
        onCloseRef.current?.();
        return;
      }

      if (event.key !== "Tab" || !dialog) return;

      const currentFocusable = getFocusableElements();

      if (!currentFocusable.length) {
        event.preventDefault();
        dialog.focus();
        return;
      }

      const first = currentFocusable[0];
      const last = currentFocusable[currentFocusable.length - 1];
      const activeElement = document.activeElement;

      if (
        event.shiftKey &&
        (activeElement === first || !dialog.contains(activeElement))
      ) {
        event.preventDefault();
        last.focus();
        return;
      }

      if (!event.shiftKey && activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };

    document.addEventListener("keydown", handleKeyDown);

    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      previous?.focus?.();
    };
  }, [open]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center overflow-y-auto bg-black/45 p-4"
      onMouseDown={(event) => {
        if (closeOnBackdrop && event.target === event.currentTarget) {
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
        className={`w-full ${
          size === "sm" ? "max-w-md" : "max-w-3xl"
        } rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--bg-elevated)] shadow-[var(--shadow-lg)]`}
      >
        <header className="flex items-start justify-between gap-4 border-b border-[var(--border-subtle)] p-5">
          <div>
            <h2 id="modal-title" className="text-xl font-bold">
              {title}
            </h2>
            {description && (
              <p className="mt-1 text-sm text-[var(--text-muted)]">
                {description}
              </p>
            )}
          </div>

          {onClose && (
            <IconButton
              aria-label="Cerrar diálogo"
              icon={X}
              onClick={onClose}
            />
          )}
        </header>

        <div className="max-h-[70vh] overflow-y-auto p-5">
          {children}
        </div>

        {footer && (
          <footer className="border-t border-[var(--border-subtle)] p-5">
            {footer}
          </footer>
        )}
      </section>
    </div>
  );
}
