import {
  Activity,
  Blocks,
  Briefcase,
  Building,
  Building2,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  Coins,
  Layers,
  LayoutDashboard,
  type LucideIcon,
  Settings,
  Shield,
  Store,
  Tags,
  Users,
  UsersRound,
  X,
} from "lucide-react";
import { AnimatePresence, motion } from "framer-motion";
import { type CSSProperties, useEffect, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useTheme } from "@/shared/hooks";
import { translateKey, useLanguage } from "@/shared/i18n";

export interface MenuItem {
  readonly path: string;
  readonly label: string;
  readonly icon: LucideIcon;
  readonly exact?: boolean;
  readonly color: string;
  readonly rgb: string;
}

export const ADMIN_DIRECT_MENU_ITEMS = [
  {
    path: "/admin",
    label: "Panel Principal",
    icon: LayoutDashboard,
    exact: true,
    color: "#6366f1",
    rgb: "99,102,241",
  },
  {
    path: "/admin/users",
    label: "Usuarios Globales",
    icon: Users,
    exact: false,
    color: "#ec4899",
    rgb: "236,72,153",
  },
] as const;

export const GESTION_NEGOCIO_ITEMS = [
  {
    path: "/admin/business-types",
    label: "Tipos de Negocio",
    icon: Tags,
    color: "#f97316",
    rgb: "249,115,22",
  },
  {
    path: "/admin/modules",
    label: "Módulos (SaaS)",
    icon: Blocks,
    color: "#eab308",
    rgb: "234,179,8",
  },
  {
    path: "/admin/plans",
    label: "Planes (SaaS)",
    icon: Layers,
    color: "#8b5cf6",
    rgb: "139,92,246",
  },
  {
    path: "/admin/token-consumption",
    label: "Consumo Tokens Cliente",
    icon: Coins,
    color: "#10b981",
    rgb: "16,185,129",
  },
] as const;

export const GESTION_CLIENTE_ITEMS = [
  {
    path: "/admin/holdings",
    label: "Grupos (Holdings)",
    icon: Building,
    color: "#3b82f6",
    rgb: "59,130,246",
  },
  {
    path: "/admin/legal-entities",
    label: "Entidades Legales",
    icon: Building2,
    color: "#a855f7",
    rgb: "168,85,247",
  },
  {
    path: "/admin/tenants",
    label: "Inquilinos (Tenants)",
    icon: Store,
    color: "#10b981",
    rgb: "16,185,129",
  },
  {
    path: "/admin/client-users",
    label: "Usuarios Clientes",
    icon: Users,
    color: "#0ea5e9",
    rgb: "14,165,233",
  },
] as const;

export const PLATAFORMA_TELEMETRIA_ITEMS = [
  {
    path: "/admin/observability",
    label: "Observabilidad 4-Pilares",
    icon: Activity,
    color: "#06b6d4",
    rgb: "6,182,212",
  },
  {
    path: "/admin/fx-rates",
    label: "Tasas FX Centrales",
    icon: Coins,
    color: "#14b8a6",
    rgb: "20,184,166",
  },
  {
    path: "/admin/backups",
    label: "Bóveda de Respaldos",
    icon: Shield,
    color: "#6366f1",
    rgb: "99,102,241",
  },
] as const;

export interface AdminSidebarProps {
  readonly isOpen?: boolean;
  readonly onClose?: () => void;
  readonly isCollapsed?: boolean;
  readonly onCollapseChange?: (collapsed: boolean) => void;
}

