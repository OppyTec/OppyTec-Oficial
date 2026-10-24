import { useState, useEffect, useRef } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import {
  Package,
  ClipboardList,
  Boxes,
  UtensilsCrossed,
  TrendingUp,
  History,
  CalendarDays,
  ChevronLeft,
  ChevronRight,
  Bell,
  AlertTriangle,
  ShoppingCart,
  ClipboardCheck,
  X,
  Truck,
  Users,
  LayoutDashboard,
  ChevronDown,
  BarChart3,
  DollarSign,
  FileText,
  CookingPot,
  ListPlus,
  Lock,
  Calculator,
  Mic,
  ShoppingBag,
  ScanLine,
} from "lucide-react";
import { toast } from "sonner";
import { cn, getImageUrl } from "@/shared/lib";
import { usePermissions } from "@/shared/auth/usePermissions";
import { useTheme } from "@/shared/hooks";

export const FEATURE_MODULE_ROUTES = [
  { id: "analytics", labelEs: "Analítica & KPIs", labelEn: "Analytics & KPIs" },
  { id: "catalog", labelEs: "Catálogo & R2", labelEn: "Catalog & R2" },
  { id: "inventory", labelEs: "Inventario & Mermas", labelEn: "Inventory & Waste" },
  { id: "recipes", labelEs: "Recetas & Escandallos", labelEn: "Recipes & BOM" },
  { id: "procurement", labelEs: "Compras & OCR DTE", labelEn: "Procurement & DTE" },
  { id: "operations", labelEs: "Operaciones & POS", labelEn: "Operations & POS" },
  { id: "oppyfy", labelEs: "Asistente IA OppyFy", labelEn: "OppyFy AI Assistant" },
  { id: "rbac-and-audit", labelEs: "RBAC 3-Niveles & Auditoría", labelEn: "3-Level RBAC & Audit" },
  { id: "platform-admin", labelEs: "SuperAdmin & Observabilidad", labelEn: "SuperAdmin & Observability" },
  { id: "auth", labelEs: "Sesión & Impersonación", labelEn: "Session & Impersonation" },
] as const;

export type FeatureRouteId = (typeof FEATURE_MODULE_ROUTES)[number]["id"];

export const PLAN_BASICO_10_NAV_ITEMS = [
  { slug: "inicio", labelEs: "1. Inicio", labelEn: "1. Home Dashboard", targetFeature: "analytics" },
  { slug: "registro_de_consumo", labelEs: "2. Registro de Consumo", labelEn: "2. Consumption Log", targetFeature: "operations" },
  { slug: "registro_de_stock", labelEs: "3. Registro de Stock", labelEn: "3. Stock Entry", targetFeature: "inventory" },
  { slug: "gestion_de_productos", labelEs: "4. Gestión de Productos", labelEn: "4. Product Management", targetFeature: "catalog" },
  { slug: "gestion_de_mermas", labelEs: "5. Gestión de Mermas", labelEn: "5. Waste Management", targetFeature: "inventory" },
  { slug: "recuento_unificado", labelEs: "6. Recuento (+ Historial)", labelEn: "6. Physical Count (+ History)", targetFeature: "inventory" },
  { slug: "notificaciones", labelEs: "7. Notificaciones", labelEn: "7. Notifications", targetFeature: "operations" },
  { slug: "alertas", labelEs: "8. Alertas", labelEn: "8. Stock & FEFO Alerts", targetFeature: "inventory" },
  { slug: "historial", labelEs: "9. Historial", labelEn: "9. Movement History", targetFeature: "rbac-and-audit" },
  { slug: "usuarios", labelEs: "10. Usuarios", labelEn: "10. Users & Seats", targetFeature: "rbac-and-audit" },
] as const;

export type BasicPlanNavItem = (typeof PLAN_BASICO_10_NAV_ITEMS)[number];

export interface MenuItem {
  readonly path: string;
  readonly label: string;
  readonly icon: any;
  readonly exact?: boolean;
  readonly hasBadge?: boolean;
  readonly color: string;
  readonly rgb: string;
  readonly slug?: string;
  readonly isSection?: boolean;
}

