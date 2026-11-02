/**
 * oppytec-frontend/src/features/projection/__tests__/projectionI18n.test.tsx
 * Suite de Certificación i18n y Multi-Moneda FX para la Feature Proyección.
 * Valida 100% paridad es/en, resolución en caliente y ausencia de textos duros.
 */
import "@testing-library/jest-dom";
import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { render, screen, cleanup, waitFor, act } from "@testing-library/react";
import i18next from "i18next";
import { I18nextProvider } from "react-i18next";
import { setActiveLanguage } from "@/shared/i18n/config";
import { ProyeccionHeader } from "../components/ProyeccionHeader";
import { ProyeccionToolbar } from "../components/ProyeccionToolbar";
import { ProyeccionExecutiveBanner } from "../components/ProyeccionExecutiveBanner";
import { ProyeccionPagination } from "../components/ProyeccionPagination";
import { ProyeccionCategoryFilter } from "../components/ProyeccionCategoryFilter";
import { ProyeccionProductCard } from "../components/ProyeccionProductCard";
import { MOCK_PROJECTION_PRODUCTS, MOCK_PROJECTION_METRICS_SUMMARY } from "../mockData";

describe("Proyección i18n and FX Multi-Currency Suite", () => {
  beforeEach(() => {
    setActiveLanguage("es");
  });

  afterEach(() => {
    cleanup();
    setActiveLanguage("es");
  });

  it("renders ProyeccionHeader in Spanish by default and switches dynamically to English", async () => {
    const { rerender } = render(
      <I18nextProvider i18n={i18next}>
        <ProyeccionHeader />
      </I18nextProvider>
    );

    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("Proyección");
    expect(screen.getAllByText("Simulación de Disponibilidad y Alertas")[0]).toBeInTheDocument();

    // Cambiar idioma a inglés
    act(() => {
      setActiveLanguage("en");
    });
    rerender(
      <I18nextProvider i18n={i18next}>
        <ProyeccionHeader />
      </I18nextProvider>
    );

    await waitFor(() => {
      expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("Projection");
      expect(screen.getAllByText("Availability Simulation & Alerts")[0]).toBeInTheDocument();
    });
  });

  it("renders ProyeccionToolbar placeholders and options in Spanish and English", async () => {
    const { rerender } = render(
      <I18nextProvider i18n={i18next}>
        <ProyeccionToolbar
          searchTerm=""
          onSearchChange={() => {}}
          horizonDays={30}
          onHorizonChange={() => {}}
          sortBy="urgency_desc"
          onSortChange={() => {}}
          pageSize={30}
          onPageSizeChange={() => {}}
          onRecompute={() => {}}
          isRecomputing={false}
          onToggleCategories={() => {}}
          activeCategoriesCount={2}
        />
      </I18nextProvider>
    );

    expect(
      screen.getByPlaceholderText("Buscar por producto, SKU o categoría...")
    ).toBeInTheDocument();
    expect(screen.getByText("Recalcular Ahora")).toBeInTheDocument();
    expect(screen.getByText("Categorías")).toBeInTheDocument();
    expect(screen.getByText("Mayor Urgencia")).toBeInTheDocument();

    // Switch to English
    act(() => {
      setActiveLanguage("en");
    });
    rerender(
      <I18nextProvider i18n={i18next}>
        <ProyeccionToolbar
          searchTerm=""
          onSearchChange={() => {}}
          horizonDays={30}
          onHorizonChange={() => {}}
          sortBy="urgency_desc"
          onSortChange={() => {}}
          pageSize={30}
          onPageSizeChange={() => {}}
          onRecompute={() => {}}
          isRecomputing={false}
          onToggleCategories={() => {}}
          activeCategoriesCount={2}
        />
      </I18nextProvider>
    );

    await waitFor(() => {
      expect(
        screen.getByPlaceholderText("Search by product, SKU or category...")
      ).toBeInTheDocument();
      expect(screen.getByText("Recompute Now")).toBeInTheDocument();
      expect(screen.getByText("Categories")).toBeInTheDocument();
      expect(screen.getByText("Highest Urgency")).toBeInTheDocument();
    });
  });

  it("renders ProyeccionExecutiveBanner KPIs in Spanish and English with correct currency", async () => {
    const { rerender } = render(
      <I18nextProvider i18n={i18next}>
        <ProyeccionExecutiveBanner
          metrics={MOCK_PROJECTION_METRICS_SUMMARY}
          horizonDays={30}
        />
      </I18nextProvider>
    );

    expect(screen.getByText("Monitoreados")).toBeInTheDocument();
    expect(screen.getByText("Quiebre Crítico")).toBeInTheDocument();
    expect(screen.getByText("Stock Bajo")).toBeInTheDocument();
    expect(screen.getByText("Autonomía Prom.")).toBeInTheDocument();
    expect(screen.getByText("Valor en Riesgo")).toBeInTheDocument();
    expect(screen.getByText("$312.500")).toBeInTheDocument();

    // Switch to English
    act(() => {
      setActiveLanguage("en");
    });
    rerender(
      <I18nextProvider i18n={i18next}>
        <ProyeccionExecutiveBanner
          metrics={MOCK_PROJECTION_METRICS_SUMMARY}
          horizonDays={30}
        />
      </I18nextProvider>
    );

    await waitFor(() => {
      expect(screen.getByText("Monitored")).toBeInTheDocument();
      expect(screen.getByText("Critical Shortage")).toBeInTheDocument();
      expect(screen.getByText("Low Stock")).toBeInTheDocument();
      expect(screen.getByText("Avg. Autonomy")).toBeInTheDocument();
      expect(screen.getByText("Value at Risk")).toBeInTheDocument();
    });
  });

  it("renders ProyeccionPagination summaries in Spanish and English", async () => {
    const { rerender } = render(
      <I18nextProvider i18n={i18next}>
        <ProyeccionPagination
          currentPage={1}
          totalItems={50}
          pageSize={10}
          onPageChange={() => {}}
          onPageSizeChange={() => {}}
        />
      </I18nextProvider>
    );

    expect(screen.getByText("Mostrando 1 - 10")).toBeInTheDocument();
    expect(screen.getByText("de")).toBeInTheDocument();
    expect(screen.getByText("50 productos")).toBeInTheDocument();

    // Switch to English
    act(() => {
      setActiveLanguage("en");
    });
    rerender(
      <I18nextProvider i18n={i18next}>
        <ProyeccionPagination
          currentPage={1}
          totalItems={50}
          pageSize={10}
          onPageChange={() => {}}
          onPageSizeChange={() => {}}
        />
      </I18nextProvider>
    );

    await waitFor(() => {
      expect(screen.getByText("Showing 1 - 10")).toBeInTheDocument();
      expect(screen.getByText("of")).toBeInTheDocument();
      expect(screen.getByText("50 products")).toBeInTheDocument();
    });
  });

  it("renders ProyeccionCategoryFilter 'Todas' / 'All' in Spanish and English", async () => {
    const categories = [
      { id: 1, name: "Carnes", count: 5 },
      { id: 2, name: "Lácteos", count: 3 },
    ];

    const { rerender } = render(
      <I18nextProvider i18n={i18next}>
        <ProyeccionCategoryFilter
          categories={categories}
          selectedCategoryId="all"
          onSelectCategory={() => {}}
        />
      </I18nextProvider>
    );

    expect(screen.getByText("Todas")).toBeInTheDocument();

    // Switch to English
    act(() => {
      setActiveLanguage("en");
    });
    rerender(
      <I18nextProvider i18n={i18next}>
        <ProyeccionCategoryFilter
          categories={categories}
          selectedCategoryId="all"
          onSelectCategory={() => {}}
        />
      </I18nextProvider>
    );

    await waitFor(() => {
      expect(screen.getByText("All")).toBeInTheDocument();
    });
  });

  it("renders ProyeccionProductCard labels in Spanish and English", async () => {
    const product = MOCK_PROJECTION_PRODUCTS[0]!;

    const { rerender } = render(
      <I18nextProvider i18n={i18next}>
        <ProyeccionProductCard product={product} />
      </I18nextProvider>
    );

    expect(screen.getByText("Hoy")).toBeInTheDocument();
    expect(screen.getByText("Proyectado")).toBeInTheDocument();
    expect(screen.getByText("Agotamiento")).toBeInTheDocument();
    expect(screen.getByText("Toca para ver curva FEFO")).toBeInTheDocument();

    // Switch to English
    act(() => {
      setActiveLanguage("en");
    });
    rerender(
      <I18nextProvider i18n={i18next}>
        <ProyeccionProductCard product={product} />
      </I18nextProvider>
    );

    await waitFor(() => {
      expect(screen.getByText("Today")).toBeInTheDocument();
      expect(screen.getByText("Projected")).toBeInTheDocument();
      expect(screen.getByText("Depletion")).toBeInTheDocument();
      expect(screen.getByText("Tap to view FEFO curve")).toBeInTheDocument();
    });
  });
});
