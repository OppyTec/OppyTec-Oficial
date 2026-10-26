// oppytec-frontend/src/features/historial/FiltrosHistorial.tsx
import { useMemo } from "react";
import {
  Calendar,
  ChevronDown,
  FilterX,
  ListFilter,
  Package,
  Search,
  X,
} from "lucide-react";
import { cn } from "@/shared/lib";
import type { TipoMovimiento, HistorialCatalogProduct } from "./types";

/**
 * Catálogo canónico de tipos de movimiento para el filtro de Historial.
 */
export const TIPOS_MOVIMIENTO: ReadonlyArray<{
  value: TipoMovimiento;
  label: string;
}> = [
  { value: "all", label: "Todos" },
  { value: "conteo", label: "Conteo" },
  { value: "consumo", label: "Consumo" },
  { value: "merma", label: "Merma" },
  { value: "ajuste", label: "Ajuste" },
  { value: "transferencia", label: "Transferencia" },
  { value: "compra", label: "Compra" },
  { value: "entrada", label: "Entrada" },
  { value: "salida", label: "Salida" },
  { value: "reversion", label: "Reversión" },
  { value: "redo", label: "Rehacer" },
  { value: "ajuste_auditoria", label: "Ajuste Auditoría" },
];

/**
 * Formatea una fecha en notación chilena y latinoamericana estándar: dd/MM/yyyy.
 */
export function formatChileDate(date: Date | undefined): string {
  if (!date || isNaN(date.getTime())) return "";
  const day = String(date.getDate()).padStart(2, "0");
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const year = date.getFullYear();
  return `${day}/${month}/${year}`;
}

/**
 * Convierte un objeto Date a string ISO 'YYYY-MM-DD' para enlace seguro con input type="date".
 */