export const LEGACY_MENU_ITEMS: readonly MenuItem[] = [
  {
    path: "/",
    label: "Inicio",
    icon: LayoutDashboard,
    exact: true,
    color: "#6366f1",
    rgb: "99,102,241",
    slug: "module:inicio",
  },
  {
    path: "/consumo",
    label: "Consumo",
    icon: UtensilsCrossed,
    color: "#f97316",
    rgb: "249,115,22",
    slug: "module:consumo",
    isSection: true,
  },
  {
    path: "/ventas",
    label: "Ventas",
    icon: ShoppingBag,
    color: "#10b981",
    rgb: "16,185,129",
    slug: "module:ventas",
  },
  {
    path: "/inventario",
    label: "Inventario",
    icon: ClipboardList,
    color: "#3b82f6",
    rgb: "59,130,246",
    slug: "module:inventario",
    isSection: true,
  },
  {
    path: "/gestion",
    label: "Gestión",
    icon: Boxes,
    color: "#a855f7",
    rgb: "168,85,247",
    slug: "module:gestion",
    isSection: true,
  },
  {
    path: "/notificaciones",
    label: "Notificaciones",
    icon: Bell,
    hasBadge: true,
    color: "#fbbf24",
    rgb: "251,191,36",
    slug: "module:notificaciones",
  },
  {
    path: "/alertas",
    label: "Alertas",
    icon: AlertTriangle,
    hasBadge: true,
    color: "#ef4444",
    rgb: "239,68,68",
    slug: "module:alertas",
  },
  {
    path: "/eventos",
    label: "Eventos",
    icon: CalendarDays,
    color: "#ec4899",
    rgb: "236,72,153",
    slug: "module:eventos",
  },
  {
    path: "/proyeccion",
    label: "Proyección",
    icon: TrendingUp,
    color: "#10b981",
    rgb: "16,185,129",
    slug: "module:proyeccion",
  },
  {
    path: "/historial",
    label: "Historial",
    icon: History,
    color: "#06b6d4",
    rgb: "6,182,212",
    slug: "module:historial",
  },
  {
    path: "/contabilidad",
    label: "Contabilidad",
    icon: Calculator,
    color: "#6366f1",
    rgb: "99,102,241",
    slug: "module:contabilidad",
    isSection: true,
  },
];

export interface SidebarProps {
  readonly logo?: string | null;
  readonly name?: string;
  readonly tipoNegocio?: string | null;
  readonly businessType?: { nombre: string; enabled_modules?: any } | null;
  readonly isOpen?: boolean;
  readonly onClose?: () => void;
  readonly isCollapsed?: boolean;
  readonly onCollapseChange?: (collapsed: boolean) => void;
  readonly enabledModules?: readonly string[];
  readonly activeFeature?: FeatureRouteId;
  readonly onSelectFeature?: (feature: FeatureRouteId) => void;
  readonly showAllFeatures?: boolean;
  readonly onToggleShowAll?: () => void;
  readonly language?: "es" | "en";
}

