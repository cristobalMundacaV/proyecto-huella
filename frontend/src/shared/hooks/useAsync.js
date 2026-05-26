import { useCallback, useState } from "react";

export function useAsync(asyncFn) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const run = useCallback(
    async (...args) => {
      setLoading(true);
      setError("");

      try {
        return await asyncFn(...args);
      } catch (requestError) {
        setError(requestError);
        throw requestError;
      } finally {
        setLoading(false);
      }
    },
    [asyncFn]
  );

  return { error, loading, run };
}
