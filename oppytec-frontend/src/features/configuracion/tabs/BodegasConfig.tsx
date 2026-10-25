import { useState, useMemo } from "react";
import {
  Plus,
  Pencil,
  Trash2,
  Box,
  Refrigerator,
  Container,
  Warehouse,
  Truck,
  Store,
  Archive,
  Package,
  Snowflake,
  Thermometer,
  ChefHat,
  Utensils,
  Coffee,
  Wine,
  GlassWater,
  ShoppingBag,
  Tag,
  Layers,
  Droplets,
  Flame,
  Zap,
  Shield,
  MapPin,
  Home,
  Bed,
  Bell,
  Key,
  DoorOpen,
  Bath,
  Wifi,
  Tv,
  Armchair,
  Dumbbell,
  Waves,
  Monitor,
  Printer,
  FileText,
  Search,
  Check,
  Beef,
  Fish,
  Carrot,
  Apple,
  Milk,
  Pizza,
  Egg,
  Wheat,
  Cookie,
  Soup,
  Croissant,
  Cake,
  CupSoda,
  Martini,
  Sparkles,
  Sprout,
  Leaf,
  CookingPot,
  ShoppingCart,
  Star,
  Clock,
  type LucideIcon,
} from "lucide-react";
import { toast } from "sonner";
import { BodegaBadge } from "@/shared/components/layout/BodegaBadge";
import { ResponsiveDialog } from "@/shared/components/ui/ResponsiveDialog";
import { cn } from "@/shared/lib";
import { translateKey, useLanguage } from "@/shared/i18n";

export interface BodegaItem {
  id: string;
  nombre: string;
  color?: string;
  icono?: string;
}

export const PRESET_COLORS_36 = [
  // 1. Rojos y Rosas (6)
  "#EF4444", "#DC2626", "#F43F5E", "#E11D48", "#EC4899", "#DB2777",
  // 2. Naranjas y Amarillos (6)
  "#F97316", "#EA580C", "#D97706", "#F59E0B", "#EAB308", "#CA8A04",
  // 3. Verdes (6)
  "#22C55E", "#16A34A", "#10B981", "#059669", "#84CC16", "#65A30D",
  // 4. Turquesas y Azules (6)
  "#06B6D4", "#0891B2", "#14B8A6", "#0EA5E9", "#3B82F6", "#2563EB",
  // 5. Morados y Violetas (6)
  "#8B5CF6", "#7C3AED", "#A855F7", "#9333EA", "#D946EF", "#C026D3",
  // 6. Grises y Neutros (6)
  "#94A3B8", "#64748B", "#475569", "#71717A", "#52525B", "#334155",
];

interface IconCategoryItem {
  id: string;
  icon: LucideIcon;
  defaultLabel: string;
}

interface CategoryGroup {
  groupKey: string;
  defaultGroup: string;
  icons: IconCategoryItem[];
}

