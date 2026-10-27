import { useState, useEffect, useMemo } from "react";
import {
  X,
  ChefHat,
  Scale,
  Clock,
  Sparkles,
  ScrollText,
  Video,
  FileText,
  Pencil,
  Layers,
  Printer,
  ShieldAlert,
} from "lucide-react";
import { useTranslation } from "react-i18next";
import { cn } from "@/shared/lib";
import { useCurrencyFormatter } from "@/shared/currency";
import { INITIAL_GRUPOS_OPCIONES_MOCK } from "../hooks/useGruposOpciones";
import { AllergenBadge } from "./AllergenBadge";
import type { Receta, GrupoOpciones, AllergenInfo } from "../types";

export interface RecetaDetalleModalProps {
  open: boolean;
  onClose: () => void;
  receta: Receta | null;
  gruposBiblioteca?: GrupoOpciones[];
  onEdit?: (receta: Receta) => void;
  alergenos?: AllergenInfo[];
}

export function RecetaDetalleModal({
  open,
  onClose,
  receta,
  gruposBiblioteca = INITIAL_GRUPOS_OPCIONES_MOCK,
  onEdit,
  alergenos: propAlergenos,
}: RecetaDetalleModalProps) {
  const { t } = useTranslation("recipes");
  const { convertAndFormat } = useCurrencyFormatter();

  const baseYield = useMemo(() => {
    if (!receta) return 1;
    return Math.max(1, Number(receta.porciones_rendimiento || receta.porciones || 1));
  }, [receta]);

  const [targetPortions, setTargetPortions] = useState<number>(1);

  useEffect(() => {
    if (open && receta) {
      setTargetPortions(
        Math.max(1, Number(receta.porciones_rendimiento || receta.porciones || 1))
      );
    }
  }, [open, receta]);

  const scaleFactor = useMemo(() => {
    const safeTarget = Math.max(0.1, Number(targetPortions) || 1);
    return safeTarget / baseYield;
  }, [targetPortions, baseYield]);

  const scaledIngredients = useMemo(() => {
    if (!receta?.ingredientes_fijos) return [];
    return receta.ingredientes_fijos.map((ing) => {
      const baseNetQty = Number(ing.cantidad_receta) || 0;
      const mermaPct = Math.min(99.99, Math.max(0, Number(ing.porcentaje_merma) || 0));
      const unitCost = Number(ing.costo_unitario) || 0;

      const scaledNetQty = Number((baseNetQty * scaleFactor).toFixed(3));
      const grossMultiplier = mermaPct > 0 ? 1 / (1 - mermaPct / 100) : 1;
      const scaledGrossQty = Number((scaledNetQty * grossMultiplier).toFixed(3));
      const scaledCost = Number((scaledGrossQty * unitCost).toFixed(2));

      return {
        ...ing,
        scaledNetQty,
        scaledGrossQty,
        scaledCost,
      };
    });
  }, [receta, scaleFactor]);

  const totalScaledCost = useMemo(() => {
    if (!receta) return 0;
    const baseTotal = receta.costo_total_calculado ?? receta.costo_total ?? 0;
    return Number((baseTotal * scaleFactor).toFixed(2));
  }, [receta, scaleFactor]);

  const consolidatedAllergens = useMemo<AllergenInfo[]>(() => {
    if (propAlergenos && propAlergenos.length > 0) return propAlergenos;
    if (!receta) return [];
    const list = receta.alergenos || receta.allergens || [];
    return list;
  }, [propAlergenos, receta]);

  const handlePrint = () => {
    if (typeof window !== "undefined" && typeof window.print === "function") {
      window.print();
    }
  };

  if (!open || !receta) return null;

  const portionUnitCost =
    receta.costo_porcion ??
    ((receta.costo_total_calculado ?? receta.costo_total ?? 0) / baseYield);

  return (
    <div
      data-testid="receta-detalle-modal"
      role="dialog"
      aria-modal="true"
      aria-label={t("modals.recipe_detail.modal_title")}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-2 sm:p-4 overflow-y-auto"
    >
      {/* CSS @media print para optimización de impresión A4 / Ticket térmico de cocina */}
      <style>{`
        @media print {
          body * {
            visibility: hidden !important;
          }
          #printable-kitchen-sheet, #printable-kitchen-sheet * {
            visibility: visible !important;
          }
          #printable-kitchen-sheet {
            position: absolute !important;
            left: 0 !important;
            top: 0 !important;
            width: 100% !important;
            min-height: 100vh !important;
            margin: 0 !important;
            padding: 24px !important;
            background: #ffffff !important;
            color: #111827 !important;
            box-shadow: none !important;
            border: none !important;
            overflow: visible !important;
          }
          .no-print, [data-testid="receta-portion-scaler"], button, [data-testid="link-detalle-video"], [data-testid="link-detalle-documento"] {
            display: none !important;
          }
          .print-header-kitchen {
            display: block !important;
          }
        }
        @media screen {
          .print-header-kitchen {
            display: none;
          }
        }
      `}</style>

      <div className="relative w-full max-w-4xl rounded-2xl border border-border bg-card text-foreground shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header Modal UI (Oculto en impresión) */}
        <div className="flex items-center justify-between border-b border-border px-5 py-4 bg-muted/30 no-print">
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-amber-500/15 text-amber-500">
              <ChefHat className="h-6 w-6" />
            </div>
            <div>
              <div className="flex items-center gap-2 flex-wrap">
                {receta.codigo && (
                  <span className="font-mono text-[10px] font-bold px-2 py-0.5 rounded bg-muted text-muted-foreground border border-border">
                    {receta.codigo}
                  </span>
                )}
                {receta.es_dinamica ? (
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-extrabold bg-purple-500/15 text-purple-600 dark:text-purple-400">
                    <Sparkles className="h-3 w-3" />
                    <span>{t("badges.dynamic")}</span>
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-extrabold bg-slate-500/15 text-slate-600 dark:text-slate-300">
                    <ScrollText className="h-3 w-3" />
                    <span>{t("badges.static")}</span>
                  </span>
                )}
              </div>
              <h2 className="text-base sm:text-lg font-extrabold text-foreground">
                {receta.nombre}
              </h2>
              <p className="text-xs text-muted-foreground">
                {t("modals.recipe_detail.modal_subtitle")}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={handlePrint}
              data-testid="btn-print-receta-detalle"
              aria-label={t("modals.recipe_detail.btn_print_sheet")}
              className="inline-flex min-h-[44px] items-center gap-1.5 px-3 py-1.5 rounded-xl border border-border bg-card text-foreground hover:bg-secondary transition-colors cursor-pointer text-xs font-bold"
            >
              <Printer className="h-4 w-4 text-amber-500" />
              <span className="hidden sm:inline">
                {t("modals.recipe_detail.btn_print_sheet")}
              </span>
            </button>

            <button
              type="button"
              onClick={onClose}
              data-testid="btn-close-receta-detalle"
              aria-label={t("modals.common.close")}
              className="inline-flex min-h-[44px] min-w-[44px] items-center justify-center rounded-xl text-muted-foreground hover:bg-secondary hover:text-foreground transition-colors cursor-pointer"
            >
              <X className="h-5 w-5" />
            </button>
          </div>
        </div>

        {/* Printable & Scrollable Body */}
        <div id="printable-kitchen-sheet" className="flex-1 overflow-y-auto p-5 space-y-5">
          {/* Encabezado Exclusivo para Impresión y Ticket de Cocina */}
          <div
            data-testid="kitchen-print-header"
            className="print-header-kitchen border-b-2 border-black pb-4 text-black mb-4"
          >
            <div className="flex items-center justify-between">
              <div>
                <h1 className="text-xl font-black uppercase tracking-tight">
                  {t("modals.recipe_detail.kitchen_header_title")}
                </h1>
                <p className="text-xs font-semibold text-gray-700">
                  {t("modals.recipe_detail.kitchen_header_restaurant")}
                </p>
              </div>
              <div className="text-right">
                <div className="text-xs font-mono font-bold">
                  {t("modals.recipe_detail.kitchen_date")}:{" "}
                  {new Date().toLocaleDateString()}
                </div>
                <div className="text-xs font-black uppercase tracking-wide">
                  {t("modals.recipe_detail.kitchen_ticket_order")}
                </div>
              </div>
            </div>
            <div className="mt-3 pt-2 border-t border-gray-400 grid grid-cols-2 gap-2 text-xs">
              <div>
                <span className="font-bold">
                  {t("modals.recipe_detail.kitchen_dish_label")}
                </span>
                <span className="font-black text-sm">{receta.nombre}</span>{" "}
                {receta.codigo && (
                  <span className="font-mono font-bold">[{receta.codigo}]</span>
                )}
              </div>
              <div className="text-right">
                <span className="font-bold">
                  {t("modals.recipe_detail.kitchen_portions_label")}
                </span>
                <span className="font-black text-sm">
                  {t("modals.recipe_detail.kitchen_portions_value", {
                    count: targetPortions,
                  })}
                </span>{" "}
                <span className="text-gray-600">
                  ({Number(scaleFactor.toFixed(2))}x)
                </span>
              </div>
            </div>
          </div>

          {/* Interactive Portion Scaler Bar (Oculto en Print) */}
          <div
            data-testid="receta-portion-scaler"
            className="rounded-2xl border border-amber-500/30 bg-amber-500/10 p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4 no-print"
          >
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <Scale className="h-4 w-4 text-amber-500" />
                <span className="text-xs sm:text-sm font-extrabold text-foreground">
                  {t("modals.recipe_detail.scaler_title")}
                </span>
                <span
                  data-testid="scaler-factor-badge"
                  className="px-2 py-0.5 rounded-full text-[11px] font-black bg-amber-500 text-slate-950"
                >
                  {t("modals.recipe_detail.scaler_factor_badge", {
                    factor: Number(scaleFactor.toFixed(2)),
                  })}
                </span>
              </div>
              <p className="text-xs text-muted-foreground">
                {t("modals.recipe_detail.scaler_base_yield", { base: baseYield })}
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <label className="text-xs font-bold text-foreground">
                {t("modals.recipe_detail.scaler_target_label")}
              </label>
              <input
                type="number"
                min={1}
                step="1"
                value={targetPortions}
                onChange={(e) =>
                  setTargetPortions(Math.max(1, Number(e.target.value) || 1))
                }
                data-testid="input-scaler-porciones"
                className="w-20 min-h-[44px] px-3 rounded-xl border border-input bg-card text-sm font-black text-center"
              />

              {/* Quick preset buttons */}
              {([1, 10, 25, 50] as const).map((preset) => (
                <button
                  key={preset}
                  type="button"
                  onClick={() => setTargetPortions(preset)}
                  data-testid={`btn-preset-porciones-${preset}`}
                  className={cn(
                    "min-h-[44px] px-3 py-1.5 rounded-xl text-xs font-extrabold border transition-colors cursor-pointer",
                    targetPortions === preset
                      ? "bg-amber-500 text-slate-950 border-amber-500"
                      : "bg-card text-foreground border-border hover:bg-secondary"
                  )}
                >
                  {t(`modals.recipe_detail.preset_${preset}`)}
                </button>
              ))}
            </div>
          </div>

          {/* Sección Destacada de Alérgenos Normados (Fase 6) */}
          <div
            data-testid="detalle-alergenos-section"
            className="rounded-2xl border border-border bg-muted/20 p-4 space-y-3"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <ShieldAlert className="h-4 w-4 text-amber-500" />
                <h3 className="text-xs font-extrabold uppercase tracking-wider text-foreground">
                  {t("modals.recipe_detail.allergens_section")}
                </h3>
              </div>
              {consolidatedAllergens.length > 0 ? (
                <span
                  data-testid="badge-allergens-count"
                  className="px-2 py-0.5 rounded-full text-[10px] font-black bg-rose-500/15 text-rose-600 dark:text-rose-400 border border-rose-500/30"
                >
                  {t("modals.recipe_detail.allergens_detected_count", {
                    count: consolidatedAllergens.length,
                  })}
                </span>
              ) : (
                <span
                  data-testid="badge-allergens-none"
                  className="px-2 py-0.5 rounded-full text-[10px] font-black bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30"
                >
                  {t("modals.recipe_detail.allergens_zero")}
                </span>
              )}
            </div>

            {consolidatedAllergens.length > 0 ? (
              <div className="space-y-2">
                <div
                  data-testid="detalle-allergen-badges-list"
                  className="flex flex-wrap items-center gap-2"
                >
                  {consolidatedAllergens.map((alg) => (
                    <AllergenBadge
                      key={alg.code}
                      allergen={alg}
                      size="md"
                      showLabel={true}
                    />
                  ))}
                </div>
                <p className="text-[11px] text-rose-600 dark:text-rose-400 font-semibold italic">
                  {t("modals.recipe_detail.kitchen_sheet_warning")}
                </p>
              </div>
            ) : (
              <p
                data-testid="detalle-allergens-empty"
                className="text-xs text-muted-foreground italic"
              >
                {t("modals.recipe_detail.allergens_none")}
              </p>
            )}
          </div>

          {/* KPI Summary Strip */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div className="rounded-xl border border-border bg-muted/20 p-3">
              <div className="text-[11px] text-muted-foreground font-semibold">
                {t("modals.recipe_detail.kpi_Scaled_total_cost", {
                  portions: targetPortions,
                })}
              </div>
              <div
                data-testid="detalle-scaled-total-cost"
                className="text-base font-black text-foreground mt-0.5"
              >
                {convertAndFormat(totalScaledCost)}
              </div>
            </div>

            <div className="rounded-xl border border-border bg-muted/20 p-3">
              <div className="text-[11px] text-muted-foreground font-semibold">
                {t("modals.recipe_detail.kpi_unit_portion_cost")}
              </div>
              <div
                data-testid="detalle-unit-portion-cost"
                className="text-base font-black text-foreground mt-0.5"
              >
                {convertAndFormat(portionUnitCost)}
              </div>
            </div>

            <div className="rounded-xl border border-border bg-muted/20 p-3 flex items-center justify-between">
              <div>
                <div className="text-[11px] text-muted-foreground font-semibold">
                  {t("modals.recipe_detail.kpi_prep_time")}
                </div>
                <div className="text-base font-black text-foreground mt-0.5">
                  {t("modals.recipe_detail.minutes_unit", {
                    min: receta.tiempo_preparacion_minutos ?? 15,
                  })}
                </div>
              </div>
              <Clock className="h-5 w-5 text-amber-500" />
            </div>
          </div>

          {/* Scaled Ingredients Table */}
          <div className="space-y-2.5">
            <div className="flex items-center justify-between">
              <h3 className="text-xs font-extrabold uppercase tracking-wider text-muted-foreground">
                {t("modals.recipe_detail.ingredients_section")}
              </h3>
              <span className="text-[11px] font-bold text-amber-600 dark:text-amber-400">
                {t("modals.recipe_detail.scaled_portions_summary", {
                  portions: targetPortions,
                  factor: Number(scaleFactor.toFixed(2)),
                })}
              </span>
            </div>

            <div className="overflow-x-auto rounded-xl border border-border">
              <table
                data-testid="detalle-scaled-ingredients-table"
                className="w-full text-left border-collapse text-xs sm:text-sm"
              >
                <thead>
                  <tr className="border-b border-border bg-muted/40 text-[10px] font-black uppercase text-muted-foreground">
                    <th className="py-2.5 px-3">
                      {t("modals.recipe_detail.col_ingredient")}
                    </th>
                    <th className="py-2.5 px-3 text-right">
                      {t("modals.recipe_detail.col_net_qty")}
                    </th>
                    <th className="py-2.5 px-3 text-center">
                      {t("modals.recipe_detail.col_merma_pct")}
                    </th>
                    <th className="py-2.5 px-3 text-right">
                      {t("modals.recipe_detail.col_gross_qty")}
                    </th>
                    <th className="py-2.5 px-3 text-right">
                      {t("modals.recipe_detail.col_scaled_cost")}
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/60">
                  {scaledIngredients.map((ing, idx) => (
                    <tr
                      key={ing.id ?? idx}
                      data-testid={`scaled-ingredient-row-${idx}`}
                      className="hover:bg-muted/20"
                    >
                      <td className="py-2.5 px-3 font-bold text-foreground">
                        {ing.nombre}
                      </td>
                      <td
                        data-testid={`scaled-net-qty-${idx}`}
                        className="py-2.5 px-3 text-right font-semibold text-foreground"
                      >
                        {ing.scaledNetQty} {ing.unidad}
                      </td>
                      <td className="py-2.5 px-3 text-center text-muted-foreground">
                        {ing.porcentaje_merma}%
                      </td>
                      <td
                        data-testid={`scaled-gross-qty-${idx}`}
                        className="py-2.5 px-3 text-right font-extrabold text-amber-600 dark:text-amber-400"
                      >
                        {ing.scaledGrossQty} {ing.unidad}
                      </td>
                      <td
                        data-testid={`scaled-cost-${idx}`}
                        className="py-2.5 px-3 text-right font-bold text-foreground"
                      >
                        {convertAndFormat(ing.scaledCost)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Dynamic Groups Section */}
          {receta.es_dinamica &&
            receta.grupos_opciones &&
            receta.grupos_opciones.length > 0 && (
              <div
                data-testid="detalle-dynamic-groups-section"
                className="space-y-2.5 pt-2 border-t border-border"
              >
                <h3 className="text-xs font-extrabold uppercase tracking-wider text-purple-600 dark:text-purple-400 flex items-center gap-1.5">
                  <Layers className="h-4 w-4" />
                  <span>{t("modals.recipe_detail.dynamic_groups_section")}</span>
                </h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {receta.grupos_opciones.map((link, idx) => {
                    const resolvedGroup =
                      link.grupo ||
                      gruposBiblioteca.find(
                        (g) => String(g.id) === String(link.grupo_id)
                      );
                    return (
                      <div
                        key={link.id ?? idx}
                        className="rounded-xl border border-purple-500/30 bg-purple-500/5 p-3 space-y-1.5"
                      >
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-extrabold text-foreground">
                            {resolvedGroup?.nombre ||
                              t("modals.common.group_fallback", {
                                id: link.grupo_id,
                              })}
                          </span>
                          <span className="text-[10px] font-bold text-purple-600 dark:text-purple-400">
                            {link.es_requerido
                              ? t("modals.common.required")
                              : t("modals.common.optional")}
                          </span>
                        </div>
                        {resolvedGroup?.items && resolvedGroup.items.length > 0 && (
                          <div className="flex flex-wrap gap-1">
                            {resolvedGroup.items.map((it, i) => (
                              <span
                                key={it.id ?? i}
                                className="px-2 py-0.5 rounded bg-card border border-border text-[11px]"
                              >
                                {it.nombre} (
                                {Number(
                                  ((it.cantidad ?? 1) * scaleFactor).toFixed(2)
                                )}{" "}
                                {t("modals.recipe_detail.portion_abbr")})
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

          {/* Step-by-Step Preparation */}
          <div
            data-testid="detalle-preparacion-section"
            className="space-y-2 pt-2 border-t border-border"
          >
            <h3 className="text-xs font-extrabold uppercase tracking-wider text-muted-foreground">
              {t("modals.recipe_detail.prep_section")}
            </h3>
            <div className="rounded-xl border border-border bg-muted/20 p-4 text-xs sm:text-sm whitespace-pre-line text-foreground">
              {receta.preparacion || t("modals.recipe_detail.prep_empty")}
            </div>
          </div>

          {/* Multimedia & Document Links (Oculto en Print) */}
          {(receta.video_url || receta.documento_url) && (
            <div className="space-y-2 pt-2 border-t border-border no-print">
              <h3 className="text-xs font-extrabold uppercase tracking-wider text-muted-foreground">
                {t("modals.recipe_detail.resources_section")}
              </h3>
              <div className="flex flex-wrap gap-3">
                {receta.video_url && (
                  <a
                    href={receta.video_url}
                    target="_blank"
                    rel="noreferrer"
                    data-testid="link-detalle-video"
                    className="inline-flex min-h-[44px] items-center gap-2 px-4 py-2 rounded-xl bg-rose-500/15 text-rose-600 dark:text-rose-400 border border-rose-500/30 text-xs font-extrabold hover:bg-rose-500/25 transition-colors"
                  >
                    <Video className="h-4 w-4" />
                    <span>{t("modals.recipe_detail.link_video")}</span>
                  </a>
                )}
                {receta.documento_url && (
                  <a
                    href={receta.documento_url}
                    target="_blank"
                    rel="noreferrer"
                    data-testid="link-detalle-documento"
                    className="inline-flex min-h-[44px] items-center gap-2 px-4 py-2 rounded-xl bg-sky-500/15 text-sky-600 dark:text-sky-400 border border-sky-500/30 text-xs font-extrabold hover:bg-sky-500/25 transition-colors"
                  >
                    <FileText className="h-4 w-4" />
                    <span>{t("modals.recipe_detail.link_document")}</span>
                  </a>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Footer (Oculto en Print) */}
        <div className="flex items-center justify-between border-t border-border px-5 py-3.5 bg-muted/30 no-print">
          <button
            type="button"
            onClick={handlePrint}
            data-testid="btn-print-receta-footer"
            className="inline-flex min-h-[44px] items-center gap-1.5 rounded-xl border border-border bg-card px-4 py-2 text-xs font-extrabold text-foreground hover:bg-secondary transition-colors cursor-pointer"
          >
            <Printer className="h-4 w-4 text-amber-500" />
            <span>{t("modals.recipe_detail.btn_print_sheet")}</span>
          </button>

          <div className="flex items-center gap-2.5">
            {onEdit && (
              <button
                type="button"
                onClick={() => {
                  onClose();
                  onEdit(receta);
                }}
                data-testid="btn-detalle-edit-receta"
                className="inline-flex min-h-[44px] items-center gap-1.5 rounded-xl bg-amber-500 px-4 py-2 text-xs font-extrabold text-slate-950 hover:bg-amber-400 transition-colors cursor-pointer"
              >
                <Pencil className="h-4 w-4" />
                <span>{t("modals.common.edit")}</span>
              </button>
            )}
            <button
              type="button"
              onClick={onClose}
              data-testid="btn-close-detalle-footer"
              className="inline-flex min-h-[44px] items-center justify-center rounded-xl border border-border bg-secondary px-4 py-2 text-xs font-bold text-foreground hover:bg-secondary/80 transition-colors cursor-pointer"
            >
              {t("modals.common.close")}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default RecetaDetalleModal;
