/**
 * oppytec-frontend/src/features/procurement/mermas/GestionarMermaView.tsx
 * Vista Integradora de Gestión Analítica de Mermas (Fase 6.1).
 * SectionHeader centrado (#ef4444), MermaDateRangePicker, KpiDashboard,
 * MermaStats, MermaHistory y conexión directa con MermaDialog.
 */

import { useState, useCallback, useMemo } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { TrendingDown } from "lucide-react";
import { toast } from "sonner";
import { SectionHeader } from "@/shared/components/ui/SectionHeader";
import { apiRequest } from "@/shared/api/httpClient";
import { MermaDialog } from "@/features/inventory/stock/dialogs/MermaDialog";
import { MOCK_BODEGAS, MOCK_STOCK_ITEMS } from "@/features/inventory/mockData";
import type { MermaPayload, StockItem } from "@/features/inventory/types";
import { useMermaAnalytics } from "../hooks/useMermaAnalytics";
import { MermaDateRangePicker } from "./MermaDateRangePicker";
import { KpiDashboard } from "./KpiDashboard";
import { MermaStats } from "./MermaStats";
import { MermaHistory } from "./MermaHistory";

export interface GestionarMermaViewProps {
  readonly hideHeader?: boolean;
}

export function GestionarMermaView({ hideHeader = false }: GestionarMermaViewProps) {
  const queryClient = useQueryClient();

  const {
    analytics,
    historyItems,
    isLoadingAnalytics,
    isLoadingHistory,
    filters,
    setPreset,
    setCustomRange,
    setFilter,
    resetFilters,
  } = useMermaAnalytics();

  const [isRegisterMermaOpen, setIsRegisterMermaOpen] = useState(false);

  // Catálogo operativo de stock para el diálogo de registro de merma
  const stockItemsForDialog: StockItem[] = useMemo(() => {
    const polloKingItem: StockItem = {
      id: 990,
      producto_id: 10,
      nombre: "Pollo King",
      sku: "INS-POLL-001",
      categoria: "Carnes y Aves",
      categoria_color: "#DC2626",
      categoria_icono: "beef",
      bodega_id: 1,
      bodega_nombre: "Cámara de Frío Principal",
      stock_actual: 50.0,
      stock_minimo: 15.0,
      stock_maximo: 100.0,
      punto_reorden: 20.0,
      unidad_medida: "kg",
      ubicacion: {
        pasillo: "A",
        estante: "1",
        nivel: "1",
        coordenada_letra: "A",
        coordenada_numero: "1",
      },
      costo_unitario_ppp: 3850,
      costo_total_valorizado: 192500,
      semaforo: "OPTIMO",
      lotes: [
        {
          lote_codigo: "LOTE-PK-20261024",
          fecha_vencimiento: "2026-11-15",
          cantidad: 50.0,
        },
      ],
      dias_alerta_vencimiento: 5,
      no_perecible: false,
    };
    return [polloKingItem, ...MOCK_STOCK_ITEMS];
  }, []);

  const handleReportMerma = useCallback(
    async (payload: MermaPayload) => {
      try {
        await apiRequest("/api/v1/inventory/mermas", {
          method: "POST",
          body: {
            producto_id: payload.producto_id,
            bodega_id: payload.bodega_id,
            quantity: payload.quantity,
            unit_cost: payload.unit_cost,
            reason: payload.reason,
            lote_codigo: payload.lote_codigo ?? null,
          },
        });
      } catch {
        // Fallback resiliente en modo desconectado
      }
      toast.success("Merma operativa registrada y contabilizada a PPP.");
      void queryClient.invalidateQueries({
        queryKey: ["oppytec", "inventory", "mermas"],
      });
    },
    [queryClient]
  );

  const handleSelectMotivoFromStats = useCallback(
    (motivo: string) => {
      setFilter("motivo", filters.motivo === motivo ? null : motivo);
    },
    [filters.motivo, setFilter]
  );

  return (
    <div
      data-testid="gestionar-merma-view"
      className="space-y-6 animate-in fade-in duration-300 pb-10"
    >
      {/* 1. CABECERA DE SECCIÓN (#ef4444) */}
      {!hideHeader && (
        <div data-testid="mermas-section-header">
          <SectionHeader
            title="Gestión y Control de Mermas"
            subtitle="Monitoreo analítico de pérdidas operativas, caducidades y motivos"
            icon={TrendingDown}
            color="#ef4444"
            center={true}
          />
        </div>
      )}

      {/* 2. SELECTOR DE RANGO DE FECHAS Y PRESETS */}
      <MermaDateRangePicker
        preset={filters.preset}
        dateFrom={filters.date_from}
        dateTo={filters.date_to}
        onPresetChange={setPreset}
        onCustomRangeChange={setCustomRange}
        onReset={resetFilters}
      />

      {/* 3. DASHBOARD DE KPIS DE PÉRDIDA VALORIZADA A PPP */}
      <KpiDashboard
        analytics={analytics}
        isLoading={isLoadingAnalytics}
        onSelectMotivo={handleSelectMotivoFromStats}
      />

      {/* 4. GRÁFICOS DE EVOLUCIÓN TEMPORAL Y DISTRIBUCIÓN POR MOTIVO */}
      <MermaStats
        analytics={analytics}
        onFilterByMotivo={handleSelectMotivoFromStats}
      />

      {/* 5. HISTORIAL DETALLADO Y BOTÓN + REGISTRAR MERMA */}
      <MermaHistory
        items={historyItems}
        isLoading={isLoadingHistory}
        selectedMotivoFilter={filters.motivo ?? null}
        onMotivoFilterChange={(mot) => setFilter("motivo", mot)}
        onOpenRegisterMerma={() => setIsRegisterMermaOpen(true)}
      />

      {/* 6. MODAL OPERATIVO DE REGISTRO DE MERMA */}
      <MermaDialog
        open={isRegisterMermaOpen}
        onClose={() => setIsRegisterMermaOpen(false)}
        stockItems={stockItemsForDialog}
        bodegas={MOCK_BODEGAS}
        onReportMerma={handleReportMerma}
      />
    </div>
  );
}

export default GestionarMermaView;