export const CATEGORIZED_BODEGA_ICONS: CategoryGroup[] = [
  {
    groupKey: "general",
    defaultGroup: "🏢 General / UI",
    icons: [
      { id: "Warehouse", icon: Warehouse, defaultLabel: "Bodega" },
      { id: "Box", icon: Box, defaultLabel: "Caja" },
      { id: "Package", icon: Package, defaultLabel: "Paquete" },
      { id: "Archive", icon: Archive, defaultLabel: "Archivo" },
      { id: "Container", icon: Container, defaultLabel: "Contenedor" },
      { id: "Store", icon: Store, defaultLabel: "Tienda" },
      { id: "Layers", icon: Layers, defaultLabel: "Capas" },
      { id: "MapPin", icon: MapPin, defaultLabel: "Ubicación" },
      { id: "Tag", icon: Tag, defaultLabel: "Etiqueta" },
      { id: "Truck", icon: Truck, defaultLabel: "Transporte" },
      { id: "ShoppingBag", icon: ShoppingBag, defaultLabel: "Compras" },
      { id: "ShoppingCart", icon: ShoppingCart, defaultLabel: "Ventas" },
      { id: "Star", icon: Star, defaultLabel: "Favorito" },
      { id: "Clock", icon: Clock, defaultLabel: "Historial" },
    ],
  },
  {
    groupKey: "alimentos",
    defaultGroup: "🍽️ Alimentos",
    icons: [
      { id: "Beef", icon: Beef, defaultLabel: "Carnes" },
      { id: "Fish", icon: Fish, defaultLabel: "Pescados" },
      { id: "Utensils", icon: Utensils, defaultLabel: "Comidas" },
      { id: "Carrot", icon: Carrot, defaultLabel: "Verduras" },
      { id: "Apple", icon: Apple, defaultLabel: "Frutas" },
      { id: "Milk", icon: Milk, defaultLabel: "Lácteos" },
      { id: "Pizza", icon: Pizza, defaultLabel: "Quesos" },
      { id: "Egg", icon: Egg, defaultLabel: "Huevos" },
      { id: "Snowflake", icon: Snowflake, defaultLabel: "Congelados" },
      { id: "Wheat", icon: Wheat, defaultLabel: "Cereales y granos" },
      { id: "Waves", icon: Waves, defaultLabel: "Pastas y fideos" },
      { id: "Cookie", icon: Cookie, defaultLabel: "Harinas y mezclas" },
      { id: "Soup", icon: Soup, defaultLabel: "Salsas y bases" },
      { id: "Croissant", icon: Croissant, defaultLabel: "Panadería" },
      { id: "Cake", icon: Cake, defaultLabel: "Repostería y pastelería" },
    ],
  },
  {
    groupKey: "bebidas",
    defaultGroup: "🥤 Bebidas",
    icons: [
      { id: "CupSoda", icon: CupSoda, defaultLabel: "Bebidas" },
      { id: "GlassWater", icon: GlassWater, defaultLabel: "Aguas y hielo" },
      { id: "Coffee", icon: Coffee, defaultLabel: "Bebidas calientes" },
      { id: "Wine", icon: Wine, defaultLabel: "Alcoholes y licores" },
      { id: "Martini", icon: Martini, defaultLabel: "Insumos de bar" },
    ],
  },
  {
    groupKey: "operacion",
    defaultGroup: "🧼 Operación y Limpieza",
    icons: [
      { id: "Sparkles", icon: Sparkles, defaultLabel: "Limpieza y aseo" },
      { id: "Trash2", icon: Trash2, defaultLabel: "Desechables" },
      { id: "Utensils", icon: Utensils, defaultLabel: "Utensilios y menaje" },
      { id: "ChefHat", icon: ChefHat, defaultLabel: "Insumos de cocina" },
      { id: "Refrigerator", icon: Refrigerator, defaultLabel: "Refrigeración" },
      { id: "Thermometer", icon: Thermometer, defaultLabel: "Temperatura" },
    ],
  },
  {
    groupKey: "especiales",
    defaultGroup: "🌱 Especiales & Preparados",
    icons: [
      { id: "Sprout", icon: Sprout, defaultLabel: "Productos veganos" },
      { id: "Leaf", icon: Leaf, defaultLabel: "Productos vegetarianos" },
      { id: "CookingPot", icon: CookingPot, defaultLabel: "Alimentos preparados" },
    ],
  },
  {
    groupKey: "hospedaje",
    defaultGroup: "🛏️ Hospedaje & Equipos",
    icons: [
      { id: "Home", icon: Home, defaultLabel: "Hogar" },
      { id: "Bed", icon: Bed, defaultLabel: "Cama" },
      { id: "Bath", icon: Bath, defaultLabel: "Baño" },
      { id: "DoorOpen", icon: DoorOpen, defaultLabel: "Puerta" },
      { id: "Bell", icon: Bell, defaultLabel: "Recepción" },
      { id: "Key", icon: Key, defaultLabel: "Llaves" },
      { id: "Armchair", icon: Armchair, defaultLabel: "Sala" },
      { id: "Wifi", icon: Wifi, defaultLabel: "Internet" },
      { id: "Tv", icon: Tv, defaultLabel: "Televisión" },
      { id: "Droplets", icon: Droplets, defaultLabel: "Agua" },
      { id: "Flame", icon: Flame, defaultLabel: "Gas" },
      { id: "Zap", icon: Zap, defaultLabel: "Electricidad" },
      { id: "Dumbbell", icon: Dumbbell, defaultLabel: "Gimnasio" },
      { id: "Shield", icon: Shield, defaultLabel: "Seguridad" },
      { id: "Monitor", icon: Monitor, defaultLabel: "Equipos" },
      { id: "Printer", icon: Printer, defaultLabel: "Impresora" },
      { id: "FileText", icon: FileText, defaultLabel: "Documentos" },
    ],
  },
];

