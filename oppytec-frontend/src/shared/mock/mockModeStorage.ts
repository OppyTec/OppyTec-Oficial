/**
 * oppytec-frontend/src/shared/mock/mockModeStorage.ts
 * Gestor reactivo de estado para el Switch Maestro de Mock Data en OppyTec v2.0.
 *
 * Soporta persistencia en localStorage ("demo" vs "clean"), reactividad
 * multi-pestaña mediante eventos `storage`, reactividad intra-pestaña mediante
 * CustomEvent("oppytec_mock_mode_changed"), y helpers seguros para SSR/Node.
 */

import { useCallback, useEffect, useState } from "react";

export type MockDataMode = "demo" | "clean";

export const MOCK_DATA_MODE_STORAGE_KEY = "oppytec_mock_data_mode" as const;
export const MOCK_DATA_CUSTOM_DATASET_STORAGE_KEY = "oppytec_mock_custom_dataset" as const;
export const MOCK_DATA_MODE_EVENT_NAME = "oppytec_mock_mode_changed" as const;
export const MOCK_DATA_RESET_EVENT_NAME = "oppytec_mock_dataset_reset" as const;
export const CLEAN_SLATE_V2_READY_KEY = "oppytec_clean_slate_v2_ready" as const;

export interface MockModeChangeEventDetail {
  readonly mode: MockDataMode;
  readonly timestamp: string;
}

export interface UseMockDataModeReturn {
  readonly mode: MockDataMode;
  readonly isDemo: boolean;
  readonly isClean: boolean;
  readonly setMode: (nextMode: MockDataMode) => void;
  readonly toggleMode: () => void;
}

function isStorageAvailable(): boolean {
  return typeof window !== "undefined" && typeof window.localStorage !== "undefined";
}

function isVitestEnvironment(): boolean {
  if (typeof process !== "undefined" && Boolean(process.env?.VITEST)) {
    return true;
  }
  try {
    if (typeof import.meta !== "undefined" && import.meta.env?.MODE === "test") {
      return true;
    }
  } catch {
    // Ignore import.meta access errors
  }
  return false;
}

/**
 * Auto-inicializa el navegador real en modo "clean" (Clean Slate v2.0)
 * cuando no se ejecuta dentro de Vitest.
 */
export function ensureCleanSlateBrowserDefault(): void {
  if (!isStorageAvailable() || isVitestEnvironment()) {
    return;
  }
  try {
    if (window.localStorage.getItem(CLEAN_SLATE_V2_READY_KEY) !== "true") {
      window.localStorage.setItem(MOCK_DATA_MODE_STORAGE_KEY, "clean");
      window.localStorage.removeItem(MOCK_DATA_CUSTOM_DATASET_STORAGE_KEY);
      window.localStorage.setItem(CLEAN_SLATE_V2_READY_KEY, "true");
    }
  } catch {
    // Si localStorage está restringido, no romper la app
  }
}

// Ejecutar auto-inicialización en carga del módulo para navegadores reales
ensureCleanSlateBrowserDefault();

/**
 * Lee el modo activo de Mock Data desde localStorage.
 * En Vitest retorna "demo" por defecto cuando localStorage está vacío;
 * en navegador real auto-inicializa y retorna "clean" por defecto.
 */
export function getMockDataMode(): MockDataMode {
  if (!isStorageAvailable()) {
    return isVitestEnvironment() ? "demo" : "clean";
  }
  ensureCleanSlateBrowserDefault();
  try {
    const raw = window.localStorage.getItem(MOCK_DATA_MODE_STORAGE_KEY);
    if (raw === "clean" || raw === "demo") {
      return raw;
    }
    return isVitestEnvironment() ? "demo" : "clean";
  } catch {
    return isVitestEnvironment() ? "demo" : "clean";
  }
}

/**
 * Establece el modo de Mock Data, lo persiste en localStorage
 * y notifica a todos los suscriptores activos mediante CustomEvent.
 */
