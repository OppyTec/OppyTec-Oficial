// oppytec-frontend/src/features/consumo/components/buffet/BuffetItemsTable.tsx
import { useState } from "react";
import {
  UtensilsCrossed,
  Plus,
  Minus,
  Trash2,
  RotateCcw,
  AlertTriangle,
  Layers,
} from "lucide-react";
import { cn } from "@/shared/lib/utils";
import type { BuffetSessionItem } from "../../types";

export interface BuffetItemsTableProps {
  items: BuffetSessionItem[];
  stage: string;
  onUpdateItemQuantity: (
    itemId: string,
    field: "cantidad_apertura" | "cantidad_reposiciones" | "cantidad_cierre",
    delta: number
  ) => void;
  onToggleAccionSobrante?: (itemId: string) => void;
  onRemoveItem?: (itemId: string) => void;
  onUpdateMotivoMerma?: (itemId: string, motivo: string) => void;
}

export const BUFFET_TABLE_GRID_LAYOUT =
  "grid grid-cols-[minmax(220px,2fr)_100px_100px_100px_120px_130px_80px] gap-3 items-center px-4 py-3";

export function BuffetItemsTable({
  items,
  stage: _stage,
  onUpdateItemQuantity,
  onToggleAccionSobrante,
  onRemoveItem,
  onUpdateMotivoMerma,
}: BuffetItemsTableProps) {
  if (items.length === 0) {
    return (
      <div
        data-testid="buffet-empty-items-state"
        className="border border-dashed border-border/70 rounded-2xl p-8 text-center bg-card/40 my-4"
      >
        <div className="mx-auto w-12 h-12 rounded-2xl bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center text-cyan-400 mb-3">
          <UtensilsCrossed className="w-6 h-6" />
        </div>
        <h4 className="text-sm font-bold text-foreground">Sin productos escaneados aún</h4>
        <p className="text-xs text-muted-foreground max-w-sm mx-auto mt-1">
          Utiliza el escáner visual con cámara para registrar las estaciones del buffet o agrega insumos al balance.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-2 my-4" data-testid="buffet-items-table">
      {/* HEADER DE TABLA (Desktop) */}
      <div
        className={cn(
          BUFFET_TABLE_GRID_LAYOUT,
          "bg-muted/50 rounded-xl border border-border/50 text-[11px] font-black uppercase tracking-wider text-muted-foreground select-none hidden md:grid"
        )}
      >
        <div>Producto / Receta</div>
        <div className="text-center">Apertura</div>
        <div className="text-center">Reposición</div>
        <div className="text-center">Cierre</div>
        <div className="text-center text-cyan-500">Consumo Neto</div>
        <div className="text-center">Destino Sobrante</div>
        <div className="text-right pr-2">Acción</div>
      </div>

      {/* FILAS DE PRODUCTOS */}
      <div className="space-y-2">
        {items.map((item) => (
          <BuffetItemRow
            key={item.id}
            item={item}
            onUpdateQuantity={onUpdateItemQuantity}
            onToggleAccion={onToggleAccionSobrante}
            onRemove={onRemoveItem}
            onUpdateMotivoMerma={onUpdateMotivoMerma}
          />
        ))}
      </div>
    </div>
  );
}

interface BuffetItemRowProps {
  item: BuffetSessionItem;
  onUpdateQuantity: (
    itemId: string,
    field: "cantidad_apertura" | "cantidad_reposiciones" | "cantidad_cierre",
    delta: number
  ) => void;
  onToggleAccion?: (itemId: string) => void;
  onRemove?: (itemId: string) => void;
  onUpdateMotivoMerma?: (itemId: string, motivo: string) => void;
}

function BuffetItemRow({
  item,
  onUpdateQuantity,
  onToggleAccion,
  onRemove,
  onUpdateMotivoMerma,
}: BuffetItemRowProps) {
  const [showMermaNotes, setShowMermaNotes] = useState(false);

  const apertura = Number(item.cantidad_apertura || 0);
  const reposiciones = Number(item.cantidad_reposiciones || 0);
  const cierre = Number(item.cantidad_cierre || 0);
  const totalPuesto = apertura + reposiciones;
  const consumoNeto = Math.max(0, Math.round((totalPuesto - cierre) * 10) / 10);
  const sobrante = cierre;

  const ratioConsumido = totalPuesto > 0 ? consumoNeto / totalPuesto : 0;
  const getSeverityBorder = () => {
    if (ratioConsumido >= 0.8) return "border-l-cyan-500";
    if (ratioConsumido >= 0.4) return "border-l-emerald-500";
    return "border-l-blue-500";
  };

  return (
    <div
      data-testid={`buffet-row-${item.id}`}
      className={cn(
        "rounded-2xl border border-border/60 bg-card hover:bg-muted/10 transition-all border-l-4 overflow-hidden shadow-xs",
        getSeverityBorder()
      )}
    >
      {/* DESKTOP ROW */}
      <div className={cn(BUFFET_TABLE_GRID_LAYOUT, "py-3 hidden md:grid")}>
        {/* COL 1: Info Producto / Receta */}
        <div className="flex items-center gap-3 min-w-0">
          <div className="w-10 h-10 rounded-xl bg-cyan-500/10 border border-cyan-500/20 shrink-0 flex items-center justify-center text-cyan-400">
            {item.item_type === "receta" ? (
              <UtensilsCrossed className="w-5 h-5" />
            ) : (
              <Layers className="w-5 h-5" />
            )}
          </div>
          <div className="min-w-0">
            <div className="flex items-center gap-1.5">
              <span className="text-[10px] font-bold uppercase px-1.5 py-0.5 rounded bg-muted text-muted-foreground border border-border">
                {item.item_type}
              </span>
              <span className="text-xs font-bold text-foreground truncate">
                {item.nombre}
              </span>
            </div>
            <div className="flex items-center gap-2 text-[11px] text-muted-foreground">
              <span>Unidad: {item.unidad}</span>
              {item.estacion_nombre && (
                <span className="text-cyan-400 font-semibold">• {item.estacion_nombre}</span>
              )}
            </div>
          </div>
        </div>

        {/* COL 2: Apertura */}
        <div className="flex items-center justify-center gap-1">
          <button
            type="button"
            onClick={() => onUpdateQuantity(item.id, "cantidad_apertura", -0.5)}
            data-testid={`btn-dec-apertura-${item.id}`}
            className="w-6 h-6 rounded-md bg-muted hover:bg-muted/80 text-foreground flex items-center justify-center cursor-pointer text-xs"
          >
            <Minus className="w-3 h-3" />
          </button>
          <span
            data-testid={`val-apertura-${item.id}`}
            className="w-10 text-center font-mono font-bold text-xs"
          >
            {apertura}
          </span>
          <button
            type="button"
            onClick={() => onUpdateQuantity(item.id, "cantidad_apertura", 0.5)}
            data-testid={`btn-inc-apertura-${item.id}`}
            className="w-6 h-6 rounded-md bg-muted hover:bg-muted/80 text-foreground flex items-center justify-center cursor-pointer text-xs"
          >
            <Plus className="w-3 h-3" />
          </button>
        </div>

        {/* COL 3: Reposición */}
        <div className="flex items-center justify-center gap-1">
          <button
            type="button"
            onClick={() => onUpdateQuantity(item.id, "cantidad_reposiciones", -0.5)}
            data-testid={`btn-dec-repos-${item.id}`}
            className="w-6 h-6 rounded-md bg-muted hover:bg-muted/80 text-foreground flex items-center justify-center cursor-pointer text-xs"
          >
            <Minus className="w-3 h-3" />
          </button>
          <span
            data-testid={`val-repos-${item.id}`}
            className="w-10 text-center font-mono font-bold text-xs text-amber-500"
          >
            {reposiciones}
          </span>
          <button
            type="button"
            onClick={() => onUpdateQuantity(item.id, "cantidad_reposiciones", 0.5)}
            data-testid={`btn-inc-repos-${item.id}`}
            className="w-6 h-6 rounded-md bg-muted hover:bg-muted/80 text-foreground flex items-center justify-center cursor-pointer text-xs"
          >
            <Plus className="w-3 h-3" />
          </button>
        </div>

        {/* COL 4: Cierre */}
        <div className="flex items-center justify-center gap-1">
          <button
            type="button"
            onClick={() => onUpdateQuantity(item.id, "cantidad_cierre", -0.5)}
            data-testid={`btn-dec-cierre-${item.id}`}
            className="w-6 h-6 rounded-md bg-muted hover:bg-muted/80 text-foreground flex items-center justify-center cursor-pointer text-xs"
          >
            <Minus className="w-3 h-3" />
          </button>
          <span
            data-testid={`val-cierre-${item.id}`}
            className="w-10 text-center font-mono font-bold text-xs text-slate-400"
          >
            {cierre}
          </span>
          <button
            type="button"
            onClick={() => onUpdateQuantity(item.id, "cantidad_cierre", 0.5)}
            data-testid={`btn-inc-cierre-${item.id}`}
            className="w-6 h-6 rounded-md bg-muted hover:bg-muted/80 text-foreground flex items-center justify-center cursor-pointer text-xs"
          >
            <Plus className="w-3 h-3" />
          </button>
        </div>

        {/* COL 5: Consumo Neto */}
        <div className="text-center font-mono font-black text-sm text-cyan-400" data-testid={`val-consumo-${item.id}`}>
          {consumoNeto} {item.unidad}
        </div>

        {/* COL 6: Destino Sobrante */}
        <div className="flex flex-col items-center gap-1">
          <button
            type="button"
            onClick={() => onToggleAccion?.(item.id)}
            data-testid={`btn-toggle-sobrante-${item.id}`}
            className={cn(
              "px-2.5 py-1 rounded-lg text-[10px] font-bold uppercase tracking-wider cursor-pointer border flex items-center gap-1 transition-colors",
              item.accion_sobrante === "retornar"
                ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/30 hover:bg-emerald-500/20"
                : "bg-rose-500/10 text-rose-400 border-rose-500/30 hover:bg-rose-500/20"
            )}
          >
            {item.accion_sobrante === "retornar" ? (
              <>
                <RotateCcw className="w-3 h-3" />
                Retornar ({sobrante})
              </>
            ) : (
              <>
                <AlertTriangle className="w-3 h-3" />
                Merma ({sobrante})
              </>
            )}
          </button>
          {item.accion_sobrante === "merma" && (
            <button
              type="button"
              onClick={() => setShowMermaNotes(!showMermaNotes)}
              className="text-[10px] text-muted-foreground underline hover:text-foreground"
            >
              {item.motivo_merma ? item.motivo_merma : "Motivo..."}
            </button>
          )}
        </div>

        {/* COL 7: Acciones */}
        <div className="flex items-center justify-end pr-2">
          {onRemove && (
            <button
              type="button"
              onClick={() => onRemove(item.id)}
              data-testid={`btn-remove-${item.id}`}
              className="w-7 h-7 rounded-lg bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 flex items-center justify-center cursor-pointer transition-colors"
              title="Eliminar del balance"
            >
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>

      {/* Input expandible de motivo de merma */}
      {showMermaNotes && item.accion_sobrante === "merma" && (
        <div className="px-4 py-2 bg-rose-950/20 border-t border-rose-900/30 flex items-center gap-3">
          <span className="text-xs font-semibold text-rose-300 shrink-0">Motivo de Merma:</span>
          <input
            type="text"
            value={item.motivo_merma || ""}
            onChange={(e) => onUpdateMotivoMerma?.(item.id, e.target.value)}
            placeholder="Ej. Tiempo prolongado en barra caliente, contaminación cruzada"
            data-testid={`input-motivo-merma-${item.id}`}
            className="flex-1 px-2.5 py-1 rounded-lg bg-background border border-rose-800/40 text-xs text-foreground focus:outline-none focus:border-rose-500"
          />
        </div>
      )}

      {/* MOBILE ROW */}
      <div className="p-3 md:hidden space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-[10px] font-bold uppercase px-1.5 py-0.5 rounded bg-muted text-muted-foreground border">
              {item.item_type}
            </span>
            <span className="text-xs font-bold text-foreground">{item.nombre}</span>
          </div>
          {onRemove && (
            <button
              type="button"
              onClick={() => onRemove(item.id)}
              className="text-rose-400 hover:text-rose-300 p-1"
            >
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          )}
        </div>

        <div className="grid grid-cols-3 gap-2 text-center text-xs">
          <div className="p-2 rounded-xl bg-muted/40">
            <span className="text-[10px] text-muted-foreground uppercase block">Apertura</span>
            <span className="font-mono font-bold">{apertura}</span>
          </div>
          <div className="p-2 rounded-xl bg-amber-500/10 text-amber-500">
            <span className="text-[10px] text-muted-foreground uppercase block">Reposición</span>
            <span className="font-mono font-bold">{reposiciones}</span>
          </div>
          <div className="p-2 rounded-xl bg-cyan-500/10 text-cyan-400">
            <span className="text-[10px] text-muted-foreground uppercase block">Consumo</span>
            <span className="font-mono font-bold">{consumoNeto}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
