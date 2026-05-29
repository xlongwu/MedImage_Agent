import { useCallback, useEffect, useState } from "react";
import type { DependencyList, Dispatch, SetStateAction } from "react";

export interface AsyncResource<T> {
  data: T;
  loading: boolean;
  error: string;
  fromFallback: boolean;
  reload: () => Promise<void>;
  setData: Dispatch<SetStateAction<T>>;
}

export function useAsyncResource<T>(
  loader: () => Promise<T>,
  fallback: T,
  deps: DependencyList
): AsyncResource<T> {
  const [data, setData] = useState<T>(fallback);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [fromFallback, setFromFallback] = useState(true);

  const reload = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const next = await loader();
      setData(next);
      setFromFallback(false);
    } catch (err) {
      setData(fallback);
      setFromFallback(true);
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }, deps);

  useEffect(() => {
    reload();
  }, [reload]);

  return { data, loading, error, fromFallback, reload, setData };
}
