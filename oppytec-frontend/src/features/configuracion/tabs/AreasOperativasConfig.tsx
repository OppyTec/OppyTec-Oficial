import { useState } from "react";
import {
  Layers,
  Plus,
  Pencil,
  Trash2,
  Warehouse,
  ShieldCheck,
  Users,
  CheckCircle2,
  Circle,
  Briefcase,
  Building2,
  Building,
  Factory,
  FolderOpen,
  Monitor,
  Package,
  Printer,
  Truck,
  Wrench,
  Hotel,
  Bed,
  BedDouble,
  BedSingle,
  ConciergeBell,
  KeyRound,
  Luggage,
  DoorClosed,
  Beer,
  Wine,
  Martini,
  GlassWater,
  CupSoda,
  Coffee,
  Utensils,
  UtensilsCrossed,
  Disc,
  Disc3,
  Music,
  Speaker,
  PartyPopper,
  Mic,
  Flame,
  CalendarDays,
  Ticket,
  Presentation,
  Crown,
  Trophy,
  Sparkles,
  type LucideIcon,
} from "lucide-react";
import { toast } from "sonner";
import { ResponsiveDialog } from "@/shared/components/ui/ResponsiveDialog";
import { cn } from "@/shared/lib";
import { translateKey, useLanguage } from "@/shared/i18n";

export interface AreaOperativaItem {
  id: string;
  nombre: string;
  icono: string;
  bodegas_ids: string[];
  bodegas_consumo_ids?: string[];
  usuarios_ids: number[];
}

interface AreaIconCategory {
  groupKey: string;
  defaultGroup: string;
  icons: { name: string; icon: LucideIcon; defaultLabel: string }[];
}

export const CATEGORIZED_AREA_ICONS: AreaIconCategory[] = [
  {
    groupKey: "general",
    defaultGroup: "🏢 General y Operaciones",
    icons: [
      { name: "Layers", icon: Layers, defaultLabel: "Áreas / Capas" },
      { name: "Briefcase", icon: Briefcase, defaultLabel: "Administración" },
      { name: "Building2", icon: Building2, defaultLabel: "Edificio Principal" },
      { name: "Building", icon: Building, defaultLabel: "Complejo" },
      { name: "Factory", icon: Factory, defaultLabel: "Producción / Taller" },
      { name: "FolderOpen", icon: FolderOpen, defaultLabel: "Archivos" },
      { name: "Monitor", icon: Monitor, defaultLabel: "Sistemas" },
      { name: "Package", icon: Package, defaultLabel: "Bodega / Envíos" },
      { name: "Printer", icon: Printer, defaultLabel: "Caja / Punto de Venta" },
      { name: "Truck", icon: Truck, defaultLabel: "Logística" },
      { name: "Wrench", icon: Wrench, defaultLabel: "Mantenimiento" },
    ],
  },
  {
    groupKey: "hoteleria",
    defaultGroup: "🏨 Hotelería y Alojamiento",
    icons: [
      { name: "Hotel", icon: Hotel, defaultLabel: "Hotel / Recepción" },
      { name: "Bed", icon: Bed, defaultLabel: "Habitación" },
      { name: "BedDouble", icon: BedDouble, defaultLabel: "Suite / Hab. Doble" },
      { name: "BedSingle", icon: BedSingle, defaultLabel: "Hab. Individual" },
      { name: "ConciergeBell", icon: ConciergeBell, defaultLabel: "Recepción / Botones" },
      { name: "KeyRound", icon: KeyRound, defaultLabel: "Llaves / Acceso" },
      { name: "Luggage", icon: Luggage, defaultLabel: "Equipaje" },
      { name: "DoorClosed", icon: DoorClosed, defaultLabel: "Sector Habitaciones" },
    ],
  },
  {
    groupKey: "pubs",
    defaultGroup: "🍻 Pubs, Bares y Cafés",
    icons: [
      { name: "Beer", icon: Beer, defaultLabel: "Pub / Cervecería" },
      { name: "Wine", icon: Wine, defaultLabel: "Barra / Vinos" },
      { name: "Martini", icon: Martini, defaultLabel: "Coctelería / Lounge" },
      { name: "GlassWater", icon: GlassWater, defaultLabel: "Barra de Bebidas" },
      { name: "CupSoda", icon: CupSoda, defaultLabel: "Fuente de Soda" },
      { name: "Coffee", icon: Coffee, defaultLabel: "Cafetería" },
      { name: "Utensils", icon: Utensils, defaultLabel: "Restaurante" },
      { name: "UtensilsCrossed", icon: UtensilsCrossed, defaultLabel: "Cocina Central" },
    ],
  },
  {
    groupKey: "discos",
    defaultGroup: "🪩 Discos, Clubes y Noche",
    icons: [
      { name: "Disc", icon: Disc, defaultLabel: "Disco / Cabina DJ" },
      { name: "Disc3", icon: Disc3, defaultLabel: "Pista de Baile" },
      { name: "Music", icon: Music, defaultLabel: "Música / Iluminación" },
      { name: "Speaker", icon: Speaker, defaultLabel: "Sonido" },
      { name: "PartyPopper", icon: PartyPopper, defaultLabel: "Club / Fiesta" },
      { name: "Mic", icon: Mic, defaultLabel: "Escenario / Shows" },
      { name: "Flame", icon: Flame, defaultLabel: "Sector VIP" },
    ],
  },
  {
    groupKey: "eventos",
    defaultGroup: "🎟️ Centros de Eventos y Gala",
    icons: [
      { name: "CalendarDays", icon: CalendarDays, defaultLabel: "Agenda de Eventos" },
      { name: "Ticket", icon: Ticket, defaultLabel: "Boletería" },
      { name: "Presentation", icon: Presentation, defaultLabel: "Auditorio" },
      { name: "Crown", icon: Crown, defaultLabel: "Salón Imperial" },
      { name: "Trophy", icon: Trophy, defaultLabel: "Salón de Gala" },
      { name: "Sparkles", icon: Sparkles, defaultLabel: "Salón Principal" },
    ],
  },
];

