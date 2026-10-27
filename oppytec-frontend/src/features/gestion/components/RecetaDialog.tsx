import { useState, useEffect, useMemo } from "react";
import {
  X,
  ChefHat,
  Plus,
  Trash2,
  Sparkles,
  ScrollText,
  Calculator,
  Library,
  Check,
  Search,
  Layers,
} from "lucide-react";
import { useTranslation } from "react-i18next";
import { cn } from "@/shared/lib";
import {
  formatScaledDecimal,
  parseScaledDecimal,
  useCurrencyFormatter,
} from "@/shared/currency";
import { getMargenBadge } from "./recetas/RecetasTable";
import { OptionGroupSelectorModal } from "./OptionGroupSelectorModal";
import { INITIAL_PRODUCTOS_MOCK } from "../useGestion";
import {
  INITIAL_RECETAS_MOCK,
  INITIAL_CATEGORIAS_RECETAS_MOCK,
} from "../hooks/useRecetas";
import { INITIAL_GRUPOS_OPCIONES_MOCK } from "../hooks/useGruposOpciones";
import type {
  Receta,
  CategoriaReceta,
  Producto,
  IngredienteFijo,
  GrupoOpciones,
  GrupoOpcionesItem,
  RecipeCreateInput,
} from "../types";

export type RecetaDialogTab = "general" | "ingredients" | "dynamic";

export interface RecetaDialogProps {
  open: boolean;
  onClose: () => void;
  receta?: Receta | null;
  isDuplicate?: boolean;
  categorias?: CategoriaReceta[];
  productos?: Producto[];
  recetasCatalogo?: Receta[];
  gruposBiblioteca?: GrupoOpciones[];
  onSave?: (payload: RecipeCreateInput, calculatedReceta: Receta) => Promise<void> | void;
}

export function calculateIngredientTotalCost(
  cantidad: number | string,
  mermaPct: number | string,
  costoUnitario: number | string
): number {
  const safeQty = Math.max(0, Number(cantidad) || 0);
  const safeMerma = Math.min(99.99, Math.max(0, Number(mermaPct) || 0));
  const safeCost = Math.max(0, Number(costoUnitario) || 0);

  const qtyScaled = parseScaledDecimal(safeQty.toFixed(6));
  const costScaled = parseScaledDecimal(safeCost.toFixed(6));
  const mermaScaled = parseScaledDecimal(safeMerma.toFixed(6));
  const hundredScaled = 100n * 100_000_000n;
  const netYieldScaled = hundredScaled - mermaScaled;
  if (netYieldScaled <= 0n) {
    return 0;
  }

  // Exact fixed-point calculation: (qty * cost * 100) / (100 - mermaPct)
  const numerator = qtyScaled * costScaled * 100n;
  const halfDivisor = netYieldScaled / 2n;
  const totalScaled = (numerator + halfDivisor) / netYieldScaled;
  return Number(formatScaledDecimal(totalScaled, 2));
}