export function AdminSidebar({
  isOpen = false,
  onClose,
  isCollapsed: controlledIsCollapsed,
  onCollapseChange,
}: AdminSidebarProps) {
  useLanguage();
  const [localIsCollapsed, setLocalIsCollapsed] = useState<boolean>(false);
  const isCollapsed = controlledIsCollapsed !== undefined ? controlledIsCollapsed : localIsCollapsed;

  const setIsCollapsed = (val: boolean | ((prev: boolean) => boolean)) => {
    const nextVal = typeof val === "function" ? val(isCollapsed) : val;
    if (onCollapseChange) {
      onCollapseChange(nextVal);
    } else {
      setLocalIsCollapsed(nextVal);
    }
  };

  const [isTransitioning, setIsTransitioning] = useState<boolean>(false);

  useEffect(() => {
    setIsTransitioning(true);
    const timer = setTimeout(() => {
      setIsTransitioning(false);
    }, 300);
    return () => clearTimeout(timer);
  }, [isCollapsed]);

  const location = useLocation();
  const navigate = useNavigate();
  const { theme } = useTheme("ocean-blue");

  const [isGestionNegocioOpen, setIsGestionNegocioOpen] = useState<boolean>(true);
  const [isGestionClienteOpen, setIsGestionClienteOpen] = useState<boolean>(true);
  const [isPlataformaOpen, setIsPlataformaOpen] = useState<boolean>(false);

  const directMenuItems = [
    {
      ...ADMIN_DIRECT_MENU_ITEMS[0],
      label: translateKey("platform_admin", "sidebar.menu_dashboard"),
    },
    {
      ...ADMIN_DIRECT_MENU_ITEMS[1],
      label: translateKey("platform_admin", "sidebar.menu_global_users"),
    },
  ];

  const gestionNegocioItems = [
    {
      ...GESTION_NEGOCIO_ITEMS[0],
      label: translateKey("platform_admin", "sidebar.menu_business_types"),
    },
    {
      ...GESTION_NEGOCIO_ITEMS[1],
      label: translateKey("platform_admin", "sidebar.menu_modules"),
    },
    {
      ...GESTION_NEGOCIO_ITEMS[2],
      label: translateKey("platform_admin", "sidebar.menu_plans"),
    },
    {
      ...GESTION_NEGOCIO_ITEMS[3],
      label: translateKey("platform_admin", "sidebar.menu_token_consumption"),
    },
  ];

  const gestionClienteItems = [
    {
      ...GESTION_CLIENTE_ITEMS[0],
      label: translateKey("platform_admin", "sidebar.menu_holdings"),
    },
    {
      ...GESTION_CLIENTE_ITEMS[1],
      label: translateKey("platform_admin", "sidebar.menu_legal_entities"),
    },
    {
      ...GESTION_CLIENTE_ITEMS[2],
      label: translateKey("platform_admin", "sidebar.menu_tenants"),
    },
    {
      ...GESTION_CLIENTE_ITEMS[3],
      label: translateKey("platform_admin", "sidebar.menu_client_users"),
    },
  ];

  const plataformaItems = [
    {
      ...PLATAFORMA_TELEMETRIA_ITEMS[0],
      label: translateKey("platform_admin", "sidebar.menu_observability"),
    },
    {
      ...PLATAFORMA_TELEMETRIA_ITEMS[1],
      label: translateKey("platform_admin", "sidebar.menu_fx_rates"),
    },
    {
      ...PLATAFORMA_TELEMETRIA_ITEMS[2],
      label: translateKey("platform_admin", "sidebar.menu_backups"),
    },
  ];

  const isSubItemActive = (itemPath: string): boolean => {
    return location.pathname.startsWith(itemPath);
  };

  useEffect(() => {
    if (GESTION_NEGOCIO_ITEMS.some((item) => location.pathname.startsWith(item.path))) {
      setIsGestionNegocioOpen(true);
    }
    if (GESTION_CLIENTE_ITEMS.some((item) => location.pathname.startsWith(item.path))) {
      setIsGestionClienteOpen(true);
    }
    if (PLATAFORMA_TELEMETRIA_ITEMS.some((item) => location.pathname.startsWith(item.path))) {
      setIsPlataformaOpen(true);
    }
  }, [location.pathname]);

  // Close mobile drawer on route change
  useEffect(() => {
    if (onClose) {
      onClose();
    }
  }, [location.pathname, onClose]);

  const renderDropdownSection = (
    label: string,
    Icon: LucideIcon,
    isOpenState: boolean,
    toggleFunc: () => void,
    items: readonly MenuItem[],
    color: string,
    rgb: string,
    fallbackPath: string
  ) => {
    const isAnySubActive = items.some((sub) => isSubItemActive(sub.path));
    const customStyle = {
      "--item-color": color,
      "--item-rgb": rgb,
    } as CSSProperties;

    return (
      <div className="pt-1">
        <div
          style={customStyle}
          className={`flex items-center gap-4 px-3 h-11 rounded-xl transition-all duration-200 group relative overflow-hidden cursor-pointer ${
            isAnySubActive
              ? "bg-[var(--item-color)] text-white shadow-md shadow-[rgba(var(--item-rgb),0.3)]"
              : theme === "light"
                ? "hover:bg-[rgba(var(--item-rgb),0.10)] text-black hover:text-[var(--item-color)]"
                : "hover:bg-[rgba(var(--item-rgb),0.10)] text-muted-foreground hover:text-[var(--item-color)]"
          }`}
          tabIndex={0}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === " ") {
              e.preventDefault();
              if (!isCollapsed || isOpen) {
                toggleFunc();
              } else {
                navigate(fallbackPath);
              }
            }
          }}
          onClick={(e) => {
            e.preventDefault();
            if (!isCollapsed || isOpen) {
              toggleFunc();
            } else {
              navigate(fallbackPath);
            }
          }}
        >
          <div
            title={isCollapsed && !isOpen ? label : undefined}
            className="flex items-center gap-4 flex-1 outline-none select-none"
          >
            <div className="relative shrink-0 w-8 flex justify-center">
              <Icon
                size={20}
                className={`shrink-0 transition-colors ${
                  isAnySubActive ? "text-white" : "text-[var(--item-color)]"
                }`}
              />
            </div>
            <span
              className={`font-medium text-sm whitespace-nowrap flex-1 text-left transition-all duration-300 ease-in-out overflow-hidden ${
                !isCollapsed || isOpen
                  ? "opacity-100 max-w-[200px] translate-x-0"
                  : "opacity-0 max-w-0 pointer-events-none select-none -translate-x-2"
              }`}
            >
              {label}
            </span>
          </div>

          <button
            type="button"
            tabIndex={-1}
            onClick={(e) => {
              e.stopPropagation();
              toggleFunc();
            }}
            aria-label={`Toggle ${label}`}
            className={`rounded shrink-0 transition-all duration-300 ease-in-out overflow-hidden flex items-center justify-center ${
              isAnySubActive
                ? "hover:bg-white/20 text-white"
                : theme === "light"
                  ? "hover:bg-black/5 text-zinc-700 hover:text-[var(--item-color)]"
                  : "hover:bg-white/10 text-zinc-400 hover:text-[var(--item-color)]"
            } ${
              !isCollapsed || isOpen
                ? "opacity-100 p-1 w-6 ml-0"
                : "opacity-0 p-0 w-0 border-none ml-0"
            }`}
          >
            <ChevronDown
              size={16}
              className={`transition-transform duration-200 ${
                isOpenState ? "rotate-180" : ""
              }`}
            />
          </button>

          {isAnySubActive && (
            <motion.div
              layoutId="active-admin-pill"
              className="absolute left-0 w-1 h-5 bg-white rounded-r-full"
            />
          )}
        </div>

        <AnimatePresence>
          {isOpenState && (!isCollapsed || isOpen) && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.2, ease: "easeInOut" }}
              className="overflow-hidden"
            >
              <div className="pt-1 pb-1 space-y-1 relative before:absolute before:left-[1.375rem] before:top-0 before:bottom-0 before:w-px before:bg-border/50">
                {items.map((subItem) => {
                  const subIsActive = isSubItemActive(subItem.path);
                  const subStyle = {
                    "--sub-color": subItem.color,
                    "--sub-rgb": subItem.rgb,
                  } as CSSProperties;
                  const SubIcon = subItem.icon;

                  return (
                    <Link
                      key={subItem.path}
                      to={subItem.path}
                      style={subStyle}
                      className={`flex items-center gap-3 pl-11 pr-3 py-2 text-sm transition-all duration-200 group relative ${
                        subIsActive
                          ? "text-[var(--sub-color)] font-medium"
                          : "text-muted-foreground hover:text-[var(--sub-color)] hover:bg-[rgba(var(--sub-rgb),0.05)] rounded-r-xl"
                      }`}
                    >
                      {subIsActive && (
                        <div className="absolute left-[1.375rem] w-[2px] h-[calc(100%-8px)] bg-[var(--sub-color)] rounded-full -translate-x-1/2" />
                      )}
                      <SubIcon
                        size={16}
                        className={`shrink-0 transition-colors ${
                          subIsActive
                            ? "text-[var(--sub-color)]"
                            : "text-muted-foreground group-hover:text-[var(--sub-color)]"
                        }`}
                      />
                      <span className="truncate">{subItem.label}</span>
                    </Link>
                  );
                })}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    );
  };

  return (
    <div
      data-testid="admin-sidebar"
      className={`flex flex-col h-full bg-background relative border-r border-border group group/sidebar ${
        isTransitioning ? "pointer-events-none" : ""
      }`}
    >
      {/* Brand Header */}
      <div
        className={`relative flex items-center flex-none h-20 border-b border-border px-4 transition-all duration-300 bg-background group/header touch-none overflow-hidden z-20 ${
          isCollapsed ? "cursor-pointer" : ""
        }`}
        onClick={() => {
          if (isCollapsed) setIsCollapsed(false);
        }}
      >
        {/* Toggle Button */}
        <motion.button
          onClick={(e) => {
            e.stopPropagation();
            setIsCollapsed(!isCollapsed);
          }}
          initial={false}
          animate={{
            right: isCollapsed && !isOpen ? 16 : 12,
            width: isCollapsed && !isOpen ? 48 : 32,
            height: isCollapsed && !isOpen ? 48 : 32,
            borderRadius: isCollapsed && !isOpen ? "1rem" : "0.5rem",
          }}
          transition={{ duration: 0.3, ease: "easeInOut" }}
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          className={`absolute inset-y-0 my-auto hidden md:flex items-center justify-center z-50 cursor-pointer shadow-sm backdrop-blur-sm border transition-[opacity,background-color,border-color,color] duration-200 opacity-0 group-hover:opacity-100 group-hover/sidebar:opacity-100 group-hover/header:opacity-100 ${
            isCollapsed && !isOpen
              ? "bg-primary/10 border-primary/20 text-primary hover:bg-primary/20"
              : "bg-secondary/90 border-border text-muted-foreground hover:text-primary hover:bg-primary/10 hover:border-primary/20"
          }`}
          title={isCollapsed ? translateKey("platform_admin", "sidebar.expand_sidebar") : translateKey("platform_admin", "sidebar.collapse_sidebar")}
          aria-label={isCollapsed ? translateKey("platform_admin", "sidebar.expand_sidebar") : translateKey("platform_admin", "sidebar.collapse_sidebar")}
        >
          {isCollapsed ? <ChevronRight size={20} /> : <ChevronLeft size={18} />}
        </motion.button>

        <div className="flex items-center gap-4 flex-1 overflow-hidden">
          <div
            className={`h-12 w-12 rounded-2xl bg-primary/10 flex items-center justify-center border border-primary/20 shrink-0 shadow-sm relative transition-opacity duration-200 ${
              isCollapsed && !isOpen
                ? "group-hover:opacity-0 group-hover/sidebar:opacity-0 group-hover/header:opacity-0"
                : ""
            }`}
          >
            <Shield className="h-6 w-6 text-primary" />
          </div>
          <div
            className={`flex flex-col justify-center min-w-0 h-full transition-all duration-300 ease-in-out overflow-hidden ${
              !isCollapsed || isOpen
                ? "opacity-100 max-w-[200px] translate-x-0"
                : "opacity-0 max-w-0 pointer-events-none select-none -translate-x-4"
            }`}
          >
            <span className="text-[10px] font-bold text-primary uppercase tracking-widest leading-none mb-1">
              OppyTec
            </span>
            <span className="font-bold text-sm uppercase whitespace-nowrap text-foreground tracking-tight">
              {translateKey("platform_admin", "sidebar.brand_panel")}
            </span>
          </div>
        </div>

        {onClose && (
          <button
            type="button"
            onClick={onClose}
            aria-label={translateKey("platform_admin", "sidebar.close_sidebar")}
            className="md:hidden absolute right-4 h-8 w-8 rounded-lg flex items-center justify-center border border-border"
          >
            <X size={16} />
          </button>
        )}
      </div>

      {/* Navigation Menu */}
      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        {directMenuItems.map((item) => {
          const isActive = item.exact
            ? location.pathname === item.path
            : location.pathname.startsWith(item.path);
          const itemStyle = {
            "--item-color": item.color,
            "--item-rgb": item.rgb,
          } as CSSProperties;
          const ItemIcon = item.icon;

          return (
            <Link
              key={item.path}
              to={item.path}
              style={itemStyle}
              title={isCollapsed && !isOpen ? item.label : undefined}
              className={`flex items-center gap-4 px-3 h-11 rounded-xl transition-all duration-200 group relative ${
                isActive
                  ? "bg-[var(--item-color)] text-white shadow-md shadow-[rgba(var(--item-rgb),0.3)]"
                  : "hover:bg-[rgba(var(--item-rgb),0.1)] text-muted-foreground hover:text-[var(--item-color)]"
              }`}
            >
              <div className="relative shrink-0 w-8 flex justify-center">
                <ItemIcon
                  size={20}
                  className={`transition-colors ${
                    isActive ? "text-white" : "text-[var(--item-color)]"
                  }`}
                />
              </div>
              <span
                className={`font-medium text-sm whitespace-nowrap transition-all duration-300 ease-in-out overflow-hidden ${
                  !isCollapsed || isOpen
                    ? "opacity-100 max-w-full"
                    : "opacity-0 max-w-0 pointer-events-none select-none"
                }`}
              >
                {item.label}
              </span>
              {isActive && (
                <motion.div
                  layoutId="active-admin-pill"
                  className="absolute left-0 w-1 h-5 bg-white rounded-r-full"
                />
              )}
            </Link>
          );
        })}

        {renderDropdownSection(
          translateKey("platform_admin", "sidebar.section_business"),
          Briefcase,
          isGestionNegocioOpen,
          () => setIsGestionNegocioOpen((prev) => !prev),
          gestionNegocioItems,
          "#eab308",
          "234,179,8",
          "/admin/business-types"
        )}

        {renderDropdownSection(
          translateKey("platform_admin", "sidebar.section_client"),
          UsersRound,
          isGestionClienteOpen,
          () => setIsGestionClienteOpen((prev) => !prev),
          gestionClienteItems,
          "#0ea5e9",
          "14,165,233",
          "/admin/holdings"
        )}

        {renderDropdownSection(
          translateKey("platform_admin", "sidebar.section_platform"),
          Activity,
          isPlataformaOpen,
          () => setIsPlataformaOpen((prev) => !prev),
          plataformaItems,
          "#06b6d4",
          "6,182,212",
          "/admin/observability"
        )}
      </nav>

      {/* Footer Settings Button */}
      <div className="p-4 border-t border-border">
        <button
          type="button"
          onClick={() => navigate("/admin/observability")}
          className={`flex items-center justify-center gap-2 w-full h-10 rounded-lg bg-secondary text-secondary-foreground hover:bg-secondary/80 transition-colors ${
            isCollapsed && !isOpen ? "px-0" : "px-4"
          }`}
          title={translateKey("platform_admin", "sidebar.settings_title")}
        >
          <Settings size={16} />
          {(!isCollapsed || isOpen) && (
            <span className="text-sm font-medium">{translateKey("platform_admin", "sidebar.settings_label")}</span>
          )}
        </button>
      </div>
    </div>
  );
}
