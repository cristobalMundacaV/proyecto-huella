import { motion } from "framer-motion";

function AnimatedModalShell({
  ariaLabel,
  children,
  className = "",
  contentClassName = "",
  onBackdropClick,
}) {
  return (
    <motion.div
      className={`fixed inset-0 z-50 flex items-start justify-center overflow-y-auto premium-modal-overlay p-4 ${className}`}
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.18, ease: "easeOut" }}
      onClick={onBackdropClick}
    >
      <motion.div
        role="dialog"
        aria-modal="true"
        aria-label={ariaLabel}
        className={contentClassName}
        initial={{ opacity: 0, y: 18, scale: 0.98 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        exit={{ opacity: 0, y: 12, scale: 0.98 }}
        transition={{ duration: 0.22, ease: [0.22, 1, 0.36, 1] }}
        onClick={(event) => event.stopPropagation()}
      >
        {children}
      </motion.div>
    </motion.div>
  );
}

export default AnimatedModalShell;