export function RecetaDialog({
  open,
  onClose,
  receta = null,
  isDuplicate = false,
  categorias = INITIAL_CATEGORIAS_RECETAS_MOCK,
  productos = INITIAL_PRODUCTOS_MOCK,
  recetasCatalogo = INITIAL_RECETAS_MOCK,
  gruposBiblioteca = INITIAL_GRUPOS_OPCIONES_MOCK,
  onSave,
}: RecetaDialogProps) {
  const { t } = useTranslation("recipes");
  const { convertAndFormat } = useCurrencyFormatter();

  const [activeTab, setActiveTab] = useState<RecetaDialogTab>("general");

  // Tab 1: General Info state
  const [nombre, setNombre] = useState("");
  const [codigo, setCodigo] = useState("");
  const [categoriaId, setCategoriaId] = useState<string | number>("");
  const [descripcion, setDescripcion] = useState("");
  const [porciones, setPorciones] = useState<number>(1);
  const [esSubreceta, setEsSubreceta] = useState<boolean>(false);
  const [esDinamica, setEsDinamica] = useState<boolean>(false);
  const [ivaPorcentaje, setIvaPorcentaje] = useState<number>(19);
  const [precioNeto, setPrecioNeto] = useState<number>(0);
  const [precioBruto, setPrecioBruto] = useState<number>(0);
  const [tiempoPreparacion, setTiempoPreparacion] = useState<number>(15);
  const [imagenUrl, setImagenUrl] = useState("");
  const [videoUrl, setVideoUrl] = useState("");
  const [documentoUrl, setDocumentoUrl] = useState("");
  const [preparacion, setPreparacion] = useState("");

  // Tab 2: Fixed Ingredients state
  const [ingredientesFijos, setIngredientesFijos] = useState<IngredienteFijo[]>([]);
  const [ingSearch, setIngSearch] = useState("");
  const [ingSourceFilter, setIngSourceFilter] = useState<"all" | "producto" | "subreceta">("all");
  const [selectedCandidateKey, setSelectedCandidateKey] = useState<string>("");

  // Tab 3: Dynamic Option Groups state
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
  const [groupCandidateItemMap, setGroupCandidateItemMap] = useState<Record<number, string>>({});

  // Hydrate state when modal opens or receta changes
  useEffect(() => {
    if (!open) return;
    setActiveTab("general");

    if (receta) {
      const baseName = isDuplicate
        ? `${t("modals.recipe.duplicate_prefix")} ${receta.nombre}`
        : receta.nombre;
      const baseCode = isDuplicate
        ? `${receta.codigo || "REC"}-COPY`
        : receta.codigo || `REC-${receta.id}`;

      setNombre(baseName);
      setCodigo(baseCode);
      setCategoriaId(receta.categoria_receta_id ?? "");
      setDescripcion(receta.descripcion || "");
      setPorciones(receta.porciones_rendimiento || receta.porciones || 1);
      setEsSubreceta(Boolean(receta.es_subreceta));

      const hydratedGroups = (receta.grupos_opciones || []).map((link, idx) => {
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
            items: (foundLib.items || []).map((i) => ({ ...i })),
          },
          es_requerido: link.es_requerido ?? true,
          orden: link.orden ?? idx + 1,
        };
      });

      setGruposVinculados(hydratedGroups);
      setEsDinamica(Boolean(receta.es_dinamica || hydratedGroups.length > 0));

      const iva = receta.iva_porcentaje ?? 19;
      setIvaPorcentaje(iva);
      const pBruto = receta.precio_venta_bruto ?? receta.precio_bruto ?? receta.precio ?? 0;
      const pNeto =
        receta.precio_venta_neto ??
        receta.precio_neto ??
        (pBruto > 0 ? Number((pBruto / (1 + iva / 100)).toFixed(2)) : 0);
      setPrecioBruto(pBruto);
      setPrecioNeto(pNeto);

      setTiempoPreparacion(receta.tiempo_preparacion_minutos ?? 15);
      setImagenUrl(receta.imagen_url || "");
      setVideoUrl(receta.video_url || "");
      setDocumentoUrl(receta.documento_url || "");
      setPreparacion(receta.preparacion || "");

      setIngredientesFijos(
        (receta.ingredientes_fijos || []).map((ing, idx) => ({
          ...ing,
          id: ing.id ?? `ing-${idx}`,
          costo_total: calculateIngredientTotalCost(
            ing.cantidad_receta,
            ing.porcentaje_merma,
            ing.costo_unitario
          ),
        }))
      );
    } else {
      setNombre("");
      setCodigo(`REC-${String(Date.now()).slice(-4)}`);
      setCategoriaId(categorias[0]?.id ?? "");
      setDescripcion("");
      setPorciones(1);
      setEsSubreceta(false);
      setEsDinamica(false);
      setIvaPorcentaje(19);
      setPrecioNeto(10000);
      setPrecioBruto(11900);
      setTiempoPreparacion(15);
      setImagenUrl("");
      setVideoUrl("");
      setDocumentoUrl("");
      setPreparacion("");
      setIngredientesFijos([]);
      setGruposVinculados([]);
    }
  }, [open, receta, isDuplicate, categorias, gruposBiblioteca, t]);

  // Candidate list for fixed ingredients (Products + Sub-recipes avoiding self-reference!)
  const availableCandidates = useMemo(() => {
    const currentRecipeId = !isDuplicate && receta?.id ? String(receta.id) : null;
    const term = ingSearch.trim().toLowerCase();

    const list: Array<{
      key: string;
      id: string | number;
      nombre: string;
      target_type: "producto" | "subreceta";
      unidad: string;
      costo_unitario: number;
    }> = [];

    if (ingSourceFilter === "all" || ingSourceFilter === "producto") {
      for (const p of productos) {
        if (!term || p.nombre.toLowerCase().includes(term) || p.sku?.toLowerCase().includes(term)) {
          list.push({
            key: `producto:${p.id}`,
            id: p.id,
            nombre: p.nombre,
            target_type: "producto",
            unidad: p.unidad || "kg",
            costo_unitario: p.costo_unitario_ppp ?? p.costo_unitario ?? 0,
          });
        }
      }
    }

    if (ingSourceFilter === "all" || ingSourceFilter === "subreceta") {
      for (const r of recetasCatalogo) {
        // Prevent self-reference!
        if (currentRecipeId && String(r.id) === currentRecipeId) continue;
        if (!term || r.nombre.toLowerCase().includes(term) || r.codigo?.toLowerCase().includes(term)) {
          list.push({
            key: `subreceta:${r.id}`,
            id: r.id,
            nombre: r.nombre,
            target_type: "subreceta",
            unidad: "porción",
            costo_unitario: r.costo_porcion ?? r.costo_total ?? 0,
          });
        }
      }
    }

    return list;
  }, [productos, recetasCatalogo, receta, isDuplicate, ingSearch, ingSourceFilter]);

  // Live Costing Calculations (Fixed + Default Dynamic + Worst-Case Dynamic)
  const liveCosting = useMemo(() => {
    const fixedCost = ingredientesFijos.reduce(
      (acc, ing) =>
        acc +
        calculateIngredientTotalCost(
          ing.cantidad_receta,
          ing.porcentaje_merma,
          ing.costo_unitario
        ),
      0
    );

    let defaultOptionsCost = 0;
    let worstCaseOptionsCost = 0;

    if (esDinamica && gruposVinculados.length > 0) {
      for (const { grupo } of gruposVinculados) {
        const groupItems = grupo.items || [];
        if (groupItems.length === 0) continue;

        const maxSel = Math.max(
          1,
          Number(grupo.seleccion_maxima ?? grupo.max_selecciones ?? 1)
        );

        // Option costs = cantidad_porcion * costo_referencial
        const itemCosts = groupItems.map((it) => {
          const qty = Number(it.cantidad ?? it.cantidad_porcion ?? 1);
          const refCost = Number(it.costo_referencial ?? 0);
          return {
            isDefault: Boolean(it.es_opcion_default ?? it.es_default),
            totalCost: qty * refCost,
          };
        });

        const defaults = itemCosts.filter((ic) => ic.isDefault);
        if (defaults.length > 0) {
          defaultOptionsCost += defaults.reduce((sum, d) => sum + d.totalCost, 0);
        } else if ((grupo.seleccion_minima ?? 0) > 0 && itemCosts[0]) {
          defaultOptionsCost += itemCosts[0].totalCost;
        }

        // Worst-case: sum of top `maxSel` most expensive options in the group (or repeat top 1 if permite_repetir)
        const sortedDesc = [...itemCosts].sort((a, b) => b.totalCost - a.totalCost);
        if (grupo.permite_repetir && sortedDesc[0]) {
          worstCaseOptionsCost += sortedDesc[0].totalCost * maxSel;
        } else {
          worstCaseOptionsCost += sortedDesc
            .slice(0, maxSel)
            .reduce((sum, ic) => sum + ic.totalCost, 0);
        }
      }
    }

    const totalBaseCost = fixedCost + defaultOptionsCost;
    const totalWorstCaseCost = Math.max(totalBaseCost, fixedCost + worstCaseOptionsCost);
    const safePorciones = Math.max(1, Number(porciones) || 1);
    const costPerPortion = totalBaseCost / safePorciones;

    const netSale = Number(precioNeto) || 0;
    const marginPct = netSale > 0 ? ((netSale - totalBaseCost) / netSale) * 100 : 0;
    const worstCaseMarginPct =
      netSale > 0 ? ((netSale - totalWorstCaseCost) / netSale) * 100 : 0;
    const foodCostPct = netSale > 0 ? (totalBaseCost / netSale) * 100 : 0;

    return {
      fixedCost: Number(fixedCost.toFixed(2)),
      defaultOptionsCost: Number(defaultOptionsCost.toFixed(2)),
      totalBaseCost: Number(totalBaseCost.toFixed(2)),
      totalWorstCaseCost: Number(totalWorstCaseCost.toFixed(2)),
      costPerPortion: Number(costPerPortion.toFixed(2)),
      marginPct: Number(marginPct.toFixed(2)),
      worstCaseMarginPct: Number(worstCaseMarginPct.toFixed(2)),
      foodCostPct: Number(foodCostPct.toFixed(2)),
    };
  }, [ingredientesFijos, esDinamica, gruposVinculados, porciones, precioNeto]);

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

  const handleAddFixedIngredient = () => {
    const candidate =
      availableCandidates.find((c) => c.key === selectedCandidateKey) ||
      availableCandidates[0];
    if (!candidate) return;

    const newIng: IngredienteFijo = {
      id: `ing-fijo-${Date.now()}-${ingredientesFijos.length}`,
      producto_id: candidate.target_type === "producto" ? candidate.id : null,
      subreceta_id: candidate.target_type === "subreceta" ? candidate.id : null,
      nombre: candidate.nombre,
      target_type: candidate.target_type,
      unidad: candidate.unidad,
      cantidad_receta: 1,
      porcentaje_merma: 0,
      costo_unitario: candidate.costo_unitario,
      costo_total: calculateIngredientTotalCost(1, 0, candidate.costo_unitario),
    };

    setIngredientesFijos((prev) => [...prev, newIng]);
  };

  const handleUpdateFixedIngredient = (
    idx: number,
    patch: Partial<IngredienteFijo>
  ) => {
    setIngredientesFijos((prev) =>
      prev.map((ing, i) => {
        if (i !== idx) return ing;
        const next = { ...ing, ...patch };
        next.costo_total = calculateIngredientTotalCost(
          next.cantidad_receta,
          next.porcentaje_merma,
          next.costo_unitario
        );
        return next;
      })
    );
  };

  const handleRemoveFixedIngredient = (idx: number) => {
    setIngredientesFijos((prev) => prev.filter((_, i) => i !== idx));
  };

  const handleLinkOptionGroup = (grupo: GrupoOpciones) => {
    setEsDinamica(true);
    setGruposVinculados((prev) => {
      const existingIdx = prev.findIndex((g) => String(g.grupo.id) === String(grupo.id));
      if (existingIdx >= 0) {
        return prev.map((item, idx) =>
          idx === existingIdx ? { ...item, grupo: { ...grupo } } : item
        );
      }
      return [
        ...prev,
        {
          grupo: {
            ...grupo,
            items: (grupo.items || []).map((it) => ({ ...it })),
          },
          es_requerido: (grupo.seleccion_minima ?? 1) > 0,
          orden: prev.length + 1,
        },
      ];
    });
  };

  const handleUpdateDynamicGroupMeta = (
    groupIdx: number,
    patch: Partial<GrupoOpciones> & { es_requerido?: boolean }
  ) => {
    setGruposVinculados((prev) =>
      prev.map((entry, idx) => {
        if (idx !== groupIdx) return entry;
        const { es_requerido, ...grupoPatch } = patch;
        return {
          ...entry,
          es_requerido: es_requerido !== undefined ? es_requerido : entry.es_requerido,
          grupo: {
            ...entry.grupo,
            ...grupoPatch,
            min_selecciones:
              grupoPatch.seleccion_minima ?? entry.grupo.seleccion_minima,
            max_selecciones:
              grupoPatch.seleccion_maxima ?? entry.grupo.seleccion_maxima,
          },
        };
      })
    );
  };

  const handleAddItemToDynamicGroup = (groupIdx: number) => {
    const selectedKey =
      groupCandidateItemMap[groupIdx] ||
      (productos[0] ? `producto:${productos[0].id}` : "");
    const [typePart, idPart] = selectedKey.split(":");

    let itemNombre = t("modals.common.default_option_name");
    let prodId: string | number | null = null;
    let recId: string | number | null = null;
    let refCost = 0;

    if (typePart === "receta") {
      const foundRec =
        recetasCatalogo.find((r) => String(r.id) === String(idPart)) || recetasCatalogo[0];
      if (foundRec) {
        recId = foundRec.id;
        itemNombre = foundRec.nombre;
        refCost = foundRec.costo_porcion ?? foundRec.costo_total ?? 0;
      }
    } else {
      const foundProd =
        productos.find((p) => String(p.id) === String(idPart)) || productos[0];
      if (foundProd) {
        prodId = foundProd.id;
        itemNombre = foundProd.nombre;
        refCost = foundProd.costo_unitario_ppp ?? foundProd.costo_unitario ?? 0;
      }
    }

    setGruposVinculados((prev) =>
      prev.map((entry, idx) => {
        if (idx !== groupIdx) return entry;
        const currentItems = entry.grupo.items || [];
        const newItem: GrupoOpcionesItem = {
          id: `gitem-${Date.now()}-${currentItems.length}`,
          grupo_id: entry.grupo.id,
          producto_id: prodId,
          receta_id: recId,
          nombre: itemNombre,
          target_type: typePart === "receta" ? "receta" : "producto",
          type: typePart === "receta" ? "receta" : "producto",
          cantidad: 1,
          cantidad_porcion: 1,
          es_opcion_default: currentItems.length === 0,
          es_default: currentItems.length === 0,
          recargo_precio: 0,
          precio_adicional: 0,
          costo_referencial: refCost,
          orden: currentItems.length + 1,
        };
        return {
          ...entry,
          grupo: {
            ...entry.grupo,
            items: [...currentItems, newItem],
          },
        };
      })
    );
  };

  const handleUpdateDynamicGroupItem = (
    groupIdx: number,
    itemIdx: number,
    patch: Partial<GrupoOpcionesItem>
  ) => {
    setGruposVinculados((prev) =>
      prev.map((entry, idx) => {
        if (idx !== groupIdx) return entry;
        const nextItems = (entry.grupo.items || []).map((it, i) => {
          if (i !== itemIdx) return it;
          const updated = { ...it, ...patch };
          if ("cantidad" in patch) updated.cantidad_porcion = patch.cantidad;
          if ("cantidad_porcion" in patch) updated.cantidad = patch.cantidad_porcion;
          if ("es_opcion_default" in patch) updated.es_default = patch.es_opcion_default;
          if ("es_default" in patch) updated.es_opcion_default = patch.es_default;
          if ("recargo_precio" in patch) updated.precio_adicional = patch.recargo_precio;
          if ("precio_adicional" in patch) updated.recargo_precio = patch.precio_adicional;
          return updated;
        });
        return {
          ...entry,
          grupo: {
            ...entry.grupo,
            items: nextItems,
          },
        };
      })
    );
  };

  const handleRemoveDynamicGroupItem = (groupIdx: number, itemIdx: number) => {
    setGruposVinculados((prev) =>
      prev.map((entry, idx) => {
        if (idx !== groupIdx) return entry;
        return {
          ...entry,
          grupo: {
            ...entry.grupo,
            items: (entry.grupo.items || []).filter((_, i) => i !== itemIdx),
          },
        };
      })
    );
  };

  const handleRemoveDynamicGroup = (groupIdx: number) => {
    setGruposVinculados((prev) => prev.filter((_, idx) => idx !== groupIdx));
  };

  const handleSubmit = async () => {
    if (!nombre.trim()) return;

    const payload: RecipeCreateInput = {
      codigo: codigo.trim() || `REC-${Date.now()}`,
      nombre: nombre.trim(),
      descripcion: descripcion.trim() || null,
      categoria_receta_id: categoriaId || null,
      es_subreceta: esSubreceta,
      es_dinamica: esDinamica || gruposVinculados.length > 0,
      porciones_rendimiento: Math.max(1, Number(porciones) || 1),
      precio_venta_neto: Number(precioNeto) || 0,
      precio_venta_bruto: Number(precioBruto) || 0,
      iva_porcentaje: Number(ivaPorcentaje) || 19,
      iva_incluido: true,
      imagen_url: imagenUrl.trim() || null,
      video_url: videoUrl.trim() || null,
      documento_url: documentoUrl.trim() || null,
      preparacion: preparacion.trim() || null,
      tiempo_preparacion_minutos: Number(tiempoPreparacion) || null,
      ingredientes: ingredientesFijos.map((ing) => ({
        producto_id: ing.target_type === "producto" ? ing.producto_id : null,
        subreceta_id: ing.target_type === "subreceta" ? ing.subreceta_id : null,
        cantidad_receta: Number(ing.cantidad_receta) || 1,
        porcentaje_merma: Number(ing.porcentaje_merma) || 0,
      })),
      grupos_opciones:
        esDinamica || gruposVinculados.length > 0
          ? gruposVinculados.map((gv, idx) => ({
              grupo_id: gv.grupo.id,
              orden: idx + 1,
              es_requerido: gv.es_requerido,
            }))
          : [],
    };

    const catObj = categorias.find((c) => String(c.id) === String(categoriaId));

    const calculatedReceta: Receta = {
      id: !isDuplicate && receta?.id ? receta.id : `rec-${Date.now()}`,
      codigo: payload.codigo,
      nombre: payload.nombre,
      descripcion: payload.descripcion,
      categoria_receta_id: payload.categoria_receta_id,
      categoria_nombre: catObj?.nombre ?? receta?.categoria_nombre ?? null,
      es_subreceta: payload.es_subreceta,
      es_dinamica: payload.es_dinamica,
      porciones: payload.porciones_rendimiento,
      porciones_rendimiento: payload.porciones_rendimiento,
      costo_total: liveCosting.totalBaseCost,
      costo_total_calculado: liveCosting.totalBaseCost,
      costo_porcion: liveCosting.costPerPortion,
      costo_peor_caso: liveCosting.totalWorstCaseCost,
      precio: payload.precio_venta_bruto,
      precio_neto: payload.precio_venta_neto,
      precio_bruto: payload.precio_venta_bruto,
      precio_venta_neto: payload.precio_venta_neto,
      precio_venta_bruto: payload.precio_venta_bruto,
      iva_porcentaje: payload.iva_porcentaje,
      margen_pct: liveCosting.marginPct,
      food_cost_pct: liveCosting.foodCostPct,
      imagen_url: payload.imagen_url,
      video_url: payload.video_url,
      documento_url: payload.documento_url,
      preparacion: payload.preparacion,
      tiempo_preparacion_minutos: payload.tiempo_preparacion_minutos,
      ingredientes_fijos: ingredientesFijos,
      grupos_opciones: gruposVinculados.map((gv, idx) => ({
        id: `rgo-${idx}`,
        grupo_id: gv.grupo.id,
        orden: idx + 1,
        es_requerido: gv.es_requerido,
        grupo: gv.grupo,
      })),
    };

    if (onSave) {
      await onSave(payload, calculatedReceta);
    }
    onClose();
  };

  const margenSemaphore = getMargenBadge(liveCosting.marginPct);

  return (
    <div
      data-testid="receta-dialog"
      role="dialog"
      aria-modal="true"
      aria-label={
        receta && !isDuplicate
          ? t("modals.recipe.edit_title")
          : t("modals.recipe.create_title")
      }
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-2 sm:p-4 overflow-y-auto"
    >
      <div className="relative w-full max-w-6xl rounded-2xl border border-border bg-card text-foreground shadow-2xl overflow-hidden flex flex-col max-h-[92vh]">
        {/* Modal Header */}
        <div className="flex items-center justify-between border-b border-border px-5 py-4 bg-muted/30">
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-amber-500/15 text-amber-500">
              <ChefHat className="h-6 w-6" />
            </div>
            <div>
              <h2 className="text-base sm:text-lg font-extrabold text-foreground">
                {receta && !isDuplicate
                  ? t("modals.recipe.edit_title")
                  : t("modals.recipe.create_title")}
              </h2>
              <p className="text-xs text-muted-foreground">
                {t("modals.recipe.subtitle")}
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            data-testid="btn-close-receta-dialog"
            aria-label={t("modals.common.close")}
            className="inline-flex min-h-[44px] min-w-[44px] items-center justify-center rounded-xl text-muted-foreground hover:bg-secondary hover:text-foreground transition-colors cursor-pointer"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* 3 Step Internal Tabs */}
        <div className="flex overflow-x-auto border-b border-border bg-muted/20 px-5 pt-2 gap-2">
          <button
            type="button"
            onClick={() => setActiveTab("general")}
            data-testid="receta-tab-general"
            className={cn(
              "inline-flex min-h-[44px] items-center gap-2 px-4 py-2 text-xs sm:text-sm font-bold border-b-2 whitespace-nowrap transition-colors cursor-pointer",
              activeTab === "general"
                ? "border-amber-500 text-amber-600 dark:text-amber-400"
                : "border-transparent text-muted-foreground hover:text-foreground"
            )}
          >
            <span>{t("modals.recipe.tab_general")}</span>
          </button>

          <button
            type="button"
            onClick={() => setActiveTab("ingredients")}
            data-testid="receta-tab-ingredients"
            className={cn(
              "inline-flex min-h-[44px] items-center gap-2 px-4 py-2 text-xs sm:text-sm font-bold border-b-2 whitespace-nowrap transition-colors cursor-pointer",
              activeTab === "ingredients"
                ? "border-amber-500 text-amber-600 dark:text-amber-400"
                : "border-transparent text-muted-foreground hover:text-foreground"
            )}
          >
            <span>{t("modals.recipe.tab_ingredients")}</span>
            <span className="px-2 py-0.5 rounded-full text-[10px] bg-secondary text-foreground">
              {ingredientesFijos.length}
            </span>
          </button>

          <button
            type="button"
            onClick={() => setActiveTab("dynamic")}
            data-testid="receta-tab-dynamic"
            className={cn(
              "inline-flex min-h-[44px] items-center gap-2 px-4 py-2 text-xs sm:text-sm font-bold border-b-2 whitespace-nowrap transition-colors cursor-pointer",
              activeTab === "dynamic"
                ? "border-purple-500 text-purple-600 dark:text-purple-400"
                : "border-transparent text-muted-foreground hover:text-foreground"
            )}
          >
            <Sparkles className="h-4 w-4 text-purple-500" />
            <span>{t("modals.recipe.tab_dynamic")}</span>
            <span className="px-2 py-0.5 rounded-full text-[10px] bg-purple-500/15 text-purple-600 dark:text-purple-400">
              {gruposVinculados.length}
            </span>
          </button>
        </div>

        {/* Main Content + Floating Live Costing Sidebar */}
        <div className="flex-1 overflow-y-auto grid grid-cols-1 lg:grid-cols-12 divide-y lg:divide-y-0 lg:divide-x divide-border">
          {/* Left / Center Form Area (8 cols on lg) */}
          <div className="lg:col-span-8 p-5 space-y-5 overflow-y-auto">
            {activeTab === "general" && (
              <div data-testid="receta-panel-general" className="space-y-5">
                {/* Basic fields */}
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                  <div className="sm:col-span-2">
                    <label className="block text-xs font-bold text-foreground mb-1">
                      {t("modals.recipe.field_name")} *
                    </label>
                    <input
                      type="text"
                      value={nombre}
                      onChange={(e) => setNombre(e.target.value)}
                      placeholder={t("modals.recipe.field_name_placeholder")}
                      data-testid="input-receta-nombre"
                      className="w-full min-h-[44px] px-3 rounded-xl border border-input bg-background text-sm font-semibold"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-bold text-foreground mb-1">
                      {t("modals.recipe.field_code")} *
                    </label>
                    <input
                      type="text"
                      value={codigo}
                      onChange={(e) => setCodigo(e.target.value)}
                      placeholder={t("modals.recipe.field_code_placeholder")}
                      data-testid="input-receta-codigo"
                      className="w-full min-h-[44px] px-3 rounded-xl border border-input bg-background text-sm font-mono"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                  <div>
                    <label className="block text-xs font-bold text-foreground mb-1">
                      {t("modals.recipe.field_category")}
                    </label>
                    <select
                      value={String(categoriaId)}
                      onChange={(e) => setCategoriaId(e.target.value)}
                      data-testid="select-receta-categoria"
                      className="w-full min-h-[44px] px-3 rounded-xl border border-input bg-background text-sm"
                    >
                      <option value="">{t("modals.recipe.field_category_none")}</option>
                      {categorias.map((cat) => (
                        <option key={cat.id} value={String(cat.id)}>
                          {cat.nombre}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="block text-xs font-bold text-foreground mb-1">
                      {t("modals.recipe.field_portions")}
                    </label>
                    <input
                      type="number"
                      min={1}
                      step="1"
                      value={porciones}
                      onChange={(e) => setPorciones(Math.max(1, Number(e.target.value) || 1))}
                      data-testid="input-receta-porciones"
                      className="w-full min-h-[44px] px-3 rounded-xl border border-input bg-background text-sm font-bold"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-bold text-foreground mb-1">
                      {t("modals.recipe.field_prep_time")}
                    </label>
                    <input
                      type="number"
                      min={0}
                      value={tiempoPreparacion}
                      onChange={(e) => setTiempoPreparacion(Number(e.target.value))}
                      data-testid="input-receta-tiempo"
                      className="w-full min-h-[44px] px-3 rounded-xl border border-input bg-background text-sm"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-bold text-foreground mb-1">
                    {t("modals.recipe.field_description")}
                  </label>
                  <textarea
                    rows={2}
                    value={descripcion}
                    onChange={(e) => setDescripcion(e.target.value)}
                    placeholder={t("modals.recipe.field_description_placeholder")}
                    data-testid="input-receta-descripcion"
                    className="w-full p-3 rounded-xl border border-input bg-background text-sm"
                  />
                </div>

                {/* Modality Toggle: Receta Estática vs Receta Dinámica */}
                <div className="space-y-2">
                  <label className="block text-xs font-bold text-foreground">
                    {t("modals.recipe.modality_label")}
                  </label>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <button
                      type="button"
                      onClick={() => setEsDinamica(false)}
                      data-testid="toggle-receta-estatica"
                      className={cn(
                        "flex items-start gap-3 p-3.5 rounded-xl border text-left transition-all cursor-pointer min-h-[44px]",
                        !esDinamica
                          ? "border-amber-500 bg-amber-500/10 text-foreground shadow-xs"
                          : "border-border bg-background/60 text-muted-foreground hover:border-border/80"
                      )}
                    >
                      <ScrollText className="h-5 w-5 text-amber-500 shrink-0 mt-0.5" />
                      <div>
                        <div className="text-xs font-extrabold">
                          {t("modals.recipe.modality_static")}
                        </div>
                        <div className="text-[11px] text-muted-foreground">
                          {t("modals.recipe.modality_static_desc")}
                        </div>
                      </div>
                    </button>

                    <button
                      type="button"
                      onClick={() => setEsDinamica(true)}
                      data-testid="toggle-receta-dinamica"
                      className={cn(
                        "flex items-start gap-3 p-3.5 rounded-xl border text-left transition-all cursor-pointer min-h-[44px]",
                        esDinamica
                          ? "border-purple-500 bg-purple-500/10 text-foreground shadow-xs"
                          : "border-border bg-background/60 text-muted-foreground hover:border-border/80"
                      )}
                    >
                      <Sparkles className="h-5 w-5 text-purple-500 shrink-0 mt-0.5" />
                      <div>
                        <div className="text-xs font-extrabold">
                          {t("modals.recipe.modality_dynamic")}
                        </div>
                        <div className="text-[11px] text-muted-foreground">
                          {t("modals.recipe.modality_dynamic_desc")}
                        </div>
                      </div>
                    </button>
                  </div>

                  <label className="inline-flex items-center gap-2 pt-1 cursor-pointer select-none min-h-[40px]">
                    <input
                      type="checkbox"
                      checked={esSubreceta}
                      onChange={(e) => setEsSubreceta(e.target.checked)}
                      data-testid="checkbox-receta-subreceta"
                      className="h-4 w-4 rounded accent-amber-500"
                    />
                    <span className="text-xs font-semibold text-foreground">
                      {t("modals.recipe.field_is_subrecipe")}
                    </span>
                  </label>
                </div>

                {/* Prices Section */}
                <div className="rounded-xl border border-border bg-muted/20 p-4 space-y-3">
                  <h3 className="text-xs font-extrabold uppercase tracking-wider text-muted-foreground">
                    {t("modals.recipe.pricing_section")}
                  </h3>
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                    <div>
                      <label className="block text-xs font-bold text-foreground mb-1">
                        {t("modals.recipe.field_price_net")}
                      </label>
                      <input
                        type="number"
                        min={0}
                        step="100"
                        value={precioNeto}
                        onChange={(e) => handlePrecioNetoChange(Number(e.target.value))}
                        data-testid="input-receta-precio-neto"
                        className="w-full min-h-[44px] px-3 rounded-xl border border-input bg-background text-sm font-semibold"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-bold text-foreground mb-1">
                        {t("modals.recipe.field_iva_pct")}
                      </label>
                      <input
                        type="number"
                        min={0}
                        max={100}
                        value={ivaPorcentaje}
                        onChange={(e) => handleIvaChange(Number(e.target.value))}
                        data-testid="input-receta-iva"
                        className="w-full min-h-[44px] px-3 rounded-xl border border-input bg-background text-sm"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-bold text-foreground mb-1">
                        {t("modals.recipe.field_price_gross")}
                      </label>
                      <input
                        type="number"
                        min={0}
                        step="100"
                        value={precioBruto}
                        onChange={(e) => handlePrecioBrutoChange(Number(e.target.value))}
                        data-testid="input-receta-precio-bruto"
                        className="w-full min-h-[44px] px-3 rounded-xl border border-input bg-background text-sm font-extrabold text-emerald-600 dark:text-emerald-400"
                      />
                    </div>
                  </div>
                </div>

                {/* Multimedia & Preparation */}
                <div className="space-y-3 pt-2 border-t border-border">
                  <h3 className="text-xs font-extrabold uppercase tracking-wider text-muted-foreground">
                    {t("modals.recipe.media_section")}
                  </h3>
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                    <div>
                      <label className="block text-[11px] font-bold text-foreground mb-1">
                        {t("modals.recipe.field_image_url")}
                      </label>
                      <input
                        type="url"
                        value={imagenUrl}
                        onChange={(e) => setImagenUrl(e.target.value)}
                        data-testid="input-receta-imagen"
                        className="w-full min-h-[40px] px-3 rounded-xl border border-input bg-background text-xs"
                      />
                    </div>
                    <div>
                      <label className="block text-[11px] font-bold text-foreground mb-1">
                        {t("modals.recipe.field_video_url")}
                      </label>
                      <input
                        type="url"
                        value={videoUrl}
                        onChange={(e) => setVideoUrl(e.target.value)}
                        data-testid="input-receta-video"
                        className="w-full min-h-[40px] px-3 rounded-xl border border-input bg-background text-xs"
                      />
                    </div>
                    <div>
                      <label className="block text-[11px] font-bold text-foreground mb-1">
                        {t("modals.recipe.field_doc_url")}
                      </label>
                      <input
                        type="url"
                        value={documentoUrl}
                        onChange={(e) => setDocumentoUrl(e.target.value)}
                        data-testid="input-receta-documento"
                        className="w-full min-h-[40px] px-3 rounded-xl border border-input bg-background text-xs"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-xs font-bold text-foreground mb-1">
                      {t("modals.recipe.field_preparation")}
                    </label>
                    <textarea
                      rows={3}
                      value={preparacion}
                      onChange={(e) => setPreparacion(e.target.value)}
                      placeholder={t("modals.recipe.field_preparation_placeholder")}
                      data-testid="input-receta-preparacion"
                      className="w-full p-3 rounded-xl border border-input bg-background text-xs sm:text-sm"
                    />
                  </div>
                </div>
              </div>
            )}

            {activeTab === "ingredients" && (
              <div data-testid="receta-panel-ingredients" className="space-y-4">
                <div>
                  <h3 className="text-sm font-extrabold text-foreground">
                    {t("modals.recipe.ingredients_title")}
                  </h3>
                  <p className="text-xs text-muted-foreground">
                    {t("modals.recipe.ingredients_subtitle")}
                  </p>
                </div>

                {/* Search & Add Ingredient Bar */}
                <div className="grid grid-cols-1 sm:grid-cols-12 gap-2.5 p-3 rounded-xl border border-border bg-muted/20 items-center">
                  <div className="sm:col-span-4 relative flex items-center">
                    <Search className="absolute left-3 h-4 w-4 text-muted-foreground pointer-events-none" />
                    <input
                      type="text"
                      value={ingSearch}
                      onChange={(e) => setIngSearch(e.target.value)}
                      placeholder={t("modals.recipe.search_ingredient_placeholder")}
                      data-testid="input-search-ingrediente"
                      className="w-full min-h-[44px] pl-9 pr-3 rounded-xl border border-input bg-background text-xs"
                    />
                  </div>

                  <div className="sm:col-span-3">
                    <select
                      value={ingSourceFilter}
                      onChange={(e) =>
                        setIngSourceFilter(
                          e.target.value as "all" | "producto" | "subreceta"
                        )
                      }
                      data-testid="select-filter-source-ingrediente"
                      className="w-full min-h-[44px] px-2.5 rounded-xl border border-input bg-background text-xs font-semibold"
                    >
                      <option value="all">{t("modals.recipe.filter_all_sources")}</option>
                      <option value="producto">
                        {t("modals.recipe.filter_only_products")}
                      </option>
                      <option value="subreceta">
                        {t("modals.recipe.filter_only_subrecipes")}
                      </option>
                    </select>
                  </div>

                  <div className="sm:col-span-3">
                    <select
                      value={selectedCandidateKey}
                      onChange={(e) => setSelectedCandidateKey(e.target.value)}
                      data-testid="select-candidate-ingrediente"
                      className="w-full min-h-[44px] px-2.5 rounded-xl border border-input bg-background text-xs"
                    >
                      {availableCandidates.map((cand) => (
                        <option key={cand.key} value={cand.key}>
                          [{cand.target_type === "producto"
                            ? t("modals.common.product")
                            : t("modals.common.subrecipe")}] {cand.nombre} (
                          {convertAndFormat(cand.costo_unitario)}/{cand.unidad})
                        </option>
                      ))}
                    </select>
                  </div>

                  <div className="sm:col-span-2">
                    <button
                      type="button"
                      onClick={handleAddFixedIngredient}
                      disabled={availableCandidates.length === 0}
                      data-testid="btn-add-ingrediente-fijo"
                      className="w-full inline-flex min-h-[44px] items-center justify-center gap-1.5 px-3 py-2 rounded-xl bg-amber-500 text-xs font-extrabold text-slate-950 hover:bg-amber-400 disabled:opacity-50 transition-colors cursor-pointer"
                    >
                      <Plus className="h-4 w-4" />
                      <span>{t("modals.recipe.add_ingredient_btn")}</span>
                    </button>
                  </div>
                </div>

                {/* Fixed Ingredients Table */}
                {ingredientesFijos.length === 0 ? (
                  <div
                    data-testid="receta-ingredients-empty"
                    className="p-8 text-center rounded-xl border border-dashed border-border text-xs text-muted-foreground"
                  >
                    {t("modals.recipe.empty_ingredients")}
                  </div>
                ) : (
                  <div className="overflow-x-auto rounded-xl border border-border">
                    <table className="w-full text-left border-collapse text-xs">
                      <thead>
                        <tr className="border-b border-border bg-muted/40 text-[10px] font-black uppercase text-muted-foreground">
                          <th className="py-2.5 px-3">{t("modals.recipe.col_item")}</th>
                          <th className="py-2.5 px-2">{t("modals.recipe.col_type")}</th>
                          <th className="py-2.5 px-2">{t("modals.recipe.col_qty")}</th>
                          <th className="py-2.5 px-2">{t("modals.recipe.col_unit")}</th>
                          <th className="py-2.5 px-2">{t("modals.recipe.col_merma")}</th>
                          <th className="py-2.5 px-2 text-right">
                            {t("modals.recipe.col_ppp_unit")}
                          </th>
                          <th className="py-2.5 px-3 text-right">
                            {t("modals.recipe.col_ppp_total")}
                          </th>
                          <th className="py-2.5 px-2 text-center">
                            {t("modals.common.actions")}
                          </th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-border/60">
                        {ingredientesFijos.map((ing, idx) => (
                          <tr
                            key={ing.id ?? idx}
                            data-testid={`ingrediente-fijo-row-${idx}`}
                            className="hover:bg-muted/20"
                          >
                            <td className="py-2.5 px-3 font-bold text-foreground">
                              {ing.nombre}
                            </td>
                            <td className="py-2.5 px-2">
                              <span
                                className={cn(
                                  "px-2 py-0.5 rounded-full text-[10px] font-extrabold",
                                  ing.target_type === "subreceta"
                                    ? "bg-sky-500/15 text-sky-600 dark:text-sky-400"
                                    : "bg-amber-500/15 text-amber-600 dark:text-amber-400"
                                )}
                              >
                                {ing.target_type === "subreceta"
                                  ? t("modals.common.subrecipe")
                                  : t("modals.common.product")}
                              </span>
                            </td>
                            <td className="py-2.5 px-2 w-24">
                              <input
                                type="number"
                                step="0.01"
                                min="0.001"
                                value={ing.cantidad_receta}
                                onChange={(e) =>
                                  handleUpdateFixedIngredient(idx, {
                                    cantidad_receta: Number(e.target.value),
                                  })
                                }
                                data-testid={`input-ingrediente-cantidad-${idx}`}
                                className="w-full min-h-[38px] px-2 rounded-lg border border-input bg-background text-xs font-bold"
                              />
                            </td>
                            <td className="py-2.5 px-2 w-24">
                              <input
                                type="text"
                                value={ing.unidad}
                                onChange={(e) =>
                                  handleUpdateFixedIngredient(idx, { unidad: e.target.value })
                                }
                                data-testid={`input-ingrediente-unidad-${idx}`}
                                className="w-full min-h-[38px] px-2 rounded-lg border border-input bg-background text-xs"
                              />
                            </td>
                            <td className="py-2.5 px-2 w-24">
                              <input
                                type="number"
                                step="0.5"
                                min="0"
                                max="99"
                                value={ing.porcentaje_merma}
                                onChange={(e) =>
                                  handleUpdateFixedIngredient(idx, {
                                    porcentaje_merma: Number(e.target.value),
                                  })
                                }
                                data-testid={`input-ingrediente-merma-${idx}`}
                                className="w-full min-h-[38px] px-2 rounded-lg border border-input bg-background text-xs"
                              />
                            </td>
                            <td className="py-2.5 px-2 w-28 text-right">
                              <input
                                type="number"
                                step="50"
                                min="0"
                                value={ing.costo_unitario}
                                onChange={(e) =>
                                  handleUpdateFixedIngredient(idx, {
                                    costo_unitario: Number(e.target.value),
                                  })
                                }
                                data-testid={`input-ingrediente-costo-unit-${idx}`}
                                className="w-full min-h-[38px] px-2 rounded-lg border border-input bg-background text-xs text-right"
                              />
                            </td>
                            <td
                              data-testid={`ingrediente-costo-total-${idx}`}
                              className="py-2.5 px-3 text-right font-extrabold text-foreground whitespace-nowrap"
                            >
                              {convertAndFormat(ing.costo_total)}
                            </td>
                            <td className="py-2.5 px-2 text-center">
                              <button
                                type="button"
                                onClick={() => handleRemoveFixedIngredient(idx)}
                                data-testid={`btn-remove-ingrediente-${idx}`}
                                aria-label={t("modals.common.delete")}
                                className="inline-flex min-h-[38px] min-w-[38px] items-center justify-center rounded-lg text-rose-500 hover:bg-rose-500/10 cursor-pointer"
                              >
                                <Trash2 className="h-4 w-4" />
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            )}

            {activeTab === "dynamic" && (
              <div data-testid="receta-panel-dynamic" className="space-y-4">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <div>
                    <h3 className="text-sm font-extrabold text-foreground flex items-center gap-2">
                      <Sparkles className="h-4 w-4 text-purple-500" />
                      <span>{t("modals.recipe.dynamic_title")}</span>
                    </h3>
                    <p className="text-xs text-muted-foreground">
                      {t("modals.recipe.dynamic_subtitle")}
                    </p>
                  </div>

                  <div className="flex flex-wrap items-center gap-2">
                    <button
                      type="button"
                      onClick={() => {
                        setOptionSelectorInitialTab("library");
                        setIsOptionSelectorOpen(true);
                      }}
                      data-testid="btn-open-option-group-selector"
                      className="inline-flex min-h-[44px] items-center gap-1.5 px-3.5 py-2 rounded-xl bg-purple-600 text-xs font-extrabold text-white hover:bg-purple-500 transition-colors cursor-pointer"
                    >
                      <Library className="h-4 w-4" />
                      <span>{t("modals.recipe.btn_add_option_group")}</span>
                    </button>

                    <button
                      type="button"
                      onClick={() => {
                        setOptionSelectorInitialTab("create");
                        setIsOptionSelectorOpen(true);
                      }}
                      data-testid="btn-create-insitu-group"
                      className="inline-flex min-h-[44px] items-center gap-1.5 px-3.5 py-2 rounded-xl border border-purple-500/40 bg-purple-500/10 text-xs font-extrabold text-purple-600 dark:text-purple-400 hover:bg-purple-500/20 transition-colors cursor-pointer"
                    >
                      <Plus className="h-4 w-4" />
                      <span>{t("modals.recipe.btn_create_insitu_group")}</span>
                    </button>
                  </div>
                </div>

                {gruposVinculados.length === 0 ? (
                  <div
                    data-testid="receta-dynamic-empty"
                    className="p-8 text-center rounded-xl border border-dashed border-border text-xs text-muted-foreground"
                  >
                    {t("modals.recipe.empty_dynamic_groups")}
                  </div>
                ) : (
                  <div className="space-y-4">
                    {gruposVinculados.map(({ grupo, es_requerido }, groupIdx) => (
                      <div
                        key={`${grupo.id}-${groupIdx}`}
                        data-testid={`receta-dynamic-group-${groupIdx}`}
                        className="rounded-xl border border-purple-500/30 bg-purple-500/5 p-4 space-y-3"
                      >
                        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-border/60 pb-3">
                          <div className="flex items-center gap-2">
                            <Layers className="h-4 w-4 text-purple-500" />
                            <span className="font-extrabold text-sm text-foreground">
                              {grupo.nombre}
                            </span>
                          </div>

                          <div className="flex flex-wrap items-center gap-3">
                            <div className="flex items-center gap-1.5">
                              <label className="text-[11px] font-bold text-muted-foreground">
                                {t("modals.recipe.group_min_label")}:
                              </label>
                              <input
                                type="number"
                                min={0}
                                value={grupo.seleccion_minima ?? 1}
                                onChange={(e) =>
                                  handleUpdateDynamicGroupMeta(groupIdx, {
                                    seleccion_minima: Number(e.target.value),
                                  })
                                }
                                data-testid={`input-dynamic-group-min-${groupIdx}`}
                                className="w-16 min-h-[36px] px-2 rounded-lg border border-input bg-background text-xs font-bold"
                              />
                            </div>

                            <div className="flex items-center gap-1.5">
                              <label className="text-[11px] font-bold text-muted-foreground">
                                {t("modals.recipe.group_max_label")}:
                              </label>
                              <input
                                type="number"
                                min={1}
                                value={grupo.seleccion_maxima ?? 1}
                                onChange={(e) =>
                                  handleUpdateDynamicGroupMeta(groupIdx, {
                                    seleccion_maxima: Number(e.target.value),
                                  })
                                }
                                data-testid={`input-dynamic-group-max-${groupIdx}`}
                                className="w-16 min-h-[36px] px-2 rounded-lg border border-input bg-background text-xs font-bold"
                              />
                            </div>

                            <label className="inline-flex items-center gap-1.5 text-xs font-semibold cursor-pointer">
                              <input
                                type="checkbox"
                                checked={es_requerido}
                                onChange={(e) =>
                                  handleUpdateDynamicGroupMeta(groupIdx, {
                                    es_requerido: e.target.checked,
                                  })
                                }
                                data-testid={`checkbox-dynamic-group-req-${groupIdx}`}
                                className="h-4 w-4 accent-purple-600"
                              />
                              <span>{t("modals.recipe.group_required_label")}</span>
                            </label>

                            <button
                              type="button"
                              onClick={() => handleRemoveDynamicGroup(groupIdx)}
                              data-testid={`btn-remove-dynamic-group-${groupIdx}`}
                              aria-label={t("modals.common.delete")}
                              className="inline-flex min-h-[36px] min-w-[36px] items-center justify-center rounded-lg text-rose-500 hover:bg-rose-500/10 cursor-pointer"
                            >
                              <Trash2 className="h-4 w-4" />
                            </button>
                          </div>
                        </div>

                        {/* Add polymorphic option to group */}
                        <div className="flex flex-wrap items-center gap-2">
                          <select
                            value={groupCandidateItemMap[groupIdx] || ""}
                            onChange={(e) =>
                              setGroupCandidateItemMap((prev) => ({
                                ...prev,
                                [groupIdx]: e.target.value,
                              }))
                            }
                            data-testid={`select-group-add-item-${groupIdx}`}
                            className="flex-1 min-h-[40px] px-2.5 rounded-xl border border-input bg-background text-xs"
                          >
                            {productos.map((p) => (
                              <option key={`producto:${p.id}`} value={`producto:${p.id}`}>
                                [{t("modals.common.product")}] {p.nombre} (
                                {convertAndFormat(p.costo_unitario_ppp ?? p.costo_unitario ?? 0)})
                              </option>
                            ))}
                            {recetasCatalogo
                              .filter((r) => !receta || String(r.id) !== String(receta.id))
                              .map((r) => (
                                <option key={`receta:${r.id}`} value={`receta:${r.id}`}>
                                  [{t("modals.common.subrecipe")}] {r.nombre} (
                                  {convertAndFormat(r.costo_porcion ?? r.costo_total ?? 0)})
                                </option>
                              ))}
                          </select>

                          <button
                            type="button"
                            onClick={() => handleAddItemToDynamicGroup(groupIdx)}
                            data-testid={`btn-group-add-item-${groupIdx}`}
                            className="inline-flex min-h-[40px] items-center gap-1.5 px-3 py-1.5 rounded-xl bg-purple-600/15 text-purple-600 dark:text-purple-400 border border-purple-500/30 text-xs font-extrabold hover:bg-purple-600/25 cursor-pointer"
                          >
                            <Plus className="h-3.5 w-3.5" />
                            <span>{t("modals.recipe.group_add_item_btn")}</span>
                          </button>
                        </div>

                        {/* Group Option Items Table */}
                        <div className="space-y-2">
                          {(grupo.items || []).map((item, itemIdx) => (
                            <div
                              key={item.id ?? itemIdx}
                              data-testid={`dynamic-group-${groupIdx}-item-${itemIdx}`}
                              className="grid grid-cols-1 sm:grid-cols-12 gap-2 items-center p-2 rounded-lg border border-border bg-card text-xs"
                            >
                              <div className="sm:col-span-4 font-semibold text-foreground">
                                {item.nombre}
                              </div>

                              <div className="sm:col-span-2 flex items-center gap-1">
                                <span className="text-[10px] text-muted-foreground">
                                  {t("modals.recipe.option_col_portion")}:
                                </span>
                                <input
                                  type="number"
                                  step="0.05"
                                  min="0.01"
                                  value={item.cantidad ?? item.cantidad_porcion ?? 1}
                                  onChange={(e) =>
                                    handleUpdateDynamicGroupItem(groupIdx, itemIdx, {
                                      cantidad: Number(e.target.value),
                                    })
                                  }
                                  data-testid={`input-group-${groupIdx}-item-qty-${itemIdx}`}
                                  className="w-16 min-h-[34px] px-1.5 rounded border border-input bg-background text-xs font-bold"
                                />
                              </div>

                              <div className="sm:col-span-2 flex items-center gap-1">
                                <label className="inline-flex items-center gap-1 cursor-pointer text-[11px] font-bold text-emerald-600 dark:text-emerald-400">
                                  <input
                                    type="checkbox"
                                    checked={Boolean(
                                      item.es_opcion_default ?? item.es_default
                                    )}
                                    onChange={(e) =>
                                      handleUpdateDynamicGroupItem(groupIdx, itemIdx, {
                                        es_opcion_default: e.target.checked,
                                      })
                                    }
                                    data-testid={`checkbox-group-${groupIdx}-item-default-${itemIdx}`}
                                    className="h-4 w-4 accent-emerald-600"
                                  />
                                  <span>{t("modals.recipe.option_col_default")}</span>
                                </label>
                              </div>

                              <div className="sm:col-span-2 flex items-center gap-1">
                                <span className="text-[10px] text-muted-foreground">+</span>
                                <input
                                  type="number"
                                  step="100"
                                  min="0"
                                  value={item.recargo_precio ?? item.precio_adicional ?? 0}
                                  onChange={(e) =>
                                    handleUpdateDynamicGroupItem(groupIdx, itemIdx, {
                                      recargo_precio: Number(e.target.value),
                                    })
                                  }
                                  data-testid={`input-group-${groupIdx}-item-surcharge-${itemIdx}`}
                                  className="w-20 min-h-[34px] px-1.5 rounded border border-input bg-background text-xs"
                                />
                              </div>

                              <div className="sm:col-span-1">
                                <input
                                  type="number"
                                  step="50"
                                  min="0"
                                  value={item.costo_referencial ?? 0}
                                  onChange={(e) =>
                                    handleUpdateDynamicGroupItem(groupIdx, itemIdx, {
                                      costo_referencial: Number(e.target.value),
                                    })
                                  }
                                  data-testid={`input-group-${groupIdx}-item-cost-${itemIdx}`}
                                  className="w-full min-h-[34px] px-1.5 rounded border border-input bg-background text-xs text-right"
                                />
                              </div>

                              <div className="sm:col-span-1 flex justify-end">
                                <button
                                  type="button"
                                  onClick={() =>
                                    handleRemoveDynamicGroupItem(groupIdx, itemIdx)
                                  }
                                  data-testid={`btn-remove-group-${groupIdx}-item-${itemIdx}`}
                                  aria-label={t("modals.common.delete")}
                                  className="inline-flex min-h-[34px] min-w-[34px] items-center justify-center rounded text-rose-500 hover:bg-rose-500/10 cursor-pointer"
                                >
                                  <Trash2 className="h-3.5 w-3.5" />
                                </button>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Right Floating Live Costing Sidebar (4 cols on lg) */}
          <aside
            data-testid="receta-live-costing-panel"
            className="lg:col-span-4 bg-muted/25 p-5 space-y-4 flex flex-col justify-between"
          >
            <div className="space-y-4">
              <div className="flex items-center gap-2.5 border-b border-border pb-3">
                <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-emerald-500/15 text-emerald-600 dark:text-emerald-400">
                  <Calculator className="h-5 w-5" />
                </div>
                <div>
                  <h3 className="text-sm font-extrabold text-foreground">
                    {t("modals.recipe.sidebar_title")}
                  </h3>
                  <p className="text-[11px] text-muted-foreground">
                    {t("modals.recipe.sidebar_subtitle")}
                  </p>
                </div>
              </div>

              <div className="space-y-2.5 text-xs">
                <div className="flex items-center justify-between py-1.5 border-b border-border/50">
                  <span className="text-muted-foreground font-medium">
                    {t("modals.recipe.cost_fixed_inputs")}
                  </span>
                  <span
                    data-testid="live-cost-fixed"
                    className="font-bold text-foreground"
                  >
                    {convertAndFormat(liveCosting.fixedCost)}
                  </span>
                </div>

                <div className="flex items-center justify-between py-1.5 border-b border-border/50">
                  <span className="text-muted-foreground font-medium">
                    {t("modals.recipe.cost_default_options")}
                  </span>
                  <span
                    data-testid="live-cost-options-default"
                    className="font-bold text-purple-600 dark:text-purple-400"
                  >
                    {convertAndFormat(liveCosting.defaultOptionsCost)}
                  </span>
                </div>

                <div className="flex items-center justify-between py-2.5 px-3 rounded-xl bg-card border border-border shadow-2xs">
                  <span className="font-extrabold text-foreground">
                    {t("modals.recipe.cost_total_base")}
                  </span>
                  <span
                    data-testid="live-cost-total-base"
                    className="text-sm font-black text-foreground"
                  >
                    {convertAndFormat(liveCosting.totalBaseCost)}
                  </span>
                </div>

                <div className="flex items-center justify-between py-1.5 px-2">
                  <span className="text-muted-foreground">
                    {t("modals.recipe.cost_per_portion")} ({porciones})
                  </span>
                  <span
                    data-testid="live-cost-per-portion"
                    className="font-bold text-foreground"
                  >
                    {convertAndFormat(liveCosting.costPerPortion)}
                  </span>
                </div>

                <div className="flex items-center justify-between py-2.5 px-3 rounded-xl bg-amber-500/10 border border-amber-500/30">
                  <span className="font-bold text-amber-700 dark:text-amber-300">
                    {t("modals.recipe.cost_worst_case")}
                  </span>
                  <span
                    data-testid="live-cost-worst-case"
                    className="text-sm font-extrabold text-amber-700 dark:text-amber-300"
                  >
                    {convertAndFormat(liveCosting.totalWorstCaseCost)}
                  </span>
                </div>
              </div>

              {/* Projected Margin Card */}
              <div className="rounded-xl border border-border bg-card p-4 space-y-2.5">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-extrabold text-foreground">
                    {t("modals.recipe.projected_margin")}
                  </span>
                  <span
                    data-testid="live-margin-badge"
                    className={cn(
                      "px-2.5 py-1 rounded-full text-xs font-black border",
                      margenSemaphore.className
                    )}
                  >
                    {margenSemaphore.label}
                  </span>
                </div>

                <div className="flex items-center justify-between text-[11px] text-muted-foreground">
                  <span>{t("modals.recipe.food_cost_label")}</span>
                  <span data-testid="live-food-cost-pct" className="font-bold">
                    {liveCosting.foodCostPct.toFixed(1)}%
                  </span>
                </div>

                {esDinamica && (
                  <div className="flex items-center justify-between text-[11px] text-muted-foreground pt-1 border-t border-border/50">
                    <span>{t("modals.recipe.worst_case_margin")}</span>
                    <span data-testid="live-worst-margin-pct" className="font-bold">
                      {liveCosting.worstCaseMarginPct.toFixed(1)}%
                    </span>
                  </div>
                )}
              </div>
            </div>

            {/* Action Buttons in Footer of Sidebar */}
            <div className="flex items-center justify-end gap-2.5 pt-4 border-t border-border">
              <button
                type="button"
                onClick={onClose}
                data-testid="btn-cancel-receta-dialog"
                className="inline-flex min-h-[44px] items-center justify-center rounded-xl border border-border bg-secondary px-4 py-2 text-xs font-bold text-foreground hover:bg-secondary/80 transition-colors cursor-pointer"
              >
                {t("modals.common.cancel")}
              </button>
              <button
                type="button"
                onClick={handleSubmit}
                disabled={!nombre.trim()}
                data-testid="btn-save-receta"
                className="inline-flex min-h-[44px] items-center gap-2 rounded-xl bg-amber-500 px-5 py-2 text-xs font-extrabold text-slate-950 hover:bg-amber-400 disabled:opacity-50 transition-colors cursor-pointer"
              >
                <Check className="h-4 w-4" />
                <span>{t("modals.recipe.save_recipe_btn")}</span>
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
        subrecetas={recetasCatalogo.filter(
          (r) => !receta || String(r.id) !== String(receta.id)
        )}
      />
    </div>
  );
}

export default RecetaDialog;
