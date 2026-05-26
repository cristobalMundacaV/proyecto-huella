import { useCallback, useState } from "react";

export function useToast() {
  const [toast, setToast] = useState(null);

  const showToast = useCallback((message) => {
    setToast({ id: Date.now(), message });
  }, []);

  const clearToast = useCallback(() => setToast(null), []);

  return { clearToast, showToast, toast };
}
