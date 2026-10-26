import { useState, useCallback } from "react";

/**
 * Hook para persistir términos de búsqueda en sessionStorage por sección.
 * Permite mantener el texto ingresado al navegar entre pantallas o recargar la pestaña.
 */
export function usePersistentSearch(key: string, initialValue: string = "") {
  const storageKey = `search_${key}`;

  const [term, setTermState] = useState<string>(() => {
    try {
      if (typeof window === "undefined" || !window.sessionStorage) {
        return initialValue;
      }
      const stored = window.sessionStorage.getItem(storageKey);
      return stored !== null ? stored : initialValue;
    } catch {
      return initialValue;
    }
  });

  const setTerm = useCallback(
    (valueOrFn: string | ((prev: string) => string)) => {
      setTermState((prev) => {
        const next = typeof valueOrFn === "function" ? valueOrFn(prev) : valueOrFn;
        try {
          if (typeof window !== "undefined" && window.sessionStorage) {
            if (next && next.trim() !== "") {
              window.sessionStorage.setItem(storageKey, next);
            } else {
              window.sessionStorage.removeItem(storageKey);
            }
          }
        } catch {
          // Fallback silencioso en entornos donde sessionStorage esté restringido
        }
        return next;
      });
    },
    [storageKey]
  );

  const clearTerm = useCallback(() => {
    setTerm("");
  }, [setTerm]);

  return [term, setTerm, clearTerm] as const;
}