const ALL_AREA_ICONS = CATEGORIZED_AREA_ICONS.flatMap((g) => g.icons);

const AVAILABLE_BODEGAS = [
  { id: "bod-cocina-central", nombre: "Cocina Central", color: "#10B981" },
  { id: "bod-barra-principal", nombre: "Barra Principal", color: "#3B82F6" },
  { id: "bod-camara-fria", nombre: "Cámara de Frío", color: "#06B6D4" },
  { id: "bod-almacen-seco", nombre: "Almacén Insumos Secos", color: "#EAB308" },
];

const AVAILABLE_USERS = [
  { id: 1, username: "admin", email: "admin@oppytec.cl" },
  { id: 2, username: "chef_ejecutivo", email: "chef@oppytec.cl" },
  { id: 3, username: "bartender_jefe", email: "bar@oppytec.cl" },
  { id: 4, username: "sommelier", email: "cava@oppytec.cl" },
];

const INITIAL_AREAS: AreaOperativaItem[] = [
  {
    id: "area-1",
    nombre: "Salón Principal & Terraza",
    icono: "Utensils",
    bodegas_ids: ["bod-cocina-central", "bod-barra-principal"],
    bodegas_consumo_ids: ["bod-cocina-central"],
    usuarios_ids: [1, 2],
  },
  {
    id: "area-2",
    nombre: "Barra Cocktails & Lounge",
    icono: "Martini",
    bodegas_ids: ["bod-barra-principal", "bod-camara-fria"],
    bodegas_consumo_ids: ["bod-barra-principal"],
    usuarios_ids: [1, 3],
  },
  {
    id: "area-3",
    nombre: "Cava & Eventos VIP",
    icono: "Wine",
    bodegas_ids: ["bod-camara-fria", "bod-almacen-seco"],
    bodegas_consumo_ids: ["bod-camara-fria"],
    usuarios_ids: [1, 4],
  },
];