export function Sidebar({
  logo = null,
  name = "OppyTec Gastronomía",
  tipoNegocio = "Restaurante & Bar",
  businessType,
  isOpen = false,
  onClose,
  isCollapsed: controlledIsCollapsed,
  onCollapseChange,
  enabledModules: propEnabledModules,
  activeFeature: _activeFeature,
  onSelectFeature: _onSelectFeature,
}: SidebarProps) {
  const [localIsCollapsed, setLocalIsCollapsed] = useState(false);
  const isCollapsed =
    controlledIsCollapsed !== undefined ? controlledIsCollapsed : localIsCollapsed;

  const resolvedTipo = businessType?.nombre || tipoNegocio;

  const setIsCollapsed = (val: boolean | ((prev: boolean) => boolean)) => {
    const nextVal = typeof val === "function" ? val(isCollapsed) : val;
    if (onCollapseChange) {
      onCollapseChange(nextVal);
    } else {
      setLocalIsCollapsed(nextVal);
    }
  };

  const [isConsumoOpen, setIsConsumoOpen] = useState(false);
  const [isInventarioOpen, setIsInventarioOpen] = useState(false);
  const [isGestionOpen, setIsGestionOpen] = useState(false);
  const [isContabilidadOpen, setIsContabilidadOpen] = useState(false);
  const [isPanelEjecutivoOpen, setIsPanelEjecutivoOpen] = useState(false);
  const [isPanelActividadesOpen, setIsPanelActividadesOpen] = useState(false);

  const location = useLocation();
  const navigate = useNavigate();
  const { theme } = useTheme();
  const { policy } = usePermissions();

  // Set of modules enabled by the contracted plan
  const planModulesSet = useRef<Set<string>>(new Set());
  useEffect(() => {
    if (propEnabledModules) {
      planModulesSet.current = new Set(propEnabledModules);
    } else if (policy?.planModules) {
      planModulesSet.current = new Set(policy.planModules);
    } else {
      // Default: basic suite is enabled, advanced enterprise features might be locked
      planModulesSet.current = new Set([
        "module:inicio",
        "module:consumo",
        "module:inventario",
        "module:gestion",
        "module:notificaciones",
        "module:alertas",
        "module:historial",
        "module:panel_ejecutivo",
        "module:panel_de_actividades",
      ]);
    }
  }, [propEnabledModules, policy?.planModules]);

  const hasModule = (slug?: string): boolean => {
    if (!slug) return true;
    if (planModulesSet.current.has("*")) return true;
    if (planModulesSet.current.has(slug)) return true;
    // Map standard submodule prefixes
    const prefix = slug.replace("module:", "");
    if (planModulesSet.current.has(prefix)) return true;
    return false;
  };

  const handleModuleClick = (slug: string | undefined, moduleName: string, action: () => void) => {
    if (!slug || hasModule(slug)) {
      action();
      return;
    }
    toast.info(`El módulo "${moduleName}" no está incluido en el plan contratado de tu negocio.`, {
      description: "Contacta al Administrador de OppyTec para activar este módulo.",
      duration: 4000,
    });
  };

  // Consumo sub-items
  const consumoSubItems = [
    { path: "/consumo/manos-libres", label: "Manos Libres", icon: Mic, color: "#f97316", rgb: "249,115,22", slug: "module:consumo" },
    { path: "/consumo/buffet", label: "Buffet Inteligente", icon: ScanLine, color: "#06b6d4", rgb: "6,182,212", slug: "module:consumo" },
    { path: "/registro-de-consumo", label: "Registro de Consumo", icon: UtensilsCrossed, color: "#eab308", rgb: "234,179,8", slug: "module:consumo" },
  ];

  // Inventario sub-items
  const inventarioSubItems = [
    { path: "/inventario/stock", label: "Registro de Stock", icon: ClipboardList, color: "#3b82f6", rgb: "59,130,246", slug: "module:inventario" },
    { path: "/contar-inventario", label: "Recuento", icon: ClipboardCheck, color: "#10b981", rgb: "16,185,129", slug: "module:inventario" },
    { path: "/recuentos", label: "Historial de Recuentos", icon: History, color: "#a855f7", rgb: "168,85,247", slug: "module:inventario" },
  ];

  // Gestión sub-items
  const gestionSubItems = [
    { path: "/gestion?tab=productos", label: "Productos", icon: Package, color: "#eab308", rgb: "234,179,8", slug: "module:gestion" },
    { path: "/gestion?tab=recetas", label: "Recetas", icon: CookingPot, color: "#a855f7", rgb: "168,85,247", slug: "module:gestion" },
    { path: "/gestion?tab=combos", label: "Combos", icon: Boxes, color: "#1c4c96", rgb: "28,76,150", slug: "module:gestion" },
    { path: "/gestion?tab=grupos-opciones", label: "Grupos Opciones", icon: ListPlus, color: "#4338ca", rgb: "67,56,202", slug: "module:gestion" },
    { path: "/gestion?tab=pedidos", label: "Pedidos", icon: ShoppingCart, color: "#10b981", rgb: "16,185,129", slug: "module:gestion" },
    { path: "/proveedores", label: "Proveedores", icon: Truck, color: "#06b6d4", rgb: "6,182,212", slug: "module:gestion" },
    { path: "/gestion?tab=mermas", label: "Mermas", icon: AlertTriangle, color: "#ef4444", rgb: "239,68,68", slug: "module:gestion" },
  ];

  // Contabilidad sub-items
  const contabilidadSubItems = [
    { path: "/contabilidad/facturas", label: "Facturas", icon: FileText, color: "#6366f1", rgb: "99,102,241", slug: "module:contabilidad" },
  ];

  // Panel Ejecutivo items
  const panelEjecutivoItems = [
    { path: "/reportes/resumen-general", label: "Resumen General", icon: LayoutDashboard, color: "#3b82f6", rgb: "59,130,246", slug: "module:panel_ejecutivo" },
    { path: "/reportes/resumen-ejecutivo", label: "Resumen Ejecutivo", icon: BarChart3, color: "#a855f7", rgb: "168,85,247", slug: "module:panel_ejecutivo" },
    { path: "/reportes/control-perdidas", label: "Control de Pérdidas", icon: AlertTriangle, color: "#ef4444", rgb: "239,68,68", slug: "module:panel_ejecutivo" },
    { path: "/reportes/eficiencia-operacional", label: "Eficiencia Operacional", icon: TrendingUp, color: "#10b981", rgb: "16,185,129", slug: "module:panel_ejecutivo" },
    { path: "/reportes/vision-financiera", label: "Visión Financiera", icon: DollarSign, color: "#22c55e", rgb: "34,197,94", slug: "module:panel_ejecutivo" },
  ];

  // Panel de Actividades items
  const panelActividadesItems = [
    { path: "/actividades/notas", label: "Notas", icon: ClipboardList, color: "#3b82f6", rgb: "59,130,246", slug: "module:panel_de_actividades" },
    { path: "/actividades/tareas", label: "Tareas", icon: ClipboardCheck, color: "#10b981", rgb: "16,185,129", slug: "module:panel_de_actividades" },
    { path: "/actividades/horarios", label: "Horarios", icon: CalendarDays, color: "#ec4899", rgb: "236,72,153", slug: "module:panel_de_actividades" },
    { path: "/actividades/usuarios", label: "Usuarios", icon: Users, color: "#3b82f6", rgb: "59,130,246", slug: "module:panel_de_actividades" },
  ];

  // Automatically expand sections based on current location
  useEffect(() => {
    const p = location.pathname;
    if (p.startsWith("/consumo") || p === "/registro-de-consumo") setIsConsumoOpen(true);
    if (p.startsWith("/inventario") || p === "/contar-inventario" || p === "/recuentos") setIsInventarioOpen(true);
    if (p.startsWith("/gestion") || p === "/proveedores") setIsGestionOpen(true);
    if (p.startsWith("/contabilidad")) setIsContabilidadOpen(true);
    if (p.startsWith("/reportes")) setIsPanelEjecutivoOpen(true);
    if (p.startsWith("/actividades")) setIsPanelActividadesOpen(true);
  }, [location.pathname]);

  const isSubActive = (path: string): boolean => {
    if (path.includes("?")) {
      return location.pathname + location.search === path;
    }
    return location.pathname === path;
  };

  const renderNavItem = (item: MenuItem) => {
    const isLocked = item.slug && !hasModule(item.slug);
    const isActive = item.exact ? location.pathname === item.path : location.pathname.startsWith(item.path);

    // Section handler for expandable parents
    if (item.label === "Consumo") {
      const isExpanded = isConsumoOpen;
      const isAnyActive = consumoSubItems.some((s) => isSubActive(s.path));
      return (
        <div key={item.path} className="pt-0.5 pb-0.5">
          <div
            style={{ ["--item-color" as any]: item.color, ["--item-rgb" as any]: item.rgb }}
            onClick={() => {
              if (isLocked) {
                handleModuleClick(item.slug, item.label, () => {});
                return;
              }
              if (!isCollapsed || isOpen) setIsConsumoOpen(!isExpanded);
              else navigate("/consumo/manos-libres");
            }}
            className={cn(
              "flex items-center gap-3 px-3 h-11 rounded-xl transition-all duration-200 group relative overflow-hidden cursor-pointer",
              isLocked && "opacity-50 cursor-not-allowed",
              isAnyActive
                ? "bg-[var(--item-color)] text-white shadow-md"
                : theme === "light"
                  ? "hover:bg-[rgba(var(--item-rgb),0.10)] text-foreground hover:text-[var(--item-color)]"
                  : "hover:bg-[rgba(var(--item-rgb),0.10)] text-muted-foreground hover:text-[var(--item-color)]"
            )}
          >
            <div className="relative shrink-0 w-8 flex justify-center">
              <UtensilsCrossed size={19} className={isAnyActive ? "text-white" : "text-[var(--item-color)]"} />
            </div>
            {(!isCollapsed || isOpen) && (
              <span className="font-semibold text-xs whitespace-nowrap flex-1 text-left">
                Consumo
              </span>
            )}
            {(!isCollapsed || isOpen) && (
              isLocked ? (
                <Lock size={14} className="text-muted-foreground ml-auto shrink-0" />
              ) : (
                <ChevronDown size={14} className={cn("transition-transform shrink-0", isExpanded && "rotate-180")} />
              )
            )}
          </div>

          {isExpanded && (!isCollapsed || isOpen) && !isLocked && (
            <div className="pl-9 pr-2 py-1 space-y-1 animate-in fade-in slide-in-from-top-1 duration-200">
              {consumoSubItems.map((sub) => {
                const subActive = isSubActive(sub.path);
                const SubIcon = sub.icon;
                return (
                  <Link
                    key={sub.path}
                    to={sub.path}
                    className={cn(
                      "flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-xs font-medium transition-colors",
                      subActive
                        ? "bg-primary/15 text-primary font-bold"
                        : "text-muted-foreground hover:text-foreground hover:bg-secondary/60"
                    )}
                  >
                    <SubIcon size={14} className={subActive ? "text-primary" : "text-muted-foreground"} />
                    <span className="truncate">{sub.label}</span>
                  </Link>
                );
              })}
            </div>
          )}
        </div>
      );
    }

    if (item.label === "Inventario") {
      const isExpanded = isInventarioOpen;
      const isAnyActive = inventarioSubItems.some((s) => isSubActive(s.path));
      return (
        <div key={item.path} className="pt-0.5 pb-0.5">
          <div
            style={{ ["--item-color" as any]: item.color, ["--item-rgb" as any]: item.rgb }}
            onClick={() => {
              if (isLocked) {
                handleModuleClick(item.slug, item.label, () => {});
                return;
              }
              if (!isCollapsed || isOpen) setIsInventarioOpen(!isExpanded);
              else navigate("/inventario/stock");
            }}
            className={cn(
              "flex items-center gap-3 px-3 h-11 rounded-xl transition-all duration-200 group relative overflow-hidden cursor-pointer",
              isLocked && "opacity-50 cursor-not-allowed",
              isAnyActive
                ? "bg-[var(--item-color)] text-white shadow-md"
                : theme === "light"
                  ? "hover:bg-[rgba(var(--item-rgb),0.10)] text-foreground hover:text-[var(--item-color)]"
                  : "hover:bg-[rgba(var(--item-rgb),0.10)] text-muted-foreground hover:text-[var(--item-color)]"
            )}
          >
            <div className="relative shrink-0 w-8 flex justify-center">
              <ClipboardList size={19} className={isAnyActive ? "text-white" : "text-[var(--item-color)]"} />
            </div>
            {(!isCollapsed || isOpen) && (
              <span className="font-semibold text-xs whitespace-nowrap flex-1 text-left">
                Inventario
              </span>
            )}
            {(!isCollapsed || isOpen) && (
              isLocked ? (
                <Lock size={14} className="text-muted-foreground ml-auto shrink-0" />
              ) : (
                <ChevronDown size={14} className={cn("transition-transform shrink-0", isExpanded && "rotate-180")} />
              )
            )}
          </div>

          {isExpanded && (!isCollapsed || isOpen) && !isLocked && (
            <div className="pl-9 pr-2 py-1 space-y-1 animate-in fade-in slide-in-from-top-1 duration-200">
              {inventarioSubItems.map((sub) => {
                const subActive = isSubActive(sub.path);
                const SubIcon = sub.icon;
                return (
                  <Link
                    key={sub.path}
                    to={sub.path}
                    className={cn(
                      "flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-xs font-medium transition-colors",
                      subActive
                        ? "bg-primary/15 text-primary font-bold"
                        : "text-muted-foreground hover:text-foreground hover:bg-secondary/60"
                    )}
                  >
                    <SubIcon size={14} className={subActive ? "text-primary" : "text-muted-foreground"} />
                    <span className="truncate">{sub.label}</span>
                  </Link>
                );
              })}
            </div>
          )}
        </div>
      );
    }

    if (item.label === "Gestión") {
      const isExpanded = isGestionOpen;
      const isAnyActive = gestionSubItems.some((s) => isSubActive(s.path));
      return (
        <div key={item.path} className="pt-0.5 pb-0.5">
          <div
            style={{ ["--item-color" as any]: item.color, ["--item-rgb" as any]: item.rgb }}
            onClick={() => {
              if (isLocked) {
                handleModuleClick(item.slug, item.label, () => {});
                return;
              }
              if (!isCollapsed || isOpen) setIsGestionOpen(!isExpanded);
              else navigate("/gestion?tab=productos");
            }}
            className={cn(
              "flex items-center gap-3 px-3 h-11 rounded-xl transition-all duration-200 group relative overflow-hidden cursor-pointer",
              isLocked && "opacity-50 cursor-not-allowed",
              isAnyActive
                ? "bg-[var(--item-color)] text-white shadow-md"
                : theme === "light"
                  ? "hover:bg-[rgba(var(--item-rgb),0.10)] text-foreground hover:text-[var(--item-color)]"
                  : "hover:bg-[rgba(var(--item-rgb),0.10)] text-muted-foreground hover:text-[var(--item-color)]"
            )}
          >
            <div className="relative shrink-0 w-8 flex justify-center">
              <Boxes size={19} className={isAnyActive ? "text-white" : "text-[var(--item-color)]"} />
            </div>
            {(!isCollapsed || isOpen) && (
              <span className="font-semibold text-xs whitespace-nowrap flex-1 text-left">
                Gestión
              </span>
            )}
            {(!isCollapsed || isOpen) && (
              isLocked ? (
                <Lock size={14} className="text-muted-foreground ml-auto shrink-0" />
              ) : (
                <ChevronDown size={14} className={cn("transition-transform shrink-0", isExpanded && "rotate-180")} />
              )
            )}
          </div>

          {isExpanded && (!isCollapsed || isOpen) && !isLocked && (
            <div className="pl-9 pr-2 py-1 space-y-1 animate-in fade-in slide-in-from-top-1 duration-200">
              {gestionSubItems.map((sub) => {
                const subActive = isSubActive(sub.path);
                const SubIcon = sub.icon;
                return (
                  <Link
                    key={sub.path}
                    to={sub.path}
                    className={cn(
                      "flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-xs font-medium transition-colors",
                      subActive
                        ? "bg-primary/15 text-primary font-bold"
                        : "text-muted-foreground hover:text-foreground hover:bg-secondary/60"
                    )}
                  >
                    <SubIcon size={14} className={subActive ? "text-primary" : "text-muted-foreground"} />
                    <span className="truncate">{sub.label}</span>
                  </Link>
                );
              })}
            </div>
          )}
        </div>
      );
    }

    if (item.label === "Contabilidad") {
      const isExpanded = isContabilidadOpen;
      const isAnyActive = contabilidadSubItems.some((s) => isSubActive(s.path));
      return (
        <div key={item.path} className="pt-0.5 pb-0.5">
          <div
            style={{ ["--item-color" as any]: item.color, ["--item-rgb" as any]: item.rgb }}
            onClick={() => {
              if (isLocked) {
                handleModuleClick(item.slug, item.label, () => {});
                return;
              }
              if (!isCollapsed || isOpen) setIsContabilidadOpen(!isExpanded);
              else navigate("/contabilidad/facturas");
            }}
            className={cn(
              "flex items-center gap-3 px-3 h-11 rounded-xl transition-all duration-200 group relative overflow-hidden cursor-pointer",
              isLocked && "opacity-50 cursor-not-allowed",
              isAnyActive
                ? "bg-[var(--item-color)] text-white shadow-md"
                : theme === "light"
                  ? "hover:bg-[rgba(var(--item-rgb),0.10)] text-foreground hover:text-[var(--item-color)]"
                  : "hover:bg-[rgba(var(--item-rgb),0.10)] text-muted-foreground hover:text-[var(--item-color)]"
            )}
          >
            <div className="relative shrink-0 w-8 flex justify-center">
              <Calculator size={19} className={isAnyActive ? "text-white" : "text-[var(--item-color)]"} />
            </div>
            {(!isCollapsed || isOpen) && (
              <span className="font-semibold text-xs whitespace-nowrap flex-1 text-left">
                Contabilidad
              </span>
            )}
            {(!isCollapsed || isOpen) && (
              isLocked ? (
                <Lock size={14} className="text-muted-foreground ml-auto shrink-0" />
              ) : (
                <ChevronDown size={14} className={cn("transition-transform shrink-0", isExpanded && "rotate-180")} />
              )
            )}
          </div>

          {isExpanded && (!isCollapsed || isOpen) && !isLocked && (
            <div className="pl-9 pr-2 py-1 space-y-1 animate-in fade-in slide-in-from-top-1 duration-200">
              {contabilidadSubItems.map((sub) => {
                const subActive = isSubActive(sub.path);
                const SubIcon = sub.icon;
                return (
                  <Link
                    key={sub.path}
                    to={sub.path}
                    className={cn(
                      "flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-xs font-medium transition-colors",
                      subActive
                        ? "bg-primary/15 text-primary font-bold"
                        : "text-muted-foreground hover:text-foreground hover:bg-secondary/60"
                    )}
                  >
                    <SubIcon size={14} className={subActive ? "text-primary" : "text-muted-foreground"} />
                    <span className="truncate">{sub.label}</span>
                  </Link>
                );
              })}
            </div>
          )}
        </div>
      );
    }

    // Direct single nav item
    const Icon = item.icon;
    return (
      <div key={item.path} className="pt-0.5 pb-0.5">
        <div
          style={{ ["--item-color" as any]: item.color, ["--item-rgb" as any]: item.rgb }}
          onClick={() => {
            if (isLocked) {
              handleModuleClick(item.slug, item.label, () => {});
              return;
            }
            navigate(item.path);
            if (onClose) onClose();
          }}
          className={cn(
            "flex items-center gap-3 px-3 h-11 rounded-xl transition-all duration-200 group relative overflow-hidden cursor-pointer",
            isLocked && "opacity-50 cursor-not-allowed",
            isActive
              ? "bg-[var(--item-color)] text-white shadow-md shadow-[rgba(var(--item-rgb),0.3)] font-bold"
              : theme === "light"
                ? "hover:bg-[rgba(var(--item-rgb),0.10)] text-foreground hover:text-[var(--item-color)]"
                : "hover:bg-[rgba(var(--item-rgb),0.10)] text-muted-foreground hover:text-[var(--item-color)]"
          )}
        >
          <div className="relative shrink-0 w-8 flex justify-center">
            <Icon size={19} className={isActive ? "text-white" : "text-[var(--item-color)]"} />
          </div>

          {(!isCollapsed || isOpen) && (
            <span className="font-semibold text-xs whitespace-nowrap flex-1 text-left truncate">
              {item.label}
            </span>
          )}

          {(!isCollapsed || isOpen) && isLocked && (
            <Lock size={14} className="text-muted-foreground ml-auto shrink-0" />
          )}
        </div>
      </div>
    );
  };

  return (
    <>
      {/* Mobile Backdrop */}
      {isOpen && (
        <div
          role="presentation"
          onClick={onClose}
          className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm md:hidden"
        />
      )}

      {/* Main Sidebar Aside */}
      <aside
        data-testid="app-sidebar"
        className={cn(
          "fixed top-0 bottom-0 left-0 z-50 flex flex-col bg-card border-r border-border transition-all duration-300 ease-in-out md:sticky md:z-30 h-screen",
          isOpen ? "translate-x-0 w-64 shadow-2xl" : "-translate-x-full md:translate-x-0",
          isCollapsed ? "md:w-20" : "md:w-64"
        )}
      >
        {/* Header con Logo, Nombre y Floating Circular Chevron */}
        <div
          style={{
            background:
              theme === "ocean-blue"
                ? "hsla(220, 40%, 10%, 0.75)"
                : theme === "dark"
                  ? "hsl(224, 71%, 4%)"
                  : "hsl(161, 72%, 38%)",
          }}
          className={cn(
            "relative flex items-center flex-none overflow-hidden group/header touch-none h-20 border-b px-4 transition-all duration-300 w-full z-20",
            theme === "ocean-blue"
              ? "border-white/5 text-white"
              : theme === "dark"
                ? "border-border/50 text-white"
                : "dark bg-primary border-primary-foreground/20 text-white"
          )}
        >
          {/* Floating Circular Chevron Button */}
          <motion.button
            type="button"
            data-testid="sidebar-collapse-toggle-btn"
            onClick={(e) => {
              e.stopPropagation();
              setIsCollapsed(!isCollapsed);
            }}
            initial={false}
            animate={{
              right: isCollapsed && !isOpen ? 16 : 12,
              width: isCollapsed && !isOpen ? 44 : 32,
              height: isCollapsed && !isOpen ? 44 : 32,
              borderRadius: isCollapsed && !isOpen ? "1rem" : "0.5rem",
            }}
            transition={{ duration: 0.3, ease: "easeInOut" }}
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            className={cn(
              "absolute inset-y-0 my-auto hidden md:flex items-center justify-center z-50 cursor-pointer shadow-md backdrop-blur-sm border transition-all duration-200 opacity-0 group-hover/header:opacity-100",
              theme === "light"
                ? "bg-white/20 border-white/30 text-white hover:bg-white/30"
                : "bg-primary/10 border-primary/20 text-primary hover:bg-primary/20"
            )}
            title={isCollapsed ? "Expandir barra lateral" : "Colapsar barra lateral"}
          >
            {isCollapsed ? <ChevronRight size={18} /> : <ChevronLeft size={16} />}
          </motion.button>

          {/* Logo & Tenant Info */}
          <div className="flex items-center gap-3 min-w-0 flex-1 h-full">
            <div
              className={cn(
                "h-11 w-11 rounded-2xl flex items-center justify-center overflow-hidden shrink-0 shadow-sm relative transition-opacity duration-200",
                theme === "light"
                  ? "bg-white/20 border border-white/30 text-white"
                  : "bg-primary/10 border border-primary/20 text-primary"
              )}
            >
              {logo ? (
                <img src={getImageUrl(logo)} className="h-full w-full object-contain p-1" alt="Logo" />
              ) : (
                <Package className="h-6 w-6" />
              )}
            </div>

            {(!isCollapsed || isOpen) && (
              <div className="flex flex-col justify-center min-w-0 flex-1 overflow-hidden">
                <span className="font-extrabold text-sm tracking-wide uppercase truncate leading-tight">
                  {name}
                </span>
                <span className="text-[10px] font-medium opacity-80 truncate leading-tight capitalize">
                  {resolvedTipo}
                </span>
              </div>
            )}
          </div>

          {/* Close Button on Mobile */}
          <button
            type="button"
            onClick={onClose}
            className="md:hidden absolute right-4 top-1/2 -translate-y-1/2 h-8 w-8 rounded-lg hover:bg-secondary flex items-center justify-center transition-colors border border-border"
          >
            <X size={18} />
          </button>
        </div>

        {/* Scrollable Navigation List */}
        <nav className="flex-1 px-2.5 py-3 space-y-1 overflow-y-auto overflow-x-hidden custom-scrollbar">
          {LEGACY_MENU_ITEMS.map((item) => renderNavItem(item))}

          {/* Separador de Paneles */}
          <div className="pt-3 pb-1">
            <div className="h-px bg-border/60 mx-1 mb-2" />
            {(!isCollapsed || isOpen) && (
              <span className="px-2 font-mono text-[10px] font-bold uppercase tracking-wider text-muted-foreground block">
                Paneles de Control
              </span>
            )}
          </div>

          {/* Panel Ejecutivo */}
          <div className="pt-0.5 pb-0.5">
            <div
              onClick={() => {
                if (!hasModule("module:panel_ejecutivo")) {
                  handleModuleClick("module:panel_ejecutivo", "Panel Ejecutivo", () => {});
                  return;
                }
                setIsPanelEjecutivoOpen(!isPanelEjecutivoOpen);
              }}
              className={cn(
                "flex items-center gap-3 px-3 h-11 rounded-xl transition-all duration-200 group relative overflow-hidden cursor-pointer",
                !hasModule("module:panel_ejecutivo") && "opacity-50 cursor-not-allowed",
                isPanelEjecutivoOpen
                  ? "bg-blue-600/10 text-blue-500 font-semibold"
                  : "hover:bg-blue-600/10 text-muted-foreground hover:text-blue-500"
              )}
            >
              <div className="relative shrink-0 w-8 flex justify-center">
                <BarChart3 size={19} className="text-blue-500" />
              </div>
              {(!isCollapsed || isOpen) && (
                <span className="font-semibold text-xs whitespace-nowrap flex-1 text-left">
                  Panel Ejecutivo
                </span>
              )}
              {(!isCollapsed || isOpen) && (
                !hasModule("module:panel_ejecutivo") ? (
                  <Lock size={14} className="text-muted-foreground ml-auto shrink-0" />
                ) : (
                  <ChevronDown size={14} className={cn("transition-transform shrink-0", isPanelEjecutivoOpen && "rotate-180")} />
                )
              )}
            </div>

            {isPanelEjecutivoOpen && (!isCollapsed || isOpen) && hasModule("module:panel_ejecutivo") && (
              <div className="pl-9 pr-2 py-1 space-y-1 animate-in fade-in slide-in-from-top-1 duration-200">
                {panelEjecutivoItems.map((sub) => {
                  const subActive = isSubActive(sub.path);
                  const SubIcon = sub.icon;
                  return (
                    <Link
                      key={sub.path}
                      to={sub.path}
                      className={cn(
                        "flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-xs font-medium transition-colors",
                        subActive
                          ? "bg-primary/15 text-primary font-bold"
                          : "text-muted-foreground hover:text-foreground hover:bg-secondary/60"
                      )}
                    >
                      <SubIcon size={14} className={subActive ? "text-primary" : "text-muted-foreground"} />
                      <span className="truncate">{sub.label}</span>
                    </Link>
                  );
                })}
              </div>
            )}
          </div>

          {/* Panel de Actividades */}
          <div className="pt-0.5 pb-0.5">
            <div
              onClick={() => {
                if (!hasModule("module:panel_de_actividades")) {
                  handleModuleClick("module:panel_de_actividades", "Panel de Actividades", () => {});
                  return;
                }
                setIsPanelActividadesOpen(!isPanelActividadesOpen);
              }}
              className={cn(
                "flex items-center gap-3 px-3 h-11 rounded-xl transition-all duration-200 group relative overflow-hidden cursor-pointer",
                !hasModule("module:panel_de_actividades") && "opacity-50 cursor-not-allowed",
                isPanelActividadesOpen
                  ? "bg-purple-600/10 text-purple-500 font-semibold"
                  : "hover:bg-purple-600/10 text-muted-foreground hover:text-purple-500"
              )}
            >
              <div className="relative shrink-0 w-8 flex justify-center">
                <Users size={19} className="text-purple-500" />
              </div>
              {(!isCollapsed || isOpen) && (
                <span className="font-semibold text-xs whitespace-nowrap flex-1 text-left">
                  Panel de Actividades
                </span>
              )}
              {(!isCollapsed || isOpen) && (
                !hasModule("module:panel_de_actividades") ? (
                  <Lock size={14} className="text-muted-foreground ml-auto shrink-0" />
                ) : (
                  <ChevronDown size={14} className={cn("transition-transform shrink-0", isPanelActividadesOpen && "rotate-180")} />
                )
              )}
            </div>

            {isPanelActividadesOpen && (!isCollapsed || isOpen) && hasModule("module:panel_de_actividades") && (
              <div className="pl-9 pr-2 py-1 space-y-1 animate-in fade-in slide-in-from-top-1 duration-200">
                {panelActividadesItems.map((sub) => {
                  const subActive = isSubActive(sub.path);
                  const SubIcon = sub.icon;
                  return (
                    <Link
                      key={sub.path}
                      to={sub.path}
                      className={cn(
                        "flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-xs font-medium transition-colors",
                        subActive
                          ? "bg-primary/15 text-primary font-bold"
                          : "text-muted-foreground hover:text-foreground hover:bg-secondary/60"
                      )}
                    >
                      <SubIcon size={14} className={subActive ? "text-primary" : "text-muted-foreground"} />
                      <span className="truncate">{sub.label}</span>
                    </Link>
                  );
                })}
              </div>
            )}
          </div>
        </nav>
      </aside>
    </>
  );
}

export default Sidebar;
