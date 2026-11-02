/**
 * oppytec-frontend/src/features/projection/components/ProyeccionTransferModal.tsx
 * Modal de Confirmación para Traspaso Preventivo entre Bodegas sugerido por Proyección.
 * Utiliza ResponsiveDialog con ADN Visual Mobile-First y feedback sonner.
 * Pre-poblado con bodega de origen (con stock ocioso), destino (con quiebre inminente) y cantidad.
 * TypeScript estricto, 0 any, 0 hardcoded strings.
 */
import { useEffect, useState, type FC, type ChangeEvent } from "react";
import {
  AlertCircle,
  ArrowRight,
  Boxes,
  CheckCircle2,
  Clock,
  Warehouse,
} from "lucide-react";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import { ResponsiveDialog } from "@/shared/components/ui/ResponsiveDialog";
import type { TransferSuggestion } from "../types";

export interface ProyeccionTransferModalProps {
  readonly open: boolean;
  readonly onClose: () => void;
  readonly suggestion: TransferSuggestion | null;
  readonly productName?: string;
  readonly productUnit?: string;
  readonly onConfirm?: (
    suggestion: TransferSuggestion,
    quantity: number
  ) => Promise<void> | void;
  readonly className?: string;
}

export const ProyeccionTransferModal: FC<ProyeccionTransferModalProps> = ({
  open,
  onClose,
  suggestion,
  productName,
  productUnit = "un",
  onConfirm,
  className,
}) => {
  const { t } = useTranslation(["projection", "common"]);

  const [quantity, setQuantity] = useState<number>(
    suggestion?.cantidad_sugerida ?? 10
  );
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);

  useEffect(() => {
    if (suggestion) {
      setQuantity(suggestion.cantidad_sugerida);
    }
  }, [suggestion]);

  if (!suggestion) {
    return null;
  }

  const originName =
    suggestion.bodega_origen_nombre ||
    t("transfer.default_origin", {
      defaultValue: `Bodega ${suggestion.bodega_origen_id}`,
    });

  const destinationName = t("transfer.default_destination", {
    defaultValue: `Bodega ${suggestion.bodega_destino_id}`,
  });

  const handleQuantityChange = (e: ChangeEvent<HTMLInputElement>) => {
    const val = parseFloat(e.target.value);
    setQuantity(isNaN(val) ? 0 : Math.max(0, val));
  };

  const handleConfirm = async () => {
    if (quantity <= 0) {
      toast.error(
        t("transfer.error_quantity", {
          defaultValue: "La cantidad a transferir debe ser mayor a 0",
        })
      );
      return;
    }

    try {
      setIsSubmitting(true);
      if (onConfirm) {
        await onConfirm(suggestion, quantity);
      }
      toast.success(
        t("transfer.success_toast", {
          defaultValue:
            "Traspaso preventivo registrado exitosamente en el inventario",
        })
      );
      onClose();
    } catch (err) {
      toast.error(
        t("transfer.error_toast", {
          defaultValue: "Error al registrar el traspaso preventivo",
        })
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <ResponsiveDialog
      open={open}
      onClose={onClose}
      title={t("transfer.title", {
        defaultValue: "Confirmar Traspaso Preventivo",
      })}
      description={t("transfer.subtitle", {
        defaultValue:
          "Reasignación inteligente de stock para evitar quiebres de servicio",
      })}
      maxWidth="max-w-md"
      className={className}
    >
      <div
        data-testid="proyeccion-transfer-modal"
        className="space-y-4 py-1 text-foreground"
      >
        {/* Banner de Producto */}
        <div className="flex items-center gap-3 rounded-xl border border-primary/20 bg-primary/5 p-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary/15 text-primary">
            <Boxes className="h-5 w-5" />
          </div>
          <div className="min-w-0 flex-1">
            <span className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground block">
              {t("transfer.product_label", {
                defaultValue: "Materia Prima",
              })}
            </span>
            <p className="font-bold text-sm text-foreground truncate">
              {productName || `ID: ${suggestion.producto_id}`}
            </p>
          </div>
        </div>

        {/* Flujo de Bodegas Origen -> Destino */}
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-[1fr,auto,1fr] sm:items-center rounded-xl border border-border/80 bg-muted/30 p-3">
          {/* Origen */}
          <div className="space-y-1">
            <div className="flex items-center gap-1.5 text-xs text-muted-foreground font-medium">
              <Warehouse className="h-3.5 w-3.5 text-emerald-500" />
              <span>
                {t("transfer.origin", { defaultValue: "Origen" })}
              </span>
            </div>
            <p className="text-xs font-bold text-foreground truncate">
              {originName}
            </p>
            <div className="flex items-center gap-1 text-[11px] text-emerald-600 dark:text-emerald-400">
              <Clock className="h-3 w-3" />
              <span>
                {t("transfer.coverage_days", {
                  days: suggestion.dias_cobertura_restante_origen,
                  defaultValue: `${suggestion.dias_cobertura_restante_origen} días de cobertura`,
                })}
              </span>
            </div>
          </div>

          {/* Flecha indicadora */}
          <div className="flex justify-center py-1 sm:py-0">
            <div className="flex h-7 w-7 items-center justify-center rounded-full bg-border text-muted-foreground">
              <ArrowRight className="h-4 w-4" />
            </div>
          </div>

          {/* Destino */}
          <div className="space-y-1 sm:text-right">
            <div className="flex items-center gap-1.5 text-xs text-muted-foreground font-medium sm:justify-end">
              <Warehouse className="h-3.5 w-3.5 text-destructive" />
              <span>
                {t("transfer.destination", {
                  defaultValue: "Destino",
                })}
              </span>
            </div>
            <p className="text-xs font-bold text-foreground truncate">
              {destinationName}
            </p>
            <span className="inline-block rounded bg-destructive/15 px-1.5 py-0.5 text-[10px] font-bold text-destructive">
              {t("transfer.imminent_shortage", {
                defaultValue: "Quiebre inminente",
              })}
            </span>
          </div>
        </div>

        {/* Input de Cantidad */}
        <div className="space-y-1.5">
          <label
            htmlFor="transfer-qty-input"
            className="flex items-center justify-between text-xs font-bold text-foreground"
          >
            <span>
              {t("transfer.quantity_to_transfer", {
                defaultValue: "Cantidad a Traspasar",
              })}
            </span>
            <span className="text-[11px] font-normal text-muted-foreground">
              {t("transfer.suggested", {
                qty: suggestion.cantidad_sugerida,
                unit: productUnit,
                defaultValue: `Sugerida: ${suggestion.cantidad_sugerida} ${productUnit}`,
              })}
            </span>
          </label>
          <div className="relative">
            <input
              id="transfer-qty-input"
              data-testid="transfer-qty-input"
              type="number"
              min="0.1"
              step="0.1"
              value={quantity}
              onChange={handleQuantityChange}
              disabled={isSubmitting}
              className="touch-target flex h-11 w-full rounded-xl border border-input bg-background px-3 py-2 text-sm font-bold text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary disabled:cursor-not-allowed disabled:opacity-50"
            />
            <span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs font-medium text-muted-foreground pointer-events-none">
              {productUnit}
            </span>
          </div>
        </div>

        {/* Nota informativa */}
        <div className="flex items-start gap-2 rounded-lg bg-blue-500/10 p-2.5 text-xs text-blue-600 dark:text-blue-400">
          <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
          <p>
            {t("transfer.info_note", {
              defaultValue:
                "El traspaso generará un movimiento Kardex automático entre las bodegas seleccionadas.",
            })}
          </p>
        </div>

        {/* Acciones */}
        <div className="flex items-center justify-end gap-2 pt-2 border-t border-border">
          <button
            type="button"
            data-testid="cancel-transfer-btn"
            onClick={onClose}
            disabled={isSubmitting}
            className="touch-target inline-flex min-h-[44px] items-center justify-center rounded-xl border border-border bg-secondary px-4 py-2 text-xs font-bold text-secondary-foreground hover:bg-secondary/80 transition-colors cursor-pointer"
          >
            {t("common.actions.cancel", { defaultValue: "Cancelar" })}
          </button>
          <button
            type="button"
            data-testid="confirm-transfer-btn"
            onClick={handleConfirm}
            disabled={isSubmitting}
            className="touch-target inline-flex min-h-[44px] items-center justify-center gap-2 rounded-xl bg-primary px-5 py-2 text-xs font-bold text-primary-foreground hover:bg-primary/90 transition-all active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed shadow cursor-pointer"
          >
            <CheckCircle2 className="h-4 w-4" />
            <span>
              {isSubmitting
                ? t("common.actions.processing", {
                    defaultValue: "Procesando...",
                  })
                : t("transfer.confirm_action", {
                    defaultValue: "Confirmar Traspaso",
                  })}
            </span>
          </button>
        </div>
      </div>
    </ResponsiveDialog>
  );
};
