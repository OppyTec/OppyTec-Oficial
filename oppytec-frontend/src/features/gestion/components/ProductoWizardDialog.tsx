// oppytec-frontend/src/features/gestion/components/ProductoWizardDialog.tsx
import { useState, useEffect, useMemo, useCallback, useRef } from "react";
import {
  Layers,
  FileSpreadsheet,
  FileText,
  CheckCircle2,
  ChevronRight,
  ChevronLeft,
  Save,
  Trash2,
  Plus,
  Package,
  Boxes,
  Warehouse,
  DollarSign,
  Tag,
  Percent,
  TrendingUp,
  Sparkles,
  RotateCcw,
} from "lucide-react";
import { ResponsiveDialog } from "@/shared/components/ui/ResponsiveDialog";
import { cn } from "@/shared/lib";
import { toast } from "sonner";
import { DRAFT_STORAGE_KEY, type DraftProductData } from "./DraftRecoveryBanner";
import type {
  Producto,
  Categoria,
  Marca,
  TipoEnvase,
  PresentacionCompra,
  BodegaConfig,
} from "../types";
import type { BodegaInfo } from "./ProductMobileCard";
import { DEFAULT_BODEGAS } from "../GestionPage";

// ============================================================================
// Defaults & Constants
// ============================================================================
export const UNIDADES_BASE = [
  { value: "kg", label: "Kilogramos (kg)" },
  { value: "g", label: "Gramos (g)" },
  { value: "L", label: "Litros (L)" },
  { value: "mL", label: "Mililitros (mL)" },
  { value: "unidad", label: "Unidades (un)" },
];

export const TIPOS_PRODUCTO = [
  { value: "insumo", label: "Insumo (Cocina / Barra)" },
  { value: "venta_directa", label: "Venta Directa (Retail / Bar)" },
  { value: "mixto", label: "Mixto (Insumo + Venta)" },
];

export const DEFAULT_AREAS_PRODUCTO = [
  { id: "area-cocina", nombre: "Cocina Caliente", color: "#EF4444" },
  { id: "area-bar", nombre: "Bar & Cava", color: "#8B5CF6" },
  { id: "area-bodega", nombre: "Bodega Central", color: "#3B82F6" },
  { id: "area-salon", nombre: "Salón & Comedor", color: "#10B981" },
];

export const DEFAULT_ENVASES_PRESET: TipoEnvase[] = [
  { id: "env-botella", nombre: "Botella", icono: "bottle" },
  { id: "env-lata", nombre: "Lata", icono: "can" },
  { id: "env-frasco", nombre: "Frasco", icono: "jar" },
  { id: "env-caja", nombre: "Caja", icono: "package" },
  { id: "env-bolsa", nombre: "Bolsa", icono: "bag" },
  { id: "env-saco", nombre: "Saco", icono: "sack" },
  { id: "env-granel", nombre: "A Granel", icono: "scale" },
];

// ============================================================================
// Formulas: Nombre Autogenerado & Métricas Financieras
// ============================================================================
export function generateFullProductName({
  nombre,
  marcaNombre,
  envaseNombre,
  contenidoEnvase,
  unidadEnvase,
  unidadBase,
}: {
  nombre: string;
  marcaNombre?: string | null;
  envaseNombre?: string | null;
  contenidoEnvase?: number | string | null;
  unidadEnvase?: string | null;
  unidadBase?: string | null;
}): string {
  if (!nombre?.trim()) return "";
  let result = nombre.trim();

  if (marcaNombre && marcaNombre.trim()) {
    result += ` - ${marcaNombre.trim()}`;
  }

  const isGranel = envaseNombre?.toLowerCase().includes("granel");
  if (isGranel) {
    result += ` (A Granel)`;
  } else if (envaseNombre || (contenidoEnvase && Number(contenidoEnvase) > 0)) {
    const parts: string[] = [];
    if (envaseNombre && envaseNombre.trim()) {
      parts.push(envaseNombre.trim());
    }
    if (contenidoEnvase && Number(contenidoEnvase) > 0) {
      parts.push(`${contenidoEnvase} ${unidadEnvase || unidadBase || "un"}`);
    }
    if (parts.length > 0) {
      result += ` (${parts.join(" ")})`;
    }
  }

  return result;
}

export function calculateFinancialKPIs({
  costoNeto,
  costoBruto,
  precioVentaNeto,
  precioVentaBruto,
}: {
  costoNeto: number;
  costoBruto: number;
  precioVentaNeto: number;
  precioVentaBruto: number;
}) {
  const margenNeto =
    precioVentaNeto > 0 && costoNeto > 0
      ? ((precioVentaNeto - costoNeto) / precioVentaNeto) * 100
      : 0;

  const margenBruto =
    precioVentaBruto > 0 && costoBruto > 0
      ? ((precioVentaBruto - costoBruto) / precioVentaBruto) * 100
      : 0;

  const markup =
    costoNeto > 0 && precioVentaNeto > 0
      ? ((precioVentaNeto - costoNeto) / costoNeto) * 100
      : 0;

  const foodCost =
    precioVentaNeto > 0 && costoNeto > 0
      ? (costoNeto / precioVentaNeto) * 100
      : 0;

  return {
    margenNeto: Math.round(margenNeto * 10) / 10,
    margenBruto: Math.round(margenBruto * 10) / 10,
    markup: Math.round(markup * 10) / 10,
    foodCost: Math.round(foodCost * 10) / 10,
  };
}

// ============================================================================
// Types
// ============================================================================
export interface ProductoWizardDialogProps {
  readonly open: boolean;
  readonly onOpenChange: (open: boolean) => void;
  readonly editingProduct?: Producto | null;
  readonly initialDraft?: DraftProductData | null;
  readonly initialStep?: 1 | 2 | 3 | 4;
  readonly categorias: Categoria[];
  readonly marcas?: Marca[];
  readonly tiposEnvase?: TipoEnvase[];
  readonly bodegas?: BodegaInfo[];
  readonly areas?: typeof DEFAULT_AREAS_PRODUCTO;
  readonly onSave: (productData: Partial<Producto>) => Promise<void> | void;
  readonly onOpenExcelImport?: () => void;
  readonly onOpenFacturaImport?: () => void;
  readonly onCreateBrand?: (name: string) => Promise<Marca | void> | Marca | void;
  readonly onCreateTipoEnvase?: (name: string, icono?: string) => Promise<TipoEnvase | void> | TipoEnvase | void;
}

interface LocalBodegaConfig {
  enabled: boolean;
  stock_actual: number;
  stock_minimo: number;
  coordenada_letra: string;
  coordenada_numero: string;
}

