// oppytec-frontend/src/features/notifications/components/NotificationMatrixView.tsx
import { useState, useMemo, useEffect } from "react";
import {
  ArrowLeft,
  Shield,
  SlidersHorizontal,
  Lock,
  Check,
  Flame,
  Boxes,
  Truck,
  Users,
  RefreshCw,
  Briefcase,
  Info,
  Save,
  CheckCircle2,
} from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/shared/lib/utils";
import { useNotificationMatrix } from "../hooks/useNotificationMatrix";
import type {
  CargoMatrixItem,
  NotificationCatalogItem,
} from "../types";

export interface NotificationMatrixViewProps {
  readonly onBack: () => void;
}

export const CATEGORY_META = {
  operaciones: {
    label: "Operaciones y Cocina",
    color: "#f59e0b",
    icon: Flame,
    bgClass: "bg-amber-500/10 text-amber-500 border-amber-500/20",
    badgeClass: "bg-amber-500/20 text-amber-400 border-amber-500/30",
  },
  inventario: {
    label: "Inventario y Recetas",
    color: "#10b981",
    icon: Boxes,
    bgClass: "bg-emerald-500/10 text-emerald-500 border-emerald-500/20",
    badgeClass: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30",
  },
  compras: {
    label: "Compras y Pedidos",
    color: "#6366f1",
    icon: Truck,
    bgClass: "bg-indigo-500/10 text-indigo-400 border-indigo-500/20",
    badgeClass: "bg-indigo-500/20 text-indigo-300 border-indigo-500/30",
  },
  equipo: {
    label: "Equipo y Actividades",
    color: "#a855f7",
    icon: Users,
    bgClass: "bg-purple-500/10 text-purple-400 border-purple-500/20",
    badgeClass: "bg-purple-500/20 text-purple-300 border-purple-500/30",
  },
} as const;

export const DEFAULT_CATALOG: readonly NotificationCatalogItem[] = [
  {
    type: "merma",
    label: "Mermas Operativas",
    category: "operaciones",
    description: "Descartes de insumos por vencimiento, rotura o merma de cocina",
  },
  {
    type: "consumo",
    label: "Consumo de Cocina",
    category: "operaciones",
    description: "Retiros de cocina para degustaciones, pruebas o preparación",
  },
  {
    type: "buffet",
    label: "Liquidación de Buffet",
    category: "operaciones",
    description: "Aprobación y cierre de consumo por comensales (Pax)",
  },
  {
    type: "conteo",
    label: "Conteos de Inventario",
    category: "inventario",
    description: "Ajustes de inventario físico, mermas teóricas y actas de recuento",
  },
  {
    type: "stock_critico",
    label: "Stock Crítico y Quiebres",
    category: "inventario",
    description: "Alertas tempranas de insumos bajo punto de reposición",
  },
  {
    type: "recibir_pedido",
    label: "Recepción de Mercadería",
    category: "compras",
    description: "Llegada de insumos desde proveedores con o sin discrepancias",
  },
  {
    type: "orden_compra",
    label: "Órdenes de Compra",
    category: "compras",
    description: "Emisión y confirmación de pedidos a proveedores externos",
  },
  {
    type: "turno_cambio",
    label: "Cambios de Turno",
    category: "equipo",
    description: "Solicitudes de relevos y rotaciones de cocineros y personal",
  },
  {
    type: "asistencia",
    label: "Asistencia y Novedades",
    category: "equipo",
    description: "Reporte de retardos, ausencias y novedades de dotación de sala",
  },
];

