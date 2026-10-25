// oppytec-frontend/src/features/inventory/recuentos/RecuentoCard.tsx
import { useState } from "react";
import { useTranslation } from "react-i18next";
import {
  ClipboardCheck,
  Calendar,
  User,
  ChevronDown,
  ChevronUp,
  CheckCircle2,
  XCircle,
  Trash2,
  Edit,
  Eye,
  Info,
} from "lucide-react";
import { CategoryIcon } from "@/shared/components/ui/CategoryIcon";
import { useCurrencyFormatter } from "@/shared/currency";
import type { PhysicalCountSession, PhysicalCountState } from "../types";

export interface RecuentoCardProps {
  readonly session: PhysicalCountSession;
  readonly isExpanded: boolean;
  readonly onToggleExpand: () => void;
  readonly onOpenDetailModal: () => void;
  readonly onApprove: (sessionId: number) => Promise<unknown>;
  readonly onReject: (sessionId: number) => Promise<unknown>;
  readonly onDelete: (sessionId: number) => Promise<unknown>;
  readonly isApproving?: boolean;
  readonly isRejecting?: boolean;
  readonly isDeleting?: boolean;
  readonly isPropietario?: boolean;
}

export function RecuentoCard({
  session,
  isExpanded,
  onToggleExpand,
  onOpenDetailModal,
  onApprove,
  onReject,
  onDelete,
  isApproving = false,
  isRejecting = false,
  isDeleting = false,
  isPropietario = true,
}: RecuentoCardProps) {
  const { t } = useTranslation("inventory");
  const { convertAndFormat } = useCurrencyFormatter();
  const [confirmReject, setConfirmReject] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);

  const getStatusBadge = (estado: PhysicalCountState) => {
    switch (estado) {
      case "EN_PROGRESO":
        return (
          <span className="inline-flex items-center gap-1 rounded-full border border-blue-500/20 bg-blue-500/10 px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-wider text-blue-400">
            {t("recuentos.card.status.in_progress", "En Progreso")}
          </span>
        );
      case "PENDIENTE_APROBACION":
        return (
          <span className="inline-flex items-center gap-1 rounded-full border border-amber-500/20 bg-amber-500/10 px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-wider text-amber-400">
            {t("recuentos.card.status.pending", "Pendiente")}
          </span>
        );
      case "APROBADO":
        return (
          <span className="inline-flex items-center gap-1 rounded-full border border-emerald-500/20 bg-emerald-500/10 px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-wider text-emerald-400">
            {t("recuentos.card.status.approved", "Aprobado")}
          </span>
        );
      case "RECHAZADO":
        return (
          <span className="inline-flex items-center gap-1 rounded-full border border-rose-500/20 bg-rose-500/10 px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-wider text-rose-400">
            {t("recuentos.card.status.rejected", "Rechazado")}
          </span>
        );
      case "ANULADO":
        return (
          <span className="inline-flex items-center gap-1 rounded-full border border-zinc-500/20 bg-zinc-500/10 px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-wider text-zinc-400">
            {t("recuentos.card.status.cancelled", "Anulado")}
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center rounded-full border border-border bg-secondary px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-wider text-foreground">
            {estado}
          </span>
        );
    }
  };

  const formatDate = (isoStr: string) => {
    try {
      return new Date(isoStr).toLocaleString("es-CL", {
        day: "2-digit",
        month: "2-digit",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      return isoStr;
    }
  };

  // Cálculos de discrepancias
  const sobrantesUnidades = session.items
    .filter((i) => i.diferencia_unidades > 0)
    .reduce((acc, i) => acc + i.diferencia_unidades, 0);

  const faltantesUnidades = session.items
    .filter((i) => i.diferencia_unidades < 0)
    .reduce((acc, i) => acc + Math.abs(i.diferencia_unidades), 0);

  const totalValorizacion = session.items.reduce(
    (acc, i) => acc + (i.valorizacion_diferencia || 0),
    0
  );

  return (
    <div
      data-testid={`recuento-card-${session.id}`}
      className="glass-card rounded-2xl border border-border/70 shadow-sm transition-all overflow-hidden hover:border-purple-500/40"
    >
      {/* Cabecera / Tarjeta principal interactiva */}
      <div
        role="button"
        tabIndex={0}
        onClick={onToggleExpand}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            onToggleExpand();
          }
        }}
        className="p-4 sm:p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4 cursor-pointer hover:bg-white/[0.02] transition-colors"
      >
        <div className="flex items-start sm:items-center gap-3.5">
          <div className="h-11 w-11 rounded-2xl bg-purple-500/10 flex items-center justify-center border border-purple-500/20 text-purple-400 shrink-0 shadow-inner">
            <ClipboardCheck className="h-5 w-5" />
          </div>

          <div className="space-y-1">
            <div className="flex items-center gap-2.5 flex-wrap">
              <span className="font-extrabold text-base tracking-tight text-foreground">
                {session.bodega_nombre}
              </span>
              <span className="text-xs font-mono font-bold text-muted-foreground">
                #{session.id}
              </span>
              {getStatusBadge(session.estado)}
            </div>

            <div className="flex items-center gap-3 text-xs text-muted-foreground flex-wrap">
              <span className="flex items-center gap-1 font-medium">
                <Calendar className="h-3.5 w-3.5 text-purple-400" />
                {formatDate(session.fecha_inicio)}
              </span>
              <span className="flex items-center gap-1 font-medium">
                <User className="h-3.5 w-3.5 text-purple-400" />
                {session.responsable_nombre}
              </span>
              <span className="font-bold text-foreground">
                {session.items.length === 1
                  ? t("recuentos.card.items_count_one", "1 insumo")
                  : t("recuentos.card.items_count_other", { count: session.items.length, defaultValue: `${session.items.length} insumos` })}
              </span>
            </div>
          </div>
        </div>

        {/* Totales y Discrepancias + Botones rápidos */}
        <div className="flex items-center justify-between sm:justify-end gap-4 w-full sm:w-auto border-t sm:border-t-0 border-border/50 pt-3 sm:pt-0">
          <div className="flex items-center gap-3 text-right">
            <div>
              <span className="text-[10px] text-muted-foreground uppercase font-bold block">
                {t("recuentos.card.discrepancy", "Discrepancia")}
              </span>
              <div className="flex items-center gap-1.5 text-xs font-mono font-extrabold">
                {sobrantesUnidades > 0 && (
                  <span className="text-emerald-500">+{sobrantesUnidades.toFixed(1)}</span>
                )}
                {faltantesUnidades > 0 && (
                  <span className="text-rose-500">-{faltantesUnidades.toFixed(1)}</span>
                )}
                {sobrantesUnidades === 0 && faltantesUnidades === 0 && (
                  <span className="text-muted-foreground">{t("recuentos.card.exact_zero", "Exacto (0)")}</span>
                )}
              </div>
            </div>

            <div className="pl-2 border-l border-border/60">
              <span className="text-[10px] text-muted-foreground uppercase font-bold block">
                {t("recuentos.card.valuation", "Valorización")}
              </span>
              <span
                className={`text-xs font-mono font-black ${
                  totalValorizacion > 0
                    ? "text-emerald-500"
                    : totalValorizacion < 0
                    ? "text-rose-500"
                    : "text-muted-foreground"
                }`}
              >
                {totalValorizacion > 0 ? "+" : ""}
                {convertAndFormat(totalValorizacion, "CLP")}
              </span>
            </div>
          </div>

          <div className="flex items-center gap-1.5 shrink-0">
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                onOpenDetailModal();
              }}
              className="touch-target inline-flex h-9 w-9 items-center justify-center rounded-xl border border-border bg-secondary/80 text-foreground hover:bg-secondary transition-colors"
              title={t("recuentos.card.view_detail_title", "Ver detalle completo / Editar")}
              aria-label={t("recuentos.card.view_detail_aria", "Ver detalle de recuento")}
            >
              <Eye className="h-4 w-4 text-purple-400" />
            </button>

            <button
              type="button"
              aria-label={isExpanded ? t("recuentos.card.collapse_aria", "Colapsar detalle") : t("recuentos.card.expand_aria", "Expandir detalle")}
              className="touch-target inline-flex h-9 w-9 items-center justify-center rounded-xl text-muted-foreground hover:text-foreground transition-colors"
            >
              {isExpanded ? (
                <ChevronUp className="h-4 w-4" />
              ) : (
                <ChevronDown className="h-4 w-4" />
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Detalle expandible con tabla de insumos y botones de acción */}
      {isExpanded && (
        <div
          data-testid={`recuento-detail-${session.id}`}
          className="border-t border-border/60 bg-secondary/20 p-4 sm:p-5 space-y-4 animate-in fade-in duration-200"
        >
          {session.notas && (
            <div className="p-3 rounded-xl bg-card/60 border border-border text-xs text-muted-foreground flex items-start gap-2">
              <Info className="h-4 w-4 text-purple-400 shrink-0 mt-0.5" />
              <div>
                <span className="font-bold text-foreground">{t("recuentos.card.observations_title", "Observaciones de la toma: ")}</span>
                {session.notas}
              </div>
            </div>
          )}

          {/* Tabla de Insumos */}
          <div className="overflow-x-auto rounded-xl border border-border bg-card">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-border bg-muted/60 text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
                  <th className="p-3 pl-4">{t("recuentos.card.col_product", "Producto")}</th>
                  <th className="p-3 text-center">{t("recuentos.card.col_unit", "Unidad")}</th>
                  <th className="p-3 text-right">{t("recuentos.card.col_theoretical", "Stock Teórico")}</th>
                  <th className="p-3 text-right">{t("recuentos.card.col_counted", "Físico Contado")}</th>
                  <th className="p-3 text-right">{t("recuentos.card.col_diff", "Diferencia")}</th>
                  <th className="p-3 text-right pr-4">{t("recuentos.card.col_valuation", "Valorización PPP")}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {session.items.map((item) => {
                  const diff = item.diferencia_unidades;
                  const isSurplus = diff > 0.0001;
                  const isShortage = diff < -0.0001;
                  const val = item.valorizacion_diferencia || diff * item.costo_unitario_ppp;

                  return (
                    <tr
                      key={item.id}
                      className="hover:bg-white/[0.01] transition-colors"
                    >
                      <td className="p-3 pl-4 font-bold text-foreground">
                        <div className="flex items-center gap-2">
                          <CategoryIcon name="package" className="h-3.5 w-3.5 text-purple-400 shrink-0" />
                          <div>
                            <span>{item.producto_nombre}</span>
                            {item.lote_codigo && (
                              <span className="block text-[10px] text-muted-foreground font-normal">
                                {t("recuentos.card.lot_label", { code: item.lote_codigo, defaultValue: `Lote: ${item.lote_codigo}` })}
                              </span>
                            )}
                          </div>
                        </div>
                      </td>
                      <td className="p-3 text-center text-muted-foreground font-mono">
                        {item.unidad_medida}
                      </td>
                      <td className="p-3 text-right text-muted-foreground font-mono">
                        {item.stock_teorico_sistema.toFixed(2)}
                      </td>
                      <td className="p-3 text-right font-mono font-black text-foreground">
                        {item.stock_fisico_contado.toFixed(2)}
                      </td>
                      <td className="p-3 text-right font-mono font-bold">
                        <span
                          className={
                            isSurplus
                              ? "text-emerald-500"
                              : isShortage
                              ? "text-rose-500"
                              : "text-muted-foreground"
                          }
                        >
                          {diff > 0 ? `+${diff.toFixed(2)}` : diff.toFixed(2)}
                        </span>
                      </td>
                      <td className="p-3 pr-4 text-right font-mono font-extrabold">
                        <span
                          className={
                            val > 0
                              ? "text-emerald-500"
                              : val < 0
                              ? "text-rose-500"
                              : "text-muted-foreground"
                          }
                        >
                          {val > 0 ? "+" : ""}
                          {convertAndFormat(val, "CLP")}
                        </span>
                      </td>
                    </tr>
                  );
                })}

                {session.items.length === 0 && (
                  <tr>
                    <td colSpan={6} className="p-4 text-center text-muted-foreground italic">
                      {t("recuentos.card.empty_items", "Sin insumos registrados.")}
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          {/* Barra de Acciones y Conciliación */}
          <div className="flex flex-wrap items-center justify-between gap-3 pt-2">
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={onOpenDetailModal}
                className="touch-target inline-flex min-h-[44px] items-center gap-1.5 rounded-xl border border-border bg-card px-3.5 py-1.5 text-xs font-semibold text-foreground hover:bg-secondary transition-colors"
              >
                <Edit className="h-3.5 w-3.5 text-purple-400" />
                {isPropietario ? t("recuentos.card.edit_quantities", "Editar Cantidades") : t("recuentos.card.view_report", "Ver Acta")}
              </button>

              {isPropietario && (
                <>
                  {confirmDelete ? (
                    <div className="flex items-center gap-1.5">
                      <button
                        type="button"
                        disabled={isDeleting}
                        onClick={() => onDelete(session.id)}
                        className="touch-target inline-flex min-h-[44px] items-center gap-1 rounded-xl bg-rose-600 px-3 py-1.5 text-xs font-bold text-white hover:bg-rose-700 transition-colors"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                        {isDeleting ? t("recuentos.card.deleting", "Eliminando...") : t("recuentos.card.confirm_delete_btn", "¿Confirmar Eliminación?")}
                      </button>
                      <button
                        type="button"
                        onClick={() => setConfirmDelete(false)}
                        className="touch-target inline-flex min-h-[44px] items-center rounded-xl border border-border px-2.5 py-1.5 text-xs text-muted-foreground"
                      >
                        {t("recuentos.card.cancel", "Cancelar")}
                      </button>
                    </div>
                  ) : (
                    <button
                      type="button"
                      onClick={() => setConfirmDelete(true)}
                      className="touch-target inline-flex min-h-[44px] items-center gap-1.5 rounded-xl border border-border bg-card px-3 py-1.5 text-xs font-semibold text-rose-500 hover:bg-rose-500/10 transition-colors"
                      title={t("recuentos.card.delete", "Eliminar")}
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                      {t("recuentos.card.delete", "Eliminar")}
                    </button>
                  )}
                </>
              )}
            </div>

            {/* Acciones de Aprobación / Rechazo (Solo si está PENDIENTE_APROBACION) */}
            {session.estado === "PENDIENTE_APROBACION" && (
              <div className="flex items-center gap-2">
                {confirmReject ? (
                  <div className="flex items-center gap-1.5">
                    <button
                      type="button"
                      disabled={isRejecting}
                      onClick={() => onReject(session.id)}
                      className="touch-target inline-flex min-h-[44px] items-center gap-1 rounded-xl bg-rose-600 px-3 py-1.5 text-xs font-bold text-white hover:bg-rose-700 transition-colors"
                    >
                      <XCircle className="h-3.5 w-3.5" />
                      {isRejecting ? t("recuentos.card.rejecting", "Rechazando...") : t("recuentos.card.confirm_reject_btn", "¿Confirmar Rechazo?")}
                    </button>
                    <button
                      type="button"
                      onClick={() => setConfirmReject(false)}
                      className="touch-target inline-flex min-h-[44px] items-center rounded-xl border border-border px-2.5 py-1.5 text-xs text-muted-foreground"
                    >
                      {t("recuentos.card.cancel", "Cancelar")}
                    </button>
                  </div>
                ) : (
                  <button
                    type="button"
                    onClick={() => setConfirmReject(true)}
                    className="touch-target inline-flex min-h-[44px] items-center gap-1.5 rounded-xl border border-rose-500/30 bg-rose-500/10 px-3.5 py-1.5 text-xs font-bold text-rose-400 hover:bg-rose-500/20 transition-colors"
                  >
                    <XCircle className="h-3.5 w-3.5" />
                    {t("recuentos.card.reject_report", "Rechazar Acta")}
                  </button>
                )}

                <button
                  type="button"
                  disabled={isApproving}
                  onClick={() => onApprove(session.id)}
                  className="touch-target inline-flex min-h-[44px] items-center gap-1.5 rounded-xl bg-emerald-600 px-4 py-2 text-xs font-bold text-white hover:bg-emerald-700 transition-colors shadow-lg shadow-emerald-600/20 disabled:opacity-50"
                >
                  <CheckCircle2 className="h-4 w-4" />
                  {isApproving ? t("recuentos.card.reconciling", "Conciliando...") : t("recuentos.card.approve_reconcile", "Aprobar y Conciliar Stock")}
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default RecuentoCard;