// ============================================================================
// Component
// ============================================================================
export function ProductoWizardDialog({
  open,
  onOpenChange,
  editingProduct,
  initialDraft,
  initialStep = 1,
  categorias,
  marcas = [],
  tiposEnvase = DEFAULT_ENVASES_PRESET,
  bodegas = DEFAULT_BODEGAS,
  areas = DEFAULT_AREAS_PRODUCTO,
  onSave,
  onOpenExcelImport,
  onOpenFacturaImport,
  onCreateBrand,
  onCreateTipoEnvase,
}: ProductoWizardDialogProps) {
  // Stepper & Channel
  const [currentStep, setCurrentStep] = useState<1 | 2 | 3 | 4>(initialStep);
  const [activeChannel, setActiveChannel] = useState<"manual" | "excel" | "invoice">("manual");
  const [draftStatus, setDraftStatus] = useState<"idle" | "saving" | "saved">("idle");
  const [isSubmitting, setIsSubmitting] = useState(false);

  // STEP 1 State: Básico & Familia
  const [nombre, setNombre] = useState("");
  const [marcaId, setMarcaId] = useState<string>("");
  const [sku, setSku] = useState("");
  const [codigoBarra, setCodigoBarra] = useState("");
  const [categoriaId, setCategoriaId] = useState<string>("");
  const [familia, setFamilia] = useState("");
  const [tipoProducto, setTipoProducto] = useState<string>("insumo");
  const [imagenUrl, setImagenUrl] = useState("");
  const [selectedAreaIds, setSelectedAreaIds] = useState<string[]>([]);

  // Brand quick creation
  const [showNewMarcaInput, setShowNewMarcaInput] = useState(false);
  const [newMarcaText, setNewMarcaText] = useState("");
  const [localMarcas, setLocalMarcas] = useState<Marca[]>(marcas);

  // STEP 2 State: Envases & Packs
  const [unidadBase, setUnidadBase] = useState<string>("kg");
  const [tipoEnvaseId, setTipoEnvaseId] = useState<string>("");
  const [contenidoEnvase, setContenidoEnvase] = useState<string>("");
  const [unidadEnvase, setUnidadEnvase] = useState<string>("g");
  const [presentaciones, setPresentaciones] = useState<PresentacionCompra[]>([]);

  // Envase quick creation
  const [showNewEnvaseInput, setShowNewEnvaseInput] = useState(false);
  const [newEnvaseText, setNewEnvaseText] = useState("");
  const [localTiposEnvase, setLocalTiposEnvase] = useState<TipoEnvase[]>(tiposEnvase);

  // STEP 3 State: Bodegas & Stock
  const [bodegasMap, setBodegasMap] = useState<Record<string, LocalBodegaConfig>>({});

  // STEP 4 State: Precios & Costos
  const [ivaPorcentaje, setIvaPorcentaje] = useState<number>(19);
  const [costoUnitarioNeto, setCostoUnitarioNeto] = useState<number>(0);
  const [costoUnitarioBruto, setCostoUnitarioBruto] = useState<number>(0);
  const [precioVentaNeto, setPrecioVentaNeto] = useState<number>(0);
  const [precioVentaBruto, setPrecioVentaBruto] = useState<number>(0);

  // Track draft initialization to prevent overwriting on first render
  const isInitialized = useRef(false);
  const saveTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // Sync external marcas/tiposEnvase
  useEffect(() => {
    if (marcas.length > 0) setLocalMarcas(marcas);
  }, [marcas]);

  useEffect(() => {
    if (tiposEnvase.length > 0) setLocalTiposEnvase(tiposEnvase);
  }, [tiposEnvase]);

  // ==========================================================================
  // Initialization: Editing Product vs Draft vs Clean
  // ==========================================================================
  useEffect(() => {
    if (!open) {
      isInitialized.current = false;
      return;
    }

    if (editingProduct) {
      // Load from editing product
      setNombre(editingProduct.nombre || "");
      setMarcaId(editingProduct.marca_id || "");
      setSku(editingProduct.sku || "");
      setCodigoBarra(editingProduct.codigo_barra || "");
      setCategoriaId(editingProduct.categoria_id || categorias[0]?.id || "");
      setFamilia(editingProduct.familia?.nombre || "");
      setTipoProducto("insumo");
      setImagenUrl(editingProduct.imagen_url || "");
      setSelectedAreaIds(editingProduct.areas_operativas_ids || []);

      setUnidadBase(editingProduct.unidad || "kg");
      setTipoEnvaseId(editingProduct.tipo_envase_id || "");
      setContenidoEnvase(editingProduct.contenido_envase ? String(editingProduct.contenido_envase) : "");
      setUnidadEnvase(editingProduct.unidad_envase || "g");
      setPresentaciones(editingProduct.presentaciones_compra || []);

      const bMap: Record<string, LocalBodegaConfig> = {};
      bodegas.forEach((b) => {
        const found = editingProduct.bodegas_config?.find((c) => c.bodega_id === b.id);
        bMap[b.id] = {
          enabled: Boolean(found),
          stock_actual: found?.stock_actual ?? 0,
          stock_minimo: found?.stock_minimo ?? 0,
          coordenada_letra: found?.coordenada_letra ?? "",
          coordenada_numero: found?.coordenada_numero ?? "",
        };
      });
      setBodegasMap(bMap);

      const iva = editingProduct.iva_porcentaje ?? 19;
      setIvaPorcentaje(iva);
      const cNeto = editingProduct.costo_unitario ?? 0;
      setCostoUnitarioNeto(cNeto);
      setCostoUnitarioBruto(Math.round(cNeto * (1 + iva / 100)));

      const pvBruto = editingProduct.precio_venta ?? 0;
      setPrecioVentaBruto(pvBruto);
      setPrecioVentaNeto(Math.round(pvBruto / (1 + iva / 100)));

      setCurrentStep(initialStep);
      isInitialized.current = true;
      return;
    }

    // Try initialDraft prop or localStorage draft
    let draftData: DraftProductData | null = initialDraft ?? null;
    if (!draftData && typeof window !== "undefined") {
      try {
        const raw = window.localStorage.getItem(DRAFT_STORAGE_KEY);
        if (raw) draftData = JSON.parse(raw);
      } catch {
        draftData = null;
      }
    }

    if (draftData) {
      setNombre(draftData.nombre || "");
      setMarcaId((draftData.marcaId as string) || "");
      setSku(draftData.sku || "");
      setCodigoBarra((draftData.codigoBarra as string) || "");
      setCategoriaId(
        (draftData.categoriaId as string) ||
        (draftData.categoria_id as string) ||
        categorias[0]?.id ||
        ""
      );
      setFamilia((draftData.familia as string) || "");
      setTipoProducto((draftData.tipoProducto as string) || "insumo");
      setImagenUrl((draftData.imagenUrl as string) || "");
      setSelectedAreaIds((draftData.selectedAreaIds as string[]) || []);

      setUnidadBase((draftData.unidadBase as string) || (draftData.unidad as string) || "kg");
      setTipoEnvaseId((draftData.tipoEnvaseId as string) || "");
      setContenidoEnvase((draftData.contenidoEnvase as string) || "");
      setUnidadEnvase((draftData.unidadEnvase as string) || "g");
      setPresentaciones((draftData.presentaciones as PresentacionCompra[]) || []);

      const bMap: Record<string, LocalBodegaConfig> = {};
      bodegas.forEach((b) => {
        bMap[b.id] = {
          enabled: b.id === bodegas[0]?.id,
          stock_actual: 0,
          stock_minimo: 5,
          coordenada_letra: "A",
          coordenada_numero: "1",
        };
      });
      setBodegasMap(bMap);

      const iva = (draftData.ivaPorcentaje as number) ?? 19;
      setIvaPorcentaje(iva);
      const cNeto = (draftData.costoUnitarioNeto as number) ?? (draftData.costo_unitario as number) ?? 0;
      setCostoUnitarioNeto(cNeto);
      setCostoUnitarioBruto(Math.round(cNeto * (1 + iva / 100)));

      const pvBruto = (draftData.precioVentaBruto as number) ?? (draftData.precio_venta as number) ?? 0;
      setPrecioVentaBruto(pvBruto);
      setPrecioVentaNeto(Math.round(pvBruto / (1 + iva / 100)));

      const step = (draftData.currentStep as 1 | 2 | 3 | 4) || initialStep;
      setCurrentStep(step);
    } else {
      // Clean form
      setNombre("");
      setMarcaId("");
      setSku("");
      setCodigoBarra("");
      setCategoriaId(categorias[0]?.id || "");
      setFamilia("");
      setTipoProducto("insumo");
      setImagenUrl("");
      setSelectedAreaIds([]);

      setUnidadBase("kg");
      setTipoEnvaseId("");
      setContenidoEnvase("");
      setUnidadEnvase("g");
      setPresentaciones([]);

      const bMap: Record<string, LocalBodegaConfig> = {};
      bodegas.forEach((b) => {
        bMap[b.id] = {
          enabled: b.id === bodegas[0]?.id,
          stock_actual: 0,
          stock_minimo: 5,
          coordenada_letra: "A",
          coordenada_numero: "1",
        };
      });
      setBodegasMap(bMap);

      setIvaPorcentaje(19);
      setCostoUnitarioNeto(0);
      setCostoUnitarioBruto(0);
      setPrecioVentaNeto(0);
      setPrecioVentaBruto(0);
      setCurrentStep(initialStep);
    }

    isInitialized.current = true;
  }, [open, editingProduct, initialDraft, initialStep, categorias, bodegas]);

  // ==========================================================================
  // Auto-generate Full Product Name Banner
  // ==========================================================================
  const selectedMarcaObj = useMemo(
    () => localMarcas.find((m) => m.id === marcaId),
    [localMarcas, marcaId]
  );
  const selectedEnvaseObj = useMemo(
    () => localTiposEnvase.find((e) => e.id === tipoEnvaseId),
    [localTiposEnvase, tipoEnvaseId]
  );

  const nombreCompletoGenerado = useMemo(() => {
    return generateFullProductName({
      nombre,
      marcaNombre: selectedMarcaObj?.nombre || null,
      envaseNombre: selectedEnvaseObj?.nombre || null,
      contenidoEnvase: contenidoEnvase || null,
      unidadEnvase,
      unidadBase,
    });
  }, [nombre, selectedMarcaObj, selectedEnvaseObj, contenidoEnvase, unidadEnvase, unidadBase]);

  // ==========================================================================
  // Financial KPIs (Margen, Markup, Food Cost)
  // ==========================================================================
  const kpis = useMemo(() => {
    return calculateFinancialKPIs({
      costoNeto: costoUnitarioNeto,
      costoBruto: costoUnitarioBruto,
      precioVentaNeto,
      precioVentaBruto,
    });
  }, [costoUnitarioNeto, costoUnitarioBruto, precioVentaNeto, precioVentaBruto]);

  // ==========================================================================
  // Live Drafting (localStorage sync)
  // ==========================================================================
  useEffect(() => {
    if (!open || !isInitialized.current || editingProduct) return;

    setDraftStatus("saving");
    if (saveTimeoutRef.current) clearTimeout(saveTimeoutRef.current);

    saveTimeoutRef.current = setTimeout(() => {
      try {
        if (typeof window !== "undefined") {
          const draftPayload: DraftProductData = {
            nombre,
            marcaId,
            sku,
            codigoBarra,
            categoriaId,
            familia,
            tipoProducto,
            imagenUrl,
            selectedAreaIds,
            unidadBase,
            tipoEnvaseId,
            contenidoEnvase,
            unidadEnvase,
            presentaciones,
            ivaPorcentaje,
            costoUnitarioNeto,
            costoUnitarioBruto,
            precioVentaNeto,
            precioVentaBruto,
            currentStep,
            updatedAt: Date.now(),
          };
          window.localStorage.setItem(DRAFT_STORAGE_KEY, JSON.stringify(draftPayload));
          setDraftStatus("saved");
        }
      } catch {
        setDraftStatus("idle");
      }
    }, 350);

    return () => {
      if (saveTimeoutRef.current) clearTimeout(saveTimeoutRef.current);
    };
  }, [
    open,
    editingProduct,
    nombre,
    marcaId,
    sku,
    codigoBarra,
    categoriaId,
    familia,
    tipoProducto,
    imagenUrl,
    selectedAreaIds,
    unidadBase,
    tipoEnvaseId,
    contenidoEnvase,
    unidadEnvase,
    presentaciones,
    ivaPorcentaje,
    costoUnitarioNeto,
    costoUnitarioBruto,
    precioVentaNeto,
    precioVentaBruto,
    currentStep,
  ]);

  // Discard draft
  const handleDiscardDraft = useCallback(() => {
    if (typeof window !== "undefined") {
      window.localStorage.removeItem(DRAFT_STORAGE_KEY);
    }
    setNombre("");
    setMarcaId("");
    setSku("");
    setCodigoBarra("");
    setFamilia("");
    setTipoEnvaseId("");
    setContenidoEnvase("");
    setCostoUnitarioNeto(0);
    setCostoUnitarioBruto(0);
    setPrecioVentaNeto(0);
    setPrecioVentaBruto(0);
    setCurrentStep(1);
    setDraftStatus("idle");
    toast.info("Borrador descartado");
  }, []);

  // Costo & Precio Calculations Handlers
  const handleCostoNetoChange = (valStr: string) => {
    const val = Number(valStr) || 0;
    setCostoUnitarioNeto(val);
    setCostoUnitarioBruto(Math.round(val * (1 + ivaPorcentaje / 100)));
  };

  const handleCostoBrutoChange = (valStr: string) => {
    const val = Number(valStr) || 0;
    setCostoUnitarioBruto(val);
    setCostoUnitarioNeto(Math.round(val / (1 + ivaPorcentaje / 100)));
  };

  const handlePrecioVentaNetoChange = (valStr: string) => {
    const val = Number(valStr) || 0;
    setPrecioVentaNeto(val);
    setPrecioVentaBruto(Math.round(val * (1 + ivaPorcentaje / 100)));
  };

  const handlePrecioVentaBrutoChange = (valStr: string) => {
    const val = Number(valStr) || 0;
    setPrecioVentaBruto(val);
    setPrecioVentaNeto(Math.round(val / (1 + ivaPorcentaje / 100)));
  };

  const handleIvaChange = (valStr: string) => {
    const iva = Number(valStr) || 0;
    setIvaPorcentaje(iva);
    setCostoUnitarioBruto(Math.round(costoUnitarioNeto * (1 + iva / 100)));
    setPrecioVentaBruto(Math.round(precioVentaNeto * (1 + iva / 100)));
  };

  // Quick brand creation
  const handleCreateBrand = async () => {
    const trimmed = newMarcaText.trim();
    if (!trimmed) return;
    try {
      if (onCreateBrand) {
        const created = await onCreateBrand(trimmed);
        if (created) {
          setLocalMarcas((prev) => [...prev, created]);
          setMarcaId(created.id);
        }
      } else {
        const tempMarca: Marca = { id: `brand-${Date.now()}`, nombre: trimmed, logo_url: null };
        setLocalMarcas((prev) => [...prev, tempMarca]);
        setMarcaId(tempMarca.id);
      }
      setNewMarcaText("");
      setShowNewMarcaInput(false);
      toast.success(`Marca "${trimmed}" agregada`);
    } catch {
      toast.error("Error al crear la marca");
    }
  };

  // Quick packaging creation
  const handleCreateEnvase = async () => {
    const trimmed = newEnvaseText.trim();
    if (!trimmed) return;
    try {
      if (onCreateTipoEnvase) {
        const created = await onCreateTipoEnvase(trimmed, "package");
        if (created) {
          setLocalTiposEnvase((prev) => [...prev, created]);
          setTipoEnvaseId(created.id);
        }
      } else {
        const tempEnvase: TipoEnvase = {
          id: `env-${Date.now()}`,
          nombre: trimmed,
          icono: "package",
        };
        setLocalTiposEnvase((prev) => [...prev, tempEnvase]);
        setTipoEnvaseId(tempEnvase.id);
      }
      setNewEnvaseText("");
      setShowNewEnvaseInput(false);
      toast.success(`Envase "${trimmed}" agregado`);
    } catch {
      toast.error("Error al crear envase");
    }
  };

  // Add / Remove Presentations
  const handleAddPresentation = () => {
    const count = presentaciones.length + 1;
    const defaultEquiv = 6;
    setPresentaciones((prev) => [
      ...prev,
      {
        nombre: `Caja x${count * 6}`,
        equivalencia: defaultEquiv * count,
        cantidad: defaultEquiv * count,
        ultimo_costo: costoUnitarioNeto * defaultEquiv * count,
        costo_bruto: costoUnitarioBruto * defaultEquiv * count,
      },
    ]);
  };

  const handleRemovePresentation = (index: number) => {
    setPresentaciones((prev) => prev.filter((_, i) => i !== index));
  };

  const handleUpdatePresentation = (index: number, patch: Partial<PresentacionCompra>) => {
    setPresentaciones((prev) =>
      prev.map((item, i) => (i === index ? { ...item, ...patch } : item))
    );
  };

  // Final submit
  const handleFinalSubmit = async () => {
    if (!nombre.trim()) {
      toast.error("El nombre del producto es obligatorio (Paso 1)");
      setCurrentStep(1);
      return;
    }

    setIsSubmitting(true);
    try {
      const activeBodegasConfig: BodegaConfig[] = Object.entries(bodegasMap)
        .filter(([, cfg]) => cfg.enabled)
        .map(([bId, cfg]) => {
          const bInfo = bodegas.find((b) => b.id === bId);
          return {
            bodega_id: bId,
            bodega_nombre: bInfo?.nombre || "Bodega",
            stock_actual: cfg.stock_actual,
            stock_minimo: cfg.stock_minimo,
            coordenada_letra: cfg.coordenada_letra,
            coordenada_numero: cfg.coordenada_numero,
          };
        });

      const totalStock = activeBodegasConfig.reduce((acc, c) => acc + (c.stock_actual || 0), 0);

      const productPayload: Partial<Producto> = {
        nombre: nombre.trim(),
        nombre_completo: nombreCompletoGenerado || nombre.trim(),
        marca_id: marcaId || null,
        marca: selectedMarcaObj?.nombre || null,
        sku: sku.trim() || null,
        codigo_barra: codigoBarra.trim() || null,
        categoria_id: categoriaId || categorias[0]?.id || "cat-carnes",
        areas_operativas_ids: selectedAreaIds,
        unidad: unidadBase,
        tipo_envase_id: tipoEnvaseId || null,
        contenido_envase: contenidoEnvase ? Number(contenidoEnvase) : null,
        unidad_envase: unidadEnvase || null,
        presentaciones_compra: presentaciones,
        bodegas_config: activeBodegasConfig,
        stock_actual: totalStock,
        costo_unitario: costoUnitarioNeto,
        ultimo_costo: costoUnitarioNeto,
        precio_venta: precioVentaBruto,
        iva_incluido: true,
        iva_porcentaje: ivaPorcentaje,
        imagen_url: imagenUrl.trim() || null,
      };

      await onSave(productPayload);

      // Clean draft upon successful save
      if (typeof window !== "undefined") {
        window.localStorage.removeItem(DRAFT_STORAGE_KEY);
      }
      onOpenChange(false);
    } catch {
      toast.error("Ocurrió un error al guardar el producto");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <ResponsiveDialog
      open={open}
      onClose={() => onOpenChange(false)}
      title={editingProduct ? "Editar Producto" : "Nuevo Producto"}
      description="Completa la ficha técnica multidimensional del producto en 4 sencillos pasos."
      maxWidth="max-w-4xl"
      className="p-0 overflow-hidden"
    >
      <div className="flex flex-col h-full max-h-[85vh]" data-testid="producto-wizard-dialog">
        {/* ================================================================= */}
        {/* CABECERA MULTICANAL Y SELECTOR DE VÍA                            */}
        {/* ================================================================= */}
        <div className="p-4 border-b border-border bg-secondary/30 space-y-3 shrink-0">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            {/* 3 Canales de Carga */}
            <div className="inline-flex p-1 rounded-xl bg-card border border-border shadow-xs gap-1">
              <button
                type="button"
                data-testid="channel-manual"
                onClick={() => setActiveChannel("manual")}
                className={cn(
                  "touch-target inline-flex min-h-[44px] px-3.5 items-center gap-2 rounded-lg text-xs font-bold transition-all cursor-pointer select-none",
                  activeChannel === "manual"
                    ? "bg-primary text-primary-foreground shadow-xs"
                    : "text-muted-foreground hover:text-foreground"
                )}
              >
                <Layers className="h-4 w-4" />
                <span>Wizard Manual</span>
              </button>

              <button
                type="button"
                data-testid="channel-excel"
                onClick={() => {
                  if (onOpenExcelImport) {
                    onOpenExcelImport();
                  } else {
                    setActiveChannel("excel");
                  }
                }}
                className={cn(
                  "touch-target inline-flex min-h-[44px] px-3.5 items-center gap-2 rounded-lg text-xs font-bold transition-all cursor-pointer select-none",
                  activeChannel === "excel"
                    ? "bg-emerald-600 text-white shadow-xs"
                    : "text-emerald-600 dark:text-emerald-400 hover:bg-emerald-500/10"
                )}
              >
                <FileSpreadsheet className="h-4 w-4" />
                <span>Importar Excel (IA)</span>
              </button>

              <button
                type="button"
                data-testid="channel-invoice"
                onClick={() => {
                  if (onOpenFacturaImport) {
                    onOpenFacturaImport();
                  } else {
                    setActiveChannel("invoice");
                  }
                }}
                className={cn(
                  "touch-target inline-flex min-h-[44px] px-3.5 items-center gap-2 rounded-lg text-xs font-bold transition-all cursor-pointer select-none",
                  activeChannel === "invoice"
                    ? "bg-indigo-600 text-white shadow-xs"
                    : "text-indigo-600 dark:text-indigo-400 hover:bg-indigo-500/10"
                )}
              >
                <FileText className="h-4 w-4" />
                <span>Factura (IA)</span>
              </button>
            </div>

            {/* Drafting indicator & Discard button */}
            <div className="flex items-center gap-2 shrink-0">
              {draftStatus === "saving" && (
                <span
                  data-testid="draft-saving-indicator"
                  className="inline-flex items-center gap-1.5 text-[11px] font-semibold text-amber-600 dark:text-amber-400 animate-pulse"
                >
                  <span className="h-2 w-2 rounded-full bg-amber-500" />
                  Guardando borrador...
                </span>
              )}
              {draftStatus === "saved" && (
                <span
                  data-testid="draft-saved-indicator"
                  className="inline-flex items-center gap-1.5 text-[11px] font-semibold text-emerald-600 dark:text-emerald-400"
                >
                  <CheckCircle2 className="h-3.5 w-3.5" />
                  Borrador autoguardado
                </span>
              )}

              {!editingProduct && (
                <button
                  type="button"
                  data-testid="btn-discard-draft"
                  onClick={handleDiscardDraft}
                  title="Descartar borrador y limpiar formulario"
                  className="touch-target inline-flex min-h-[44px] px-2.5 items-center gap-1 text-[11px] font-bold text-muted-foreground hover:text-destructive transition-colors cursor-pointer"
                >
                  <RotateCcw className="h-3.5 w-3.5" />
                  <span className="hidden sm:inline">Descartar</span>
                </button>
              )}
            </div>
          </div>

          {/* Stepper de 4 Pasos (Solo visible en canal manual) */}
          {activeChannel === "manual" && (
            <div
              className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-1"
              data-testid="wizard-stepper"
            >
              {[
                { step: 1, title: "1. Básico & Familia", icon: Package },
                { step: 2, title: "2. Envases & Packs", icon: Boxes },
                { step: 3, title: "3. Bodegas & Stock", icon: Warehouse },
                { step: 4, title: "4. Precios & Costos", icon: DollarSign },
              ].map(({ step, title, icon: Icon }) => {
                const isActive = currentStep === step;
                const isPassed = currentStep > step;
                return (
                  <button
                    key={step}
                    type="button"
                    data-testid={`stepper-step-${step}`}
                    onClick={() => setCurrentStep(step as 1 | 2 | 3 | 4)}
                    className={cn(
                      "touch-target flex min-h-[44px] items-center gap-2 p-2 rounded-xl text-left transition-all border cursor-pointer select-none",
                      isActive
                        ? "bg-card border-primary text-primary shadow-xs ring-1 ring-primary/30"
                        : isPassed
                        ? "bg-secondary/40 border-border text-foreground hover:bg-secondary/70"
                        : "bg-transparent border-transparent text-muted-foreground hover:bg-secondary/30"
                    )}
                  >
                    <span
                      className={cn(
                        "h-6 w-6 rounded-lg flex items-center justify-center text-xs font-black shrink-0",
                        isActive
                          ? "bg-primary text-primary-foreground"
                          : isPassed
                          ? "bg-emerald-500/20 text-emerald-600 dark:text-emerald-400"
                          : "bg-muted text-muted-foreground"
                      )}
                    >
                      {isPassed ? "✓" : step}
                    </span>
                    <div className="flex items-center gap-1.5 min-w-0">
                      <Icon className="h-3 w-3 shrink-0 opacity-70" />
                      <span className="text-[11px] font-bold truncate leading-tight">
                        {title}
                      </span>
                    </div>
                  </button>
                );
              })}
            </div>
          )}
        </div>

        {/* ================================================================= */}
        {/* BANNER GLOBAL DE NOMBRE AUTOGENERADO                            */}
        {/* ================================================================= */}
        {nombre.trim() && (
          <div
            data-testid="banner-nombre-autogenerado"
            className="px-4 py-2.5 bg-primary/10 border-b border-primary/20 flex items-center gap-2 shrink-0 animate-in fade-in"
          >
            <Sparkles className="h-4 w-4 text-primary shrink-0" />
            <div className="flex flex-col sm:flex-row sm:items-center gap-1 min-w-0 flex-1">
              <span className="text-[10px] uppercase font-black tracking-wider text-muted-foreground shrink-0">
                Nombre Autogenerado:
              </span>
              <span
                data-testid="text-nombre-completo-generado"
                className="text-xs sm:text-sm font-black text-primary truncate"
              >
                {nombreCompletoGenerado}
              </span>
            </div>
          </div>
        )}

        {/* ================================================================= */}
        {/* CONTENIDO DEL WIZARD                                            */}
        {/* ================================================================= */}
        <div className="flex-1 overflow-y-auto p-4 sm:p-5 custom-scrollbar">
          {activeChannel === "excel" && (
            <div className="flex flex-col items-center justify-center p-8 text-center space-y-4">
              <div className="h-16 w-16 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-600 dark:text-emerald-400 flex items-center justify-center shadow-lg">
                <FileSpreadsheet className="h-8 w-8" />
              </div>
              <div className="space-y-1 max-w-md">
                <h3 className="text-base font-bold text-foreground">
                  Importación Masiva de Productos (Excel IA)
                </h3>
                <p className="text-xs text-muted-foreground">
                  Arrastra tu planilla Excel o descarga la plantilla oficial. Nuestro
                  asistente IA mapeará columnas de códigos, envases y costos automáticamente.
                </p>
              </div>
              <button
                type="button"
                onClick={() => onOpenExcelImport?.()}
                className="touch-target inline-flex min-h-[44px] px-6 items-center gap-2 rounded-xl bg-emerald-600 text-white font-bold text-xs shadow-lg shadow-emerald-600/20 hover:bg-emerald-700 cursor-pointer"
              >
                <Sparkles className="h-4 w-4" />
                <span>Abrir Modal de Importación Excel</span>
              </button>
            </div>
          )}

          {activeChannel === "invoice" && (
            <div className="flex flex-col items-center justify-center p-8 text-center space-y-4">
              <div className="h-16 w-16 rounded-2xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-600 dark:text-indigo-400 flex items-center justify-center shadow-lg">
                <FileText className="h-8 w-8" />
              </div>
              <div className="space-y-1 max-w-md">
                <h3 className="text-base font-bold text-foreground">
                  Ingreso Inteligente por Factura de Proveedor
                </h3>
                <p className="text-xs text-muted-foreground">
                  Carga un archivo PDF o foto de factura. La IA extraerá los ítems, asociará
                  los precios de compra y creará los nuevos productos al vuelo.
                </p>
              </div>
              <button
                type="button"
                onClick={() => onOpenFacturaImport?.()}
                className="touch-target inline-flex min-h-[44px] px-6 items-center gap-2 rounded-xl bg-indigo-600 text-white font-bold text-xs shadow-lg shadow-indigo-600/20 hover:bg-indigo-700 cursor-pointer"
              >
                <Sparkles className="h-4 w-4" />
                <span>Abrir Escáner de Factura</span>
              </button>
            </div>
          )}

          {activeChannel === "manual" && (
            <>
              {/* ======================================================= */}
              {/* PASO 1: BÁSICO & FAMILIA                                */}
              {/* ======================================================= */}
              {currentStep === 1 && (
                <div className="space-y-5 animate-in fade-in" data-testid="step-1-content">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {/* Nombre Comercial */}
                    <div className="md:col-span-2 space-y-1.5">
                      <label className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1">
                        <span>Nombre Comercial del Producto</span>
                        <span className="text-destructive">*</span>
                      </label>
                      <input
                        type="text"
                        data-testid="input-product-name"
                        value={nombre}
                        onChange={(e) => setNombre(e.target.value)}
                        placeholder="Ej: Lomo Vetado Angus Premium, Cerveza Artesanal IPA, etc."
                        className="touch-target w-full min-h-[44px] rounded-xl border border-border bg-card px-3 text-xs font-bold text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary"
                      />
                    </div>

                    {/* Marca con creación al vuelo */}
                    <div className="space-y-1.5">
                      <div className="flex items-center justify-between">
                        <label className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">
                          Marca
                        </label>
                        <button
                          type="button"
                          data-testid="btn-toggle-new-marca"
                          onClick={() => setShowNewMarcaInput((v) => !v)}
                          className="text-[10px] font-bold text-primary hover:underline cursor-pointer"
                        >
                          {showNewMarcaInput ? "Cancelar" : "+ Nueva Marca"}
                        </button>
                      </div>

                      {showNewMarcaInput ? (
                        <div className="flex gap-2">
                          <input
                            type="text"
                            data-testid="input-new-marca"
                            value={newMarcaText}
                            onChange={(e) => setNewMarcaText(e.target.value)}
                            placeholder="Nombre de la nueva marca"
                            className="touch-target flex-1 min-h-[44px] rounded-xl border border-primary bg-card px-3 text-xs font-bold text-foreground focus:outline-none"
                          />
                          <button
                            type="button"
                            data-testid="btn-save-new-marca"
                            onClick={handleCreateBrand}
                            className="touch-target inline-flex min-h-[44px] px-3 items-center rounded-xl bg-primary text-primary-foreground font-bold text-xs cursor-pointer"
                          >
                            Crear
                          </button>
                        </div>
                      ) : (
                        <select
                          data-testid="select-marca"
                          value={marcaId}
                          onChange={(e) => setMarcaId(e.target.value)}
                          className="touch-target w-full min-h-[44px] rounded-xl border border-border bg-card px-3 text-xs font-semibold text-foreground focus:outline-none focus:border-primary"
                        >
                          <option value="">Sin marca específica</option>
                          {localMarcas.map((m) => (
                            <option key={m.id} value={m.id}>
                              {m.nombre}
                            </option>
                          ))}
                        </select>
                      )}
                    </div>

                    {/* Categoría */}
                    <div className="space-y-1.5">
                      <label className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">
                        Categoría
                      </label>
                      <select
                        data-testid="select-categoria"
                        value={categoriaId}
                        onChange={(e) => setCategoriaId(e.target.value)}
                        className="touch-target w-full min-h-[44px] rounded-xl border border-border bg-card px-3 text-xs font-semibold text-foreground focus:outline-none focus:border-primary"
                      >
                        {categorias.map((c) => (
                          <option key={c.id} value={c.id}>
                            {c.nombre}
                          </option>
                        ))}
                      </select>
                    </div>

                    {/* SKU y Código de Barras */}
                    <div className="space-y-1.5">
                      <label className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">
                        SKU Interno
                      </label>
                      <input
                        type="text"
                        data-testid="input-sku"
                        value={sku}
                        onChange={(e) => setSku(e.target.value)}
                        placeholder="Ej: CAR-LOM-001"
                        className="touch-target w-full min-h-[44px] rounded-xl border border-border bg-card px-3 text-xs font-semibold text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:border-primary"
                      />
                    </div>

                    <div className="space-y-1.5">
                      <label className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">
                        Código de Barras / PLU
                      </label>
                      <input
                        type="text"
                        data-testid="input-barcode"
                        value={codigoBarra}
                        onChange={(e) => setCodigoBarra(e.target.value)}
                        placeholder="Ej: 7801234567890"
                        className="touch-target w-full min-h-[44px] rounded-xl border border-border bg-card px-3 text-xs font-semibold text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:border-primary"
                      />
                    </div>

                    {/* Familia / Subcategoría */}
                    <div className="space-y-1.5">
                      <label className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">
                        Subcategoría / Familia
                      </label>
                      <input
                        type="text"
                        data-testid="input-familia"
                        value={familia}
                        onChange={(e) => setFamilia(e.target.value)}
                        placeholder="Ej: Cortes Premium, Bebidas Gaseosas"
                        className="touch-target w-full min-h-[44px] rounded-xl border border-border bg-card px-3 text-xs font-semibold text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:border-primary"
                      />
                    </div>

                    {/* Tipo de Producto */}
                    <div className="space-y-1.5">
                      <label className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">
                        Tipo de Producto
                      </label>
                      <div className="grid grid-cols-3 gap-1">
                        {TIPOS_PRODUCTO.map((tp) => (
                          <button
                            key={tp.value}
                            type="button"
                            data-testid={`btn-tipo-${tp.value}`}
                            onClick={() => setTipoProducto(tp.value)}
                            className={cn(
                              "touch-target flex min-h-[44px] items-center justify-center p-2 rounded-xl text-[11px] font-bold text-center border transition-all cursor-pointer select-none",
                              tipoProducto === tp.value
                                ? "bg-primary text-primary-foreground border-primary shadow-xs"
                                : "bg-card border-border text-muted-foreground hover:bg-secondary/40"
                            )}
                          >
                            {tp.label.split(" ")[0]}
                          </button>
                        ))}
                      </div>
                    </div>

                    {/* Foto / Imagen URL */}
                    <div className="md:col-span-2 space-y-1.5">
                      <label className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">
                        URL de Imagen / Foto
                      </label>
                      <div className="flex gap-2">
                        <input
                          type="text"
                          data-testid="input-imagen-url"
                          value={imagenUrl}
                          onChange={(e) => setImagenUrl(e.target.value)}
                          placeholder="https://ejemplo.com/foto-producto.jpg"
                          className="touch-target flex-1 min-h-[44px] rounded-xl border border-border bg-card px-3 text-xs font-semibold text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:border-primary"
                        />
                        {imagenUrl && (
                          <div className="h-11 w-11 rounded-xl border border-border overflow-hidden shrink-0">
                            <img
                              src={imagenUrl}
                              alt="Vista previa"
                              className="h-full w-full object-cover"
                              onError={(e) => {
                                (e.target as HTMLElement).style.display = "none";
                              }}
                            />
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Áreas Operativas Asignadas */}
                    <div className="md:col-span-2 space-y-1.5">
                      <label className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">
                        Áreas Operativas Asignadas (Chips)
                      </label>
                      <div className="flex flex-wrap gap-2 pt-1">
                        {areas.map((area) => {
                          const isSelected = selectedAreaIds.includes(area.id);
                          return (
                            <button
                              key={area.id}
                              type="button"
                              data-testid={`chip-area-${area.id}`}
                              onClick={() => {
                                setSelectedAreaIds((prev) =>
                                  isSelected
                                    ? prev.filter((id) => id !== area.id)
                                    : [...prev, area.id]
                                );
                              }}
                              className={cn(
                                "touch-target inline-flex min-h-[44px] px-3.5 items-center gap-1.5 rounded-xl text-xs font-bold border transition-all cursor-pointer select-none",
                                isSelected
                                  ? "bg-primary text-primary-foreground border-primary shadow-xs"
                                  : "bg-card border-border text-muted-foreground hover:bg-secondary/40"
                              )}
                            >
                              <span
                                className="h-2 w-2 rounded-full shrink-0"
                                style={{ backgroundColor: area.color || "#6366F1" }}
                              />
                              <span>{area.nombre}</span>
                            </button>
                          );
                        })}
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* ======================================================= */}
              {/* PASO 2: ENVASES & PACKS                                 */}
              {/* ======================================================= */}
              {currentStep === 2 && (
                <div className="space-y-5 animate-in fade-in" data-testid="step-2-content">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {/* Unidad Base */}
                    <div className="space-y-1.5">
                      <label className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">
                        Unidad Base de Medida
                      </label>
                      <select
                        data-testid="select-unidad-base"
                        value={unidadBase}
                        onChange={(e) => setUnidadBase(e.target.value)}
                        className="touch-target w-full min-h-[44px] rounded-xl border border-border bg-card px-3 text-xs font-bold text-foreground focus:outline-none focus:border-primary"
                      >
                        {UNIDADES_BASE.map((u) => (
                          <option key={u.value} value={u.value}>
                            {u.label}
                          </option>
                        ))}
                      </select>
                      <p className="text-[10px] text-muted-foreground">
                        Es la unidad en la que se calculan las recetas e inventario final.
                      </p>
                    </div>

                    {/* Envase Primario con creación rápida */}
                    <div className="space-y-1.5">
                      <div className="flex items-center justify-between">
                        <label className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">
                          Envase Primario
                        </label>
                        <button
                          type="button"
                          data-testid="btn-toggle-new-envase"
                          onClick={() => setShowNewEnvaseInput((v) => !v)}
                          className="text-[10px] font-bold text-primary hover:underline cursor-pointer"
                        >
                          {showNewEnvaseInput ? "Cancelar" : "+ Nuevo Envase"}
                        </button>
                      </div>

                      {showNewEnvaseInput ? (
                        <div className="flex gap-2">
                          <input
                            type="text"
                            data-testid="input-new-envase"
                            value={newEnvaseText}
                            onChange={(e) => setNewEnvaseText(e.target.value)}
                            placeholder="Ej: Doypack, Sachet"
                            className="touch-target flex-1 min-h-[44px] rounded-xl border border-primary bg-card px-3 text-xs font-bold text-foreground focus:outline-none"
                          />
                          <button
                            type="button"
                            data-testid="btn-save-new-envase"
                            onClick={handleCreateEnvase}
                            className="touch-target inline-flex min-h-[44px] px-3 items-center rounded-xl bg-primary text-primary-foreground font-bold text-xs cursor-pointer"
                          >
                            Crear
                          </button>
                        </div>
                      ) : (
                        <select
                          data-testid="select-tipo-envase"
                          value={tipoEnvaseId}
                          onChange={(e) => setTipoEnvaseId(e.target.value)}
                          className="touch-target w-full min-h-[44px] rounded-xl border border-border bg-card px-3 text-xs font-semibold text-foreground focus:outline-none focus:border-primary"
                        >
                          <option value="">Selecciona envase primario...</option>
                          {localTiposEnvase.map((env) => (
                            <option key={env.id} value={env.id}>
                              {env.nombre}
                            </option>
                          ))}
                        </select>
                      )}
                    </div>

                    {/* Contenido Neto por Envase y Unidad */}
                    <div className="space-y-1.5">
                      <label className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">
                        Contenido Neto por Envase
                      </label>
                      <input
                        type="number"
                        data-testid="input-contenido-envase"
                        min="0"
                        step="any"
                        value={contenidoEnvase}
                        onChange={(e) => setContenidoEnvase(e.target.value)}
                        placeholder="Ej: 750, 1000, 1"
                        className="touch-target w-full min-h-[44px] rounded-xl border border-border bg-card px-3 text-xs font-semibold text-foreground focus:outline-none focus:border-primary"
                      />
                    </div>

                    <div className="space-y-1.5">
                      <label className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">
                        Unidad de Envase
                      </label>
                      <select
                        data-testid="select-unidad-envase"
                        value={unidadEnvase}
                        onChange={(e) => setUnidadEnvase(e.target.value)}
                        className="touch-target w-full min-h-[44px] rounded-xl border border-border bg-card px-3 text-xs font-semibold text-foreground focus:outline-none focus:border-primary"
                      >
                        <option value="g">Gramos (g)</option>
                        <option value="kg">Kilogramos (kg)</option>
                        <option value="mL">Mililitros (mL)</option>
                        <option value="L">Litros (L)</option>
                        <option value="un">Unidades (un)</option>
                      </select>
                    </div>
                  </div>

                  {/* Presentaciones de Compra / Embalajes */}
                  <div className="space-y-3 pt-3 border-t border-border">
                    <div className="flex items-center justify-between">
                      <div>
                        <h4 className="text-xs font-bold uppercase tracking-wider text-foreground">
                          Presentaciones de Compra / Embalajes
                        </h4>
                        <p className="text-[11px] text-muted-foreground">
                          Configura cajas, packs o sacos de compra y su equivalencia en unidades base.
                        </p>
                      </div>
                      <button
                        type="button"
                        data-testid="btn-add-presentacion"
                        onClick={handleAddPresentation}
                        className="touch-target inline-flex min-h-[44px] px-3.5 items-center gap-1.5 rounded-xl bg-primary/10 text-primary border border-primary/20 hover:bg-primary/20 text-xs font-bold cursor-pointer"
                      >
                        <Plus className="h-4 w-4" />
                        <span>+ Presentación</span>
                      </button>
                    </div>

                    {presentaciones.length === 0 ? (
                      <div className="p-4 rounded-xl border border-dashed border-border text-center text-xs text-muted-foreground">
                        No has registrado embalajes de compra. Se comprará por unidad base ({unidadBase}).
                      </div>
                    ) : (
                      <div className="space-y-2.5">
                        {presentaciones.map((pres, idx) => (
                          <div
                            key={idx}
                            data-testid={`item-presentacion-${idx}`}
                            className="p-3 rounded-xl border border-border bg-card flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-xs"
                          >
                            <div className="flex-1 grid grid-cols-1 sm:grid-cols-2 gap-2">
                              <div>
                                <label className="text-[10px] font-bold text-muted-foreground uppercase">
                                  Nombre Embalaje
                                </label>
                                <input
                                  type="text"
                                  data-testid={`input-pres-nombre-${idx}`}
                                  value={pres.nombre}
                                  onChange={(e) =>
                                    handleUpdatePresentation(idx, { nombre: e.target.value })
                                  }
                                  placeholder="Ej: Caja x6 Botellas"
                                  className="w-full h-8 rounded-lg border border-border bg-secondary/30 px-2 text-xs font-semibold text-foreground focus:outline-none"
                                />
                              </div>
                              <div>
                                <label className="text-[10px] font-bold text-muted-foreground uppercase">
                                  Equivalencia ({unidadBase})
                                </label>
                                <input
                                  type="number"
                                  data-testid={`input-pres-equiv-${idx}`}
                                  min="1"
                                  value={pres.equivalencia}
                                  onChange={(e) =>
                                    handleUpdatePresentation(idx, {
                                      equivalencia: Number(e.target.value) || 1,
                                    })
                                  }
                                  className="w-full h-8 rounded-lg border border-border bg-secondary/30 px-2 text-xs font-bold text-foreground focus:outline-none"
                                />
                              </div>
                            </div>

                            <button
                              type="button"
                              data-testid={`btn-remove-pres-${idx}`}
                              onClick={() => handleRemovePresentation(idx)}
                              className="touch-target self-end sm:self-center p-2 rounded-lg text-muted-foreground hover:text-destructive hover:bg-destructive/10 cursor-pointer"
                              title="Eliminar presentación"
                            >
                              <Trash2 className="h-4 w-4" />
                            </button>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* ======================================================= */}
              {/* PASO 3: BODEGAS & STOCK                                 */}
              {/* ======================================================= */}
              {currentStep === 3 && (
                <div className="space-y-4 animate-in fade-in" data-testid="step-3-content">
                  <div>
                    <h4 className="text-xs font-bold uppercase tracking-wider text-foreground">
                      Distribución y Ubicación por Bodega
                    </h4>
                    <p className="text-[11px] text-muted-foreground">
                      Activa las bodegas donde residirá el producto, asigna su stock inicial y
                      coordenadas de estantería.
                    </p>
                  </div>

                  <div className="space-y-3">
                    {bodegas.map((bodega) => {
                      const cfg = bodegasMap[bodega.id] || {
                        enabled: false,
                        stock_actual: 0,
                        stock_minimo: 0,
                        coordenada_letra: "A",
                        coordenada_numero: "1",
                      };

                      return (
                        <div
                          key={bodega.id}
                          data-testid={`bodega-card-${bodega.id}`}
                          className={cn(
                            "p-3.5 rounded-2xl border transition-all space-y-3",
                            cfg.enabled
                              ? "bg-card border-primary/40 shadow-xs"
                              : "bg-secondary/20 border-border/60 opacity-75"
                          )}
                        >
                          <div className="flex items-center justify-between">
                            <label className="flex items-center gap-2.5 cursor-pointer">
                              <input
                                type="checkbox"
                                data-testid={`check-bodega-${bodega.id}`}
                                checked={cfg.enabled}
                                onChange={(e) => {
                                  const isChecked = e.target.checked;
                                  setBodegasMap((prev) => ({
                                    ...prev,
                                    [bodega.id]: { ...cfg, enabled: isChecked },
                                  }));
                                }}
                                className="h-4 w-4 rounded text-primary focus:ring-primary cursor-pointer"
                              />
                              <div className="flex items-center gap-2">
                                <span
                                  className="h-3 w-3 rounded-full shrink-0"
                                  style={{ backgroundColor: bodega.color || "#6366F1" }}
                                />
                                <span className="text-xs font-bold text-foreground">
                                  {bodega.nombre}
                                </span>
                              </div>
                            </label>

                            <span className="text-[10px] font-bold text-muted-foreground uppercase">
                              {cfg.enabled ? "Activa" : "Inactiva"}
                            </span>
                          </div>

                          {cfg.enabled && (
                            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 pt-2 border-t border-border">
                              <div>
                                <label className="text-[10px] font-bold uppercase text-muted-foreground block mb-1">
                                  Stock Inicial ({unidadBase})
                                </label>
                                <input
                                  type="number"
                                  data-testid={`input-stock-actual-${bodega.id}`}
                                  min="0"
                                  step="any"
                                  value={cfg.stock_actual}
                                  onChange={(e) => {
                                    const val = Number(e.target.value) || 0;
                                    setBodegasMap((prev) => ({
                                      ...prev,
                                      [bodega.id]: { ...cfg, stock_actual: val },
                                    }));
                                  }}
                                  className="w-full h-8 rounded-lg border border-border bg-card px-2 text-xs font-bold text-foreground focus:outline-none"
                                />
                              </div>

                              <div>
                                <label className="text-[10px] font-bold uppercase text-muted-foreground block mb-1">
                                  Stock Mínimo Alerta
                                </label>
                                <input
                                  type="number"
                                  data-testid={`input-stock-minimo-${bodega.id}`}
                                  min="0"
                                  step="any"
                                  value={cfg.stock_minimo}
                                  onChange={(e) => {
                                    const val = Number(e.target.value) || 0;
                                    setBodegasMap((prev) => ({
                                      ...prev,
                                      [bodega.id]: { ...cfg, stock_minimo: val },
                                    }));
                                  }}
                                  className="w-full h-8 rounded-lg border border-border bg-card px-2 text-xs font-semibold text-foreground focus:outline-none"
                                />
                              </div>

                              <div>
                                <label className="text-[10px] font-bold uppercase text-muted-foreground block mb-1">
                                  Pasillo / Letra
                                </label>
                                <input
                                  type="text"
                                  data-testid={`input-coord-letra-${bodega.id}`}
                                  maxLength={3}
                                  value={cfg.coordenada_letra}
                                  onChange={(e) => {
                                    const val = e.target.value.toUpperCase();
                                    setBodegasMap((prev) => ({
                                      ...prev,
                                      [bodega.id]: { ...cfg, coordenada_letra: val },
                                    }));
                                  }}
                                  placeholder="Ej: B"
                                  className="w-full h-8 rounded-lg border border-border bg-card px-2 text-xs font-bold text-center text-foreground focus:outline-none"
                                />
                              </div>

                              <div>
                                <label className="text-[10px] font-bold uppercase text-muted-foreground block mb-1">
                                  Estante / Número
                                </label>
                                <input
                                  type="text"
                                  data-testid={`input-coord-numero-${bodega.id}`}
                                  maxLength={3}
                                  value={cfg.coordenada_numero}
                                  onChange={(e) => {
                                    const val = e.target.value;
                                    setBodegasMap((prev) => ({
                                      ...prev,
                                      [bodega.id]: { ...cfg, coordenada_numero: val },
                                    }));
                                  }}
                                  placeholder="Ej: 3"
                                  className="w-full h-8 rounded-lg border border-border bg-card px-2 text-xs font-bold text-center text-foreground focus:outline-none"
                                />
                              </div>
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* ======================================================= */}
              {/* PASO 4: PRECIOS & COSTOS                                */}
              {/* ======================================================= */}
              {currentStep === 4 && (
                <div className="space-y-5 animate-in fade-in" data-testid="step-4-content">
                  {/* Banner de KPIs Reactivos */}
                  <div
                    data-testid="financial-kpi-banner"
                    className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 p-3 rounded-2xl bg-secondary/30 border border-border"
                  >
                    {/* Margen Neto */}
                    <div className="p-2.5 rounded-xl bg-card border border-border flex flex-col shadow-xs">
                      <span className="text-[10px] font-bold text-muted-foreground uppercase flex items-center gap-1">
                        <TrendingUp className="h-3 w-3 text-emerald-500" />
                        Margen Neto
                      </span>
                      <span
                        data-testid="kpi-margen-neto"
                        className={cn(
                          "text-base font-black mt-1",
                          kpis.margenNeto >= 50
                            ? "text-emerald-600 dark:text-emerald-400"
                            : kpis.margenNeto > 0
                            ? "text-amber-600 dark:text-amber-400"
                            : "text-muted-foreground"
                        )}
                      >
                        {kpis.margenNeto}%
                      </span>
                    </div>

                    {/* Margen Bruto */}
                    <div className="p-2.5 rounded-xl bg-card border border-border flex flex-col shadow-xs">
                      <span className="text-[10px] font-bold text-muted-foreground uppercase flex items-center gap-1">
                        <Percent className="h-3 w-3 text-blue-500" />
                        Margen Bruto
                      </span>
                      <span
                        data-testid="kpi-margen-bruto"
                        className={cn(
                          "text-base font-black mt-1",
                          kpis.margenBruto >= 50
                            ? "text-emerald-600 dark:text-emerald-400"
                            : kpis.margenBruto > 0
                            ? "text-blue-600 dark:text-blue-400"
                            : "text-muted-foreground"
                        )}
                      >
                        {kpis.margenBruto}%
                      </span>
                    </div>

                    {/* Markup */}
                    <div className="p-2.5 rounded-xl bg-card border border-border flex flex-col shadow-xs">
                      <span className="text-[10px] font-bold text-muted-foreground uppercase flex items-center gap-1">
                        <Tag className="h-3 w-3 text-purple-500" />
                        Markup %
                      </span>
                      <span
                        data-testid="kpi-markup"
                        className="text-base font-black text-purple-600 dark:text-purple-400 mt-1"
                      >
                        {kpis.markup}%
                      </span>
                    </div>

                    {/* Food Cost */}
                    <div className="p-2.5 rounded-xl bg-card border border-border flex flex-col shadow-xs">
                      <span className="text-[10px] font-bold text-muted-foreground uppercase flex items-center gap-1">
                        <Percent className="h-3 w-3 text-amber-500" />
                        Food Cost
                      </span>
                      <span
                        data-testid="kpi-food-cost"
                        className={cn(
                          "text-base font-black mt-1",
                          kpis.foodCost > 40
                            ? "text-destructive"
                            : kpis.foodCost > 0
                            ? "text-emerald-600 dark:text-emerald-400"
                            : "text-muted-foreground"
                        )}
                      >
                        {kpis.foodCost}%
                      </span>
                    </div>
                  </div>

                  {/* Formulario de Costos & Precios */}
                  <div className="space-y-4">
                    {/* Costos de Adquisición */}
                    <div className="p-4 rounded-2xl border border-border bg-card space-y-3">
                      <div className="flex items-center justify-between">
                        <h4 className="text-xs font-bold uppercase tracking-wider text-foreground">
                          Costo Unitario de Adquisición ({unidadBase})
                        </h4>
                        <div className="flex items-center gap-2">
                          <label className="text-[10px] font-bold uppercase text-muted-foreground">
                            IVA %:
                          </label>
                          <input
                            type="number"
                            data-testid="input-iva-porcentaje"
                            value={ivaPorcentaje}
                            onChange={(e) => handleIvaChange(e.target.value)}
                            className="w-14 h-7 rounded-lg border border-border bg-secondary/30 px-2 text-xs font-bold text-center text-foreground focus:outline-none"
                          />
                        </div>
                      </div>

                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                        <div className="space-y-1">
                          <label className="text-[10px] font-bold uppercase text-muted-foreground">
                            Costo Unitario Neto ($)
                          </label>
                          <input
                            type="number"
                            data-testid="input-costo-neto"
                            min="0"
                            step="any"
                            value={costoUnitarioNeto || ""}
                            onChange={(e) => handleCostoNetoChange(e.target.value)}
                            placeholder="Ej: 10000"
                            className="touch-target w-full min-h-[44px] rounded-xl border border-border bg-card px-3 text-xs font-bold text-foreground focus:outline-none focus:border-primary"
                          />
                        </div>

                        <div className="space-y-1">
                          <label className="text-[10px] font-bold uppercase text-muted-foreground">
                            Costo Unitario Bruto ($ c/IVA)
                          </label>
                          <input
                            type="number"
                            data-testid="input-costo-bruto"
                            min="0"
                            step="any"
                            value={costoUnitarioBruto || ""}
                            onChange={(e) => handleCostoBrutoChange(e.target.value)}
                            placeholder="Ej: 11900"
                            className="touch-target w-full min-h-[44px] rounded-xl border border-border bg-card px-3 text-xs font-bold text-foreground focus:outline-none focus:border-primary"
                          />
                        </div>
                      </div>
                    </div>

                    {/* Precios de Venta al Público */}
                    <div className="p-4 rounded-2xl border border-border bg-card space-y-3">
                      <div>
                        <h4 className="text-xs font-bold uppercase tracking-wider text-foreground">
                          Precio de Venta al Público
                        </h4>
                        <p className="text-[11px] text-muted-foreground">
                          Opcional para insumos que no se comercializan directamente en barra o salón.
                        </p>
                      </div>

                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                        <div className="space-y-1">
                          <label className="text-[10px] font-bold uppercase text-muted-foreground">
                            Precio de Venta Neto ($)
                          </label>
                          <input
                            type="number"
                            data-testid="input-precio-venta-neto"
                            min="0"
                            step="any"
                            value={precioVentaNeto || ""}
                            onChange={(e) => handlePrecioVentaNetoChange(e.target.value)}
                            placeholder="Ej: 20000"
                            className="touch-target w-full min-h-[44px] rounded-xl border border-border bg-card px-3 text-xs font-bold text-foreground focus:outline-none focus:border-primary"
                          />
                        </div>

                        <div className="space-y-1">
                          <label className="text-[10px] font-bold uppercase text-muted-foreground">
                            Precio de Venta Bruto ($ c/IVA)
                          </label>
                          <input
                            type="number"
                            data-testid="input-precio-venta-bruto"
                            min="0"
                            step="any"
                            value={precioVentaBruto || ""}
                            onChange={(e) => handlePrecioVentaBrutoChange(e.target.value)}
                            placeholder="Ej: 23800"
                            className="touch-target w-full min-h-[44px] rounded-xl border border-border bg-card px-3 text-xs font-bold text-foreground focus:outline-none focus:border-primary"
                          />
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </>
          )}
        </div>

        {/* ================================================================= */}
        {/* FOOTER GENERAL DE NAVEGACIÓN Y ENVÍO                             */}
        {/* ================================================================= */}
        <div className="p-4 border-t border-border bg-secondary/20 flex items-center justify-between gap-3 shrink-0">
          <div>
            {currentStep > 1 && activeChannel === "manual" && (
              <button
                type="button"
                data-testid="btn-wizard-prev"
                onClick={() => setCurrentStep((s) => (s - 1) as 1 | 2 | 3 | 4)}
                className="touch-target inline-flex min-h-[44px] px-4 items-center gap-1.5 rounded-xl border border-border bg-card text-xs font-bold text-foreground hover:bg-secondary/50 cursor-pointer select-none"
              >
                <ChevronLeft className="h-4 w-4" />
                <span>Anterior</span>
              </button>
            )}
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              data-testid="btn-wizard-cancel"
              onClick={() => onOpenChange(false)}
              className="touch-target inline-flex min-h-[44px] px-4 items-center justify-center rounded-xl bg-secondary text-xs font-bold text-secondary-foreground hover:bg-secondary/80 cursor-pointer select-none"
            >
              Cancelar
            </button>

            {currentStep < 4 && activeChannel === "manual" ? (
              <button
                type="button"
                data-testid="btn-wizard-next"
                onClick={() => {
                  if (currentStep === 1 && !nombre.trim()) {
                    toast.error("El nombre del producto es obligatorio");
                    return;
                  }
                  setCurrentStep((s) => (s + 1) as 1 | 2 | 3 | 4);
                }}
                className="touch-target inline-flex min-h-[44px] px-5 items-center gap-1.5 rounded-xl bg-primary text-xs font-bold text-primary-foreground hover:bg-primary/90 shadow-md cursor-pointer select-none"
              >
                <span>Siguiente</span>
                <ChevronRight className="h-4 w-4" />
              </button>
            ) : (
              <button
                type="button"
                data-testid="btn-wizard-submit"
                disabled={isSubmitting}
                onClick={handleFinalSubmit}
                className="touch-target inline-flex min-h-[44px] px-6 items-center gap-2 rounded-xl bg-primary text-xs font-black text-primary-foreground hover:bg-primary/90 shadow-lg shadow-primary/25 cursor-pointer disabled:opacity-50 select-none"
              >
                <Save className="h-4 w-4" />
                <span>{isSubmitting ? "Guardando..." : "Guardar Producto"}</span>
              </button>
            )}
          </div>
        </div>
      </div>
    </ResponsiveDialog>
  );
}

export default ProductoWizardDialog;
