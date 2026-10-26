// oppytec-frontend/src/features/historial/HistorialPage.tsx
import { useState } from "react";
import { History } from "lucide-react";
import { SectionHeader } from "@/shared/components/ui/SectionHeader";
import { HistorialToolbar } from "./HistorialToolbar";
import { FiltrosHistorial } from "./FiltrosHistorial";
import { TablaHistorial } from "./TablaHistorial";
import { useHistorial } from "./useHistorial";
import {
  CANONICAL_AUDIT_CSV_COLUMNS,
  sanitizeCsvField,
  formatCsvRow,
  getChileanDateIsoString,
  generateAuditoriaCsvContent,
  downloadHistorialCSV,
  type CsvExportOptions,
} from "./exportCSV";

export {
  CANONICAL_AUDIT_CSV_COLUMNS,
  sanitizeCsvField,
  formatCsvRow,
  getChileanDateIsoString,
  generateAuditoriaCsvContent,
  downloadHistorialCSV,
  type CsvExportOptions,
};

/**
 * Vista Principal del Módulo de Historial y Auditoría de Inventario (/historial).
 * Réplica 1:1 con SectionHeader centrado (#06b6d4), Toolbar unificado de gobernanza,
 * exportador CSV resiliente con UTF-8 BOM y paginación server-side.
 */
export function HistorialPage() {
  const [selectedAreaId, setSelectedAreaId] = useState<string>("all");
  const [selectedBodegaId, setSelectedBodegaId] = useState<string>("all");

  const {
    filtered,
    loading,
    pagination,
    computeBeforeAfter,
    prodName,
    prodUnit,
    productos,
    filtros,
  } = useHistorial({
    selectedBodegaId,
  });

  const handleExportCSV = () => {
    if (filtered.length === 0 || loading) return;

    downloadHistorialCSV(filtered, {
      computeBeforeAfter,
      prodName,
      prodUnit,
    });
  };

  return (
    <div className="relative min-h-screen" data-testid="historial-page">
      <div className="relative space-y-6 pb-10">
        {/* Cabecera visual canónica con animación de máquina de escribir y color cian #06b6d4 */}
        <SectionHeader
          title="Historial"
          subtitle="Auditoría y Trazabilidad de Inventario"
          icon={History}
          color="#06b6d4"
          center
        />

        {/* Toolbar unificado de gobernanza */}
        <HistorialToolbar
          selectedAreaId={selectedAreaId}
          onSelectArea={setSelectedAreaId}
          activeWarehouseId={selectedBodegaId}
          onSelectWarehouse={setSelectedBodegaId}
          onExportCSV={handleExportCSV}
          isExportDisabled={filtered.length === 0 || loading}
          recordsCount={filtered.length}
        />

        {/* Panel de filtros multi-criterio */}
        <FiltrosHistorial
          filtroProducto={filtros.filtroProducto}
          setFiltroProducto={filtros.setFiltroProducto}
          filtroTipo={filtros.filtroTipo}
          setFiltroTipo={filtros.setFiltroTipo}
          fechaDesde={filtros.fechaDesde}
          setFechaDesde={filtros.setFechaDesde}
          fechaHasta={filtros.fechaHasta}
          setFechaHasta={filtros.setFechaHasta}
          filtroUsuario={filtros.filtroUsuario}
          setFiltroUsuario={filtros.setFiltroUsuario}
          productos={productos}
          clearFilters={filtros.clearFilters}
        />

        {/* Contenido principal y tabla */}
        {loading ? (
          <div
            data-testid="historial-loading"
            className="py-12 text-center text-muted-foreground animate-pulse"
          >
            Cargando historial...
          </div>
        ) : (
          <div className="space-y-4" data-testid="historial-content">
            {/* Contenedor responsivo de la tabla de auditoría */}
            <div data-testid="historial-table-container">
              <TablaHistorial
                registros={filtered}
                loading={false}
                computeBeforeAfter={computeBeforeAfter}
                prodName={prodName}
                prodUnit={prodUnit}
              />
            </div>

            {/* Paginación server-side inferior */}
            <div
              data-testid="historial-pagination"
              className="flex flex-col md:flex-row items-center justify-between gap-4 pt-2"
            >
              <p
                data-testid="pagination-summary"
                className="text-xs text-muted-foreground"
              >
                Mostrando {filtered.length} registros en esta página (Total en base de datos: {pagination.total})
              </p>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  data-testid="pagination-prev"
                  className="h-9 px-4 rounded-xl border border-input bg-card text-foreground hover:bg-secondary disabled:opacity-50 disabled:cursor-not-allowed text-xs font-semibold cursor-pointer select-none touch-target min-h-[44px]"
                  onClick={() => pagination.setPage((p: number) => Math.max(1, p - 1))}
                  disabled={pagination.page === 1 || loading}
                >
                  Anterior
                </button>
                <span
                  data-testid="pagination-page-indicator"
                  className="text-sm font-medium"
                >
                  Página {pagination.page}
                </span>
                <button
                  type="button"
                  data-testid="pagination-next"
                  className="h-9 px-4 rounded-xl border border-input bg-card text-foreground hover:bg-secondary disabled:opacity-50 disabled:cursor-not-allowed text-xs font-semibold cursor-pointer select-none touch-target min-h-[44px]"
                  onClick={() => pagination.setPage((p: number) => p + 1)}
                  disabled={
                    pagination.page >= pagination.totalPages ||
                    loading
                  }
                >
                  Siguiente
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default HistorialPage;
