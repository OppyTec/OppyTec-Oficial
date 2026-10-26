// oppytec-frontend/src/features/consumo/components/buffet/BuffetConciliationDialog.tsx
import { useState, useMemo } from "react";
import { useTranslation } from "react-i18next";
import {
  Calculator,
  Users,
  DollarSign,
  Check,
  ShieldCheck,
  Loader2,
} from "lucide-react";
import { toast } from "sonner";
import { useCurrencyFormatter } from "@/shared/currency";
import type { BuffetSession } from "../../types";

export interface BuffetConciliationDialogProps {
  open: boolean;
  onClose: () => void;
  session: BuffetSession | null;
  onFinalize: (pax: number, valorSobrante: number) => Promise<void> | void;
  isFinalizing?: boolean;
}

export function BuffetConciliationDialog({
  open,
  onClose,
  session,
  onFinalize,
  isFinalizing = false,
}: BuffetConciliationDialogProps) {
  const { t } = useTranslation("operations");
  const { format } = useCurrencyFormatter();
  const [paxInput, setPaxInput] = useState<string>(() =>
    String(session?.pax_comensales ?? 50)
  );
  const [sobranteInput, setSobranteInput] = useState<string>(() =>
    String(session?.valor_sobrante_reutilizable ?? 25000)
  );

  const costoMontaje = session?.costo_total_montaje ?? 120000;
  const pax = Math.max(1, parseInt(paxInput, 10) || 1);
  const valorSobrante = Math.max(0, parseFloat(sobranteInput) || 0);

  const costoNetoConsumido = Math.max(0, costoMontaje - valorSobrante);
  const costoNetoPax = useMemo(() => {
    return +(costoNetoConsumido / pax).toFixed(2);
  }, [costoNetoConsumido, pax]);

  const itemsResumen = useMemo(() => {
    if (!session?.items) return { retornan: 0, merman: 0, consumidos: 0 };
    let retornan = 0;
    let merman = 0;
    let consumidos = 0;

    session.items.forEach((it) => {
      consumidos += it.cantidad_consumida ?? 0;
      if (it.accion_sobrante === "retornar") {
        retornan += it.cantidad_sobrante ?? 0;
      } else {
        merman += it.cantidad_sobrante ?? 0;
      }
    });

    return { retornan, merman, consumidos };
  }, [session]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (pax <= 0 || isNaN(pax)) {
      toast.error(
        t("consumption.buffet.conciliation.pax_error", {
          defaultValue: "El número de comensales (Pax) debe ser mayor a 0",
        })
      );
      return;
    }

    try {
      await onFinalize(pax, valorSobrante);
      onClose();
    } catch {
      // Error handled by hook toast
    }
  };

  if (!open) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Liquidación y Conciliación de Buffet"
      data-testid="buffet-conciliation-dialog"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4 overflow-y-auto"
    >
      <div className="w-full max-w-xl rounded-3xl bg-card border border-border text-foreground shadow-2xl overflow-hidden my-auto flex flex-col">
        {/* Encabezado */}
        <div className="px-6 py-4 border-b border-border bg-muted/40 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center text-cyan-400">
              <Calculator className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-foreground">
                {t("consumption.buffet.conciliation.title", { defaultValue: "Liquidación y Conciliación de Buffet" })}
              </h3>
              <p className="text-xs text-muted-foreground">
                Cuadratura de consumo real, remanentes y costeo unitario Pax
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            disabled={isFinalizing}
            data-testid="close-conciliation-btn"
            className="touch-target px-3 py-1.5 rounded-xl bg-secondary text-secondary-foreground text-xs font-semibold cursor-pointer"
          >
            Cancelar
          </button>
        </div>

        {/* Formulario */}
        <form onSubmit={handleSubmit} className="p-6 space-y-5">
          {/* Tarjeta de Métricas Clave */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <div className="p-3 rounded-2xl bg-muted/30 border border-border/50 text-center">
              <span className="text-[10px] uppercase font-bold text-muted-foreground block mb-1">
                {t("consumption.buffet.metrics.total_montaje", { defaultValue: "Costo Montaje" })}
              </span>
              <span className="text-sm font-mono font-bold text-foreground" data-testid="costo-montaje-val">
                {format(costoMontaje)}
              </span>
            </div>

            <div className="p-3 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 text-center">
              <span className="text-[10px] uppercase font-bold text-emerald-500 block mb-1">
                {t("consumption.buffet.metrics.total_sobrante", { defaultValue: "Sobrante Devuelto" })}
              </span>
              <span className="text-sm font-mono font-bold text-emerald-400" data-testid="sobrante-devuelto-val">
                -{format(valorSobrante)}
              </span>
            </div>

            <div className="p-3 rounded-2xl bg-cyan-500/10 border border-cyan-500/20 text-center">
              <span className="text-[10px] uppercase font-bold text-cyan-500 block mb-1">
                {t("consumption.buffet.metrics.total_consumido", { defaultValue: "Consumo Neto" })}
              </span>
              <span className="text-sm font-mono font-bold text-cyan-400" data-testid="consumo-neto-val">
                {format(costoNetoConsumido)}
              </span>
            </div>

            <div className="p-3 rounded-2xl bg-gradient-to-br from-cyan-500/20 to-teal-500/20 border border-cyan-500/30 text-center shadow-xs">
              <span className="text-[10px] uppercase font-bold text-cyan-300 block mb-1">
                {t("consumption.buffet.metrics.costo_pax", { defaultValue: "Costo / Pax" })}
              </span>
              <span className="text-base font-mono font-black text-cyan-400" data-testid="costo-pax-val">
                {format(costoNetoPax)}
              </span>
            </div>
          </div>

          {/* Inputs de Comensales y Valoración de Sobrante */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label
                htmlFor="pax-input"
                className="block text-xs font-bold text-foreground mb-1.5 flex items-center gap-1.5"
              >
                <Users className="w-3.5 h-3.5 text-cyan-500" />
                {t("consumption.buffet.conciliation.pax_label", { defaultValue: "Comensales Atendidos (Pax)" })}
              </label>
              <input
                id="pax-input"
                type="number"
                min="1"
                step="1"
                value={paxInput}
                onChange={(e) => setPaxInput(e.target.value)}
                required
                data-testid="pax-input"
                className="w-full px-3.5 py-2.5 rounded-xl bg-background border border-border text-foreground font-mono text-sm focus:border-cyan-500 focus:outline-none"
              />
              <span className="text-[11px] text-muted-foreground mt-1 block">
                Total de clientes comensales registrados en salón.
              </span>
            </div>

            <div>
              <label
                htmlFor="sobrante-val-input"
                className="block text-xs font-bold text-foreground mb-1.5 flex items-center gap-1.5"
              >
                <DollarSign className="w-3.5 h-3.5 text-emerald-500" />
                {t("consumption.buffet.conciliation.leftover_value_label", { defaultValue: "Valor Sobrante Reutilizable ($)" })}
              </label>
              <input
                id="sobrante-val-input"
                type="number"
                min="0"
                step="100"
                value={sobranteInput}
                onChange={(e) => setSobranteInput(e.target.value)}
                data-testid="sobrante-val-input"
                className="w-full px-3.5 py-2.5 rounded-xl bg-background border border-border text-foreground font-mono text-sm focus:border-cyan-500 focus:outline-none"
              />
              <span className="text-[11px] text-muted-foreground mt-1 block">
                Valorización de bandejas retornadas intactas a almacén.
              </span>
            </div>
          </div>

          {/* Resumen de Impacto en Kardex */}
          <div className="p-4 rounded-2xl bg-muted/40 border border-border/60 space-y-2">
            <span className="text-xs font-bold text-foreground flex items-center gap-1.5">
              <ShieldCheck className="w-4 h-4 text-emerald-400" />
              Impacto Inmediato en Kardex y Contabilidad
            </span>
            <ul className="text-xs text-muted-foreground space-y-1 pl-5 list-disc">
              <li>
                Descuento permanente de consumo neto de productos y recetas por un total de{" "}
                <span className="text-foreground font-bold">{format(costoNetoConsumido)}</span>.
              </li>
              <li>
                Retorno de stock para remanentes reutilizables ({itemsResumen.retornan} unidades).
              </li>
              <li>
                Generación automática de asiento de merma de cocina ({itemsResumen.merman} unidades).
              </li>
            </ul>
          </div>

          {/* Botones de Acción */}
          <div className="flex items-center justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              disabled={isFinalizing}
              className="px-4 py-2.5 rounded-xl bg-secondary text-secondary-foreground text-xs font-semibold cursor-pointer"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={isFinalizing}
              data-testid="confirm-finalize-buffet-btn"
              className="touch-target px-5 py-2.5 rounded-xl bg-gradient-to-r from-cyan-500 to-teal-500 hover:from-cyan-400 hover:to-teal-400 text-black font-bold text-xs flex items-center gap-2 shadow-lg shadow-cyan-500/20 cursor-pointer disabled:opacity-50"
            >
              {isFinalizing ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  {t("consumption.buffet.conciliation.finalizing", { defaultValue: "Liquidando Kardex..." })}
                </>
              ) : (
                <>
                  <Check className="w-4 h-4 stroke-[3]" />
                  {t("consumption.buffet.conciliation.finalize_btn", { defaultValue: "Finalizar y Liquidar Buffet" })}
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
