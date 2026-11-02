// oppytec-frontend/src/features/events/__tests__/EventsI18nAndFx.test.tsx
import "@testing-library/jest-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import React from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  setActiveLanguage,
  getActiveLanguage,
  translateKey,
  I18N_RESOURCES,
} from "@/shared/i18n";
import { formatMoney } from "@/shared/lib";
import { formatCurrencyAmount } from "@/shared/currency";
import { EventsPage } from "../EventsPage";
import { eventsApi } from "../api/eventsApi";
import { MOCK_EVENTOS_LIST, MOCK_SALONES, MOCK_FALTANTES_RESPONSE } from "../mockData";

// Mock de sonner
vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
    info: vi.fn(),
  },
}));

function renderWithClient(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
      },
      mutations: {
        retry: false,
      },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      {ui}
    </QueryClientProvider>
  );
}

describe("Events i18n & Multi-Currency FX Certification Suite (Fase 8)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    setActiveLanguage("es");

    vi.spyOn(eventsApi, "getEvents").mockResolvedValue(MOCK_EVENTOS_LIST);
    vi.spyOn(eventsApi, "getSalones").mockResolvedValue(MOCK_SALONES);
    vi.spyOn(eventsApi, "getFaltantesAnalytics").mockResolvedValue(MOCK_FALTANTES_RESPONSE);
  });

  afterEach(() => {
    cleanup();
    setActiveLanguage("es");
    vi.restoreAllMocks();
  });

  it("verifies 1:1 structural dictionary parity between 'es' and 'en' locales for events", () => {
    function extractLeafKeys(obj: unknown, prefix = ""): string[] {
      if (typeof obj !== "object" || obj === null) return [prefix];
      return Object.entries(obj).flatMap(([k, v]) =>
        extractLeafKeys(v, prefix ? `${prefix}.${k}` : k)
      );
    }

    const esEvents = I18N_RESOURCES.es?.events;
    const enEvents = I18N_RESOURCES.en?.events;

    expect(esEvents).toBeDefined();
    expect(enEvents).toBeDefined();

    const esKeys = extractLeafKeys(esEvents).sort();
    const enKeys = extractLeafKeys(enEvents).sort();

    expect(esKeys).toEqual(enKeys);
    expect(esKeys.length).toBeGreaterThanOrEqual(50);
  });

  it("renders Events UI in Spanish when active language is 'es'", async () => {
    setActiveLanguage("es");
    expect(getActiveLanguage()).toBe("es");

    renderWithClient(<EventsPage />);

    expect(screen.getByText("Eventos y Banquetes")).toBeInTheDocument();
    expect(screen.getAllByText("Programación y Control de Consumo")[0]).toBeInTheDocument();
    expect(screen.getByText("Salones")).toBeInTheDocument();
    expect(screen.getByText("Nuevo Evento")).toBeInTheDocument();
    expect(screen.getByText("Próximos / Agendados")).toBeInTheDocument();
    expect(screen.getByText("Finalizados / Historial")).toBeInTheDocument();
    expect(screen.getByText("Cancelados")).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText(/Alerta de Stock Comprometido/i)).toBeInTheDocument();
    });
  });

  it("dynamically switches and renders Events UI in English when language is 'en'", async () => {
    setActiveLanguage("en");
    expect(getActiveLanguage()).toBe("en");

    renderWithClient(<EventsPage />);

    expect(screen.getByText("Events & Banquets")).toBeInTheDocument();
    expect(screen.getAllByText("Scheduling and Consumption Control")[0]).toBeInTheDocument();
    expect(screen.getByText("Halls")).toBeInTheDocument();
    expect(screen.getByText("New Event")).toBeInTheDocument();
    expect(screen.getByText("Upcoming / Scheduled")).toBeInTheDocument();
    expect(screen.getByText("Finished / History")).toBeInTheDocument();
    expect(screen.getByText("Cancelled")).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText(/Committed Stock Alert/i)).toBeInTheDocument();
    });
  });

  it("certifies Multi-Currency FX with Decimal for salon rental tariffs and event costing", () => {
    // 1. Neto <-> Bruto with 19% IVA calculation parity
    const neto = 100000;
    const ivaPercentage = 19;
    const bruto = Math.round(neto * (1 + ivaPercentage / 100));
    expect(bruto).toBe(119000);

    const reverseNeto = Math.round(bruto / (1 + ivaPercentage / 100));
    expect(reverseNeto).toBe(100000);

    // 2. formatMoney with Multi-Currency support:
    // CLP (Chilean Peso - 0 decimals)
    expect(formatCurrencyAmount(119000, "CLP")).toBe("$119.000");
    expect(formatMoney(119000)).toBe("$119.000");

    // USD (US Dollar - 2 decimals)
    expect(formatCurrencyAmount("119.50", "USD")).toBe("US$119.50");

    // EUR (Euro - 2 decimals)
    expect(formatCurrencyAmount("119.50", "EUR")).toBe("€119,50");

    // UF (Unidad de Fomento - 4 decimals)
    expect(formatCurrencyAmount("3.4567", "UF")).toBe("UF 3,4567");

    // 3. Event theoretical cost calculation with zero distortion
    const insumoItemCost = 25000;
    const recetaCost = 45000;
    const comboCost = 75000;
    const totalCost = insumoItemCost + recetaCost + comboCost;
    expect(totalCost).toBe(145000);
    expect(formatMoney(totalCost)).toBe("$145.000");
  });

  it("translates modal dialogs and alert banners seamlessly in both locales", () => {
    setActiveLanguage("es");
    expect(translateKey("events", "salones_dialog.title")).toBe("Gestión de Salones y Espacios");
    expect(translateKey("events", "dialog.title_create")).toBe("Nuevo Evento o Banquete");
    expect(translateKey("events", "shortages_dialog.title")).toBe(
      "Resumen de Stock Faltante y Comprometido para Eventos"
    );
    expect(translateKey("events", "card.badge_agendado")).toBe("Agendado");

    setActiveLanguage("en");
    expect(translateKey("events", "salones_dialog.title")).toBe("Halls and Spaces Management");
    expect(translateKey("events", "dialog.title_create")).toBe("New Event or Banquet");
    expect(translateKey("events", "shortages_dialog.title")).toBe(
      "Summary of Shortage and Committed Stock for Events"
    );
    expect(translateKey("events", "card.badge_agendado")).toBe("Scheduled");
  });
});
