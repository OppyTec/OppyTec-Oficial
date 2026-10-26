// oppytec-frontend/src/features/consumo/components/ConsumoCart.tsx
import { useState } from "react";
import { useTranslation } from "react-i18next";
import {
  Trash2,
  ShoppingCart,
  X,
  CookingPot,
  Package,
  Minus,
  Plus,
  Layers,
  ChevronDown,
  Check,
  Calendar,
  Loader2,
} from "lucide-react";
import { cn, formatMoney } from "@/shared/lib/utils";
import { useCurrencyFormatter } from "@/shared/currency";
import type {
  CartItem,
  RecetaConsumo,
  ComboConsumo,
  ProductoConsumo,
  LotInfo,
} from "../types";

export interface ConsumoCartProps {
  readonly open: boolean;
  readonly onOpenChange: (open: boolean) => void;
  readonly cart: CartItem[];
  readonly allRecetas?: RecetaConsumo[];
  readonly combos?: ComboConsumo[];
  readonly productos?: ProductoConsumo[];
  readonly saving?: boolean;
  readonly lotsByProduct?: Record<string, LotInfo[]>;
  readonly onUpdateQty: (cartItemId: string, qty: number) => void;
  readonly onRemove: (cartItemId: string) => void;
  readonly onClearCart: () => void;
  readonly onSubmit: () => Promise<void> | void;
  readonly getStock: (id: string) => number;
  readonly onUpdateLot?: (cartItemId: string, lot: string | null) => void;
  readonly onUpdateIngredientLot?: (
    cartItemId: string,
    productoId: string,
    fechaVencimiento: string | null
  ) => void;
}

function formatLotLabel(fecha: string | null | undefined): string {
  if (!fecha) return "Sin fecha";
  const d = new Date(fecha + "T00:00:00");
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const diffDays = Math.ceil((d.getTime() - today.getTime()) / (1000 * 3600 * 24));
  const dateStr = d.toLocaleDateString("es-CL", {
    day: "2-digit",
    month: "short",
    year: "2-digit",
  });
  if (diffDays < 0) return `${dateStr} ⚠ Vencido`;
  if (diffDays === 0) return `${dateStr} · Vence hoy`;
  if (diffDays <= 7) return `${dateStr} · ${diffDays}d`;
  return dateStr;
}

function getLotColor(fecha: string | null | undefined): string {
  if (!fecha) return "text-muted-foreground";
  const d = new Date(fecha + "T00:00:00");
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const diffDays = Math.ceil((d.getTime() - today.getTime()) / (1000 * 3600 * 24));
  if (diffDays < 0) return "text-destructive font-black";
  if (diffDays <= 7) return "text-orange-500 font-bold";
  return "text-emerald-500 font-medium";
}

