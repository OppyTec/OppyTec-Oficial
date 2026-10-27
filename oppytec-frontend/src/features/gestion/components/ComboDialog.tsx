import { useState, useEffect, useMemo } from "react";
import {
  X,
  Boxes,
  Plus,
  Trash2,
  Sparkles,
  Library,
  Check,
  Calculator,
  Layers,
} from "lucide-react";
import { useTranslation } from "react-i18next";
import { cn } from "@/shared/lib";
import { useCurrencyFormatter } from "@/shared/currency";
import { getMargenBadge } from "./recetas/RecetasTable";
import { OptionGroupSelectorModal } from "./OptionGroupSelectorModal";
import { INITIAL_PRODUCTOS_MOCK } from "../useGestion";
import { INITIAL_RECETAS_MOCK } from "../hooks/useRecetas";
import { INITIAL_CATEGORIAS_COMBOS_MOCK } from "../hooks/useCombos";
import { INITIAL_GRUPOS_OPCIONES_MOCK } from "../hooks/useGruposOpciones";
import type {
  Combo,
  CategoriaCombo,
  Producto,
  Receta,
  ComboItemFijo,
  GrupoOpciones,
  ComboCreateInput,
} from "../types";

export interface ComboDialogProps {
  open: boolean;
  onClose: () => void;
  combo?: Combo | null;
  isDuplicate?: boolean;
  categorias?: CategoriaCombo[];
  productos?: Producto[];
  recetas?: Receta[];
  gruposBiblioteca?: GrupoOpciones[];
  onSave?: (payload: ComboCreateInput, calculatedCombo: Combo) => Promise<void> | void;
}

