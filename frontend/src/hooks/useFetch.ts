import { useCallback, useEffect, useRef, useState } from "react";

export function useFetch<T>(fn: () => Promise<T>, deps: unknown[], enabled = true) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);
  const fnRef = useRef(fn);
  fnRef.current = fn;
  const reload = useCallback(() => setTick((t) => t + 1), []);
  const key = JSON.stringify(deps) + "|" + tick + "|" + enabled;

  useEffect(() => {
    if (!enabled) {
      setLoading(false);
      return;
    }
    let alive = true;
    setLoading(true);
    fnRef
      .current()
      .then((result) => {
        if (alive) {
          setData(result);
          setError(null);
        }
      })
      .catch((err: unknown) => {
        if (alive) {
          setError(err instanceof Error ? err.message : String(err));
        }
      })
      .finally(() => {
        if (alive) setLoading(false);
      });
    return () => {
      alive = false;
    };
  }, [key]);

  const clear = useCallback(() => setData(null), []);

  return { data, loading, error, reload, clear };
}
