/**
 * oppytec-frontend/src/features/projection/hooks/useProyeccionState.ts
 * Hook de Estado Global y Persistencia UI para la vista de Proyección.
 * Maneja búsqueda con debounce (300 ms), filtros por bodega/categoría/urgencia,
 * selección de horizonte y orden, paginación server-side y sincronización con localStorage.
 */
import { useCallback, useEffect, useMemo, useState } from "react";
import type {
  ProjectionFilters,
  ProjectionHorizonDays,
  ProjectionSortOrder,
  ProjectionUrgencyStatus,
} from "../types";

const STORAGE_KEY_PAGE_SIZE = "projection_page_size";
const STORAGE_KEY_HORIZON_DAYS = "projection_horizon_days";

const VALID_PAGE_SIZES = [10, 30, 50, 100] as const;
const VALID_HORIZONS: readonly ProjectionHorizonDays[] = [7, 15, 30, 60, 90] as const;

function getStoredPageSize(): number {
  if (typeof window === "undefined" || !window.localStorage) return 30;
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY_PAGE_SIZE);
    if (!raw) return 30;
    const parsed = parseInt(raw, 10);
    return (VALID_PAGE_SIZES as readonly number[]).includes(parsed) ? parsed : 30;
  } catch {
    return 30;
  }
}

function getStoredHorizonDays(): number {
  if (typeof window === "undefined" || !window.localStorage) return 30;
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY_HORIZON_DAYS);
    if (!raw) return 30;
    const parsed = parseInt(raw, 10);
    return (VALID_HORIZONS as readonly number[]).includes(parsed as ProjectionHorizonDays) ? parsed : 30;
  } catch {
    return 30;
  }
}

export interface UseProyeccionStateOptions {
  readonly initialSearch?: string;
  readonly initialBodegaId?: string | number | "all";
  readonly initialCategoryId?: string | number | "all";
  readonly initialStatus?: "all" | ProjectionUrgencyStatus;
  readonly initialSortBy?: ProjectionSortOrder;
  readonly initialHorizonDays?: number;
  readonly initialPage?: number;
  readonly initialPageSize?: number;
}

export function useProyeccionState(options?: UseProyeccionStateOptions) {
  const [searchTerm, setSearchTerm] = useState<string>(options?.initialSearch ?? "");
  const [debouncedSearch, setDebouncedSearch] = useState<string>(options?.initialSearch ?? "");

  const [bodegaId, setBodegaIdState] = useState<string | number | "all">(
    options?.initialBodegaId ?? "all"
  );
  const [categoryId, setCategoryIdState] = useState<string | number | "all">(
    options?.initialCategoryId ?? "all"
  );
  const [status, setStatusState] = useState<"all" | ProjectionUrgencyStatus>(
    options?.initialStatus ?? "all"
  );
  const [sortBy, setSortByState] = useState<ProjectionSortOrder>(
    options?.initialSortBy ?? "urgency_desc"
  );
  const [horizonDays, setHorizonDaysState] = useState<number>(
    options?.initialHorizonDays ?? getStoredHorizonDays()
  );
  const [page, setPageState] = useState<number>(options?.initialPage ?? 1);
  const [pageSize, setPageSizeState] = useState<number>(
    options?.initialPageSize ?? getStoredPageSize()
  );

  const [selectedProductId, setSelectedProductId] = useState<string | number | null>(null);

  // Debounce del término de búsqueda (300 ms)
  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedSearch(searchTerm);
      setPageState(1); // Reset a página 1 ante nueva búsqueda
    }, 300);

    return () => {
      clearTimeout(handler);
    };
  }, [searchTerm]);

  const setSearch = useCallback((val: string) => {
    setSearchTerm(val);
  }, []);

  const setBodegaId = useCallback((id: string | number | "all") => {
    setBodegaIdState(id);
    setPageState(1);
  }, []);

  const setCategoryId = useCallback((id: string | number | "all") => {
    setCategoryIdState(id);
    setPageState(1);
  }, []);

  const setStatus = useCallback((st: "all" | ProjectionUrgencyStatus) => {
    setStatusState(st);
    setPageState(1);
  }, []);

  const setSortBy = useCallback((sort: ProjectionSortOrder) => {
    setSortByState(sort);
    setPageState(1);
  }, []);

  const setHorizonDays = useCallback((days: number) => {
    setHorizonDaysState(days);
    setPageState(1);
    if (typeof window !== "undefined" && window.localStorage) {
      try {
        window.localStorage.setItem(STORAGE_KEY_HORIZON_DAYS, String(days));
      } catch {
        // Ignorar excepciones de cuota de storage
      }
    }
  }, []);

  const setPageSize = useCallback((size: number) => {
    setPageSizeState(size);
    setPageState(1);
    if (typeof window !== "undefined" && window.localStorage) {
      try {
        window.localStorage.setItem(STORAGE_KEY_PAGE_SIZE, String(size));
      } catch {
        // Ignorar excepciones de storage
      }
    }
  }, []);

  const setPage = useCallback((p: number) => {
    setPageState(Math.max(1, p));
  }, []);

  const resetFilters = useCallback(() => {
    setSearchTerm("");
    setDebouncedSearch("");
    setBodegaIdState("all");
    setCategoryIdState("all");
    setStatusState("all");
    setSortByState("urgency_desc");
    setPageState(1);
  }, []);

  // Objeto reactivo canónico de filtros para useProyeccionData
  const filters: ProjectionFilters = useMemo(() => {
    return {
      search: debouncedSearch.trim() || undefined,
      bodegaId,
      categoryId,
      status,
      sortBy,
      horizonDays,
      page,
      pageSize,
    };
  }, [debouncedSearch, bodegaId, categoryId, status, sortBy, horizonDays, page, pageSize]);

  const activeFiltersCount = useMemo(() => {
    let count = 0;
    if (debouncedSearch.trim()) count++;
    if (bodegaId !== "all") count++;
    if (categoryId !== "all") count++;
    if (status !== "all") count++;
    return count;
  }, [debouncedSearch, bodegaId, categoryId, status]);

  return {
    searchTerm,
    debouncedSearch,
    bodegaId,
    categoryId,
    status,
    sortBy,
    horizonDays,
    page,
    pageSize,
    selectedProductId,
    filters,
    activeFiltersCount,
    setSearch,
    setBodegaId,
    setCategoryId,
    setStatus,
    setSortBy,
    setHorizonDays,
    setPageSize,
    setPage,
    resetFilters,
    setSelectedProductId,
  };
}
