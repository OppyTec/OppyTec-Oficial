// oppytec-frontend/src/features/consumo/components/LocateStockDialog.tsx
import { useState } from "react";
import { useTranslation } from "react-i18next";
import {
  Package,
  Building2,
  ArrowRightLeft,
  X,
  Search,
  CheckCircle2,
  Loader2,
} from "lucide-react";
import { toast } from "sonner";
import type { ProductoConsumo } from "../types";

export interface WarehouseStockResult {
  bodega_id: string;
  bodega_nombre: string;
  stock_disponible: number;
}

export interface LocateStockDialogProps {
  readonly open: boolean;
  readonly onOpenChange: (open: boolean) => void;
  readonly missingProducts: string[];
  readonly productos: ProductoConsumo[];
  readonly currentBodegaId: string;
  readonly onRequestTransfer?: (
    productoId: string,
    bodegaOrigenId: string
  ) => Promise<void> | void;
}

export function LocateStockDialog({
  open,
  onOpenChange,
  missingProducts,
  productos,
  currentBodegaId: _currentBodegaId,
  onRequestTransfer,
}: LocateStockDialogProps) {
  const { t } = useTranslation("operations");
  const [requestingId, setRequestingId] = useState<string | null>(null);

  if (!open) return null;

  const handleTransfer = async (prodId: string, bodegaId: string) => {
    setRequestingId(`${prodId}-${bodegaId}`);
    try {
      if (onRequestTransfer) {
        await onRequestTransfer(prodId, bodegaId);
      } else {
        await new Promise((r) => setTimeout(r, 400));
        toast.success("Solicitud de reposición enviada a supervisión");
      }
    } finally {
      setRequestingId(null);
    }
  };

  // Mock de existencias en otras bodegas para visualización inmediata
  const mockLocations: Record<string, WarehouseStockResult[]> = {
    default: [
      {
        bodega_id: "bodega-central",
        bodega_nombre: "Bodega Central de Almacén",
        stock_disponible: 45,
      },
      {
        bodega_id: "bodega-camara",
        bodega_nombre: "Cámara de Frío Principal",
        stock_disponible: 28,
      },
    ],
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      data-testid="locate-stock-dialog"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-in fade-in duration-200"
    >
      <div className="w-full max-w-2xl rounded-3xl bg-card border border-border shadow-2xl flex flex-col max-h-[85vh] overflow-hidden">
        {/* Cabecera */}
        <div className="p-4 border-b border-border flex items-center justify-between bg-muted/30 shrink-0">
          <div className="flex items-center gap-2.5">
            <div className="h-10 w-10 rounded-2xl bg-blue-600/15 text-blue-600 border border-blue-600/30 flex items-center justify-center">
              <Search className="h-5 w-5" />
            </div>
            <div>
              <h3 className="text-sm font-black uppercase tracking-wider text-foreground">
                {t("consumption.modals.locate_stock.title", { defaultValue: "Localizador de Stock en Otras Bodegas" })}
              </h3>
              <p className="text-xs text-muted-foreground">
                Consulta de disponibilidad multi-bodega y solicitud de reposición
              </p>
            </div>
          </div>

          <button
            type="button"
            data-testid="locate-close-btn"
            onClick={() => onOpenChange(false)}
            className="p-1.5 rounded-xl text-muted-foreground hover:text-foreground hover:bg-muted cursor-pointer"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Contenido */}
        <div className="flex-1 overflow-y-auto p-5 space-y-4 custom-scrollbar">
          {missingProducts.length === 0 ? (
            <div className="text-center py-12 space-y-2 text-muted-foreground">
              <CheckCircle2 className="h-10 w-10 text-emerald-500 mx-auto" />
              <p className="text-xs font-bold uppercase tracking-wider">
                Todos los insumos requeridos cuentan con stock suficiente
              </p>
            </div>
          ) : (
            missingProducts.map((pId) => {
              const prod = productos.find((p) => p.id === pId);
              const locations = mockLocations.default;

              return (
                <div
                  key={pId}
                  data-testid={`locate-product-card-${pId}`}
                  className="rounded-2xl border border-border bg-muted/20 p-4 space-y-3"
                >
                  <div className="flex items-center justify-between border-b border-border/50 pb-2">
                    <div className="flex items-center gap-2">
                      <Package className="h-4 w-4 text-primary" />
                      <h4 className="text-xs font-black uppercase text-foreground">
                        {prod?.nombre || pId}
                      </h4>
                      {prod?.sku && (
                        <span className="text-[10px] text-muted-foreground">
                          ({prod.sku})
                        </span>
                      )}
                    </div>
                    <span className="text-[10px] font-bold text-destructive bg-destructive/10 px-2 py-0.5 rounded-full border border-destructive/20">
                      Sin stock en bodega actual
                    </span>
                  </div>

                  {/* Lista de bodegas alternativas */}
                  <div className="space-y-2">
                    {(locations || []).map((loc) => {
                      const isRequesting =
                        requestingId === `${pId}-${loc.bodega_id}`;

                      return (
                        <div
                          key={loc.bodega_id}
                          data-testid={`locate-warehouse-row-${loc.bodega_id}`}
                          className="flex items-center justify-between p-3 rounded-xl border border-border bg-card shadow-sm"
                        >
                          <div className="flex items-center gap-2.5">
                            <Building2 className="h-4 w-4 text-muted-foreground shrink-0" />
                            <div>
                              <p className="text-xs font-bold text-foreground">
                                {loc.bodega_nombre}
                              </p>
                              <p className="text-[10px] text-emerald-500 font-bold">
                                {loc.stock_disponible} {prod?.unidad || "und"} disponibles
                              </p>
                            </div>
                          </div>

                          <button
                            type="button"
                            data-testid={`locate-request-transfer-btn-${pId}-${loc.bodega_id}`}
                            disabled={isRequesting}
                            onClick={() => handleTransfer(pId, loc.bodega_id)}
                            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-primary/10 hover:bg-primary/20 text-primary border border-primary/30 text-xs font-black uppercase tracking-wider transition-all cursor-pointer active:scale-95 disabled:opacity-50"
                          >
                            {isRequesting ? (
                              <Loader2 className="h-3.5 w-3.5 animate-spin" />
                            ) : (
                              <ArrowRightLeft className="h-3.5 w-3.5" />
                            )}
                            <span>Solicitar Reposición</span>
                          </button>
                        </div>
                      );
                    })}
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-border bg-muted/20 flex justify-end shrink-0">
          <button
            type="button"
            onClick={() => onOpenChange(false)}
            className="px-4 py-2 rounded-xl bg-primary text-primary-foreground text-xs font-bold uppercase tracking-wider hover:opacity-90 transition-opacity cursor-pointer"
          >
            Cerrar
          </button>
        </div>
      </div>
    </div>
  );
}

export default LocateStockDialog;