export const EXTENDED_CARGOS: readonly CargoMatrixItem[] = [
  {
    id: 1,
    name: "administrador",
    role_name: "Administrador General",
    description: "Supervisión total y control de costos",
    is_system: true,
    notification_permissions: {
      merma: true,
      consumo: true,
      buffet: true,
      conteo: true,
      stock_critico: true,
      recibir_pedido: true,
      orden_compra: true,
      turno_cambio: true,
      asistencia: true,
    },
  },
  {
    id: 2,
    name: "supervisor",
    role_name: "Supervisor de Turno",
    description: "Control de piso y autorizaciones",
    is_system: true,
    notification_permissions: {
      merma: true,
      consumo: true,
      buffet: true,
      conteo: true,
      stock_critico: true,
      recibir_pedido: true,
      orden_compra: true,
      turno_cambio: true,
      asistencia: true,
    },
  },
  {
    id: 3,
    name: "chef",
    role_name: "Chef Ejecutivo",
    description: "Operaciones de cocina y recetas",
    is_system: true,
    notification_permissions: {
      merma: true,
      consumo: true,
      buffet: true,
      conteo: false,
      stock_critico: true,
      recibir_pedido: false,
      orden_compra: false,
      turno_cambio: true,
      asistencia: true,
    },
  },
  {
    id: 4,
    name: "cocinero",
    role_name: "Cocinero de Estación",
    description: "Elaboración y despacho de platos",
    is_system: false,
    notification_permissions: {
      merma: true,
      consumo: true,
      buffet: false,
      conteo: false,
      stock_critico: true,
      recibir_pedido: false,
      orden_compra: false,
      turno_cambio: true,
      asistencia: false,
    },
  },
  {
    id: 5,
    name: "bodeguero",
    role_name: "Encargado de Bodega",
    description: "Control de entradas, salidas y conteos",
    is_system: false,
    notification_permissions: {
      merma: true,
      consumo: false,
      buffet: false,
      conteo: true,
      stock_critico: true,
      recibir_pedido: true,
      orden_compra: true,
      turno_cambio: false,
      asistencia: false,
    },
  },
  {
    id: 6,
    name: "garzon",
    role_name: "Garzón de Sala",
    description: "Atención a comensales y pedidos",
    is_system: false,
    notification_permissions: {
      merma: false,
      consumo: false,
      buffet: false,
      conteo: false,
      stock_critico: false,
      recibir_pedido: false,
      orden_compra: false,
      turno_cambio: true,
      asistencia: true,
    },
  },
  {
    id: 7,
    name: "cajero",
    role_name: "Cajero / POS",
    description: "Cobro, cierres y liquidaciones de caja",
    is_system: false,
    notification_permissions: {
      merma: false,
      consumo: false,
      buffet: true,
      conteo: false,
      stock_critico: false,
      recibir_pedido: false,
      orden_compra: false,
      turno_cambio: true,
      asistencia: true,
    },
  },
];