export function ComboDialog({
  open,
  onClose,
  combo = null,
  isDuplicate = false,
  categorias = INITIAL_CATEGORIAS_COMBOS_MOCK,
  productos = INITIAL_PRODUCTOS_MOCK,
  recetas = INITIAL_RECETAS_MOCK,
  gruposBiblioteca = INITIAL_GRUPOS_OPCIONES_MOCK,
  onSave,
}: ComboDialogProps) {
  const { t } = useTranslation("recipes");
  const { convertAndFormat } = useCurrencyFormatter();

  const [nombre, setNombre] = useState("");
  const [codigo, setCodigo] = useState("");
  const [categoriaId, setCategoriaId] = useState<string | number>("");
  const [descripcion, setDescripcion] = useState("");
  const [imagenUrl, setImagenUrl] = useState("");
  const [ivaPorcentaje, setIvaPorcentaje] = useState<number>(19);
  const [precioNeto, setPrecioNeto] = useState<number>(0);
  const [precioBruto, setPrecioBruto] = useState<number>(0);

  // Block 1: Fixed Components
  const [itemsFijos, setItemsFijos] = useState<ComboItemFijo[]>([]);
  const [selectedFixedCandidateKey, setSelectedFixedCandidateKey] = useState<string>("");

  // Block 2: Dynamic Option Groups
  const [gruposVinculados, setGruposVinculados] = useState<
    Array<{
      grupo: GrupoOpciones;
      es_requerido: boolean;
      orden: number;
    }>
  >([]);
  const [isOptionSelectorOpen, setIsOptionSelectorOpen] = useState(false);
  const [optionSelectorInitialTab, setOptionSelectorInitialTab] = useState<"library" | "create">(
    "library"
  );

  useEffect(() => {
    if (!open) return;

    if (combo) {
      setNombre(
        isDuplicate ? `${t("modals.recipe.duplicate_prefix")} ${combo.nombre}` : combo.nombre
      );
      setCodigo(
        isDuplicate
          ? `${combo.codigo || "CMB"}-COPY`
          : combo.codigo || `CMB-${combo.id}`
      );
      setCategoriaId(combo.categoria_combo_id ?? "");
      setDescripcion(combo.descripcion || "");
      setImagenUrl(combo.imagen_url || "");

      const iva = combo.iva_porcentaje ?? 19;
      setIvaPorcentaje(iva);
      const pBruto = combo.precio_venta_bruto ?? combo.precio_bruto ?? combo.precio ?? 0;
      const pNeto =
        combo.precio_venta_neto ??
        combo.precio_neto ??
        (pBruto > 0 ? Number((pBruto / (1 + iva / 100)).toFixed(2)) : 0);
      setPrecioBruto(pBruto);
      setPrecioNeto(pNeto);

      setItemsFijos(
        (combo.items_fijos || []).map((item, idx) => ({
          ...item,
          id: item.id ?? `cf-${idx}`,
          costo_total: Number((item.cantidad * item.costo_unitario).toFixed(2)),
        }))
      );

      const hydratedGroups = (combo.grupos_opciones || []).map((link, idx) => {
        const foundLib =
          link.grupo ||
          gruposBiblioteca.find((g) => String(g.id) === String(link.grupo_id)) || {
            id: link.grupo_id,
            nombre: t("modals.common.group_fallback", { id: link.grupo_id }),
            seleccion_minima: 1,
            seleccion_maxima: 1,
            items: [],
          };
        return {
          grupo: {
            ...foundLib,
            items: (foundLib.items || []).map((it) => ({ ...it })),
          },
          es_requerido: link.es_requerido ?? true,
          orden: link.orden ?? idx + 1,
        };
      });
      setGruposVinculados(hydratedGroups);
    } else {
      setNombre("");
      setCodigo(`CMB-${String(Date.now()).slice(-4)}`);
      setCategoriaId(categorias[0]?.id ?? "");
      setDescripcion("");
      setImagenUrl("");
      setIvaPorcentaje(19);
      setPrecioNeto(16722.69);
      setPrecioBruto(19900);
      setItemsFijos([]);
      setGruposVinculados([]);
    }
  }, [open, combo, isDuplicate, categorias, gruposBiblioteca, t]);

  const fixedCandidates = useMemo(() => {
    const list: Array<{
      key: string;
      id: string | number;
      nombre: string;
      target_type: "receta" | "producto";
      costo_unitario: number;
      precio_individual: number;
    }> = [];

    for (const r of recetas.filter((rec) => !rec.es_subreceta)) {
      list.push({
        key: `receta:${r.id}`,
        id: r.id,
        nombre: r.nombre,
        target_type: "receta",
        costo_unitario: r.costo_porcion ?? r.costo_total ?? 0,
        precio_individual: r.precio_venta_bruto ?? r.precio_bruto ?? r.precio ?? 0,
      });
    }

    for (const p of productos) {
      list.push({
        key: `producto:${p.id}`,
        id: p.id,
        nombre: p.nombre,
        target_type: "producto",
        costo_unitario: p.costo_unitario_ppp ?? p.costo_unitario ?? 0,
        precio_individual: p.precio_venta ?? (p.costo_unitario ?? 0) * 2,
      });
    }

    return list;
  }, [recetas, productos]);

  // Financial Summary in Real Time
  const financialSummary = useMemo(() => {
    let fixedCost = 0;
    let individualPriceTotal = 0;

    for (const item of itemsFijos) {
      const qty = Math.max(0, Number(item.cantidad) || 0);
      const unitCost = Math.max(0, Number(item.costo_unitario) || 0);
      fixedCost += qty * unitCost;

      const cand = fixedCandidates.find(
        (c) =>
          c.target_type === item.target_type &&
          String(c.id) === String(item.target_type === "receta" ? item.receta_id : item.producto_id)
      );
      const indPrice = cand ? cand.precio_individual : unitCost * 2.5;
      individualPriceTotal += qty * indPrice;
    }

    let dynamicDefaultCost = 0;
    for (const { grupo } of gruposVinculados) {
      const items = grupo.items || [];
      const defaults = items.filter((it) => Boolean(it.es_opcion_default ?? it.es_default));
      const activeItems = defaults.length > 0 ? defaults : items.slice(0, 1);
      for (const act of activeItems) {
        const qty = Number(act.cantidad ?? act.cantidad_porcion ?? 1);
        const refCost = Number(act.costo_referencial ?? 0);
        dynamicDefaultCost += qty * refCost;
        individualPriceTotal += qty * (refCost > 0 ? refCost * 2.2 : 2500);
      }
    }

    const baseCost = fixedCost + dynamicDefaultCost;
    const netSale = Number(precioNeto) || 0;
    const grossSale = Number(precioBruto) || 0;
    const marginPct = netSale > 0 ? ((netSale - baseCost) / netSale) * 100 : 0;
    const clientSavings = Math.max(0, individualPriceTotal - grossSale);

    return {
      baseCost: Number(baseCost.toFixed(2)),
      individualPriceTotal: Number(individualPriceTotal.toFixed(2)),
      comboPrice: grossSale,
      clientSavings: Number(clientSavings.toFixed(2)),
      marginPct: Number(marginPct.toFixed(2)),
    };
  }, [itemsFijos, gruposVinculados, fixedCandidates, precioNeto, precioBruto]);

  if (!open) return null;

  const handlePrecioNetoChange = (val: number) => {
    setPrecioNeto(val);
    setPrecioBruto(Math.round(val * (1 + (Number(ivaPorcentaje) || 0) / 100)));
  };

  const handlePrecioBrutoChange = (val: number) => {
    setPrecioBruto(val);
    const factor = 1 + (Number(ivaPorcentaje) || 0) / 100;
    setPrecioNeto(factor > 0 ? Number((val / factor).toFixed(2)) : val);
  };

  const handleIvaChange = (iva: number) => {
    setIvaPorcentaje(iva);
    setPrecioBruto(Math.round(precioNeto * (1 + (Number(iva) || 0) / 100)));
  };

  const handleAddFixedItem = () => {
    const candidate =
      fixedCandidates.find((c) => c.key === selectedFixedCandidateKey) ||
      fixedCandidates[0];
    if (!candidate) return;

    const newItem: ComboItemFijo = {
      id: `cf-${Date.now()}-${itemsFijos.length}`,
      producto_id: candidate.target_type === "producto" ? candidate.id : null,
      receta_id: candidate.target_type === "receta" ? candidate.id : null,
      nombre: candidate.nombre,
      target_type: candidate.target_type,
      cantidad: 1,
      costo_unitario: candidate.costo_unitario,
      costo_total: candidate.costo_unitario,
    };

    setItemsFijos((prev) => [...prev, newItem]);
  };

  const handleUpdateFixedItemQty = (idx: number, qty: number) => {
    setItemsFijos((prev) =>
      prev.map((item, i) => {
        if (i !== idx) return item;
        const safeQty = Math.max(0.01, Number(qty) || 1);
        return {
          ...item,
          cantidad: safeQty,
          costo_total: Number((safeQty * item.costo_unitario).toFixed(2)),
        };
      })
    );
  };

  const handleRemoveFixedItem = (idx: number) => {
    setItemsFijos((prev) => prev.filter((_, i) => i !== idx));
  };

  const handleLinkOptionGroup = (grupo: GrupoOpciones) => {
    setGruposVinculados((prev) => {
      const existingIdx = prev.findIndex((g) => String(g.grupo.id) === String(grupo.id));
      if (existingIdx >= 0) {
        return prev.map((entry, idx) =>
          idx === existingIdx ? { ...entry, grupo: { ...grupo } } : entry
        );
      }
      return [
        ...prev,
        {
          grupo: { ...grupo },
          es_requerido: (grupo.seleccion_minima ?? 1) > 0,
          orden: prev.length + 1,
        },
      ];
    });
  };

  const handleRemoveDynamicGroup = (idx: number) => {
    setGruposVinculados((prev) => prev.filter((_, i) => i !== idx));
  };

  const handleSubmit = async () => {
    if (!nombre.trim()) return;

    const payload: ComboCreateInput = {
      nombre: nombre.trim(),
      codigo: codigo.trim() || `CMB-${Date.now()}`,
      descripcion: descripcion.trim() || null,
      categoria_combo_id: categoriaId || null,
      es_dinamico: gruposVinculados.length > 0,
      precio_venta_neto: Number(precioNeto) || 0,
      precio_venta_bruto: Number(precioBruto) || 0,
      iva_porcentaje: Number(ivaPorcentaje) || 19,
      iva_incluido: true,
      imagen_url: imagenUrl.trim() || null,
      items: itemsFijos.map((item) => ({
        producto_id: item.target_type === "producto" ? item.producto_id : null,
        receta_id: item.target_type === "receta" ? item.receta_id : null,
        cantidad: Number(item.cantidad) || 1,
      })),
      grupos_opciones: gruposVinculados.map((gv, idx) => ({
        grupo_id: gv.grupo.id,
        orden: idx + 1,
        es_requerido: gv.es_requerido,
      })),
    };

    const catObj = categorias.find((c) => String(c.id) === String(categoriaId));

    const calculatedCombo: Combo = {
      id: !isDuplicate && combo?.id ? combo.id : `combo-${Date.now()}`,
      codigo: payload.codigo,
      nombre: payload.nombre,
      descripcion: payload.descripcion,
      categoria_combo_id: payload.categoria_combo_id,
      categoria_nombre: catObj?.nombre ?? combo?.categoria_nombre ?? null,
      es_dinamico: payload.es_dinamico,
      precio: payload.precio_venta_bruto,
      precio_neto: payload.precio_venta_neto,
      precio_bruto: payload.precio_venta_bruto,
      precio_venta_neto: payload.precio_venta_neto,
      precio_venta_bruto: payload.precio_venta_bruto,
      iva_porcentaje: payload.iva_porcentaje,
      costo_base: financialSummary.baseCost,
      costo_total_calculado: financialSummary.baseCost,
      margen_pct: financialSummary.marginPct,
      esta_disponible: true,
      disponibilidad_stock_porciones: 15,
      imagen_url: payload.imagen_url,
      items_fijos: itemsFijos,
      grupos_opciones: gruposVinculados.map((gv, idx) => ({
        id: `cgo-${idx}`,
        grupo_id: gv.grupo.id,
        orden: idx + 1,
        es_requerido: gv.es_requerido,
        grupo: gv.grupo,
      })),
    };

    if (onSave) {
      await onSave(payload, calculatedCombo);
    }
    onClose();
  };

  const marginBadge = getMargenBadge(financialSummary.marginPct);

  return (
    <div
      data-testid="combo-dialog"
      role="dialog"
      aria-modal="true"
      aria-label={
        combo && !isDuplicate
          ? t("modals.combo.edit_title")
          : t("modals.combo.create_title")
      }
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-2 sm:p-4 overflow-y-auto"
    >
      <div className="relative w-full max-w-6xl rounded-2xl border border-border bg-card text-foreground shadow-2xl overflow-hidden flex flex-col max-h-[92vh]">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-border px-5 py-4 bg-muted/30">
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-pink-500/15 text-pink-600 dark:text-pink-400">
              <Boxes className="h-6 w-6" />
            </div>
            <div>
              <h2 className="text-base sm:text-lg font-extrabold text-foreground">
                {combo && !isDuplicate
                  ? t("modals.combo.edit_title")
                  : t("modals.combo.create_title")}
              </h2>
              <p className="text-xs text-muted-foreground">
                {t("modals.combo.subtitle")}
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            data-testid="btn-close-combo-dialog"
            aria-label={t("modals.common.close")}
            className="inline-flex min-h-[44px] min-w-[44px] items-center justify-center rounded-xl text-muted-foreground hover:bg-secondary hover:text-foreground transition-colors cursor-pointer"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Main Content + Financial Summary Sidebar */}
        <div className="flex-1 overflow-y-auto grid grid-cols-1 lg:grid-cols-12 divide-y lg:divide-y-0 lg:divide-x divide-border">
          {/* Left Form Area */}
          <div className="lg:col-span-8 p-5 space-y-6 overflow-y-auto">
            {/* General Combo Fields */}
            <div className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div className="sm:col-span-2">
                  <label className="block text-xs font-bold text-foreground mb-1">
                    {t("modals.combo.field_name")} *
                  </label>
                  <input
                    type="text"
                    value={nombre}
                    onChange={(e) => setNombre(e.target.value)}
                    placeholder={t("modals.combo.field_name_placeholder")}
                    data-testid="input-combo-nombre"
                    className="w-full min-h-[44px] px-3 rounded-xl border border-input bg-background text-sm font-semibold"
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold text-foreground mb-1">
                    {t("modals.combo.field_code")}
                  </label>
                  <input
                    type="text"
                    value={codigo}
                    onChange={(e) => setCodigo(e.target.value)}
                    placeholder={t("modals.combo.field_code_placeholder")}
                    data-testid="input-combo-codigo"
                    className="w-full min-h-[44px] px-3 rounded-xl border border-input bg-background text-sm font-mono"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-bold text-foreground mb-1">
                    {t("modals.combo.field_category")}
                  </label>
                  <select
                    value={String(categoriaId)}
                    onChange={(e) => setCategoriaId(e.target.value)}
                    data-testid="select-combo-categoria"
                    className="w-full min-h-[44px] px-3 rounded-xl border border-input bg-background text-sm"
                  >
                    <option value="">{t("modals.combo.field_category_none")}</option>
                    {categorias.map((cat) => (
                      <option key={cat.id} value={String(cat.id)}>
                        {cat.nombre}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-bold text-foreground mb-1">
                    {t("modals.combo.field_image_url")}
                  </label>
                  <input
                    type="url"
                    value={imagenUrl}
                    onChange={(e) => setImagenUrl(e.target.value)}
                    data-testid="input-combo-imagen"
                    className="w-full min-h-[44px] px-3 rounded-xl border border-input bg-background text-sm"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-bold text-foreground mb-1">
                  {t("modals.combo.field_description")}
                </label>
                <textarea
                  rows={2}
                  value={descripcion}
                  onChange={(e) => setDescripcion(e.target.value)}
                  placeholder={t("modals.combo.field_description_placeholder")}
                  data-testid="input-combo-descripcion"
                  className="w-full p-3 rounded-xl border border-input bg-background text-xs sm:text-sm"
                />
              </div>

              {/* Prices */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 rounded-xl border border-border bg-muted/20 p-3.5">
                <div>
                  <label className="block text-xs font-bold text-foreground mb-1">
                    {t("modals.combo.field_price_net")}
                  </label>
                  <input
                    type="number"
                    min={0}
                    step="100"
                    value={precioNeto}
                    onChange={(e) => handlePrecioNetoChange(Number(e.target.value))}
                    data-testid="input-combo-precio-neto"
                    className="w-full min-h-[44px] px-3 rounded-xl border border-input bg-background text-sm font-semibold"
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold text-foreground mb-1">
                    {t("modals.combo.field_iva_pct")}
                  </label>
                  <input
                    type="number"
                    min={0}
                    max={100}
                    value={ivaPorcentaje}
                    onChange={(e) => handleIvaChange(Number(e.target.value))}
                    data-testid="input-combo-iva"
                    className="w-full min-h-[44px] px-3 rounded-xl border border-input bg-background text-sm"
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold text-foreground mb-1">
                    {t("modals.combo.field_price_gross")}
                  </label>
                  <input
                    type="number"
                    min={0}
                    step="100"
                    value={precioBruto}
                    onChange={(e) => handlePrecioBrutoChange(Number(e.target.value))}
                    data-testid="input-combo-precio-bruto"
                    className="w-full min-h-[44px] px-3 rounded-xl border border-input bg-background text-sm font-extrabold text-pink-600 dark:text-pink-400"
                  />
                </div>
              </div>
            </div>

            {/* Block 1: Fixed Components */}
            <div
              data-testid="combo-block-fixed"
              className="rounded-2xl border border-border bg-background/50 p-4 space-y-3"
            >
              <div>
                <h3 className="text-sm font-extrabold text-foreground">
                  {t("modals.combo.block_fixed_title")}
                </h3>
                <p className="text-xs text-muted-foreground">
                  {t("modals.combo.block_fixed_subtitle")}
                </p>
              </div>

              <div className="flex flex-col sm:flex-row gap-2">
                <select
                  value={selectedFixedCandidateKey}
                  onChange={(e) => setSelectedFixedCandidateKey(e.target.value)}
                  data-testid="select-combo-fixed-candidate"
                  className="flex-1 min-h-[44px] px-3 rounded-xl border border-input bg-background text-xs font-semibold"
                >
                  {fixedCandidates.map((cand) => (
                    <option key={cand.key} value={cand.key}>
                      [{cand.target_type === "receta"
                        ? t("modals.common.recipe")
                        : t("modals.common.product")}] {cand.nombre} (
                      {convertAndFormat(cand.costo_unitario)})
                    </option>
                  ))}
                </select>
                <button
                  type="button"
                  onClick={handleAddFixedItem}
                  data-testid="btn-add-combo-fixed-item"
                  className="inline-flex min-h-[44px] items-center justify-center gap-1.5 px-4 py-2 rounded-xl bg-pink-600 text-xs font-extrabold text-white hover:bg-pink-500 transition-colors cursor-pointer"
                >
                  <Plus className="h-4 w-4" />
                  <span>{t("modals.combo.add_fixed_btn")}</span>
                </button>
              </div>

              {itemsFijos.length === 0 ? (
                <div
                  data-testid="combo-fixed-empty"
                  className="p-5 text-center rounded-xl border border-dashed border-border text-xs text-muted-foreground"
                >
                  {t("modals.combo.empty_fixed_items")}
                </div>
              ) : (
                <div className="space-y-2">
                  {itemsFijos.map((item, idx) => (
                    <div
                      key={item.id ?? idx}
                      data-testid={`combo-fixed-item-row-${idx}`}
                      className="flex flex-wrap items-center justify-between gap-2 p-2.5 rounded-xl border border-border bg-card text-xs"
                    >
                      <div className="flex items-center gap-2">
                        <span className="px-2 py-0.5 rounded-full text-[10px] font-extrabold bg-pink-500/15 text-pink-600 dark:text-pink-400">
                          {item.target_type === "receta"
                            ? t("modals.common.recipe")
                            : t("modals.common.product")}
                        </span>
                        <span className="font-bold text-foreground">{item.nombre}</span>
                      </div>

                      <div className="flex items-center gap-3">
                        <div className="flex items-center gap-1.5">
                          <label className="text-[11px] text-muted-foreground">
                            {t("modals.common.quantity")}:
                          </label>
                          <input
                            type="number"
                            min={1}
                            step="1"
                            value={item.cantidad}
                            onChange={(e) =>
                              handleUpdateFixedItemQty(idx, Number(e.target.value))
                            }
                            data-testid={`input-combo-fixed-qty-${idx}`}
                            className="w-16 min-h-[36px] px-2 rounded-lg border border-input bg-background text-xs font-bold"
                          />
                        </div>

                        <span className="font-extrabold text-foreground min-w-[75px] text-right">
                          {convertAndFormat(item.costo_total)}
                        </span>

                        <button
                          type="button"
                          onClick={() => handleRemoveFixedItem(idx)}
                          data-testid={`btn-remove-combo-fixed-${idx}`}
                          aria-label={t("modals.common.delete")}
                          className="inline-flex min-h-[36px] min-w-[36px] items-center justify-center rounded-lg text-rose-500 hover:bg-rose-500/10 cursor-pointer"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Block 2: Dynamic Option Groups */}
            <div
              data-testid="combo-block-dynamic"
              className="rounded-2xl border border-purple-500/30 bg-purple-500/5 p-4 space-y-3"
            >
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                <div>
                  <h3 className="text-sm font-extrabold text-foreground flex items-center gap-1.5">
                    <Sparkles className="h-4 w-4 text-purple-500" />
                    <span>{t("modals.combo.block_dynamic_title")}</span>
                  </h3>
                  <p className="text-xs text-muted-foreground">
                    {t("modals.combo.block_dynamic_subtitle")}
                  </p>
                </div>

                <div className="flex flex-wrap items-center gap-2">
                  <button
                    type="button"
                    onClick={() => {
                      setOptionSelectorInitialTab("library");
                      setIsOptionSelectorOpen(true);
                    }}
                    data-testid="btn-combo-open-option-group-selector"
                    className="inline-flex min-h-[44px] items-center gap-1.5 px-3.5 py-2 rounded-xl bg-purple-600 text-xs font-extrabold text-white hover:bg-purple-500 transition-colors cursor-pointer"
                  >
                    <Library className="h-4 w-4" />
                    <span>{t("modals.combo.btn_add_group")}</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => {
                      setOptionSelectorInitialTab("create");
                      setIsOptionSelectorOpen(true);
                    }}
                    data-testid="btn-combo-create-insitu-group"
                    className="inline-flex min-h-[44px] items-center gap-1.5 px-3 py-2 rounded-xl border border-purple-500/40 bg-purple-500/10 text-xs font-extrabold text-purple-600 dark:text-purple-400 hover:bg-purple-500/20 transition-colors cursor-pointer"
                  >
                    <Plus className="h-4 w-4" />
                    <span>{t("modals.recipe.btn_create_insitu_group")}</span>
                  </button>
                </div>
              </div>

              {gruposVinculados.length === 0 ? (
                <div
                  data-testid="combo-dynamic-empty"
                  className="p-5 text-center rounded-xl border border-dashed border-border text-xs text-muted-foreground"
                >
                  {t("modals.combo.empty_dynamic_groups")}
                </div>
              ) : (
                <div className="space-y-2.5">
                  {gruposVinculados.map(({ grupo }, idx) => (
                    <div
                      key={`${grupo.id}-${idx}`}
                      data-testid={`combo-dynamic-group-${idx}`}
                      className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 p-3 rounded-xl border border-purple-500/30 bg-card text-xs"
                    >
                      <div className="space-y-1">
                        <div className="flex items-center gap-2">
                          <Layers className="h-4 w-4 text-purple-500" />
                          <span className="font-extrabold text-foreground">
                            {grupo.nombre}
                          </span>
                          <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-purple-500/15 text-purple-600 dark:text-purple-400">
                            {t("modals.option_group.cardinality_hint", {
                              min: grupo.seleccion_minima ?? 1,
                              max: grupo.seleccion_maxima ?? 1,
                            })}
                          </span>
                        </div>
                        <div className="flex flex-wrap gap-1.5">
                          {(grupo.items || []).map((it, i) => (
                            <span
                              key={it.id ?? i}
                              className="px-2 py-0.5 rounded bg-muted text-muted-foreground text-[11px]"
                            >
                              {it.nombre}
                            </span>
                          ))}
                        </div>
                      </div>

                      <button
                        type="button"
                        onClick={() => handleRemoveDynamicGroup(idx)}
                        data-testid={`btn-remove-combo-dynamic-group-${idx}`}
                        aria-label={t("modals.common.delete")}
                        className="inline-flex min-h-[36px] min-w-[36px] items-center justify-center rounded-lg text-rose-500 hover:bg-rose-500/10 cursor-pointer self-end sm:self-center"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Right Live Financial Summary Sidebar */}
          <aside
            data-testid="combo-live-summary"
            className="lg:col-span-4 bg-muted/25 p-5 space-y-4 flex flex-col justify-between"
          >
            <div className="space-y-4">
              <div className="flex items-center gap-2.5 border-b border-border pb-3">
                <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-pink-500/15 text-pink-600 dark:text-pink-400">
                  <Calculator className="h-5 w-5" />
                </div>
                <div>
                  <h3 className="text-sm font-extrabold text-foreground">
                    {t("modals.combo.summary_title")}
                  </h3>
                </div>
              </div>

              <div className="space-y-2.5 text-xs">
                <div className="flex items-center justify-between py-2 border-b border-border/50">
                  <span className="text-muted-foreground font-medium">
                    {t("modals.combo.summary_base_cost")}
                  </span>
                  <span
                    data-testid="combo-summary-base-cost"
                    className="font-bold text-foreground"
                  >
                    {convertAndFormat(financialSummary.baseCost)}
                  </span>
                </div>

                <div className="flex items-center justify-between py-2 border-b border-border/50">
                  <span className="text-muted-foreground font-medium">
                    {t("modals.combo.summary_individual_price")}
                  </span>
                  <span
                    data-testid="combo-summary-individual-price"
                    className="font-semibold text-muted-foreground line-through"
                  >
                    {convertAndFormat(financialSummary.individualPriceTotal)}
                  </span>
                </div>

                <div className="flex items-center justify-between py-2.5 px-3 rounded-xl bg-card border border-border">
                  <span className="font-extrabold text-foreground">
                    {t("modals.combo.summary_combo_price")}
                  </span>
                  <span
                    data-testid="combo-summary-combo-price"
                    className="text-sm font-black text-pink-600 dark:text-pink-400"
                  >
                    {convertAndFormat(financialSummary.comboPrice)}
                  </span>
                </div>

                <div className="flex items-center justify-between py-2.5 px-3 rounded-xl bg-emerald-500/10 border border-emerald-500/30">
                  <span className="font-bold text-emerald-700 dark:text-emerald-300">
                    {t("modals.combo.summary_client_savings")}
                  </span>
                  <span
                    data-testid="combo-summary-client-savings"
                    className="text-sm font-extrabold text-emerald-700 dark:text-emerald-300"
                  >
                    {convertAndFormat(financialSummary.clientSavings)}
                  </span>
                </div>
              </div>

              <div className="rounded-xl border border-border bg-card p-4 flex items-center justify-between">
                <span className="text-xs font-extrabold text-foreground">
                  {t("modals.combo.summary_margin_pct")}
                </span>
                <span
                  data-testid="combo-summary-margin-badge"
                  className={cn(
                    "px-2.5 py-1 rounded-full text-xs font-black border",
                    marginBadge.className
                  )}
                >
                  {marginBadge.label}
                </span>
              </div>
            </div>

            <div className="flex items-center justify-end gap-2.5 pt-4 border-t border-border">
              <button
                type="button"
                onClick={onClose}
                data-testid="btn-cancel-combo-dialog"
                className="inline-flex min-h-[44px] items-center justify-center rounded-xl border border-border bg-secondary px-4 py-2 text-xs font-bold text-foreground hover:bg-secondary/80 transition-colors cursor-pointer"
              >
                {t("modals.common.cancel")}
              </button>
              <button
                type="button"
                onClick={handleSubmit}
                disabled={!nombre.trim()}
                data-testid="btn-save-combo"
                className="inline-flex min-h-[44px] items-center gap-2 rounded-xl bg-pink-600 px-5 py-2 text-xs font-extrabold text-white hover:bg-pink-500 disabled:opacity-50 transition-colors cursor-pointer"
              >
                <Check className="h-4 w-4" />
                <span>{t("modals.combo.save_combo_btn")}</span>
              </button>
            </div>
          </aside>
        </div>
      </div>

      {/* Assistant Modal for Library / In-Situ Option Groups */}
      <OptionGroupSelectorModal
        open={isOptionSelectorOpen}
        onClose={() => setIsOptionSelectorOpen(false)}
        onSelectGroup={handleLinkOptionGroup}
        initialTab={optionSelectorInitialTab}
        gruposBiblioteca={gruposBiblioteca}
        productos={productos}
        subrecetas={recetas}
      />
    </div>
  );
}

export default ComboDialog;
