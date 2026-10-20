import {
  Bell,
  LogOut,
  Moon,
  ShieldAlert,
  Sun,
  UserCircle,
  Waves,
} from "lucide-react";
import { useEffect, useState } from "react";
import { Outlet, useNavigate } from "react-router-dom";
import { apiRequest } from "@/shared/api/httpClient";
import { useAuth } from "@/shared/auth/usePermissions";
import { CurrencySelector } from "@/shared/currency";
import { useSwipeNavigation, useTheme } from "@/shared/hooks";
import { LanguageFlagSelector } from "@/shared/i18n";
import { AdminSidebar } from "./AdminSidebar";

export interface TenantOptionItem {
  readonly schema_name: string;
  readonly display_name: string;
}

export function AdminTenantSwitcher() {
  const [tenants, setTenants] = useState<readonly TenantOptionItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [selectedTenant, setSelectedTenant] = useState<string>(() => {
    try {
      return localStorage.getItem("admin_impersonate_tenant") || "global";
    } catch {
      return "global";
    }
  });

  useEffect(() => {
    let isMounted = true;
    apiRequest<TenantOptionItem[]>("/tenancy/tenants")
      .then((res) => {
        if (isMounted) {
          setTenants(Array.isArray(res.data) ? res.data : []);
          setLoading(false);
        }
      })
      .catch(() => {
        if (isMounted) {
          setTenants([]);
          setLoading(false);
        }
      });
    return () => {
      isMounted = false;
    };
  }, []);

  const handleSwitch = (val: string) => {
    setSelectedTenant(val);
    try {
      if (val === "global") {
        localStorage.removeItem("admin_impersonate_tenant");
      } else {
        localStorage.setItem("admin_impersonate_tenant", val);
      }
    } catch {
      // Ignora storage no disponible
    }
  };

  return (
    <select
      aria-label="Seleccionar Entorno Tenant"
      value={selectedTenant}
      disabled={loading}
      onChange={(e) => handleSwitch(e.target.value)}
      className="h-9 w-[180px] sm:w-[210px] rounded-lg border border-border bg-background px-2.5 text-xs font-semibold text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
    >
      <option value="global" className="font-bold text-primary">
        Modo Global (SaaS)
      </option>
      {tenants.map((t) => (
        <option key={t.schema_name} value={t.schema_name}>
          {t.display_name || t.schema_name}
        </option>
      ))}
    </select>
  );
}