export function NotificationMatrixView({ onBack }: NotificationMatrixViewProps) {
  const {
    catalog: hookCatalog,
    cargos: hookCargos,
    rules,
    isAdmin,
    isLoading,
    updateCargoPermissions,
    isUpdating,
  } = useNotificationMatrix();

  const [activeTab, setActiveTab] = useState<"mis_notificaciones" | "gobernanza_cargos">(
    "mis_notificaciones"
  );

  // Unificar catálogo asegurando cobertura de las 4 categorías
  const unifiedCatalog = useMemo(() => {
    const map = new Map<string, NotificationCatalogItem>();
    DEFAULT_CATALOG.forEach((item) => map.set(item.type, item));
    if (hookCatalog && Array.isArray(hookCatalog)) {
      hookCatalog.forEach((item) => map.set(item.type, item));
    }
    return Array.from(map.values());
  }, [hookCatalog]);

  // Unificar cargos asegurando la dotación completa de roles
  const unifiedCargos = useMemo(() => {
    const map = new Map<number, CargoMatrixItem>();
    EXTENDED_CARGOS.forEach((c) => map.set(c.id, c));
    if (hookCargos && Array.isArray(hookCargos)) {
      hookCargos.forEach((c) => map.set(c.id, c));
    }
    return Array.from(map.values());
  }, [hookCargos]);

  // Cargo seleccionado para edición de gobernanza
  const [selectedCargoId, setSelectedCargoId] = useState<number>(() => {
    return unifiedCargos[0]?.id ?? 1;
  });

  const selectedCargo = useMemo(() => {
    return unifiedCargos.find((c) => c.id === selectedCargoId) || unifiedCargos[0] || null;
  }, [unifiedCargos, selectedCargoId]);

  // Borrador editable de permisos para el cargo seleccionado
  const [cargoPermissionsDraft, setCargoPermissionsDraft] = useState<Record<string, boolean>>({});

  useEffect(() => {
    if (selectedCargo?.notification_permissions) {
      setCargoPermissionsDraft({ ...selectedCargo.notification_permissions });
    } else {
      setCargoPermissionsDraft({});
    }
  }, [selectedCargo]);

  // Preferencias personales del usuario (inicializadas desde localStorage o default)
  const [userPreferences, setUserPreferences] = useState<Record<string, boolean>>(() => {
    try {
      const saved = localStorage.getItem("oppytec_user_notification_prefs");
      if (saved) return JSON.parse(saved);
    } catch {
      // Ignorar fallos de entorno
    }
    return {
      merma: true,
      consumo: true,
      buffet: true,
      conteo: true,
      stock_critico: true,
      recibir_pedido: true,
      orden_compra: true,
      turno_cambio: true,
      asistencia: true,
    };
  });

  // Cargo actual simulado del usuario (Administrador por defecto en entorno supervisor)
  const currentUserCargo = useMemo(() => {
    return unifiedCargos[0] || null;
  }, [unifiedCargos]);

  // Permisos efectivos asignados al cargo del usuario actual
  const userCargoEffectivePerms = useMemo(() => {
    return currentUserCargo?.notification_permissions || {};
  }, [currentUserCargo]);

  // Toggle de preferencia personal
  const handleToggleUserPref = (type: string) => {
    const isAllowedByCargo = userCargoEffectivePerms[type] !== false;
    if (!isAllowedByCargo) {
      toast.warning("Esta notificación está deshabilitada para tu cargo por la administración");
      return;
    }

    setUserPreferences((prev) => {
      const current = prev[type] !== false;
      const next = { ...prev, [type]: !current };
      try {
        localStorage.setItem("oppytec_user_notification_prefs", JSON.stringify(next));
      } catch {
        // Ignorar
      }
      return next;
    });
    toast.success("Preferencia actualizada");
  };

  // Toggle de permiso en el borrador de cargo
  const handleToggleCargoPerm = (type: string) => {
    setCargoPermissionsDraft((prev) => {
      const current = prev[type] !== false;
      return {
        ...prev,
        [type]: !current,
      };
    });
  };

  // Guardar permisos del cargo
  const handleSaveCargoPermissions = async () => {
    if (!selectedCargo) return;
    try {
      await updateCargoPermissions(selectedCargo.id, cargoPermissionsDraft);
      toast.success(`Permisos de notificación actualizados para ${selectedCargo.role_name}`);
    } catch {
      toast.error("Error al actualizar permisos del cargo");
    }
  };

  // Agrupar catálogo por categorías
  const catalogByCategory = useMemo(() => {
    const groups: Record<string, NotificationCatalogItem[]> = {
      operaciones: [],
      inventario: [],
      compras: [],
      equipo: [],
    };
    unifiedCatalog.forEach((item) => {
      const cat = item.category || "operaciones";
      const target = groups[cat];
      if (target) {
        target.push(item);
      } else {
        const fallback = groups.operaciones;
        if (fallback) fallback.push(item);
      }
    });
    return groups;
  }, [unifiedCatalog]);

  // Evalúa si un cargo posee atribuciones de aprobación en rules
  const cargoHasApprovalAuthority = (cargoName: string) => {
    if (!rules || !Array.isArray(rules)) return false;
    return rules.some(
      (r) => r.cargo.toLowerCase() === cargoName.toLowerCase() && r.es_aprobador
    );
  };

  if (isLoading && unifiedCargos.length === 0) {
    return (
      <div
        data-testid="matrix-loading-state"
        className="flex flex-col items-center justify-center py-24 gap-3"
      >
        <RefreshCw className="h-8 w-8 animate-spin text-amber-500" />
        <span className="text-xs font-bold text-muted-foreground uppercase tracking-widest">
          Cargando Matriz de Notificaciones...
        </span>
      </div>
    );
  }

  return (
    <div
      data-testid="notification-matrix-view"
      className="space-y-6 animate-in fade-in duration-300"
    >
      {/* ── 1. BARRA SUPERIOR DE ENCABEZADO Y TABS DUALES ── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-card/60 backdrop-blur-md p-4 rounded-3xl border border-border shadow-xl">
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={onBack}
            data-testid="btn-back-matrix"
            className="touch-target inline-flex items-center gap-1.5 h-9 px-3 rounded-xl border border-border bg-secondary hover:bg-secondary/80 text-secondary-foreground text-xs font-bold cursor-pointer transition-colors"
          >
            <ArrowLeft className="h-4 w-4" />
            <span>Volver</span>
          </button>
          <div>
            <h2 className="text-lg font-black uppercase tracking-wider text-foreground flex items-center gap-2">
              <SlidersHorizontal className="h-5 w-5 text-amber-500" />
              Matriz de Notificaciones y Gobernanza
            </h2>
            <p className="text-xs text-muted-foreground">
              Configura las notificaciones permitidas por cargo y tus preferencias personales
            </p>
          </div>
        </div>

        {/* Selector de Pestañas Duales (Tabs) */}
        {isAdmin && (
          <div
            data-testid="matrix-tabs-container"
            className="flex items-center bg-muted/50 p-1 rounded-2xl border border-border shadow-inner"
          >
            <button
              type="button"
              onClick={() => setActiveTab("mis_notificaciones")}
              data-testid="tab-mis-notificaciones"
              className={cn(
                "px-4 py-2 rounded-xl text-xs font-black uppercase tracking-wider transition-all cursor-pointer",
                activeTab === "mis_notificaciones"
                  ? "bg-card text-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground"
              )}
            >
              Mis Notificaciones
            </button>
            <button
              type="button"
              onClick={() => setActiveTab("gobernanza_cargos")}
              data-testid="tab-gobernanza-cargos"
              className={cn(
                "px-4 py-2 rounded-xl text-xs font-black uppercase tracking-wider transition-all cursor-pointer",
                activeTab === "gobernanza_cargos"
                  ? "bg-primary text-primary-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground"
              )}
            >
              Gobernanza de Cargos
            </button>
          </div>
        )}
      </div>

      {/* ── 2. TAB 1: MIS NOTIFICACIONES (PREFERENCIAS PERSONALES) ── */}
      {activeTab === "mis_notificaciones" && (
        <div data-testid="tab-content-mis-notificaciones" className="space-y-6">
          {/* Banner Informativo del Cargo */}
          <div className="bg-primary/10 border border-primary/20 p-4 rounded-2xl flex items-center justify-between">
            <div className="flex items-center gap-2.5 text-xs font-semibold text-foreground">
              <Info className="h-4 w-4 text-primary shrink-0" />
              <span>
                Tu cargo operativo es{" "}
                <strong className="text-primary capitalize">
                  {currentUserCargo?.role_name || "Administrador General"}
                </strong>
                . Las alertas denegadas por administración para tu rol aparecen bloqueadas con candado.
              </span>
            </div>
          </div>

          {/* Grilla de Categorías */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {(["operaciones", "inventario", "compras", "equipo"] as const).map((catKey) => {
              const meta = CATEGORY_META[catKey];
              const items = catalogByCategory[catKey] || [];
              const Icon = meta.icon;

              return (
                <div
                  key={catKey}
                  data-testid={`category-card-${catKey}`}
                  className="rounded-3xl border border-border bg-card/60 backdrop-blur-xl shadow-xl overflow-hidden flex flex-col"
                >
                  {/* Cabecera de Categoría */}
                  <div className="border-b border-border bg-muted/30 p-4 px-6 flex items-center justify-between">
                    <div className="flex items-center gap-2.5">
                      <div
                        className={cn(
                          "h-8 w-8 rounded-xl flex items-center justify-center border",
                          meta.bgClass
                        )}
                      >
                        <Icon className="h-4 w-4" />
                      </div>
                      <h3 className="text-sm font-black uppercase tracking-wider text-foreground">
                        {meta.label}
                      </h3>
                    </div>
                    <span
                      className={cn(
                        "text-[10px] font-bold uppercase px-2 py-0.5 rounded-full border",
                        meta.badgeClass
                      )}
                    >
                      {items.length} Tipos
                    </span>
                  </div>

                  {/* Lista de Notificaciones de la Categoría */}
                  <div className="p-6 divide-y divide-border/40 space-y-4 flex-1">
                    {items.map((item) => {
                      const isAllowedByCargo = userCargoEffectivePerms[item.type] !== false;
                      const isUserEnabled = userPreferences[item.type] !== false;

                      return (
                        <div
                          key={item.type}
                          data-testid={`user-pref-row-${item.type}`}
                          className="pt-3 first:pt-0 flex items-start justify-between gap-4"
                        >
                          <div className="space-y-1">
                            <span className="text-xs font-bold text-foreground flex items-center gap-2">
                              {item.label}
                              {!isAllowedByCargo && (
                                <span className="inline-flex items-center gap-1 text-[9px] font-black uppercase bg-destructive/15 text-destructive border border-destructive/30 px-1.5 py-0.5 rounded-md">
                                  <Lock className="h-2.5 w-2.5" /> Bloqueado por Admin
                                </span>
                              )}
                            </span>
                            <p className="text-[11px] text-muted-foreground leading-relaxed">
                              {item.description}
                            </p>
                          </div>

                          {/* Switch de Preferencia Personal */}
                          <div className="shrink-0 pt-0.5">
                            {isAllowedByCargo ? (
                              <button
                                type="button"
                                role="switch"
                                aria-checked={isUserEnabled}
                                data-testid={`toggle-user-pref-${item.type}`}
                                onClick={() => handleToggleUserPref(item.type)}
                                className={cn(
                                  "relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none",
                                  isUserEnabled ? "bg-primary" : "bg-muted"
                                )}
                              >
                                <span
                                  aria-hidden="true"
                                  className={cn(
                                    "pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow-lg ring-0 transition duration-200 ease-in-out",
                                    isUserEnabled ? "translate-x-5" : "translate-x-0"
                                  )}
                                />
                              </button>
                            ) : (
                              <div
                                className="h-6 w-11 rounded-full bg-muted/40 border border-border flex items-center justify-center cursor-not-allowed opacity-50"
                                title="Deshabilitado para tu cargo por administración"
                              >
                                <Lock className="h-3 w-3 text-muted-foreground" />
                              </div>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* ── 3. TAB 2: GOBERNANZA POR CARGOS (ADMINISTRACIÓN MULTI-ROL) ── */}
      {isAdmin && activeTab === "gobernanza_cargos" && (
        <div data-testid="tab-content-gobernanza" className="grid grid-cols-1 md:grid-cols-4 gap-6">
          {/* Columna Izquierda: Selector de Cargos */}
          <div className="md:col-span-1 space-y-3">
            <span className="text-[10px] font-black uppercase text-muted-foreground tracking-wider block px-1">
              Cargos del Negocio ({unifiedCargos.length})
            </span>

            <div className="space-y-2">
              {unifiedCargos.map((cargo) => {
                const isSelected = selectedCargoId === cargo.id;
                const isApprover = cargoHasApprovalAuthority(cargo.name);

                return (
                  <button
                    key={cargo.id}
                    type="button"
                    onClick={() => setSelectedCargoId(cargo.id)}
                    data-testid={`cargo-item-${cargo.id}`}
                    className={cn(
                      "w-full text-left p-3.5 rounded-2xl border text-xs transition-all flex flex-col gap-1 cursor-pointer",
                      isSelected
                        ? "bg-primary/10 border-primary shadow-lg shadow-primary/10 text-foreground ring-1 ring-primary/40"
                        : "bg-card/60 border-border hover:bg-card text-muted-foreground"
                    )}
                  >
                    <div className="flex items-center justify-between gap-1">
                      <span className="font-bold flex items-center gap-2 text-foreground text-xs">
                        <Briefcase
                          className={cn(
                            "h-3.5 w-3.5",
                            isSelected ? "text-primary" : "text-muted-foreground"
                          )}
                        />
                        {cargo.role_name}
                      </span>
                      {cargo.is_system && (
                        <span className="text-[9px] font-black uppercase px-1.5 py-0.2 rounded bg-muted text-muted-foreground border border-border">
                          Sistema
                        </span>
                      )}
                    </div>
                    <span className="text-[10px] text-muted-foreground line-clamp-1">
                      {cargo.description || `Rol: ${cargo.name}`}
                    </span>
                    {isApprover && (
                      <span className="inline-flex items-center gap-1 text-[9px] font-bold text-emerald-400 mt-0.5">
                        <CheckCircle2 className="h-2.5 w-2.5" />
                        Facultad de Aprobación
                      </span>
                    )}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Columna Derecha: Matriz de Permisos para el Cargo */}
          <div className="md:col-span-3 space-y-6 p-6 rounded-3xl border border-border bg-card/60 backdrop-blur-xl shadow-xl">
            {selectedCargo ? (
              <>
                {/* Cabecera del Cargo */}
                <div className="border-b border-border pb-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <div>
                    <h3 className="text-base font-black uppercase tracking-wider text-foreground flex items-center gap-2">
                      <Shield className="h-5 w-5 text-primary" />
                      Permisos para: <span className="text-primary">{selectedCargo.role_name}</span>
                    </h3>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      Determina qué notificaciones tienen derecho a ver y activar los colaboradores con este cargo.
                    </p>
                  </div>

                  {/* Botón de Guardado Persistente */}
                  <button
                    type="button"
                    onClick={handleSaveCargoPermissions}
                    disabled={isUpdating}
                    data-testid="btn-save-cargo-perms"
                    className="touch-target inline-flex items-center gap-2 h-10 px-5 rounded-2xl bg-gradient-to-r from-amber-500 to-yellow-500 hover:from-amber-400 hover:to-yellow-400 text-black font-black text-xs uppercase tracking-wider shadow-lg shadow-amber-500/20 cursor-pointer disabled:opacity-50 transition-all"
                  >
                    {isUpdating ? (
                      <>
                        <RefreshCw className="h-4 w-4 animate-spin" />
                        Guardando...
                      </>
                    ) : (
                      <>
                        <Save className="h-4 w-4" />
                        Guardar Permisos
                      </>
                    )}
                  </button>
                </div>

                {/* Secciones por Categoría */}
                <div className="space-y-6">
                  {(["operaciones", "inventario", "compras", "equipo"] as const).map((catKey) => {
                    const meta = CATEGORY_META[catKey];
                    const items = catalogByCategory[catKey] || [];
                    const Icon = meta.icon;

                    return (
                      <div key={catKey} className="space-y-3">
                        <div className="flex items-center gap-2 border-b border-border/40 pb-2">
                          <Icon className="h-4 w-4" style={{ color: meta.color }} />
                          <span
                            className="text-xs font-black uppercase tracking-wider"
                            style={{ color: meta.color }}
                          >
                            {meta.label}
                          </span>
                        </div>

                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                          {items.map((item) => {
                            const isAllowed = cargoPermissionsDraft[item.type] !== false;

                            return (
                              <button
                                key={item.type}
                                type="button"
                                onClick={() => handleToggleCargoPerm(item.type)}
                                data-testid={`toggle-cargo-perm-${item.type}`}
                                className={cn(
                                  "p-3 rounded-2xl border text-left transition-all flex items-start justify-between gap-3 cursor-pointer",
                                  isAllowed
                                    ? "bg-primary/10 border-primary/30 text-foreground"
                                    : "bg-card/40 border-border text-muted-foreground hover:bg-card/70"
                                )}
                              >
                                <div className="space-y-0.5">
                                  <span className="text-xs font-bold block">{item.label}</span>
                                  <p className="text-[10px] text-muted-foreground line-clamp-2 leading-relaxed">
                                    {item.description}
                                  </p>
                                </div>

                                <div className="mt-0.5 shrink-0">
                                  {isAllowed ? (
                                    <div className="h-5 w-5 rounded-lg bg-primary text-primary-foreground flex items-center justify-center border border-primary shadow-sm">
                                      <Check className="h-3.5 w-3.5 stroke-[3]" />
                                    </div>
                                  ) : (
                                    <div className="h-5 w-5 rounded-lg border border-border bg-background" />
                                  )}
                                </div>
                              </button>
                            );
                          })}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </>
            ) : (
              <div className="text-center py-16 text-muted-foreground text-xs">
                Selecciona un cargo para configurar sus permisos de notificación.
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default NotificationMatrixView;
