import {
  SlidersHorizontal,
  Tags,
  FolderTree,
  ArrowLeftRight,
  Plus,
  Globe,
  Lock,
  Eye,
  EyeOff,
  Check,
  FileSpreadsheet,
  FileText,
} from "lucide-react";
import { useTranslation } from "react-i18next";
import { AreaSelector } from "@/shared/components/layout/AreaSelector";
import { BodegaSelector } from "@/shared/components/layout/BodegaSelector";
import { Can } from "@/shared/auth/Can";
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSub,
  DropdownMenuSubTrigger,
  DropdownMenuSubContent,
  DropdownMenuSeparator,
} from "@/shared/components/ui/dropdown-menu";
import { cn } from "@/shared/lib";

export interface TablePreset {
  id: string;
  name: string;
  description?: string;
  columns?: readonly string[];
  isPublic?: boolean;
}

export const DEFAULT_PUBLIC_PRESETS: readonly TablePreset[] = [
  {
    id: "preset-general",
    name: "Vista General",
    description: "Columnas esenciales de catálogo y stock",
    columns: ["nombre", "categoria", "unidad", "costo_unitario", "precio_venta", "stock_actual"],
    isPublic: true,
  },
  {
    id: "preset-costos",
    name: "Costos y Rentabilidad",
    description: "Análisis financiero, PPP y margen",
    columns: ["nombre", "costo_unitario", "ultimo_costo", "costo_promedio", "precio_venta"],
    isPublic: true,
  },
  {
    id: "preset-inventario",
    name: "Control de Inventario",
    description: "Bodegas, stock actual, mínimo y valorizado",
    columns: ["nombre", "sku", "codigo_barra", "stock_actual", "valor_inventario"],
    isPublic: true,
  },
];

export interface ToolbarGestionProps {
  // Area & Warehouse
  readonly selectedAreaId?: string;
  readonly onSelectArea?: (areaId: string) => void;
  readonly activeWarehouseId?: string;
  readonly onSelectWarehouse?: (warehouseId: string) => void;

  // Table Presets & Config
  readonly publicPresets?: readonly TablePreset[];
  readonly privatePresets?: readonly TablePreset[];
  readonly activePresetId?: string;
  readonly onApplyTablePreset?: (preset: TablePreset) => void;
  readonly onOpenTableConfig: () => void;

  // Categories Dropdown
  readonly showCategories: boolean;
  readonly onToggleShowCategories: () => void;
  readonly onOpenAdminCategorias: () => void;

  // Catalogs
  readonly onOpenCatalogos: () => void;

  // Actions
  readonly onOpenTransfer: () => void;
  readonly onOpenExcelImport?: () => void;
  readonly onOpenFacturaImport?: () => void;

  // Primary Action
  readonly onNewProduct: () => void;

  readonly className?: string;
}