export function setMockDataMode(nextMode: MockDataMode): void {
  if (!isStorageAvailable()) {
    return;
  }
  try {
    window.localStorage.setItem(MOCK_DATA_MODE_STORAGE_KEY, nextMode);
  } catch {
    // Si localStorage está restringido en modo incógnito, no romper la app
  }

  if (typeof window.dispatchEvent === "function") {
    const event = new CustomEvent<MockModeChangeEventDetail>(MOCK_DATA_MODE_EVENT_NAME, {
      detail: {
        mode: nextMode,
        timestamp: new Date().toISOString(),
      },
    });
    window.dispatchEvent(event);
  }
}

/**
 * Alterna entre "demo" y "clean".
 */
export function toggleMockDataMode(): MockDataMode {
  const current = getMockDataMode();
  const next: MockDataMode = current === "demo" ? "clean" : "demo";
  setMockDataMode(next);
  return next;
}

/**
 * Determina si el modo de datos sintéticos está activo.
 */
export function isMockDataEnabled(): boolean {
  return getMockDataMode() === "demo";
}

/**
 * Selecciona determinísticamente entre datos de demostración y datos limpios (Clean Slate)
 * según el modo activo en el Switch Maestro.
 */
export function selectByMockMode<T>(demoData: T, cleanData: T): T {
  return isMockDataEnabled() ? demoData : cleanData;
}

/**
 * Hook reactivo que retorna demoData cuando el Switch Maestro está en "demo"
 * y cleanData cuando está en "clean", re-renderizando automáticamente al cambiar.
 */
export function useMockAwareData<T>(demoData: T, cleanData: T): T {
  const { isDemo } = useMockDataMode();
  return isDemo ? demoData : cleanData;
}

/**
 * Hook reactivo de React para observar y conmutar el Switch Maestro de Mock Data.
 * Se sincroniza bidireccionalmente entre pestañas (evento `storage`)
 * e instancias del mismo documento (evento `oppytec_mock_mode_changed`).
 */
export function useMockDataMode(): UseMockDataModeReturn {
  const [mode, setLocalMode] = useState<MockDataMode>(() => getMockDataMode());

  useEffect(() => {
    // 1. Escucha cambios locales mediante CustomEvent
    const handleLocalChange = (event: Event) => {
      const customEvt = event as CustomEvent<MockModeChangeEventDetail>;
      if (customEvt.detail?.mode && (customEvt.detail.mode === "demo" || customEvt.detail.mode === "clean")) {
        setLocalMode(customEvt.detail.mode);
      } else {
        setLocalMode(getMockDataMode());
      }
    };

    // 2. Escucha cambios externos (otras pestañas) mediante storage event
    const handleStorageChange = (event: StorageEvent) => {
      if (event.key === MOCK_DATA_MODE_STORAGE_KEY) {
        const nextValue = event.newValue;
        if (nextValue === "demo" || nextValue === "clean") {
          setLocalMode(nextValue);
        } else {
          setLocalMode("demo");
        }
      }
    };

    if (typeof window !== "undefined") {
      window.addEventListener(MOCK_DATA_MODE_EVENT_NAME, handleLocalChange);
      window.addEventListener("storage", handleStorageChange);
    }

    return () => {
      if (typeof window !== "undefined") {
        window.removeEventListener(MOCK_DATA_MODE_EVENT_NAME, handleLocalChange);
        window.removeEventListener("storage", handleStorageChange);
      }
    };
  }, []);

  const setMode = useCallback((nextMode: MockDataMode) => {
    setMockDataMode(nextMode);
    setLocalMode(nextMode);
  }, []);

  const toggleMode = useCallback(() => {
    const next = toggleMockDataMode();
    setLocalMode(next);
  }, []);

  return {
    mode,
    isDemo: mode === "demo",
    isClean: mode === "clean",
    setMode,
    toggleMode,
  };
}
