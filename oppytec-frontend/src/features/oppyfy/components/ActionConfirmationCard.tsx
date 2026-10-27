import { useState } from "react";
import { CheckCircle2, AlertCircle, Loader2 } from "lucide-react";
import { toast } from "sonner";

export interface ActionDraftCard {
  action_type: "merma_draft" | "purchase_order_draft";
  title: string;
  item_name?: string;
  quantity?: number;
  unit?: string;
  reason?: string;
  details?: string;
  confirmed?: boolean;
}

export interface ActionConfirmationCardProps {
  readonly card: ActionDraftCard;
  readonly onConfirmAction?: (card: ActionDraftCard) => Promise<void> | void;
}

export function ActionConfirmationCard({
  card,
  onConfirmAction,
}: ActionConfirmationCardProps) {
  const [isProcessing, setIsProcessing] = useState(false);
  const [isConfirmed, setIsConfirmed] = useState(Boolean(card.confirmed));
  const [isDismissed, setIsDismissed] = useState(false);

  if (isDismissed) {
    return (
      <div
        data-testid="action-card-dismissed"
        className="my-2 px-3.5 py-2 rounded-lg bg-secondary/30 border border-border text-xs text-muted-foreground italic flex items-center justify-between"
      >
        <span>Acción descartada por el usuario.</span>
      </div>
    );
  }

  const handleConfirm = async () => {
    setIsProcessing(true);
    try {
      if (onConfirmAction) {
        await onConfirmAction(card);
      } else {
        await new Promise((res) => setTimeout(res, 400));
      }
      setIsConfirmed(true);
      toast.success(
        card.action_type === "merma_draft"
          ? "Merma registrada exitosamente en el inventario."
          : "Acción confirmada y procesada."
      );
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Error desconocido";
      toast.error(`Ocurrió un error al registrar la acción: ${msg}`);
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div
      data-testid="action-confirmation-card"
      className="my-3 p-4 rounded-xl border border-primary/30 bg-card/95 shadow-sm max-w-md text-foreground"
    >
      <div className="flex items-start justify-between gap-2 border-b border-border/60 pb-2.5">
        <div className="flex items-center gap-2 min-w-0">
          <div className="p-1.5 rounded-lg bg-amber-500/10 text-amber-500 shrink-0">
            <AlertCircle className="w-4 h-4" />
          </div>
          <div className="min-w-0">
            <h4 className="text-xs font-semibold text-foreground truncate">
              {card.title || "Confirmación Requerida"}
            </h4>
            <p className="text-[11px] text-muted-foreground">
              {card.action_type === "merma_draft"
                ? "Registro de merma de inventario (Human-in-the-Loop)"
                : "Borrador operativo"}
            </p>
          </div>
        </div>

        {isConfirmed && (
          <span
            data-testid="action-card-confirmed-badge"
            className="inline-flex items-center gap-1 text-[11px] font-medium text-emerald-500 bg-emerald-500/10 px-2 py-0.5 rounded-full"
          >
            <CheckCircle2 className="w-3 h-3" />
            Registrado
          </span>
        )}
      </div>

      {/* Datos del borrador */}
      <div className="py-3 space-y-1.5 text-xs">
        {card.item_name && (
          <div className="flex justify-between py-1 border-b border-border/30">
            <span className="text-muted-foreground">Insumo / Producto:</span>
            <span className="font-semibold text-foreground">{card.item_name}</span>
          </div>
        )}
        {card.quantity !== undefined && (
          <div className="flex justify-between py-1 border-b border-border/30">
            <span className="text-muted-foreground">Cantidad:</span>
            <span className="font-mono font-medium text-foreground">
              {card.quantity} {card.unit || "unidades"}
            </span>
          </div>
        )}
        {card.reason && (
          <div className="flex justify-between py-1 border-b border-border/30">
            <span className="text-muted-foreground">Motivo:</span>
            <span className="text-foreground">{card.reason}</span>
          </div>
        )}
        {card.details && (
          <p className="text-[11px] text-muted-foreground/90 pt-1 italic">
            {card.details}
          </p>
        )}
      </div>

      {/* Botones de acción */}
      {!isConfirmed && (
        <div className="pt-2 flex items-center justify-end gap-2 border-t border-border/40">
          <button
            type="button"
            data-testid="action-card-discard-btn"
            onClick={() => setIsDismissed(true)}
            disabled={isProcessing}
            className="h-8 px-3 rounded-lg text-xs font-medium text-muted-foreground hover:text-foreground hover:bg-secondary transition-colors cursor-pointer"
          >
            Descartar
          </button>

          <button
            type="button"
            data-testid="action-card-confirm-btn"
            onClick={handleConfirm}
            disabled={isProcessing}
            className="h-8 text-xs px-3.5 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white font-medium flex items-center gap-1.5 shadow-sm transition-colors cursor-pointer"
          >
            {isProcessing ? (
              <>
                <Loader2 className="w-3 h-3 animate-spin" />
                Registrando...
              </>
            ) : (
              <>
                <CheckCircle2 className="w-3.5 h-3.5" />
                Confirmar y Registrar
              </>
            )}
          </button>
        </div>
      )}
    </div>
  );
}

export default ActionConfirmationCard;