export function ToolbarGestion({
  selectedAreaId = "all",
  onSelectArea,
  activeWarehouseId = "bod-cocina-central",
  onSelectWarehouse,
  publicPresets = DEFAULT_PUBLIC_PRESETS,
  privatePresets = [],
  activePresetId,
  onApplyTablePreset,
  onOpenTableConfig,
  showCategories,
  onToggleShowCategories,
  onOpenAdminCategorias,
  onOpenCatalogos,
  onOpenTransfer,
  onOpenExcelImport,
  onOpenFacturaImport,
  onNewProduct,
  className,
}: ToolbarGestionProps) {
  const { t } = useTranslation("gestion");

  return (
    <div data-testid="toolbar-gestion" className={cn("w-full mb-4", className)}>
      {/* ==================================================================== */}
      {/* DESKTOP TOOLBAR (Grid 12 cols: 4 left / 5 center / 3 right)          */}
      {/* ==================================================================== */}
      <div className="hidden lg:block bg-muted/50 p-2.5 px-6 rounded-2xl border border-input shadow-inner w-full">
        <div className="grid grid-cols-12 gap-4 items-center w-full">
          {/* Left Column: Selectores de Área y Bodega */}
          <div className="col-span-4 flex items-center justify-start gap-3">
            <AreaSelector
              selectedAreaId={selectedAreaId}
              onSelectArea={onSelectArea}
              className="w-auto"
              buttonClassName="h-10 rounded-xl bg-card border-border shadow-sm text-[9px] min-w-[140px]"
            />
            <BodegaSelector
              activeWarehouseId={activeWarehouseId}
              onSelectWarehouse={(wh) => onSelectWarehouse?.(wh)}
            />
          </div>

          {/* Center Column: Tabla, Categorías y Catálogos */}
          <div className="col-span-5 flex items-center justify-center gap-3">
            {/* Dropdown Tabla */}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <button
                  type="button"
                  data-testid="toolbar-table-dropdown-trigger"
                  className="h-10 px-5 gap-2 rounded-xl border border-border bg-card hover:bg-secondary text-muted-foreground hover:text-foreground transition-all font-black text-[9px] uppercase tracking-wider shadow-sm active:scale-95 inline-flex items-center justify-center cursor-pointer select-none"
                >
                  <SlidersHorizontal className="h-3.5 w-3.5 text-primary shrink-0" />
                  <span>Tabla</span>
                </button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="center" className="w-64 z-[100] shadow-xl">
                {/* Submenú: Plantillas Públicas */}
                <DropdownMenuSub>
                  <DropdownMenuSubTrigger
                    data-testid="submenu-public-presets"
                    className="cursor-pointer py-2 px-3 text-xs font-bold gap-2"
                  >
                    <Globe className="h-4 w-4 text-emerald-500 shrink-0" />
                    <span>Plantillas Públicas</span>
                    <span className="ml-auto text-[9px] font-black px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-500 border border-emerald-500/20">
                      {publicPresets.length}
                    </span>
                  </DropdownMenuSubTrigger>
                  <DropdownMenuSubContent className="w-72 max-h-80 overflow-y-auto z-[100]">
                    {publicPresets.map((preset) => {
                      const isSelected = activePresetId === preset.id;
                      return (
                        <DropdownMenuItem
                          key={preset.id}
                          onClick={() => onApplyTablePreset?.(preset)}
                          data-testid={`preset-item-${preset.id}`}
                          className="cursor-pointer flex flex-col items-start gap-0.5 py-2 px-3"
                        >
                          <div className="flex items-center justify-between w-full">
                            <span className="font-bold text-xs text-foreground">
                              {preset.name}
                            </span>
                            {isSelected && (
                              <Check className="h-3.5 w-3.5 text-primary shrink-0 ml-1.5" />
                            )}
                          </div>
                          {preset.description && (
                            <span className="text-[10px] text-muted-foreground line-clamp-1">
                              {preset.description}
                            </span>
                          )}
                        </DropdownMenuItem>
                      );
                    })}
                  </DropdownMenuSubContent>
                </DropdownMenuSub>

                {/* Submenú: Plantillas Privadas */}
                <DropdownMenuSub>
                  <DropdownMenuSubTrigger
                    data-testid="submenu-private-presets"
                    className="cursor-pointer py-2 px-3 text-xs font-bold gap-2"
                  >
                    <Lock className="h-4 w-4 text-amber-500 shrink-0" />
                    <span>Mis Plantillas Privadas</span>
                    <span className="ml-auto text-[9px] font-black px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-500 border border-amber-500/20">
                      {privatePresets.length}
                    </span>
                  </DropdownMenuSubTrigger>
                  <DropdownMenuSubContent className="w-72 max-h-80 overflow-y-auto z-[100]">
                    {privatePresets.length === 0 ? (
                      <div className="px-3 py-3 text-xs text-muted-foreground italic text-center">
                        No tienes plantillas privadas guardadas
                      </div>
                    ) : (
                      privatePresets.map((preset) => {
                        const isSelected = activePresetId === preset.id;
                        return (
                          <DropdownMenuItem
                            key={preset.id}
                            onClick={() => onApplyTablePreset?.(preset)}
                            className="cursor-pointer flex flex-col items-start gap-0.5 py-2 px-3"
                          >
                            <div className="flex items-center justify-between w-full">
                              <span className="font-bold text-xs text-foreground">
                                {preset.name}
                              </span>
                              {isSelected && (
                                <Check className="h-3.5 w-3.5 text-primary shrink-0 ml-1.5" />
                              )}
                            </div>
                            {preset.description && (
                              <span className="text-[10px] text-muted-foreground line-clamp-1">
                                {preset.description}
                              </span>
                            )}
                          </DropdownMenuItem>
                        );
                      })
                    )}
                  </DropdownMenuSubContent>
                </DropdownMenuSub>

                <DropdownMenuSeparator className="my-1" />

                {/* Opción: Personalizar Vista de Tabla */}
                <DropdownMenuItem
                  onClick={onOpenTableConfig}
                  data-testid="btn-open-table-config"
                  className="cursor-pointer py-2 px-3 text-xs font-black text-primary focus:text-primary focus:bg-primary/10 gap-2"
                >
                  <SlidersHorizontal className="h-4 w-4 text-primary shrink-0" />
                  <span>Personalizar Vista de Tabla</span>
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>

            {/* Dropdown Categorías */}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <button
                  type="button"
                  data-testid="toolbar-categories-dropdown-trigger"
                  className={cn(
                    "h-10 px-5 gap-2 rounded-xl transition-all active:scale-95 text-[9px] font-black uppercase tracking-wider shadow-sm inline-flex items-center justify-center cursor-pointer select-none",
                    showCategories
                      ? "bg-primary text-primary-foreground shadow-primary/20"
                      : "border border-border bg-card hover:bg-secondary text-muted-foreground hover:text-foreground"
                  )}
                >
                  <Tags className={cn("h-3.5 w-3.5 shrink-0", !showCategories && "text-primary")} />
                  <span>Categorías</span>
                </button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="center" className="w-56 z-[100]">
                <DropdownMenuItem
                  onClick={onOpenAdminCategorias}
                  data-testid="btn-admin-categories"
                  className="gap-2 cursor-pointer"
                >
                  <Tags className="h-4 w-4 text-primary shrink-0" />
                  <span>Administrar Categorías</span>
                </DropdownMenuItem>
                <DropdownMenuItem
                  onClick={onToggleShowCategories}
                  data-testid="btn-toggle-show-categories"
                  className="gap-2 cursor-pointer"
                >
                  {showCategories ? (
                    <EyeOff className="h-4 w-4 text-muted-foreground shrink-0" />
                  ) : (
                    <Eye className="h-4 w-4 text-muted-foreground shrink-0" />
                  )}
                  <span>{showCategories ? "Ocultar Categorías" : "Mostrar Categorías"}</span>
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>

            {/* Botón Catálogos */}
            <button
              type="button"
              onClick={onOpenCatalogos}
              data-testid="toolbar-btn-catalogos"
              className="h-10 px-5 gap-2 rounded-xl border border-border bg-card hover:bg-secondary text-muted-foreground hover:text-foreground transition-all font-black text-[9px] uppercase tracking-wider shadow-sm active:scale-95 inline-flex items-center justify-center cursor-pointer select-none"
            >
              <FolderTree className="h-3.5 w-3.5 text-primary shrink-0" />
              <span>Catálogos</span>
            </button>
          </div>

          {/* Right Column: Acciones y Botón Primario */}
          <div className="col-span-3 flex items-center justify-end gap-3">
            {/* Dropdown Acciones */}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <button
                  type="button"
                  data-testid="toolbar-actions-dropdown-trigger"
                  className="h-10 px-4 gap-2 rounded-xl border border-border bg-card hover:bg-secondary text-muted-foreground hover:text-foreground transition-all active:scale-95 inline-flex items-center justify-center cursor-pointer select-none"
                >
                  <ArrowLeftRight className="h-4 w-4 text-primary shrink-0" />
                  <span className="text-[9px] font-black uppercase tracking-wider">Acciones</span>
                </button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-52 z-[100]">
                <DropdownMenuItem
                  onClick={onOpenTransfer}
                  data-testid="btn-action-transfer-stock"
                  className="gap-2 cursor-pointer"
                >
                  <ArrowLeftRight className="h-4 w-4 text-primary shrink-0" />
                  <span>Transferir Stock</span>
                </DropdownMenuItem>
                {onOpenExcelImport && (
                  <DropdownMenuItem
                    onClick={onOpenExcelImport}
                    data-testid="btn-action-import-excel"
                    className="gap-2 cursor-pointer"
                  >
                    <FileSpreadsheet className="h-4 w-4 text-emerald-600 dark:text-emerald-400 shrink-0" />
                    <span>{t("toolbar.import_excel", "Importar Excel (IA)")}</span>
                  </DropdownMenuItem>
                )}
                {onOpenFacturaImport && (
                  <DropdownMenuItem
                    onClick={onOpenFacturaImport}
                    data-testid="btn-action-import-factura"
                    className="gap-2 cursor-pointer"
                  >
                    <FileText className="h-4 w-4 text-primary shrink-0" />
                    <span>{t("toolbar.import_factura", "Cargar Factura (IA)")}</span>
                  </DropdownMenuItem>
                )}
              </DropdownMenuContent>
            </DropdownMenu>

            {/* Botón Primario + Producto */}
            <Can perform="catalog.products.create">
              <button
                type="button"
                onClick={onNewProduct}
                data-testid="toolbar-btn-new-product"
                className="h-10 px-6 gap-2 rounded-xl bg-yellow-500 hover:bg-yellow-600 text-black shadow-lg shadow-yellow-500/20 transition-all font-black text-[10px] uppercase tracking-wider active:scale-95 inline-flex items-center justify-center cursor-pointer select-none shrink-0"
              >
                <Plus className="h-4 w-4" />
                <span>+ Producto</span>
              </button>
            </Can>
          </div>
        </div>
      </div>

      {/* ==================================================================== */}
      {/* MOBILE-FIRST TOOLBAR                                                 */}
      {/* ==================================================================== */}
      <div className="block lg:hidden w-full space-y-3">
        {/* Top row: Area & Warehouse Selectors */}
        <div className="grid grid-cols-2 gap-2 w-full bg-muted/50 p-2 rounded-2xl border border-input shadow-inner">
          <AreaSelector
            selectedAreaId={selectedAreaId}
            onSelectArea={onSelectArea}
            className="w-full"
            buttonClassName="w-full min-h-[44px] justify-between text-center"
          />
          <BodegaSelector
            activeWarehouseId={activeWarehouseId}
            onSelectWarehouse={(wh) => onSelectWarehouse?.(wh)}
          />
        </div>

        {/* Second row: Action Buttons */}
        <div className="flex flex-wrap items-center justify-between gap-2 w-full">
          {/* Tabla */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <button
                type="button"
                data-testid="mobile-table-dropdown-trigger"
                className="flex-1 min-w-[70px] min-h-[44px] rounded-xl border border-border bg-card hover:bg-secondary px-2.5 py-2 inline-flex items-center justify-center gap-1.5 font-black uppercase text-[10px] tracking-wider text-muted-foreground hover:text-foreground cursor-pointer select-none"
              >
                <SlidersHorizontal className="h-3.5 w-3.5 text-primary shrink-0" />
                <span>Tabla</span>
              </button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="center" className="w-64 z-[100] shadow-xl">
              <DropdownMenuSub>
                <DropdownMenuSubTrigger className="cursor-pointer py-2 px-3 text-xs font-bold gap-2">
                  <Globe className="h-4 w-4 text-emerald-500 shrink-0" />
                  <span>Plantillas Públicas</span>
                  <span className="ml-auto text-[9px] font-black px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-500 border border-emerald-500/20">
                    {publicPresets.length}
                  </span>
                </DropdownMenuSubTrigger>
                <DropdownMenuSubContent className="w-72 max-h-80 overflow-y-auto z-[100]">
                  {publicPresets.map((preset) => (
                    <DropdownMenuItem
                      key={preset.id}
                      onClick={() => onApplyTablePreset?.(preset)}
                      className="cursor-pointer flex flex-col items-start gap-0.5 py-2 px-3"
                    >
                      <div className="flex items-center justify-between w-full">
                        <span className="font-bold text-xs text-foreground">{preset.name}</span>
                        {activePresetId === preset.id && (
                          <Check className="h-3.5 w-3.5 text-primary shrink-0 ml-1.5" />
                        )}
                      </div>
                      {preset.description && (
                        <span className="text-[10px] text-muted-foreground line-clamp-1">
                          {preset.description}
                        </span>
                      )}
                    </DropdownMenuItem>
                  ))}
                </DropdownMenuSubContent>
              </DropdownMenuSub>

              <DropdownMenuSub>
                <DropdownMenuSubTrigger className="cursor-pointer py-2 px-3 text-xs font-bold gap-2">
                  <Lock className="h-4 w-4 text-amber-500 shrink-0" />
                  <span>Mis Plantillas Privadas</span>
                  <span className="ml-auto text-[9px] font-black px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-500 border border-amber-500/20">
                    {privatePresets.length}
                  </span>
                </DropdownMenuSubTrigger>
                <DropdownMenuSubContent className="w-72 max-h-80 overflow-y-auto z-[100]">
                  {privatePresets.length === 0 ? (
                    <div className="px-3 py-3 text-xs text-muted-foreground italic text-center">
                      No tienes plantillas privadas guardadas
                    </div>
                  ) : (
                    privatePresets.map((preset) => (
                      <DropdownMenuItem
                        key={preset.id}
                        onClick={() => onApplyTablePreset?.(preset)}
                        className="cursor-pointer flex flex-col items-start gap-0.5 py-2 px-3"
                      >
                        <span className="font-bold text-xs text-foreground">{preset.name}</span>
                      </DropdownMenuItem>
                    ))
                  )}
                </DropdownMenuSubContent>
              </DropdownMenuSub>

              <DropdownMenuSeparator className="my-1" />

              <DropdownMenuItem
                onClick={onOpenTableConfig}
                className="cursor-pointer py-2 px-3 text-xs font-black text-primary focus:text-primary focus:bg-primary/10 gap-2"
              >
                <SlidersHorizontal className="h-4 w-4 text-primary shrink-0" />
                <span>Personalizar Vista de Tabla</span>
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>

          {/* Categorías */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <button
                type="button"
                data-testid="mobile-categories-dropdown-trigger"
                className={cn(
                  "flex-1 min-w-[70px] min-h-[44px] rounded-xl px-2.5 py-2 inline-flex items-center justify-center gap-1.5 font-black uppercase text-[10px] tracking-wider cursor-pointer select-none",
                  showCategories
                    ? "bg-primary text-primary-foreground shadow-sm shadow-primary/20"
                    : "border border-border bg-card hover:bg-secondary text-muted-foreground hover:text-foreground"
                )}
              >
                <Tags className={cn("h-3.5 w-3.5 shrink-0", !showCategories && "text-primary")} />
                <span>Cats</span>
              </button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="center" className="w-56 z-[100]">
              <DropdownMenuItem onClick={onOpenAdminCategorias} className="gap-2 cursor-pointer">
                <Tags className="h-4 w-4 text-primary shrink-0" />
                <span>Administrar Categorías</span>
              </DropdownMenuItem>
              <DropdownMenuItem onClick={onToggleShowCategories} className="gap-2 cursor-pointer">
                {showCategories ? (
                  <EyeOff className="h-4 w-4 text-muted-foreground shrink-0" />
                ) : (
                  <Eye className="h-4 w-4 text-muted-foreground shrink-0" />
                )}
                <span>{showCategories ? "Ocultar Categorías" : "Mostrar Categorías"}</span>
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>

          {/* Catálogos */}
          <button
            type="button"
            onClick={onOpenCatalogos}
            data-testid="mobile-btn-catalogos"
            className="flex-1 min-w-[70px] min-h-[44px] rounded-xl border border-border bg-card hover:bg-secondary px-2.5 py-2 inline-flex items-center justify-center gap-1.5 font-black uppercase text-[10px] tracking-wider text-muted-foreground hover:text-foreground cursor-pointer select-none"
          >
            <FolderTree className="h-3.5 w-3.5 text-primary shrink-0" />
            <span>Catálogo</span>
          </button>

          {/* Transferir */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <button
                type="button"
                data-testid="mobile-actions-dropdown-trigger"
                className="min-h-[44px] px-3 rounded-xl border border-border bg-card hover:bg-secondary inline-flex items-center justify-center gap-1.5 font-black uppercase text-[10px] tracking-wider text-muted-foreground hover:text-foreground cursor-pointer select-none"
              >
                <ArrowLeftRight className="h-3.5 w-3.5 text-primary shrink-0" />
              </button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-52 z-[100]">
              <DropdownMenuItem onClick={onOpenTransfer} className="gap-2 cursor-pointer">
                <ArrowLeftRight className="h-4 w-4 text-primary shrink-0" />
                <span>Transferir Stock</span>
              </DropdownMenuItem>
              {onOpenExcelImport && (
                <DropdownMenuItem
                  onClick={onOpenExcelImport}
                  data-testid="mobile-btn-action-import-excel"
                  className="gap-2 cursor-pointer"
                >
                  <FileSpreadsheet className="h-4 w-4 text-emerald-600 dark:text-emerald-400 shrink-0" />
                  <span>{t("toolbar.import_excel", "Importar Excel (IA)")}</span>
                </DropdownMenuItem>
              )}
              {onOpenFacturaImport && (
                <DropdownMenuItem
                  onClick={onOpenFacturaImport}
                  data-testid="mobile-btn-action-import-factura"
                  className="gap-2 cursor-pointer"
                >
                  <FileText className="h-4 w-4 text-primary shrink-0" />
                  <span>{t("toolbar.import_factura", "Cargar Factura (IA)")}</span>
                </DropdownMenuItem>
              )}
            </DropdownMenuContent>
          </DropdownMenu>

          {/* + Producto Primary Button */}
          <Can perform="catalog.products.create">
            <button
              type="button"
              onClick={onNewProduct}
              data-testid="mobile-btn-new-product"
              className="flex-1 min-w-[100px] min-h-[44px] rounded-xl bg-yellow-500 hover:bg-yellow-600 text-black px-3 py-2 inline-flex items-center justify-center gap-1.5 font-black uppercase text-[10px] tracking-wider shadow-md shadow-yellow-500/20 active:scale-95 cursor-pointer select-none"
            >
              <Plus className="h-4 w-4" />
              <span>+ Producto</span>
            </button>
          </Can>
        </div>
      </div>
    </div>
  );
}

export default ToolbarGestion;
