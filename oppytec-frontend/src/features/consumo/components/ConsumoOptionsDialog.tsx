// oppytec-frontend/src/features/consumo/components/ConsumoOptionsDialog.tsx
import { useState, useEffect, useMemo } from "react";
import {
  ListPlus,
  CheckCircle2,
  AlertTriangle,
  Minus,
  Plus,
  X,
  CookingPot,
  Layers,
} from "lucide-react";
import { formatMoney, cn } from "@/shared/lib/utils";
import type {
  OptionSelection,
  RecetaConsumo,
  ComboConsumo,
  ProductoConsumo,
} from "../types";

export interface ConsumoOptionGroupOption {
  id: string;
  item_id: string;
  type: "producto" | "receta";
  nombre: string;
  precio_adicional?: number;
  disponible?: number;
}

export interface ConsumoOptionGroup {
  id: string;
  nombre: string;
  seleccion_minima: number;
  seleccion_maxima: number;
  opciones: ConsumoOptionGroupOption[];
}

export interface ConsumoOptionsDialogProps {
  readonly open: boolean;
  readonly onOpenChange: (open: boolean) => void;
  readonly item: RecetaConsumo | ComboConsumo | null;
  readonly type: "receta" | "combo";
  readonly gruposOpciones?: ConsumoOptionGroup[];
  readonly productos?: ProductoConsumo[];
  readonly recetas?: RecetaConsumo[];
  readonly getStock?: (productId: string) => number;
  readonly onConfirm: (selections: OptionSelection[]) => void;
}