export function AdminLayout() {
  useSwipeNavigation();
  const [isSidebarOpen, setIsSidebarOpen] = useState<boolean>(false);
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState<boolean>(false);
  const { user, loading, signOut, isGlobalAdmin } = useAuth();
  const { theme, setTheme } = useTheme("ocean-blue");
  const navigate = useNavigate();

  const toggleTheme = (): void => {
    setTheme(theme === "light" ? "dark" : theme === "dark" ? "ocean-blue" : "light");
  };

  useEffect(() => {
    if (!loading && user && !isGlobalAdmin) {
      navigate("/");
    }
  }, [user, loading, isGlobalAdmin, navigate]);

  if (loading) {
    return null;
  }

  const displayName = user?.firstName
    ? `${user.firstName} ${user.lastName || ""}`.trim()
    : user?.username || user?.email || "Admin";

  return (
    <div
      data-testid="admin-layout-root"
      className="flex h-screen w-screen overflow-hidden bg-background text-foreground selection:bg-primary/20"
    >
      {/* Mobile Sidebar Overlay */}
      <div
        className={`fixed inset-0 z-[60] bg-black/60 backdrop-blur-sm transition-all duration-300 md:hidden ${
          isSidebarOpen ? "opacity-100" : "opacity-0 pointer-events-none"
        }`}
        onClick={() => setIsSidebarOpen(false)}
      />

      {/* Responsive Collapsible Aside */}
      <aside
        className={`fixed inset-y-0 left-0 z-[70] group group/sidebar transition-all duration-300 ease-in-out md:static md:z-auto shrink-0 ${
          isSidebarCollapsed ? "w-20" : "w-[280px]"
        } ${isSidebarOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0"}`}
      >
        <AdminSidebar
          isOpen={isSidebarOpen}
          onClose={() => setIsSidebarOpen(false)}
          isCollapsed={isSidebarCollapsed}
          onCollapseChange={setIsSidebarCollapsed}
        />
      </aside>

      {/* Main Content Area */}
      <div className="flex flex-1 flex-col min-w-0 overflow-hidden relative">
        <header className="h-20 flex items-center justify-between px-4 sm:px-6 border-b border-border bg-background/95 backdrop-blur-sm z-40 shrink-0">
          <div className="flex items-center gap-3 sm:gap-4">
            <button
              type="button"
              onClick={() => setIsSidebarOpen(true)}
              aria-label="Abrir menú"
              className="md:hidden flex h-10 w-10 items-center justify-center rounded-lg border border-border bg-background hover:bg-secondary transition-colors"
            >
              <div className="space-y-1.5 w-5">
                <div className="h-0.5 w-full bg-foreground rounded-full" />
                <div className="h-0.5 w-4/5 bg-foreground rounded-full" />
                <div className="h-0.5 w-full bg-foreground rounded-full" />
              </div>
            </button>

            <h1 className="text-base sm:text-lg font-semibold flex items-center gap-2">
              <ShieldAlert className="w-5 h-5 text-primary shrink-0" />
              <span className="truncate">Administración Global</span>
            </h1>
          </div>

          <div className="flex items-center gap-2 sm:gap-3">
            {/* Tenant Switcher */}
            <div className="flex items-center gap-2">
              <span className="text-xs text-muted-foreground hidden lg:block">
                Entorno:
              </span>
              <AdminTenantSwitcher />
            </div>

            <div className="h-6 w-px bg-border hidden sm:block" />

            {/* Selector de Moneda */}
            <CurrencySelector />

            {/* Selector de Idioma con Bandera SVG */}
            <LanguageFlagSelector />

            {/* Selector de los 3 Temas Legacy */}
            <button
              type="button"
              onClick={toggleTheme}
              className="h-9 w-9 rounded-lg flex items-center justify-center transition-colors shrink-0 cursor-pointer border border-border/50 hover:bg-secondary text-muted-foreground hover:text-foreground"
              title={
                theme === "light"
                  ? "Modo Oscuro"
                  : theme === "dark"
                    ? "Ocean Blue"
                    : "Modo Claro"
              }
              aria-label="Alternar tema visual"
            >
              {theme === "light" && <Sun className="w-4 h-4 text-foreground" />}
              {theme === "dark" && <Moon className="w-4 h-4" />}
              {theme === "ocean-blue" && (
                <Waves className="w-4 h-4 text-sky-400" />
              )}
            </button>

            {/* Campanita de Notificaciones */}
            <button
              type="button"
              className="h-9 w-9 rounded-lg flex items-center justify-center relative transition-colors cursor-pointer border border-border/50 hover:bg-secondary text-muted-foreground hover:text-foreground"
              title="Notificaciones de Sistema"
              aria-label="Notificaciones de Sistema"
            >
              <Bell className="w-4 h-4" />
            </button>

            <div className="h-6 w-px bg-border hidden sm:block" />

            {/* User Menu */}
            <div className="flex items-center gap-2 sm:gap-3">
              <div className="hidden sm:flex items-center gap-1.5 text-xs font-semibold text-foreground">
                <UserCircle className="w-5 h-5 text-muted-foreground" />
                <span className="max-w-[140px] truncate">{displayName}</span>
              </div>

              <button
                type="button"
                className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-semibold text-muted-foreground hover:text-destructive hover:bg-destructive/10 transition-colors"
                onClick={() => void signOut()}
              >
                <LogOut className="w-4 h-4 hidden sm:block" />
                <span className="hidden sm:inline">Cerrar Sesión</span>
                <span className="sm:hidden">Salir</span>
              </button>
            </div>
          </div>
        </header>

        <main className="flex-1 overflow-y-auto overflow-x-hidden relative scroll-smooth focus:outline-none">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