// ─── Selector de Lote para Producto Suelto ───────────────────────────────────
function ProductLotSelector({
  item,
  lots,
  onSelectLot,
}: {
  readonly item: CartItem;
  readonly lots: LotInfo[];
  readonly onSelectLot: (lot: string | null) => void;
}) {
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const selectedLot = item.selectedLot;

  if (lots.length <= 1) return null;

  return (
    <div className="relative inline-block mt-1">
      <button
        type="button"
        data-testid={`cart-lot-trigger-${item.cartItemId}`}
        onClick={() => setDropdownOpen(!dropdownOpen)}
        className="flex items-center gap-1 text-[10px] font-bold uppercase tracking-wider text-muted-foreground hover:text-foreground bg-muted/60 hover:bg-muted px-2 py-1 rounded-lg border border-border transition-colors cursor-pointer"
      >
        <Calendar className="h-3 w-3 text-primary shrink-0" />
        <span>
          {selectedLot ? `Lote: ${formatLotLabel(selectedLot)}` : "FIFO automático"}
        </span>
        <ChevronDown className="h-3 w-3 opacity-60" />
      </button>

      {dropdownOpen && (
        <div
          data-testid={`cart-lot-dropdown-${item.cartItemId}`}
          className="absolute left-0 mt-1 z-50 w-64 rounded-xl border border-border bg-popover p-1.5 shadow-xl animate-in fade-in zoom-in-95 duration-150"
        >
          <div className="px-2 py-1 text-[10px] font-black uppercase tracking-wider text-muted-foreground border-b border-border/50 mb-1">
            Seleccionar Lote
          </div>

          <button
            type="button"
            data-testid={`lot-option-fifo-${item.cartItemId}`}
            onClick={() => {
              onSelectLot(null);
              setDropdownOpen(false);
            }}
            className={cn(
              "flex items-center justify-between w-full px-2 py-1.5 rounded-lg text-xs font-bold transition-colors cursor-pointer text-left",
              !selectedLot
                ? "bg-primary/10 text-primary"
                : "text-foreground hover:bg-muted"
            )}
          >
            <span>FIFO automático</span>
            {!selectedLot && <Check className="h-3.5 w-3.5 text-primary" />}
          </button>

          {lots.map((lot) => {
            const isSelected = selectedLot === lot.fecha_vencimiento;
            return (
              <button
                type="button"
                key={lot.fecha_vencimiento}
                data-testid={`lot-option-${lot.fecha_vencimiento}`}
                onClick={() => {
                  onSelectLot(lot.fecha_vencimiento);
                  setDropdownOpen(false);
                }}
                className={cn(
                  "flex items-center justify-between w-full px-2 py-1.5 rounded-lg text-xs transition-colors cursor-pointer text-left mt-0.5",
                  isSelected
                    ? "bg-primary/10 text-primary font-bold"
                    : "text-foreground hover:bg-muted"
                )}
              >
                <div className="flex flex-col">
                  <span className={getLotColor(lot.fecha_vencimiento)}>
                    {formatLotLabel(lot.fecha_vencimiento)}
                  </span>
                  <span className="text-[10px] text-muted-foreground">
                    Stock: {lot.cantidad}
                  </span>
                </div>
                {isSelected && <Check className="h-3.5 w-3.5 text-primary shrink-0" />}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}

// ─── Modal de Lotes por Ingrediente para Recetas ─────────────────────────────
function RecipeLotsModal({
  open,
  onClose,
  item,
  receta,
  productos,
  lotsByProduct,
  onUpdateIngredientLot,
}: {
  readonly open: boolean;
  readonly onClose: () => void;
  readonly item: CartItem;
  readonly receta?: RecetaConsumo;
  readonly productos: ProductoConsumo[];
  readonly lotsByProduct: Record<string, LotInfo[]>;
  readonly onUpdateIngredientLot: (
    cartItemId: string,
    productoId: string,
    fecha: string | null
  ) => void;
}) {
  if (!open || !receta) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      data-testid={`recipe-lots-modal-${item.cartItemId}`}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-in fade-in duration-200"
    >
      <div className="w-full max-w-md rounded-2xl bg-card border border-border p-5 shadow-2xl space-y-4 max-h-[85vh] flex flex-col">
        <div className="flex items-center justify-between border-b border-border pb-3 shrink-0">
          <div className="flex items-center gap-2">
            <CookingPot className="h-5 w-5 text-purple-500" />
            <div>
              <h3 className="text-sm font-black uppercase tracking-wider text-foreground">
                Lotes de Ingredientes
              </h3>
              <p className="text-xs text-muted-foreground">{receta.nombre}</p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            data-testid="recipe-lots-modal-close"
            className="p-1 rounded-xl text-muted-foreground hover:text-foreground hover:bg-muted cursor-pointer"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="overflow-y-auto space-y-4 pr-1">
          {receta.ingredientes.map((ing, idx) => {
            if (!ing.producto_id) return null;
            const prod = productos.find((p) => p.id === ing.producto_id);
            const prodName = prod?.nombre || ing.producto_id;
            const lots = lotsByProduct[ing.producto_id] || [];
            const override = item.ingredientLotOverrides?.find(
              (ov) => ov.producto_id === ing.producto_id
            );
            const selectedFecha = override?.fecha_vencimiento ?? null;

            return (
              <div
                key={idx}
                className="p-3 rounded-xl border border-border bg-muted/30 space-y-2"
                data-testid={`ingredient-lot-row-${ing.producto_id}`}
              >
                <div className="flex items-center justify-between">
                  <p className="text-xs font-bold text-foreground truncate max-w-[200px]">
                    {prodName}
                  </p>
                  <span className="text-[10px] font-bold text-muted-foreground">
                    {(
                      (ing.cantidad * item.quantity) /
                      (Number(receta.porciones) || 1)
                    ).toFixed(2)}{" "}
                    {prod?.unidad || "und"}
                  </span>
                </div>

                {lots.length === 0 ? (
                  <p className="text-[10px] text-muted-foreground italic">
                    Sin lotes registrados
                  </p>
                ) : (
                  <div className="flex flex-wrap gap-1.5">
                    <button
                      type="button"
                      data-testid={`ingredient-lot-fifo-${ing.producto_id}`}
                      onClick={() =>
                        onUpdateIngredientLot(item.cartItemId, ing.producto_id!, null)
                      }
                      className={cn(
                        "text-[10px] px-2.5 py-1 rounded-lg border font-bold cursor-pointer transition-all",
                        !selectedFecha
                          ? "bg-primary text-primary-foreground border-primary shadow-sm"
                          : "bg-background border-border text-muted-foreground hover:border-primary/50"
                      )}
                    >
                      FIFO
                    </button>
                    {lots.map((lot) => {
                      const isSelected = selectedFecha === lot.fecha_vencimiento;
                      return (
                        <button
                          type="button"
                          key={lot.fecha_vencimiento}
                          data-testid={`ingredient-lot-${ing.producto_id}-${lot.fecha_vencimiento}`}
                          onClick={() =>
                            onUpdateIngredientLot(
                              item.cartItemId,
                              ing.producto_id!,
                              lot.fecha_vencimiento
                            )
                          }
                          className={cn(
                            "text-[10px] px-2.5 py-1 rounded-lg border font-bold cursor-pointer transition-all",
                            isSelected
                              ? "bg-primary text-primary-foreground border-primary shadow-sm"
                              : "bg-background border-border hover:border-primary/50",
                            getLotColor(lot.fecha_vencimiento)
                          )}
                        >
                          {formatLotLabel(lot.fecha_vencimiento)} ({lot.cantidad})
                        </button>
                      );
                    })}
                  </div>
                )}
              </div>
            );
          })}
        </div>

        <div className="pt-2 border-t border-border flex justify-end shrink-0">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 rounded-xl bg-primary text-primary-foreground text-xs font-bold uppercase tracking-wider hover:opacity-90 transition-opacity cursor-pointer"
          >
            Aceptar
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── COMPONENTE PRINCIPAL ConsumoCart ────────────────────────────────────────
export function ConsumoCart({
  open,
  onOpenChange,
  cart,
  allRecetas = [],
  combos: _combos = [],
  productos = [],
  saving = false,
  lotsByProduct = {},
  onUpdateQty,
  onRemove,
  onClearCart,
  onSubmit,
  getStock: _getStock,
  onUpdateLot,
  onUpdateIngredientLot,
}: ConsumoCartProps) {
  const { t } = useTranslation("operations");
  const { format } = useCurrencyFormatter();
  const [activeRecipeLotId, setActiveRecipeLotId] = useState<string | null>(null);

  if (!open) return null;

  const totalUnits = cart.reduce((acc, item) => acc + item.quantity, 0);
  const totalCost = cart.reduce(
    (acc, item) => acc + (item.price || 0) * item.quantity,
    0
  );

  const activeRecipeItem = cart.find((i) => i.cartItemId === activeRecipeLotId);
  const activeRecipe = activeRecipeItem
    ? allRecetas.find((r) => r.id === activeRecipeItem.id)
    : undefined;

  const handleQtyInput = (cartItemId: string, rawVal: string) => {
    const parsed = parseFloat(rawVal);
    if (!isNaN(parsed) && parsed > 0) {
      onUpdateQty(cartItemId, parsed);
    }
  };

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm animate-in fade-in duration-200"
        onClick={() => onOpenChange(false)}
        data-testid="consumo-cart-backdrop"
      />

      {/* Drawer Panel (Desktop derecho, Mobile bottom-sheet / modal completo) */}
      <div
        role="dialog"
        aria-modal="true"
        data-testid="consumo-cart-drawer"
        className="fixed inset-y-0 right-0 z-50 w-full sm:max-w-md bg-card border-l border-border shadow-2xl flex flex-col animate-in slide-in-from-right duration-300"
      >
        {/* Cabecera del Carrito */}
        <div className="p-4 border-b border-border flex items-center justify-between bg-muted/30 shrink-0">
          <div className="flex items-center gap-2.5">
            <div className="h-9 w-9 rounded-xl bg-yellow-500/15 border border-yellow-500/30 flex items-center justify-center text-yellow-500">
              <ShoppingCart className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-sm font-black uppercase tracking-wider text-foreground">
                {t("consumption.modals.cart.title", { defaultValue: "Carrito de Consumo" })}
              </h2>
              <p className="text-[11px] font-bold text-muted-foreground">
                {cart.length} {cart.length === 1 ? "ítem" : "ítems"} · {totalUnits}{" "}
                {totalUnits === 1 ? "unidad" : "unidades"}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {cart.length > 0 && (
              <button
                type="button"
                data-testid="cart-clear-btn"
                onClick={onClearCart}
                className="text-xs font-bold text-muted-foreground hover:text-destructive px-2.5 py-1.5 rounded-lg hover:bg-destructive/10 transition-colors cursor-pointer"
                title={t("consumption.modals.cart.clear", { defaultValue: "Vaciar Carrito" })}
              >
                {t("consumption.modals.cart.clear", { defaultValue: "Vaciar" })}
              </button>
            )}
            <button
              type="button"
              data-testid="cart-close-btn"
              onClick={() => onOpenChange(false)}
              className="p-1.5 rounded-xl text-muted-foreground hover:text-foreground hover:bg-muted transition-colors cursor-pointer"
              aria-label="Cerrar carrito"
            >
              <X className="h-5 w-5" />
            </button>
          </div>
        </div>

        {/* Lista de Ítems */}
        <div className="flex-1 overflow-y-auto p-4 space-y-3 custom-scrollbar">
          {cart.length === 0 ? (
            <div
              data-testid="consumo-cart-empty"
              className="flex flex-col items-center justify-center h-full text-center py-16 space-y-3"
            >
              <div className="h-16 w-16 rounded-2xl bg-muted/60 flex items-center justify-center text-muted-foreground">
                <ShoppingCart className="h-8 w-8" />
              </div>
              <p className="text-sm font-bold text-foreground">
                {t("consumption.modals.cart.empty", { defaultValue: "Tu carrito está vacío" })}
              </p>
              <p className="text-xs text-muted-foreground max-w-xs">
                Selecciona productos, recetas o combos del catálogo para registrar
                su consumo o merma.
              </p>
            </div>
          ) : (
            cart.map((item) => {
              const lots = lotsByProduct[item.id] || [];
              const isRecipe = item.type === "receta";

              return (
                <div
                  key={item.cartItemId}
                  data-testid={`cart-item-${item.cartItemId}`}
                  className="p-3 rounded-2xl border border-border bg-card shadow-sm hover:border-border/80 transition-all space-y-2.5"
                >
                  {/* Fila superior: Ícono, Nombre y Eliminar */}
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex items-start gap-2.5 min-w-0">
                      <div
                        className={cn(
                          "h-8 w-8 rounded-xl flex items-center justify-center shrink-0 mt-0.5",
                          item.type === "producto" &&
                            "bg-yellow-500/15 text-yellow-500 border border-yellow-500/30",
                          item.type === "receta" &&
                            "bg-purple-600/15 text-purple-600 border border-purple-600/30",
                          item.type === "combo" &&
                            "bg-[#1c4c96]/15 text-[#1c4c96] border border-[#1c4c96]/30"
                        )}
                      >
                        {item.type === "producto" && (
                          <Package className="h-4 w-4" />
                        )}
                        {item.type === "receta" && (
                          <CookingPot className="h-4 w-4" />
                        )}
                        {item.type === "combo" && <Layers className="h-4 w-4" />}
                      </div>

                      <div className="min-w-0">
                        <p className="text-xs font-black uppercase text-foreground truncate">
                          {item.name}
                        </p>
                        <div className="flex items-center gap-2 text-[10px] font-bold text-muted-foreground">
                          <span>
                            {item.price ? formatMoney(item.price) : "$0"}
                          </span>
                          {item.unit && <span>· {item.unit}</span>}
                          {item.bodega_id && (
                            <span className="truncate">
                              · Bodega: {item.bodega_id}
                            </span>
                          )}
                        </div>
                      </div>
                    </div>

                    <button
                      type="button"
                      data-testid={`cart-remove-btn-${item.cartItemId}`}
                      onClick={() => onRemove(item.cartItemId)}
                      className="p-1 rounded-lg text-muted-foreground hover:text-destructive hover:bg-destructive/10 transition-colors cursor-pointer shrink-0"
                      title="Eliminar del carrito"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>

                  {/* Opciones personalizadas seleccionadas */}
                  {item.optionSelections && item.optionSelections.length > 0 && (
                    <div
                      data-testid={`cart-options-summary-${item.cartItemId}`}
                      className="text-[10px] bg-muted/40 p-1.5 rounded-lg border border-border/50 text-muted-foreground space-y-0.5"
                    >
                      <span className="font-bold uppercase tracking-wider block">
                        Opciones:
                      </span>
                      {item.optionSelections.map((opt, i) => (
                        <div key={i} className="flex justify-between pl-1">
                          <span>
                            {opt.nombre || "Opción"} × {opt.cantidad}
                          </span>
                          {opt.precio_adicional ? (
                            <span className="font-bold">
                              +{formatMoney(opt.precio_adicional)}
                            </span>
                          ) : null}
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Selectores de Lote */}
                  {item.type === "producto" && onUpdateLot && (
                    <ProductLotSelector
                      item={item}
                      lots={lots}
                      onSelectLot={(lot) => onUpdateLot(item.cartItemId, lot)}
                    />
                  )}

                  {isRecipe && onUpdateIngredientLot && (
                    <div className="pt-0.5">
                      <button
                        type="button"
                        data-testid={`cart-recipe-lots-btn-${item.cartItemId}`}
                        onClick={() => setActiveRecipeLotId(item.cartItemId)}
                        className="flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wider text-purple-600 hover:text-purple-500 bg-purple-500/10 hover:bg-purple-500/20 px-2 py-1 rounded-lg border border-purple-500/20 transition-colors cursor-pointer"
                      >
                        <CookingPot className="h-3 w-3" />
                        <span>Configurar Lotes Insumos</span>
                        {item.ingredientLotOverrides &&
                          item.ingredientLotOverrides.length > 0 && (
                            <span className="h-1.5 w-1.5 rounded-full bg-purple-600 animate-ping" />
                          )}
                      </button>
                    </div>
                  )}

                  {/* Fila inferior: Controles de Cantidad y Subtotal */}
                  <div className="flex items-center justify-between pt-1 border-t border-border/40">
                    <div className="flex items-center gap-1 bg-muted/50 rounded-xl p-0.5 border border-border">
                      <button
                        type="button"
                        data-testid={`cart-qty-minus-${item.cartItemId}`}
                        onClick={() =>
                          onUpdateQty(
                            item.cartItemId,
                            Math.max(1, item.quantity - 1)
                          )
                        }
                        className="h-7 w-7 rounded-lg flex items-center justify-center text-foreground hover:bg-background transition-colors cursor-pointer active:scale-90"
                        title="Restar 1"
                      >
                        <Minus className="h-3.5 w-3.5" />
                      </button>

                      <input
                        type="number"
                        data-testid={`cart-qty-input-${item.cartItemId}`}
                        value={item.quantity}
                        min="0.01"
                        step="any"
                        onChange={(e) =>
                          handleQtyInput(item.cartItemId, e.target.value)
                        }
                        className="w-14 text-center text-xs font-black bg-transparent border-none focus:outline-none focus:ring-0 text-foreground"
                      />

                      <button
                        type="button"
                        data-testid={`cart-qty-plus-${item.cartItemId}`}
                        onClick={() =>
                          onUpdateQty(item.cartItemId, item.quantity + 1)
                        }
                        className="h-7 w-7 rounded-lg flex items-center justify-center text-foreground hover:bg-background transition-colors cursor-pointer active:scale-90"
                        title="Sumar 1"
                      >
                        <Plus className="h-3.5 w-3.5" />
                      </button>
                    </div>

                    <div className="text-right">
                      <p className="text-[10px] text-muted-foreground uppercase font-bold">
                        Subtotal
                      </p>
                      <p className="text-xs font-black text-foreground">
                        {formatMoney((item.price || 0) * item.quantity)}
                      </p>
                    </div>
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* Footer con Resumen y Botón de Envío */}
        {cart.length > 0 && (
          <div className="p-4 border-t border-border bg-muted/20 space-y-3 shrink-0">
            <div className="space-y-1 text-xs">
              <div className="flex items-center justify-between text-muted-foreground">
                <span>{t("consumption.modals.cart.subtotal", { defaultValue: "Subtotal neto estimado" })}</span>
                <span className="font-bold">{format(totalCost)}</span>
              </div>
              <div className="flex items-center justify-between text-sm font-black text-foreground pt-1 border-t border-border/50">
                <span>{t("consumption.modals.cart.total", { defaultValue: "Total a consumir" })}</span>
                <span className="text-base text-primary">
                  {format(totalCost)}
                </span>
              </div>
            </div>

            <button
              type="button"
              data-testid="cart-submit-btn"
              disabled={saving}
              onClick={() => void onSubmit()}
              className="w-full h-12 rounded-2xl bg-yellow-500 hover:bg-yellow-400 text-black font-black uppercase text-xs tracking-wider shadow-xl shadow-yellow-500/25 flex items-center justify-center gap-2 cursor-pointer transition-all active:scale-98 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {saving ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span>{t("consumption.modals.cart.processing", { defaultValue: "Procesando Kardex..." })}</span>
                </>
              ) : (
                <>
                  <Check className="h-4 w-4" />
                  <span>{t("consumption.modals.cart.submit_btn", { defaultValue: "Registrar Consumo" })} ({totalUnits})</span>
                </>
              )}
            </button>
          </div>
        )}
      </div>

      {/* Modal de Lotes para Receta */}
      {activeRecipeItem && onUpdateIngredientLot && (
        <RecipeLotsModal
          open={!!activeRecipeLotId}
          onClose={() => setActiveRecipeLotId(null)}
          item={activeRecipeItem}
          receta={activeRecipe}
          productos={productos}
          lotsByProduct={lotsByProduct}
          onUpdateIngredientLot={onUpdateIngredientLot}
        />
      )}
    </>
  );
}

export default ConsumoCart;
