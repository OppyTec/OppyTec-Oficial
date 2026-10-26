import {
  Clock,
  Inbox,
  LayoutGrid,
  Rows,
  Search,
  SlidersHorizontal,
  X,
} from "lucide-react";
import { AreaSelector, BodegaSelector } from "@/shared/components/layout";
import { cn } from "@/shared/lib";
import type { MainViewType } from "../types";

export interface NotificationsToolbarProps {
  readonly searchTerm: string;
  readonly onSearchChange: (value: string) => void;
  readonly onClearSearch?: () => void;
  readonly selectedAreaId: string;
  readonly onSelectArea: (areaId: string) => void;
  readonly selectedBodegaId: string;
  readonly onSelectWarehouse: (bodegaId: string) => void;
  readonly viewLayout: "cards" | "compact";
  readonly onViewLayoutChange: (layout: "cards" | "compact") => void;
  readonly mainView: MainViewType;
  readonly onMainViewChange: (view: MainViewType) => void;
  readonly pendingCount?: number;
  readonly historyCount?: number;
  readonly className?: string;
}

export function NotificationsToolbar({
  searchTerm,
  onSearchChange,
  onClearSearch,
  selectedAreaId,
  onSelectArea,
  selectedBodegaId,
  onSelectWarehouse,
  viewLayout,
  onViewLayoutChange,
  mainView,
  onMainViewChange,
  pendingCount = 0,
  historyCount = 0,
  className,
}: NotificationsToolbarProps) {
  return (
    <div
      data-testid="notifications-toolbar"
      className={cn(
        "bg-card backdrop-blur-md p-3 sm:p-4 rounded-2xl border border-input shadow-xl space-y-3 relative z-40",
        className
      )}
    >
      {/* Fila Superior: Selectores + Switcher Layout + Vistas Principales */}
      <div className="flex flex-col xl:flex-row items-center justify-between gap-3 w-full">
        {/* Columna Izquierda: Selectores de Área Operativa y Bodega */}
        <div className="w-full xl:w-auto flex flex-wrap items-center justify-start gap-2">
          <AreaSelector
            allowAll
            selectedAreaId={selectedAreaId}
            onSelectArea={onSelectArea}
            className="w-full sm:w-auto"
            buttonClassName="h-10 rounded-xl bg-background border-input shadow-sm text-[9px] min-w-0 w-full sm:min-w-[160px]"
          />
          <BodegaSelector
            allowAll
            activeWarehouseId={selectedBodegaId}
            onSelectWarehouse={onSelectWarehouse}
            className="w-full sm:w-auto min-w-[160px] h-10 rounded-xl bg-background border-input shadow-sm text-[9px]"
          />
        </div>

        {/* Columna Derecha: Switcher Layout (Cards vs Compact) + Vistas Principales (Bandeja / Historial / Configuración) */}
        <div className="flex flex-wrap items-center justify-end gap-2 w-full xl:w-auto shrink-0">
          {/* Switcher Cards vs Compact */}
          <button
            type="button"
            data-testid="toggle-view-layout"
            onClick={() =>
              onViewLayoutChange(viewLayout === "cards" ? "compact" : "cards")
            }
            title={
              viewLayout === "cards"
                ? "Cambiar a vista compacta (Tabla)"
                : "Cambiar a vista de tarjetas"
            }
            className="h-10 w-10 inline-flex items-center justify-center rounded-xl border border-input bg-background hover:bg-muted text-muted-foreground transition-all cursor-pointer shadow-sm shrink-0"
          >
            {viewLayout === "cards" ? (
              <Rows className="h-4 w-4" />
            ) : (
              <LayoutGrid className="h-4 w-4" />
            )}
          </button>

          {/* Bandeja de Entrada Button */}
          <button
            type="button"
            data-testid="mainview-bandeja"
            onClick={() => onMainViewChange("bandeja")}
            className={cn(
              "h-10 px-3.5 gap-1.5 inline-flex items-center justify-center rounded-xl transition-all active:scale-95 text-[9px] font-black uppercase tracking-wider shrink-0 cursor-pointer select-none border",
              mainView === "bandeja"
                ? "bg-amber-500 text-black border-amber-500 shadow-md shadow-amber-500/20"
                : "border-input bg-background hover:bg-muted text-muted-foreground hover:text-foreground"
            )}
          >
            <Inbox className="h-3.5 w-3.5" />
            <span>Bandeja</span>
            {pendingCount > 0 && (
              <span
                data-testid="badge-toolbar-pending"
                className={cn(
                  "ml-1 px-1.5 py-0.5 rounded-full text-[8px] font-black",
                  mainView === "bandeja"
                    ? "bg-black text-amber-400"
                    : "bg-amber-500 text-black"
                )}
              >
                {pendingCount}
              </span>
            )}
          </button>

          {/* Historial Button */}
          <button
            type="button"
            data-testid="mainview-historial"
            onClick={() => onMainViewChange("historial")}
            className={cn(
              "h-10 px-3.5 gap-1.5 inline-flex items-center justify-center rounded-xl transition-all active:scale-95 text-[9px] font-black uppercase tracking-wider shrink-0 cursor-pointer select-none border",
              mainView === "historial"
                ? "bg-primary text-primary-foreground border-primary shadow-md shadow-primary/20"
                : "border-input bg-background hover:bg-muted text-muted-foreground hover:text-foreground"
            )}
          >
            <Clock className="h-3.5 w-3.5" />
            <span>Historial</span>
            {historyCount > 0 && (
              <span
                data-testid="badge-toolbar-history"
                className="ml-1 px-1.5 py-0.5 rounded-full bg-primary/20 text-primary text-[8px] font-bold"
              >
                {historyCount}
              </span>
            )}
          </button>

          {/* Configuración Button */}
          <button
            type="button"
            data-testid="mainview-configuracion"
            onClick={() => onMainViewChange("configuracion")}
            className={cn(
              "h-10 px-3.5 gap-1.5 inline-flex items-center justify-center rounded-xl transition-all active:scale-95 text-[9px] font-black uppercase tracking-wider shrink-0 cursor-pointer select-none border",
              mainView === "configuracion"
                ? "bg-amber-600 hover:bg-amber-500 text-white border-amber-600 shadow-md shadow-amber-600/20"
                : "border-input bg-background hover:bg-muted text-muted-foreground hover:text-foreground"
            )}
          >
            <SlidersHorizontal className="h-3.5 w-3.5" />
            <span>Configuración</span>
          </button>
        </div>
      </div>

      {/* Fila Inferior: Buscador en tiempo real (solo visible cuando no está en configuración) */}
      {mainView !== "configuracion" && (
        <div className="relative group w-full">
          <div className="absolute left-3.5 top-1/2 -translate-y-1/2 p-1 rounded-lg bg-amber-500/10 transition-colors group-focus-within:bg-amber-500/20">
            <Search className="h-4 w-4 text-amber-500" />
          </div>
          <input
            type="text"
            data-testid="notifications-search-input"
            placeholder="Buscar notificaciones por producto, usuario, área, motivo o descripción..."
            value={searchTerm}
            onChange={(e) => onSearchChange(e.target.value)}
            className="w-full pl-11 pr-10 h-11 bg-card/60 backdrop-blur-md border border-input shadow-md focus-within:shadow-[0_0_16px_rgba(245,158,11,0.15)] focus:border-amber-500/50 rounded-2xl text-sm font-medium transition-all text-foreground placeholder:text-muted-foreground focus:outline-none"
          />
          {searchTerm.trim() !== "" && (
            <button
              type="button"
              data-testid="clear-search-button"
              onClick={onClearSearch ?? (() => onSearchChange(""))}
              className="absolute right-3.5 top-1/2 -translate-y-1/2 p-1 rounded-full text-muted-foreground hover:text-foreground hover:bg-muted/50 transition-colors cursor-pointer"
              title="Limpiar búsqueda"
            >
              <X className="h-4 w-4" />
            </button>
          )}
        </div>
      )}
    </div>
  );
}

export default NotificationsToolbar;