const INITIAL_BODEGAS: BodegaItem[] = [
  { id: "bod-cocina-central", nombre: "Cocina Central", color: "#10B981", icono: "ChefHat" },
  { id: "bod-barra-principal", nombre: "Barra Principal", color: "#3B82F6", icono: "Wine" },
  { id: "bod-camara-fria", nombre: "Cámara de Frío", color: "#06B6D4", icono: "Snowflake" },
  { id: "bod-almacen-seco", nombre: "Almacén Insumos Secos", color: "#EAB308", icono: "Archive" },
];

export function BodegasConfig() {
  useLanguage();
  const [bodegas, setBodegas] = useState<BodegaItem[]>(INITIAL_BODEGAS);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingBodega, setEditingBodega] = useState<BodegaItem | null>(null);
  const [deleteBodegaId, setDeleteBodegaId] = useState<string | null>(null);

  const [nombre, setNombre] = useState("");
  const [color, setColor] = useState("#10B981");
  const [icono, setIcono] = useState("Box");
  const [iconSearch, setIconSearch] = useState("");
  const [saving, setSaving] = useState(false);

  const nameExists = useMemo(() => {
    return bodegas.some(
      (b) =>
        b.nombre.trim().toLowerCase() === nombre.trim().toLowerCase() &&
        b.id !== editingBodega?.id
    );
  }, [bodegas, nombre, editingBodega]);

  const handleOpenNew = () => {
    setEditingBodega(null);
    setNombre("");
    const usedColors = new Set(bodegas.map((b) => b.color));
    const nextColor = PRESET_COLORS_36.find((c) => !usedColors.has(c)) ?? PRESET_COLORS_36[2] ?? "#10B981";
    setColor(nextColor);
    setIcono("Warehouse");
    setIconSearch("");
    setDialogOpen(true);
  };

  const handleOpenEdit = (b: BodegaItem) => {
    setEditingBodega(b);
    setNombre(b.nombre);
    setColor(b.color || "#10B981");
    setIcono(b.icono || "Warehouse");
    setIconSearch("");
    setDialogOpen(true);
  };

  const handleSave = () => {
    if (!nombre.trim()) {
      toast.error(translateKey("configuracion", "bodegas.toast_nombre_obligatorio"));
      return;
    }
    if (nameExists) {
      toast.error(translateKey("configuracion", "bodegas.toast_nombre_duplicado"));
      return;
    }
    setSaving(true);
    setTimeout(() => {
      if (editingBodega) {
        setBodegas((prev) =>
          prev.map((b) =>
            b.id === editingBodega.id ? { ...b, nombre: nombre.trim(), color, icono } : b
          )
        );
        toast.success(translateKey("configuracion", "bodegas.toast_actualizada"));
      } else {
        const newId = `bod-${Date.now()}`;
        setBodegas((prev) => [...prev, { id: newId, nombre: nombre.trim(), color, icono }]);
        toast.success(translateKey("configuracion", "bodegas.toast_creada"));
      }
      setSaving(false);
      setDialogOpen(false);
    }, 200);
  };

  const handleDelete = (id: string) => {
    setBodegas((prev) => prev.filter((b) => b.id !== id));
    toast.success(translateKey("configuracion", "bodegas.toast_eliminada"));
    setDeleteBodegaId(null);
  };

  return (
    <div className="space-y-4" data-testid="bodegas-config-section">
      <div className="flex items-center justify-between">
        <div className="space-y-0.5">
          <h3 className="text-sm font-black uppercase tracking-tight">
            {translateKey("configuracion", "bodegas.header_title")}
          </h3>
          <p className="text-[10px] text-muted-foreground font-medium uppercase tracking-widest">
            {translateKey("configuracion", "bodegas.header_subtitle")}
          </p>
        </div>
        <button
          type="button"
          onClick={handleOpenNew}
          className="rounded-xl gap-2 font-black text-[10px] uppercase shadow-lg shadow-primary/20 bg-primary hover:bg-primary/90 text-primary-foreground px-3.5 py-2 inline-flex items-center cursor-pointer min-h-[44px]"
        >
          <Plus className="h-4 w-4" /> {translateKey("configuracion", "bodegas.nueva_bodega")}
        </button>
      </div>

      {/* Bodegas Grid */}
      <div className="grid gap-3 sm:grid-cols-2">
        {bodegas.map((b) => (
          <div
            key={b.id}
            className="flex items-center justify-between p-4 rounded-2xl border border-border bg-card/50 hover:bg-secondary/30 transition-all group"
          >
            <BodegaBadge nombre={b.nombre} color={b.color} icono={b.icono} />
            <div className="flex gap-1.5 opacity-90 sm:opacity-0 group-hover:opacity-100 transition-opacity">
              <button
                type="button"
                onClick={() => handleOpenEdit(b)}
                aria-label={translateKey("configuracion", "bodegas.editar_aria", { nombre: b.nombre })}
                className="h-9 w-9 rounded-lg hover:bg-secondary flex items-center justify-center text-muted-foreground hover:text-foreground cursor-pointer transition-colors"
              >
                <Pencil className="h-4 w-4" />
              </button>
              <button
                type="button"
                onClick={() => setDeleteBodegaId(b.id)}
                aria-label={translateKey("configuracion", "bodegas.eliminar_aria", { nombre: b.nombre })}
                className="h-9 w-9 rounded-lg hover:bg-destructive/10 text-destructive flex items-center justify-center cursor-pointer transition-colors"
              >
                <Trash2 className="h-4 w-4" />
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* Dialog Modal: Crear / Editar Bodega */}
      <ResponsiveDialog
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
        title={
          editingBodega
            ? translateKey("configuracion", "bodegas.dialog_edit_title")
            : translateKey("configuracion", "bodegas.dialog_new_title")
        }
        description={translateKey("configuracion", "bodegas.dialog_description")}
      >
        <div className="space-y-5 max-h-[70vh] overflow-y-auto pr-1">
          {/* Nombre */}
          <div className="space-y-1.5">
            <label className="text-[10px] font-black uppercase tracking-widest text-muted-foreground block">
              {translateKey("configuracion", "bodegas.nombre_label")}
            </label>
            <input
              type="text"
              value={nombre}
              onChange={(e) => setNombre(e.target.value)}
              placeholder={translateKey("configuracion", "bodegas.nombre_placeholder")}
              className={cn(
                "w-full h-11 rounded-xl border px-3 font-bold text-sm bg-background outline-none transition-colors",
                nameExists ? "border-red-500 focus:ring-1 focus:ring-red-500" : "border-border focus:border-primary"
              )}
            />
            {nameExists && (
              <p className="text-[10px] font-bold text-red-500">
                {translateKey("configuracion", "bodegas.error_nombre_duplicado")}
              </p>
            )}
          </div>

          {/* Vista Previa */}
          <div className="space-y-1.5">
            <label className="text-[10px] font-black uppercase tracking-widest text-muted-foreground block">
              {translateKey("configuracion", "bodegas.preview_label")}
            </label>
            <div className="p-4 border border-border rounded-2xl bg-secondary/20 flex justify-center items-center">
              <BodegaBadge
                nombre={nombre || translateKey("configuracion", "bodegas.preview_default")}
                color={color}
                icono={icono}
                className="text-sm px-4 py-2"
              />
            </div>
          </div>

          {/* Selector Cromático: 36 Colores */}
          <div className="space-y-2">
            <label className="text-[10px] font-black uppercase tracking-widest text-muted-foreground block">
              {translateKey("configuracion", "bodegas.color_label", { count: PRESET_COLORS_36.length })}
            </label>
            <div className="flex flex-wrap gap-2 p-2 border border-border rounded-xl bg-secondary/10">
              {PRESET_COLORS_36.map((c) => {
                const isSelected = color === c;
                return (
                  <button
                    key={c}
                    type="button"
                    onClick={() => setColor(c)}
                    className={cn(
                      "h-7 w-7 rounded-full border-2 transition-transform hover:scale-110 flex items-center justify-center cursor-pointer",
                      isSelected ? "border-foreground scale-110 shadow-md ring-2 ring-primary/40" : "border-transparent"
                    )}
                    style={{ backgroundColor: c }}
                    title={c}
                  >
                    {isSelected && <Check className="h-3.5 w-3.5 text-white stroke-[3.5px] drop-shadow" />}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Buscador de Íconos */}
          <div className="space-y-2">
            <label className="text-[10px] font-black uppercase tracking-widest text-muted-foreground block">
              {translateKey("configuracion", "bodegas.icono_label")}
            </label>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <input
                type="text"
                placeholder={translateKey("configuracion", "bodegas.buscar_icono_placeholder")}
                className="w-full pl-9 h-9 rounded-xl border border-border bg-background text-xs outline-none focus:border-primary"
                value={iconSearch}
                onChange={(e) => setIconSearch(e.target.value)}
              />
            </div>

            <div className="border border-border rounded-xl p-3 bg-secondary/15 max-h-48 overflow-y-auto space-y-3">
              {CATEGORIZED_BODEGA_ICONS.map((group) => {
                const groupLabel =
                  translateKey("configuracion", `bodegas.icon_groups.${group.groupKey}`) ||
                  group.defaultGroup;
                const filtered = group.icons.filter((i) => {
                  const itemLabel =
                    translateKey("configuracion", `bodegas.icon_labels.${i.id}`) ||
                    i.defaultLabel;
                  return (
                    itemLabel.toLowerCase().includes(iconSearch.toLowerCase()) ||
                    i.id.toLowerCase().includes(iconSearch.toLowerCase())
                  );
                });
                if (filtered.length === 0) return null;
                return (
                  <div key={group.groupKey} className="space-y-1.5">
                    <p className="text-[9px] font-black uppercase tracking-wider text-muted-foreground/70 border-b border-border/50 pb-0.5">
                      {groupLabel}
                    </p>
                    <div className="grid grid-cols-6 sm:grid-cols-7 gap-1.5">
                      {filtered.map((item) => {
                        const isSelected = icono === item.id;
                        const IconComponent = item.icon;
                        const label =
                          translateKey("configuracion", `bodegas.icon_labels.${item.id}`) ||
                          item.defaultLabel;
                        return (
                          <button
                            key={item.id}
                            type="button"
                            onClick={() => setIcono(item.id)}
                            title={label}
                            className={cn(
                              "p-2 rounded-lg flex items-center justify-center border transition-all cursor-pointer",
                              isSelected
                                ? "bg-primary/15 border-primary text-primary shadow-sm scale-105"
                                : "border-transparent text-muted-foreground hover:bg-secondary hover:text-foreground"
                            )}
                          >
                            <IconComponent className="h-4 w-4" />
                          </button>
                        );
                      })}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Botones de acción del Modal */}
          <div className="flex justify-end gap-2 pt-3 border-t border-border">
            <button
              type="button"
              onClick={() => setDialogOpen(false)}
              className="px-4 py-2 rounded-xl text-xs font-bold text-muted-foreground hover:bg-secondary cursor-pointer min-h-[44px]"
            >
              {translateKey("configuracion", "bodegas.boton_cancelar")}
            </button>
            <button
              type="button"
              onClick={handleSave}
              disabled={saving || nameExists || !nombre.trim()}
              className="px-5 py-2 rounded-xl text-xs font-black uppercase tracking-wider bg-primary hover:bg-primary/90 text-primary-foreground shadow-md cursor-pointer disabled:opacity-50 min-h-[44px]"
            >
              {saving
                ? translateKey("configuracion", "bodegas.boton_guardando")
                : translateKey("configuracion", "bodegas.boton_confirmar")}
            </button>
          </div>
        </div>
      </ResponsiveDialog>

      {/* Modal de Confirmación de Eliminación */}
      <ResponsiveDialog
        open={!!deleteBodegaId}
        onClose={() => setDeleteBodegaId(null)}
        title={translateKey("configuracion", "bodegas.dialog_delete_title")}
        description={translateKey("configuracion", "bodegas.dialog_delete_description")}
      >
        <div className="space-y-4 pt-2">
          <p className="text-xs text-muted-foreground">
            {translateKey("configuracion", "bodegas.dialog_delete_confirm_text")}
          </p>
          <div className="flex justify-end gap-2">
            <button
              type="button"
              onClick={() => setDeleteBodegaId(null)}
              className="px-4 py-2 rounded-xl text-xs font-bold hover:bg-secondary text-muted-foreground cursor-pointer min-h-[44px]"
            >
              {translateKey("configuracion", "bodegas.boton_cancelar")}
            </button>
            <button
              type="button"
              onClick={() => deleteBodegaId && handleDelete(deleteBodegaId)}
              className="px-4 py-2 rounded-xl text-xs font-black uppercase bg-destructive text-destructive-foreground hover:bg-destructive/90 cursor-pointer min-h-[44px]"
            >
              {translateKey("configuracion", "bodegas.boton_eliminar_bodega")}
            </button>
          </div>
        </div>
      </ResponsiveDialog>
    </div>
  );
}

export default BodegasConfig;