export function ConsumoOptionsDialog({
  open,
  onOpenChange,
  item,
  type,
  gruposOpciones = [],
  productos: _productos = [],
  recetas: _recetas = [],
  getStock: _getStock,
  onConfirm,
}: ConsumoOptionsDialogProps) {
  // Estado local de selecciones: Record<grupo_id, Array<{ id, type, quantity, nombre, precio_adicional }>>
  const [selections, setSelections] = useState<
    Record<
      string,
      Array<{
        id: string;
        type: "producto" | "receta";
        quantity: number;
        nombre: string;
        precio_adicional: number;
      }>
    >
  >({});

  // Reset al abrir
  useEffect(() => {
    if (open) {
      setSelections({});
    }
  }, [open, item]);

  // Resolver los grupos requeridos por el ítem
  const activeGroups = useMemo(() => {
    if (!item) return [];

    // Extraer IDs de grupos definidos en ingredientes (receta) o items (combo)
    const groupIds: string[] = [];
    if (type === "receta") {
      const rec = item as RecetaConsumo;
      rec.ingredientes?.forEach((ing) => {
        if (ing.grupo_opciones_id) groupIds.push(ing.grupo_opciones_id);
      });
    } else {
      const combo = item as ComboConsumo;
      combo.items?.forEach((it) => {
        if (it.grupo_opciones_id) groupIds.push(it.grupo_opciones_id);
      });
    }

    if (groupIds.length === 0 && gruposOpciones.length > 0) {
      return gruposOpciones;
    }

    return groupIds
      .map((gId) => gruposOpciones.find((g) => g.id === gId))
      .filter((g): g is ConsumoOptionGroup => !!g);
  }, [item, type, gruposOpciones]);

  if (!open || !item) return null;

  const handleUpdateOption = (
    groupId: string,
    option: ConsumoOptionGroupOption,
    delta: number
  ) => {
    setSelections((prev) => {
      const currentList = prev[groupId] ? [...prev[groupId]] : [];
      const existingIdx = currentList.findIndex((opt) => opt.id === option.id);
      const groupConfig = activeGroups.find((g) => g.id === groupId);
      const maxAllowed = groupConfig?.seleccion_maxima || 999;

      const currentTotalInGroup = currentList.reduce(
        (sum, opt) => sum + opt.quantity,
        0
      );

      if (delta > 0 && currentTotalInGroup >= maxAllowed) {
        return prev; // No exceder el máximo configurado
      }

      if (existingIdx >= 0) {
        const itemInList = currentList[existingIdx];
        if (!itemInList) return prev;
        const nextQty = itemInList.quantity + delta;
        if (nextQty <= 0) {
          currentList.splice(existingIdx, 1);
        } else {
          currentList[existingIdx] = {
            id: itemInList.id,
            type: itemInList.type,
            quantity: nextQty,
            nombre: itemInList.nombre,
            precio_adicional: itemInList.precio_adicional,
          };
        }
      } else if (delta > 0) {
        currentList.push({
          id: option.id,
          type: option.type,
          quantity: 1,
          nombre: option.nombre,
          precio_adicional: option.precio_adicional || 0,
        });
      }

      return {
        ...prev,
        [groupId]: currentList,
      };
    });
  };

  // Validar si todos los grupos cumplen el mínimo requerido
  const isValid = activeGroups.every((grp) => {
    const list = selections[grp.id] || [];
    const count = list.reduce((sum, item) => sum + item.quantity, 0);
    return count >= grp.seleccion_minima && count <= grp.seleccion_maxima;
  });

  const handleConfirm = () => {
    if (!isValid) return;

    const flattened: OptionSelection[] = [];
    Object.entries(selections).forEach(([groupId, itemsList]) => {
      itemsList.forEach((it) => {
        flattened.push({
          grupo_id: groupId,
          producto_id: it.type === "producto" ? it.id : null,
          receta_id: it.type === "receta" ? it.id : null,
          cantidad: it.quantity,
          nombre: it.nombre,
          precio_adicional: it.precio_adicional,
        });
      });
    });

    onConfirm(flattened);
    onOpenChange(false);
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      data-testid="consumo-options-dialog"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-in fade-in duration-200"
    >
      <div className="w-full max-w-lg rounded-3xl bg-card border border-border shadow-2xl flex flex-col max-h-[85vh] overflow-hidden">
        {/* Cabecera */}
        <div className="p-4 border-b border-border flex items-center justify-between bg-muted/30 shrink-0">
          <div className="flex items-center gap-2.5">
            <div
              className={cn(
                "h-10 w-10 rounded-2xl flex items-center justify-center border",
                type === "receta"
                  ? "bg-purple-600/15 text-purple-600 border-purple-600/30"
                  : "bg-[#1c4c96]/15 text-[#1c4c96] border-[#1c4c96]/30"
              )}
            >
              {type === "receta" ? (
                <CookingPot className="h-5 w-5" />
              ) : (
                <Layers className="h-5 w-5" />
              )}
            </div>
            <div>
              <h3 className="text-sm font-black uppercase tracking-wider text-foreground">
                Personalizar {type === "receta" ? "Receta" : "Combo"}
              </h3>
              <p className="text-xs text-muted-foreground">{item.nombre}</p>
            </div>
          </div>

          <button
            type="button"
            data-testid="options-cancel-btn"
            onClick={() => onOpenChange(false)}
            className="p-1.5 rounded-xl text-muted-foreground hover:text-foreground hover:bg-muted cursor-pointer"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Cuerpo con grupos de opciones */}
        <div className="flex-1 overflow-y-auto p-4 space-y-5 custom-scrollbar">
          {activeGroups.length === 0 ? (
            <div className="text-center py-12 space-y-2 text-muted-foreground">
              <ListPlus className="h-10 w-10 mx-auto opacity-50" />
              <p className="text-xs font-bold uppercase tracking-wider">
                Sin opciones configuradas
              </p>
            </div>
          ) : (
            activeGroups.map((group) => {
              const currentList = selections[group.id] || [];
              const currentCount = currentList.reduce(
                (sum, it) => sum + it.quantity,
                0
              );
              const isGroupSatisfied =
                currentCount >= group.seleccion_minima &&
                currentCount <= group.seleccion_maxima;

              return (
                <div
                  key={group.id}
                  data-testid={`options-group-${group.id}`}
                  className="rounded-2xl border border-border bg-muted/20 p-4 space-y-3"
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <h4 className="text-xs font-black uppercase tracking-wider text-foreground">
                        {group.nombre}
                      </h4>
                      <p className="text-[10px] text-muted-foreground">
                        {group.seleccion_minima === group.seleccion_maxima
                          ? `Selecciona exactamente ${group.seleccion_minima}`
                          : `Selecciona entre ${group.seleccion_minima} y ${group.seleccion_maxima}`}
                      </p>
                    </div>

                    <span
                      className={cn(
                        "text-[10px] font-black px-2.5 py-0.5 rounded-full border",
                        isGroupSatisfied
                          ? "bg-emerald-500/10 text-emerald-500 border-emerald-500/30"
                          : "bg-destructive/10 text-destructive border-destructive/30"
                      )}
                    >
                      {currentCount} / {group.seleccion_maxima}
                    </span>
                  </div>

                  {/* Lista de alternativas del grupo */}
                  <div className="space-y-1.5 pt-1">
                    {group.opciones.map((opt) => {
                      const selectedItem = currentList.find(
                        (it) => it.id === opt.id
                      );
                      const qty = selectedItem?.quantity || 0;

                      return (
                        <div
                          key={opt.id}
                          data-testid={`option-item-${opt.id}`}
                          className={cn(
                            "flex items-center justify-between p-2.5 rounded-xl border transition-all",
                            qty > 0
                              ? "bg-primary/5 border-primary/40 shadow-sm"
                              : "bg-card border-border hover:border-border/80"
                          )}
                        >
                          <div className="min-w-0 pr-2">
                            <p className="text-xs font-bold text-foreground truncate">
                              {opt.nombre}
                            </p>
                            {opt.precio_adicional ? (
                              <p className="text-[10px] font-bold text-primary">
                                +{formatMoney(opt.precio_adicional)}
                              </p>
                            ) : null}
                          </div>

                          <div className="flex items-center gap-1.5 shrink-0">
                            <button
                              type="button"
                              data-testid={`option-minus-${opt.id}`}
                              disabled={qty === 0}
                              onClick={() =>
                                handleUpdateOption(group.id, opt, -1)
                              }
                              className="h-7 w-7 rounded-lg flex items-center justify-center bg-muted text-foreground hover:bg-muted/80 disabled:opacity-30 disabled:cursor-not-allowed cursor-pointer transition-colors"
                            >
                              <Minus className="h-3 w-3" />
                            </button>

                            <span
                              data-testid={`option-qty-${opt.id}`}
                              className="w-6 text-center text-xs font-black text-foreground"
                            >
                              {qty}
                            </span>

                            <button
                              type="button"
                              data-testid={`option-plus-${opt.id}`}
                              disabled={currentCount >= group.seleccion_maxima}
                              onClick={() =>
                                handleUpdateOption(group.id, opt, 1)
                              }
                              className="h-7 w-7 rounded-lg flex items-center justify-center bg-muted text-foreground hover:bg-muted/80 disabled:opacity-30 disabled:cursor-not-allowed cursor-pointer transition-colors"
                            >
                              <Plus className="h-3 w-3" />
                            </button>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* Footer con Confirmación */}
        <div className="p-4 border-t border-border bg-muted/20 flex items-center justify-between gap-3 shrink-0">
          <div className="text-xs">
            {!isValid ? (
              <span className="flex items-center gap-1.5 text-destructive font-bold">
                <AlertTriangle className="h-4 w-4 shrink-0" />
                <span>Completa los requisitos mínimos</span>
              </span>
            ) : (
              <span className="flex items-center gap-1.5 text-emerald-500 font-bold">
                <CheckCircle2 className="h-4 w-4 shrink-0" />
                <span>Listo para agregar al carrito</span>
              </span>
            )}
          </div>

          <button
            type="button"
            data-testid="options-confirm-btn"
            disabled={!isValid}
            onClick={handleConfirm}
            className="px-5 py-2.5 rounded-xl bg-primary text-primary-foreground text-xs font-black uppercase tracking-wider shadow-md hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed transition-all cursor-pointer"
          >
            Confirmar y Agregar
          </button>
        </div>
      </div>
    </div>
  );
}

export default ConsumoOptionsDialog;