export function AreasOperativasConfig() {
  useLanguage();
  const [areas, setAreas] = useState<AreaOperativaItem[]>(INITIAL_AREAS);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingArea, setEditingArea] = useState<AreaOperativaItem | null>(null);
  const [deleteAreaId, setDeleteAreaId] = useState<string | null>(null);

  const [nombre, setNombre] = useState("");
  const [icono, setIcono] = useState("Layers");
  const [selectedBodegasIds, setSelectedBodegasIds] = useState<string[]>([]);
  const [bodegasConsumoIds, setBodegasConsumoIds] = useState<string[]>([]);
  const [selectedUsuariosIds, setSelectedUsuariosIds] = useState<number[]>([]);
  const [saving, setSaving] = useState(false);

  const openNew = () => {
    setEditingArea(null);
    setNombre("");
    setIcono("Layers");
    setSelectedBodegasIds(["bod-cocina-central"]);
    setBodegasConsumoIds(["bod-cocina-central"]);
    setSelectedUsuariosIds([1]);
    setDialogOpen(true);
  };

  const openEdit = (area: AreaOperativaItem) => {
    setEditingArea(area);
    setNombre(area.nombre);
    setIcono(area.icono || "Layers");
    setSelectedBodegasIds(area.bodegas_ids);
    setBodegasConsumoIds(area.bodegas_consumo_ids || [area.bodegas_ids[0] || ""]);
    setSelectedUsuariosIds(area.usuarios_ids);
    setDialogOpen(true);
  };

  const toggleBodega = (id: string) => {
    setSelectedBodegasIds((prev) => {
      const exists = prev.includes(id);
      const next = exists ? prev.filter((x) => x !== id) : [...prev, id];
      setBodegasConsumoIds((curr) => {
        const filtered = curr.filter((cid) => next.includes(cid));
        if (!exists && filtered.length === 0) return [id];
        return filtered;
      });
      return next;
    });
  };

  const toggleConsumoBodega = (id: string) => {
    setBodegasConsumoIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    );
  };

  const toggleUsuario = (id: number) => {
    setSelectedUsuariosIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    );
  };

  const handleSave = () => {
    if (!nombre.trim()) {
      toast.error(translateKey("configuracion", "areas.toast_nombre_requerido"));
      return;
    }
    if (selectedBodegasIds.length > 0 && bodegasConsumoIds.length === 0) {
      toast.error(translateKey("configuracion", "areas.toast_consumo_requerido"));
      return;
    }
    setSaving(true);
    setTimeout(() => {
      if (editingArea) {
        setAreas((prev) =>
          prev.map((a) =>
            a.id === editingArea.id
              ? {
                  ...a,
                  nombre: nombre.trim(),
                  icono,
                  bodegas_ids: selectedBodegasIds,
                  bodegas_consumo_ids: bodegasConsumoIds,
                  usuarios_ids: selectedUsuariosIds,
                }
              : a
          )
        );
        toast.success(translateKey("configuracion", "areas.toast_actualizada"));
      } else {
        const newArea: AreaOperativaItem = {
          id: `area-${Date.now()}`,
          nombre: nombre.trim(),
          icono,
          bodegas_ids: selectedBodegasIds,
          bodegas_consumo_ids: bodegasConsumoIds,
          usuarios_ids: selectedUsuariosIds,
        };
        setAreas((prev) => [...prev, newArea]);
        toast.success(translateKey("configuracion", "areas.toast_creada"));
      }
      setSaving(false);
      setDialogOpen(false);
    }, 200);
  };

  const handleDelete = (id: string) => {
    setAreas((prev) => prev.filter((a) => a.id !== id));
    toast.success(translateKey("configuracion", "areas.toast_eliminada"));
    setDeleteAreaId(null);
  };

  return (
    <div className="space-y-4" data-testid="areas-operativas-section">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="space-y-0.5">
          <h3 className="text-sm font-black uppercase tracking-tight">
            {translateKey("configuracion", "areas.header_title")}
          </h3>
          <p className="text-[10px] text-muted-foreground font-medium uppercase tracking-widest">
            {translateKey("configuracion", "areas.header_subtitle")}
          </p>
        </div>
        <button
          type="button"
          onClick={openNew}
          className="rounded-xl gap-2 font-black text-[10px] uppercase shadow-lg shadow-primary/20 bg-primary hover:bg-primary/90 text-primary-foreground px-3.5 py-2 inline-flex items-center cursor-pointer min-h-[44px]"
        >
          <Plus className="h-4 w-4" /> {translateKey("configuracion", "areas.nueva_area")}
        </button>
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        {areas.map((area) => {
          const IconDef = ALL_AREA_ICONS.find((i) => i.name === area.icono);
          const IconComp = IconDef?.icon || Layers;
          const matchedBodegas = AVAILABLE_BODEGAS.filter((b) =>
            area.bodegas_consumo_ids?.includes(b.id)
          );

          return (
            <div
              key={area.id}
              className="flex flex-col gap-3 p-4 rounded-2xl border border-border bg-card/50 hover:bg-secondary/20 transition-all group"
            >
              <div className="flex items-start justify-between gap-2">
                <div className="flex items-center gap-3 min-w-0">
                  <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary">
                    <IconComp className="h-4.5 w-4.5" />
                  </div>
                  <div className="min-w-0">
                    <p className="font-black text-sm truncate">{area.nombre}</p>
                    <p className="text-[10px] text-muted-foreground font-bold uppercase tracking-wider">
                      {area.bodegas_ids.length === 1
                        ? translateKey("configuracion", "areas.stats_bodegas_one")
                        : translateKey("configuracion", "areas.stats_bodegas_other", {
                            count: area.bodegas_ids.length,
                          })}{" "}
                      ·{" "}
                      {area.usuarios_ids.length === 1
                        ? translateKey("configuracion", "areas.stats_usuarios_one")
                        : translateKey("configuracion", "areas.stats_usuarios_other", {
                            count: area.usuarios_ids.length,
                          })}
                    </p>
                  </div>
                </div>
                <div className="flex gap-1 opacity-90 sm:opacity-0 group-hover:opacity-100 transition-opacity shrink-0">
                  <button
                    type="button"
                    onClick={() => openEdit(area)}
                    aria-label={translateKey("configuracion", "areas.editar_aria", {
                      nombre: area.nombre,
                    })}
                    className="h-8 w-8 rounded-lg hover:bg-secondary flex items-center justify-center text-muted-foreground hover:text-foreground cursor-pointer transition-colors"
                  >
                    <Pencil className="h-3.5 w-3.5" />
                  </button>
                  <button
                    type="button"
                    onClick={() => setDeleteAreaId(area.id)}
                    aria-label={translateKey("configuracion", "areas.eliminar_aria", {
                      nombre: area.nombre,
                    })}
                    className="h-8 w-8 rounded-lg hover:bg-destructive/10 text-destructive flex items-center justify-center cursor-pointer transition-colors"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </div>
              </div>

              {/* Bodega de Consumo Badges */}
              {matchedBodegas.length > 0 && (
                <div className="flex flex-wrap gap-2 pt-1 border-t border-border/50">
                  {matchedBodegas.map((cb) => (
                    <div
                      key={cb.id}
                      className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[10px] font-black uppercase tracking-wider"
                      style={{
                        backgroundColor: `${cb.color}15`,
                        color: cb.color,
                        border: `1px solid ${cb.color}30`,
                      }}
                    >
                      <ShieldCheck className="h-3.5 w-3.5 shrink-0" />
                      <span>
                        {translateKey("configuracion", "areas.badge_consumo", {
                          nombre: cb.nombre,
                        })}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Modal Dialog: Crear / Editar Área Operativa */}
      <ResponsiveDialog
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
        title={
          editingArea
            ? translateKey("configuracion", "areas.dialog_edit_title")
            : translateKey("configuracion", "areas.dialog_new_title")
        }
        description={translateKey("configuracion", "areas.dialog_description")}
      >
        <div className="space-y-5 max-h-[70vh] overflow-y-auto pr-1">
          {/* Nombre */}
          <div className="space-y-1.5">
            <label className="text-[10px] font-black uppercase tracking-widest text-muted-foreground block">
              {translateKey("configuracion", "areas.nombre_label")}
            </label>
            <input
              type="text"
              value={nombre}
              onChange={(e) => setNombre(e.target.value)}
              placeholder={translateKey("configuracion", "areas.nombre_placeholder")}
              className="w-full h-11 rounded-xl border border-border px-3 font-bold text-sm bg-background outline-none focus:border-primary transition-colors"
            />
          </div>

          {/* Ícono por Rubro */}
          <div className="space-y-1.5">
            <label className="text-[10px] font-black uppercase tracking-widest text-muted-foreground block">
              {translateKey("configuracion", "areas.icono_rubro_label")}
            </label>
            <div className="border border-border rounded-xl p-3 bg-secondary/15 max-h-48 overflow-y-auto space-y-3">
              {CATEGORIZED_AREA_ICONS.map((group) => {
                const groupTitle =
                  translateKey("configuracion", `areas.icon_groups.${group.groupKey}`) ||
                  group.defaultGroup;
                return (
                  <div key={group.groupKey} className="space-y-1.5">
                    <p className="text-[9px] font-black uppercase tracking-wider text-muted-foreground/70 border-b border-border/50 pb-0.5">
                      {groupTitle}
                    </p>
                    <div className="grid grid-cols-6 sm:grid-cols-8 gap-1.5">
                      {group.icons.map((item) => {
                        const isSelected = icono === item.name;
                        const IconComp = item.icon;
                        const itemLabel =
                          translateKey("configuracion", `areas.icon_labels.${item.name}`) ||
                          item.defaultLabel;
                        return (
                          <button
                            key={item.name}
                            type="button"
                            onClick={() => setIcono(item.name)}
                            title={itemLabel}
                            className={cn(
                              "h-9 w-full flex items-center justify-center rounded-xl border transition-all cursor-pointer",
                              isSelected
                                ? "bg-primary/15 border-primary text-primary shadow-sm font-bold scale-105"
                                : "border-transparent text-muted-foreground hover:bg-secondary hover:text-foreground"
                            )}
                          >
                            <IconComp className="h-4 w-4" />
                          </button>
                        );
                      })}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Bodegas Asociadas */}
          <div className="space-y-2">
            <label className="text-[10px] font-black uppercase tracking-widest text-muted-foreground flex items-center gap-2">
              <Warehouse className="h-3.5 w-3.5" />{" "}
              {translateKey("configuracion", "areas.bodegas_asociadas_label")}
            </label>
            <div className="grid grid-cols-2 gap-2">
              {AVAILABLE_BODEGAS.map((b) => {
                const active = selectedBodegasIds.includes(b.id);
                return (
                  <button
                    key={b.id}
                    type="button"
                    onClick={() => toggleBodega(b.id)}
                    className={cn(
                      "flex items-center gap-2 rounded-xl border px-3 py-2 text-[10px] font-bold uppercase tracking-wide transition-all text-left cursor-pointer",
                      active
                        ? "bg-primary/10 border-primary text-primary"
                        : "hover:bg-secondary border-border text-muted-foreground"
                    )}
                  >
                    {active ? (
                      <CheckCircle2 className="h-3.5 w-3.5 shrink-0" />
                    ) : (
                      <Circle className="h-3.5 w-3.5 shrink-0" />
                    )}
                    <span className="truncate">{b.nombre}</span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Bodegas de Consumo */}
          {selectedBodegasIds.length > 0 && (
            <div className="space-y-2">
              <label className="text-[10px] font-black uppercase tracking-widest text-muted-foreground flex items-center gap-2">
                <ShieldCheck className="h-3.5 w-3.5 text-amber-500" />{" "}
                {translateKey("configuracion", "areas.bodega_consumo_label")}
              </label>
              <div className="grid grid-cols-2 gap-2">
                {AVAILABLE_BODEGAS.filter((b) => selectedBodegasIds.includes(b.id)).map((b) => {
                  const active = bodegasConsumoIds.includes(b.id);
                  return (
                    <button
                      key={b.id}
                      type="button"
                      onClick={() => toggleConsumoBodega(b.id)}
                      className={cn(
                        "flex items-center gap-2 rounded-xl border px-3 py-2 text-[10px] font-bold uppercase tracking-wide transition-all text-left cursor-pointer",
                        active
                          ? "bg-amber-500/10 border-amber-500 text-amber-600 dark:text-amber-400"
                          : "hover:bg-secondary border-border text-muted-foreground"
                      )}
                    >
                      {active ? (
                        <CheckCircle2 className="h-3.5 w-3.5 shrink-0" />
                      ) : (
                        <Circle className="h-3.5 w-3.5 shrink-0" />
                      )}
                      <span className="truncate">{b.nombre}</span>
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {/* Usuarios Asignados */}
          <div className="space-y-2">
            <label className="text-[10px] font-black uppercase tracking-widest text-muted-foreground flex items-center gap-2">
              <Users className="h-3.5 w-3.5" />{" "}
              {translateKey("configuracion", "areas.colaboradores_label")}
            </label>
            <div className="space-y-1.5 max-h-36 overflow-y-auto pr-1">
              {AVAILABLE_USERS.map((u) => {
                const active = selectedUsuariosIds.includes(u.id);
                return (
                  <button
                    key={u.id}
                    type="button"
                    onClick={() => toggleUsuario(u.id)}
                    className={cn(
                      "flex w-full items-center gap-3 rounded-xl border px-3 py-2 text-left transition-all cursor-pointer",
                      active ? "bg-primary/10 border-primary" : "hover:bg-secondary border-border"
                    )}
                  >
                    <div
                      className={cn(
                        "h-6 w-6 shrink-0 rounded-full flex items-center justify-center text-[10px] font-black",
                        active
                          ? "bg-primary text-primary-foreground"
                          : "bg-secondary text-muted-foreground"
                      )}
                    >
                      {(u.username[0] ?? "U").toUpperCase()}
                    </div>
                    <div className="min-w-0">
                      <p className={cn("text-xs font-bold truncate", active ? "text-primary" : "")}>
                        {u.username}
                      </p>
                      <p className="text-[10px] text-muted-foreground truncate">{u.email}</p>
                    </div>
                    <div className="ml-auto shrink-0">
                      {active ? (
                        <CheckCircle2 className="h-4 w-4 text-primary" />
                      ) : (
                        <Circle className="h-4 w-4 text-muted-foreground/30" />
                      )}
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Acciones */}
          <div className="flex justify-end gap-2 pt-3 border-t border-border">
            <button
              type="button"
              onClick={() => setDialogOpen(false)}
              className="px-4 py-2 rounded-xl text-xs font-bold text-muted-foreground hover:bg-secondary cursor-pointer min-h-[44px]"
            >
              {translateKey("configuracion", "areas.boton_cancelar")}
            </button>
            <button
              type="button"
              onClick={handleSave}
              disabled={saving || !nombre.trim()}
              className="px-5 py-2 rounded-xl text-xs font-black uppercase tracking-wider bg-primary hover:bg-primary/90 text-primary-foreground shadow-md cursor-pointer disabled:opacity-50 min-h-[44px]"
            >
              {saving
                ? translateKey("configuracion", "areas.boton_guardando")
                : editingArea
                ? translateKey("configuracion", "areas.boton_actualizar")
                : translateKey("configuracion", "areas.boton_crear")}
            </button>
          </div>
        </div>
      </ResponsiveDialog>

      {/* Modal Confirmación de Eliminación */}
      <ResponsiveDialog
        open={!!deleteAreaId}
        onClose={() => setDeleteAreaId(null)}
        title={translateKey("configuracion", "areas.dialog_delete_title")}
        description={translateKey("configuracion", "areas.dialog_delete_description")}
      >
        <div className="space-y-4 pt-2">
          <p className="text-xs text-muted-foreground">
            {translateKey("configuracion", "areas.dialog_delete_confirm_text")}
          </p>
          <div className="flex justify-end gap-2">
            <button
              type="button"
              onClick={() => setDeleteAreaId(null)}
              className="px-4 py-2 rounded-xl text-xs font-bold hover:bg-secondary text-muted-foreground cursor-pointer min-h-[44px]"
            >
              {translateKey("configuracion", "areas.boton_cancelar")}
            </button>
            <button
              type="button"
              onClick={() => deleteAreaId && handleDelete(deleteAreaId)}
              className="px-4 py-2 rounded-xl text-xs font-black uppercase bg-destructive text-destructive-foreground hover:bg-destructive/90 cursor-pointer min-h-[44px]"
            >
              {translateKey("configuracion", "areas.boton_eliminar_area")}
            </button>
          </div>
        </div>
      </ResponsiveDialog>
    </div>
  );
}

export default AreasOperativasConfig;