export function toDateInputValue(date: Date | undefined): string {
  if (!date || isNaN(date.getTime())) return "";
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

/**
 * Parsea un string 'YYYY-MM-DD' creando una instancia Date local para evitar desfases de huso horario UTC.
 */
export function parseLocalDate(val: string): Date | undefined {
  if (!val) return undefined;
  const parts = val.split("-").map(Number);
  if (parts.length === 3 && parts[0] && parts[1] && parts[2]) {
    return new Date(parts[0], parts[1] - 1, parts[2]);
  }
  const parsed = new Date(val);
  return isNaN(parsed.getTime()) ? undefined : parsed;
}

export interface FiltrosHistorialProps {
  readonly filtroProducto: string;
  readonly setFiltroProducto: (v: string) => void;
  readonly filtroTipo: TipoMovimiento;
  readonly setFiltroTipo: (v: TipoMovimiento) => void;
  readonly fechaDesde: Date | undefined;
  readonly setFechaDesde: (v: Date | undefined) => void;
  readonly fechaHasta: Date | undefined;
  readonly setFechaHasta: (v: Date | undefined) => void;
  readonly filtroUsuario?: string;
  readonly setFiltroUsuario?: (v: string | ((prev: string) => string)) => void;
  readonly productos: HistorialCatalogProduct[];
  readonly clearFilters?: () => void;
  readonly className?: string;
}

/**
 * Componente de Filtros Multi-Criterio de Historial y Auditoría de Inventario (Fase 5).
 * - Búsqueda predictiva por usuario con debounce y botón X de limpieza rápida.
 * - Selector de Producto ordenado alfabéticamente con sincronización URL.
 * - Selector de Tipo de Movimiento normalizado.
 * - Selectores de Rango de Fechas ("Desde" y "Hasta") formateados en dd/MM/yyyy.
 * - Botón "Limpiar filtros" visible condicionalmente para restablecimiento instantáneo.
 */
export function FiltrosHistorial({
  filtroProducto,
  setFiltroProducto,
  filtroTipo,
  setFiltroTipo,
  fechaDesde,
  setFechaDesde,
  fechaHasta,
  setFechaHasta,
  filtroUsuario = "",
  setFiltroUsuario,
  productos,
  clearFilters,
  className,
}: FiltrosHistorialProps) {
  // Ordenamiento alfabético de productos por nombre (case-insensitive)
  const productosOrdenados = useMemo(() => {
    return [...productos].sort((a, b) =>
      a.nombre.localeCompare(b.nombre, "es", { sensitivity: "base" })
    );
  }, [productos]);

  // Indicador de filtros activos
  const hasFilters = Boolean(
    filtroProducto !== "all" ||
      filtroTipo !== "all" ||
      fechaDesde !== undefined ||
      fechaHasta !== undefined ||
      (filtroUsuario && filtroUsuario.trim() !== "")
  );

  const handleClear = () => {
    if (clearFilters) {
      clearFilters();
    } else {
      setFiltroProducto("all");
      setFiltroTipo("all");
      setFechaDesde(undefined);
      setFechaHasta(undefined);
      setFiltroUsuario?.("");
    }
  };

  return (
    <div
      data-testid="filtros-historial"
      className={cn(
        "flex flex-col gap-2.5 sm:flex-row sm:flex-wrap items-stretch sm:items-center",
        className
      )}
    >
      {/* 1. Búsqueda Predictiva por Usuario con Botón X */}
      <div className="relative w-full sm:w-48">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
        <input
          type="text"
          aria-label="Buscar por usuario"
          data-testid="filtro-usuario-input"
          placeholder="Buscar por usuario..."
          value={filtroUsuario}
          onChange={(e) => setFiltroUsuario?.(e.target.value)}
          className="w-full h-11 pl-9 pr-8 rounded-xl border border-input bg-card text-xs font-medium text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-cyan-500 shadow-sm transition-all touch-target min-h-[44px]"
        />
        {filtroUsuario ? (
          <button
            type="button"
            onClick={() => setFiltroUsuario?.("")}
            className="absolute right-2.5 top-1/2 -translate-y-1/2 p-1 rounded-full text-muted-foreground hover:text-foreground hover:bg-muted/50 transition-colors cursor-pointer touch-target flex items-center justify-center"
            title="Limpiar búsqueda"
            aria-label="Limpiar búsqueda"
            data-testid="filtro-usuario-clear"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        ) : null}
      </div>

      {/* 2. Selector de Producto (Alfabético + Todos) */}
      <div className="relative inline-flex items-center w-full sm:w-52">
        <Package className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-cyan-500 pointer-events-none shrink-0" />
        <select
          aria-label="Filtrar por producto"
          data-testid="filtro-producto-select"
          value={filtroProducto}
          onChange={(e) => setFiltroProducto(e.target.value)}
          className="w-full h-11 pl-9 pr-8 rounded-xl border border-input bg-card text-xs font-semibold text-foreground focus:outline-none focus:ring-1 focus:ring-cyan-500 shadow-sm appearance-none cursor-pointer touch-target min-h-[44px]"
        >
          <option value="all">Todos los productos</option>
          {productosOrdenados.map((p) => (
            <option key={p.id} value={String(p.id)}>
              {p.nombre} {p.unidad ? `(${p.unidad})` : ""}
            </option>
          ))}
        </select>
        <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
      </div>

      {/* 3. Selector de Tipo de Movimiento */}
      <div className="relative inline-flex items-center w-full sm:w-40">
        <ListFilter className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-cyan-500 pointer-events-none shrink-0" />
        <select
          aria-label="Filtrar por tipo"
          data-testid="filtro-tipo-select"
          value={filtroTipo}
          onChange={(e) => setFiltroTipo(e.target.value as TipoMovimiento)}
          className="w-full h-11 pl-9 pr-8 rounded-xl border border-input bg-card text-xs font-semibold text-foreground focus:outline-none focus:ring-1 focus:ring-cyan-500 shadow-sm appearance-none cursor-pointer touch-target min-h-[44px]"
        >
          {TIPOS_MOVIMIENTO.map((t) => (
            <option key={t.value} value={t.value}>
              {t.label}
            </option>
          ))}
        </select>
        <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
      </div>

      {/* 4. Selector de Rango de Fechas: Desde */}
      <div className="relative inline-flex items-center w-full sm:w-40">
        <div
          data-testid="fecha-desde-display"
          className={cn(
            "flex items-center gap-2 w-full h-11 px-3 rounded-xl border border-input bg-card text-xs font-semibold shadow-sm pointer-events-none select-none transition-colors",
            !fechaDesde ? "text-muted-foreground" : "text-foreground"
          )}
        >
          <Calendar className="h-4 w-4 text-cyan-500 shrink-0" />
          <span className="truncate">
            {fechaDesde ? formatChileDate(fechaDesde) : "Desde"}
          </span>
        </div>
        <input
          type="date"
          aria-label="Desde"
          data-testid="filtro-fecha-desde"
          value={toDateInputValue(fechaDesde)}
          onChange={(e) => {
            setFechaDesde(parseLocalDate(e.target.value));
          }}
          className="absolute inset-0 opacity-0 cursor-pointer w-full h-full min-h-[44px]"
        />
        {fechaDesde ? (
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              setFechaDesde(undefined);
            }}
            className="absolute right-2 top-1/2 -translate-y-1/2 p-1 rounded-full text-muted-foreground hover:text-foreground hover:bg-muted/50 transition-colors z-10 cursor-pointer"
            title="Limpiar fecha desde"
            aria-label="Limpiar fecha desde"
          >
            <X className="h-3 w-3" />
          </button>
        ) : null}
      </div>

      {/* 5. Selector de Rango de Fechas: Hasta */}
      <div className="relative inline-flex items-center w-full sm:w-40">
        <div
          data-testid="fecha-hasta-display"
          className={cn(
            "flex items-center gap-2 w-full h-11 px-3 rounded-xl border border-input bg-card text-xs font-semibold shadow-sm pointer-events-none select-none transition-colors",
            !fechaHasta ? "text-muted-foreground" : "text-foreground"
          )}
        >
          <Calendar className="h-4 w-4 text-cyan-500 shrink-0" />
          <span className="truncate">
            {fechaHasta ? formatChileDate(fechaHasta) : "Hasta"}
          </span>
        </div>
        <input
          type="date"
          aria-label="Hasta"
          data-testid="filtro-fecha-hasta"
          value={toDateInputValue(fechaHasta)}
          onChange={(e) => {
            setFechaHasta(parseLocalDate(e.target.value));
          }}
          className="absolute inset-0 opacity-0 cursor-pointer w-full h-full min-h-[44px]"
        />
        {fechaHasta ? (
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              setFechaHasta(undefined);
            }}
            className="absolute right-2 top-1/2 -translate-y-1/2 p-1 rounded-full text-muted-foreground hover:text-foreground hover:bg-muted/50 transition-colors z-10 cursor-pointer"
            title="Limpiar fecha hasta"
            aria-label="Limpiar fecha hasta"
          >
            <X className="h-3 w-3" />
          </button>
        ) : null}
      </div>

      {/* 6. Botón de Limpieza Global de Filtros (Visible si hasFilters) */}
      {hasFilters && (
        <button
          type="button"
          onClick={handleClear}
          data-testid="btn-limpiar-filtros"
          className="h-11 px-4 rounded-xl border border-transparent hover:border-border text-xs font-bold text-muted-foreground hover:text-foreground bg-muted/30 hover:bg-muted/70 transition-all inline-flex items-center gap-2 cursor-pointer active:scale-95 touch-target min-h-[44px]"
          aria-label="Limpiar filtros"
        >
          <FilterX className="h-4 w-4 text-cyan-500 shrink-0" />
          <span>Limpiar filtros</span>
        </button>
      )}
    </div>
  );
}

export default FiltrosHistorial;
