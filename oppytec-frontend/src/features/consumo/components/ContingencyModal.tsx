// oppytec-frontend/src/features/consumo/components/ContingencyModal.tsx
import { useTranslation } from "react-i18next";
import {
  AlertTriangle,
  Clock,
  PackageX,
  ShieldAlert,
  ArrowRight,
  Flame,
  Search,
  X,
} from "lucide-react";

export interface ContingencyModalProps {
  readonly open: boolean;
  readonly onOpenChange: (open: boolean) => void;
  readonly contingencyResult: {
    isContingency?: boolean;
    reason?: "out_of_stock" | "expired_lots" | string;
    hasExpiredLots?: boolean;
    hasInsufficientStock?: boolean;
    expiredProductNames?: string[];
    insufficientStockNames?: string[];
    expiredLots?: Array<{
      fecha_vencimiento?: string;
      cantidad?: number;
      lote_codigo?: string | null;
    }>;
    productName?: string;
  } | null;
  readonly onForceConsume: () => void;
  readonly onTriggerMerma: () => void;
  readonly onLocateStock: () => void;
}

export function ContingencyModal({
  open,
  onOpenChange,
  contingencyResult,
  onForceConsume,
  onTriggerMerma,
  onLocateStock,
}: ContingencyModalProps) {
  const { t } = useTranslation("operations");
  if (!open || !contingencyResult) return null;

  const hasExpiredLots =
    contingencyResult.hasExpiredLots ??
    (contingencyResult.reason === "expired_lots" ||
      (contingencyResult.expiredLots && contingencyResult.expiredLots.length > 0));

  const hasInsufficientStock =
    contingencyResult.hasInsufficientStock ??
    contingencyResult.reason === "out_of_stock";

  const expiredProductNames =
    contingencyResult.expiredProductNames ??
    (contingencyResult.productName ? [contingencyResult.productName] : []);

  const insufficientStockNames =
    contingencyResult.insufficientStockNames ??
    (contingencyResult.productName ? [contingencyResult.productName] : []);

  return (
    <div
      role="dialog"
      aria-modal="true"
      data-testid="contingency-modal"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-in fade-in duration-200"
    >
      <div className="w-full max-w-lg rounded-3xl bg-card border border-destructive/40 shadow-2xl flex flex-col overflow-hidden animate-in zoom-in-95 duration-200">
        {/* Cabecera de Alerta Crítica */}
        <div className="p-4 border-b border-border flex items-center justify-between bg-destructive/10 shrink-0">
          <div className="flex items-center gap-2.5">
            <div className="h-10 w-10 rounded-2xl bg-destructive text-destructive-foreground flex items-center justify-center shadow-lg shadow-destructive/20 animate-pulse">
              <ShieldAlert className="h-5 w-5" />
            </div>
            <div>
              <h3 className="text-sm font-black uppercase tracking-wider text-destructive">
                {t("consumption.modals.contingency.title", { defaultValue: "Alerta de Contingencia de Stock" })}
              </h3>
              <p className="text-xs text-muted-foreground">
                {t("consumption.modals.contingency.subtitle", { defaultValue: "Inconsistencia detectada en existencias o caducidades" })}
              </p>
            </div>
          </div>

          <button
            type="button"
            data-testid="contingency-cancel-btn"
            onClick={() => onOpenChange(false)}
            className="p-1.5 rounded-xl text-muted-foreground hover:text-foreground hover:bg-muted cursor-pointer"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Detalle de Inconsistencias */}
        <div className="p-5 space-y-4 overflow-y-auto max-h-[60vh] custom-scrollbar">
          {hasExpiredLots && (
            <div
              data-testid="contingency-expired-section"
              className="p-3.5 rounded-2xl border border-destructive/30 bg-destructive/5 space-y-2"
            >
              <div className="flex items-center gap-2 text-destructive font-black text-xs uppercase tracking-wide">
                <Clock className="h-4 w-4" />
                <span>Lotes Vencidos Detectados ({expiredProductNames.length})</span>
              </div>
              <ul className="text-xs text-muted-foreground list-disc list-inside space-y-1 font-medium pl-1">
                {expiredProductNames.map((name, i) => (
                  <li key={i} className="text-foreground font-bold">
                    {name}
                  </li>
                ))}
              </ul>
              <p className="text-[11px] text-destructive/80 font-medium">
                Consumir productos con lote vencido requiere autorización de supervisión y registrará una traza en la bitácora de auditoría.
              </p>
            </div>
          )}

          {hasInsufficientStock && (
            <div
              data-testid="contingency-stock-section"
              className="p-3.5 rounded-2xl border border-orange-500/30 bg-orange-500/5 space-y-2"
            >
              <div className="flex items-center gap-2 text-orange-500 font-black text-xs uppercase tracking-wide">
                <PackageX className="h-4 w-4" />
                <span>Stock Insuficiente en Bodega ({insufficientStockNames.length})</span>
              </div>
              <ul className="text-xs text-muted-foreground list-disc list-inside space-y-1 font-medium pl-1">
                {insufficientStockNames.map((name, i) => (
                  <li key={i} className="text-foreground font-bold">
                    {name}
                  </li>
                ))}
              </ul>
              <p className="text-[11px] text-orange-500/80 font-medium">
                La cantidad requerida supera el inventario registrado en esta bodega.
              </p>
            </div>
          )}

          {/* Opciones de Resolución (3 Caminos) */}
          <div className="space-y-2.5 pt-2">
            <p className="text-xs font-black uppercase tracking-wider text-foreground">
              ¿Cómo deseas proceder?
            </p>

            {/* Camino 1: Localizar Stock en otras Bodegas */}
            <button
              type="button"
              data-testid="contingency-locate-btn"
              onClick={() => {
                onOpenChange(false);
                onLocateStock();
              }}
              className="w-full flex items-center justify-between p-3 rounded-2xl border border-blue-500/30 bg-blue-500/10 hover:bg-blue-500/20 text-blue-600 transition-all cursor-pointer text-left group"
            >
              <div className="flex items-center gap-3">
                <div className="h-9 w-9 rounded-xl bg-blue-600 text-white flex items-center justify-center shrink-0">
                  <Search className="h-4 w-4" />
                </div>
                <div>
                  <p className="text-xs font-black uppercase tracking-wider text-blue-600">
                    Localizar Stock en Otras Bodegas
                  </p>
                  <p className="text-[10px] text-muted-foreground">
                    Verificar existencias en bodegas centrales o solicitar transferencia
                  </p>
                </div>
              </div>
              <ArrowRight className="h-4 w-4 text-blue-600 group-hover:translate-x-1 transition-transform" />
            </button>

            {/* Camino 2: Registrar Merma Inmediata */}
            {hasExpiredLots && (
              <button
                type="button"
                data-testid="contingency-merma-btn"
                onClick={() => {
                  onOpenChange(false);
                  onTriggerMerma();
                }}
                className="w-full flex items-center justify-between p-3 rounded-2xl border border-destructive/30 bg-destructive/10 hover:bg-destructive/20 text-destructive transition-all cursor-pointer text-left group"
              >
                <div className="flex items-center gap-3">
                  <div className="h-9 w-9 rounded-xl bg-destructive text-destructive-foreground flex items-center justify-center shrink-0">
                    <Flame className="h-4 w-4" />
                  </div>
                  <div>
                    <p className="text-xs font-black uppercase tracking-wider text-destructive">
                      Mermar Lote Vencido
                    </p>
                    <p className="text-[10px] text-muted-foreground">
                      Dar de baja las unidades vencidas registrando motivo de merma
                    </p>
                  </div>
                </div>
                <ArrowRight className="h-4 w-4 text-destructive group-hover:translate-x-1 transition-transform" />
              </button>
            )}

            {/* Camino 3: Forzar Consumo bajo Auditoría */}
            <button
              type="button"
              data-testid="contingency-force-btn"
              onClick={() => {
                onOpenChange(false);
                onForceConsume();
              }}
              className="w-full flex items-center justify-between p-3 rounded-2xl border border-border bg-muted/40 hover:bg-muted text-foreground transition-all cursor-pointer text-left group"
            >
              <div className="flex items-center gap-3">
                <div className="h-9 w-9 rounded-xl bg-secondary text-foreground flex items-center justify-center shrink-0 border border-border">
                  <AlertTriangle className="h-4 w-4 text-amber-500" />
                </div>
                <div>
                  <p className="text-xs font-black uppercase tracking-wider text-foreground">
                    Forzar Consumo Bajo Auditoría
                  </p>
                  <p className="text-[10px] text-muted-foreground">
                    Permite continuar descontando stock con registro en Kardex
                  </p>
                </div>
              </div>
              <ArrowRight className="h-4 w-4 text-muted-foreground group-hover:translate-x-1 transition-transform" />
            </button>
          </div>
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-border bg-muted/20 flex justify-end shrink-0">
          <button
            type="button"
            onClick={() => onOpenChange(false)}
            className="px-4 py-2 rounded-xl border border-border text-xs font-bold hover:bg-muted transition-colors cursor-pointer text-muted-foreground hover:text-foreground"
          >
            Cancelar
          </button>
        </div>
      </div>
    </div>
  );
}

export default ContingencyModal;
