import { useState, useEffect } from "react";
import { fetchApi } from "../lib/api";

export function useApi<T>(endpoint: string, options?: RequestInit) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const fetch = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await fetchApi(endpoint, options);
      setData(res);
    } catch (err) {
      setError(err as Error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetch();
  }, [endpoint]);

  return { data, loading, error, refetch: fetch };
}
