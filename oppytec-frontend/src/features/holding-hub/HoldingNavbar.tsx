import { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Bell,
  Command,
  Globe2,
  LogOut,
  Moon,
  RefreshCw,
  Sun,
  User,
  Waves,
} from "lucide-react";
import { useAuth } from "@/shared/auth/usePermissions";
import { CurrencySelector } from "@/shared/currency";
import { useTheme } from "@/shared/hooks";
import { translateKey } from "@/shared/i18n";
import type { HoldingHubSummary } from "./types";

export interface HoldingNavbarProps {
  readonly holdingData: HoldingHubSummary;
  readonly refreshing: boolean;
  readonly onRefresh: () => void;
  readonly onOpenCommandPalette: () => void;
  readonly theme?: "light" | "dark" | "ocean-blue";
  readonly onToggleTheme?: () => void;
}

export function HoldingNavbar({
  holdingData,
  refreshing,
  onRefresh,
  onOpenCommandPalette,
  theme: propTheme,
  onToggleTheme: propToggleTheme,
}: HoldingNavbarProps) {
  const navigate = useNavigate();
  const { user, signOut } = useAuth();
  const hookTheme = useTheme();
  const theme = propTheme ?? hookTheme.theme;
  const toggleTheme = propToggleTheme ?? hookTheme.toggleTheme;
  const [showUserMenu, setShowUserMenu] = useState(false);
  const [showNotifications, setShowNotifications] = useState(false);

  const displayName = user
    ? `${user.firstName || user.username} ${user.lastName || ""}`.trim()
    : translateKey("holding_hub", "navbar.role_owner");

  return (
    <header
      data-testid="holding-navbar"
      className="sticky top-0 z-40 flex h-20 min-h-[80px] w-full items-center justify-between border-b border-border/70 bg-card/85 px-4 md:px-8 backdrop-blur-xl shadow-sm transition-colors"
    >
      {/* Left: Branding & Holding Identity */}
      <div className="flex items-center gap-4 md:gap-6">
        <button
          type="button"
          onClick={() => navigate("/")}
          title={translateKey("holding_hub", "navbar.back_to_app")}
          className="group flex items-center gap-3 text-left focus:outline-none"
        >
          <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-gradient-to-br from-primary to-emerald-600 text-primary-foreground shadow-lg shadow-primary/25 transition-transform group-hover:scale-105">
            <span className="font-extrabold text-xl tracking-tighter">O</span>
          </div>
          <div className="hidden sm:block">
            <div className="flex items-center gap-2">
              <span className="font-bold text-base tracking-tight text-foreground">
                {translateKey("holding_hub", "navbar.title")}
              </span>
              <span
                data-testid="holding-enterprise-badge"
                className="rounded-full border border-primary/40 bg-primary/10 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-primary shadow-xs"
              >
                {translateKey("holding_hub", "navbar.enterprise_badge")}
              </span>
            </div>
            <p className="text-xs text-muted-foreground truncate max-w-[220px]">
              {holdingData.name}
            </p>
          </div>
        </button>
      </div>

      {/* Center: Quick Command Palette Trigger */}
      <div className="hidden lg:flex items-center">
        <button
          type="button"
          onClick={onOpenCommandPalette}
          data-testid="holding-search-trigger"
          className="flex h-10 w-80 items-center justify-between rounded-xl border border-border/80 bg-background/50 px-3.5 text-sm text-muted-foreground transition hover:border-primary/50 hover:bg-background/80 shadow-xs"
        >
          <span className="truncate">{translateKey("holding_hub", "navbar.search_placeholder")}</span>
          <kbd className="inline-flex items-center gap-1 rounded border border-border bg-muted/60 px-2 py-0.5 font-mono text-[11px] font-semibold text-foreground">
            <Command className="h-3 w-3" />
            <span>K</span>
          </kbd>
        </button>
      </div>

      {/* Right: Actions, Currency, Theme, Notifications & User */}
      <div className="flex items-center gap-2 md:gap-3">
        {/* Mobile Command Palette Button */}
        <button
          type="button"
          onClick={onOpenCommandPalette}
          aria-label={translateKey("holding_hub", "navbar.search_placeholder")}
          className="lg:hidden flex h-10 w-10 items-center justify-center rounded-xl border border-border/70 bg-card/60 text-muted-foreground hover:text-foreground"
        >
          <Command className="h-4 w-4" />
        </button>

        {/* Multi-Currency FX Selector */}
        <div data-testid="holding-currency-selector" className="hidden sm:block">
          <CurrencySelector className="border border-border/70 bg-background/40" />
        </div>

        {/* Data Refresh Button */}
        <button
          type="button"
          data-testid="holding-refresh-btn"
          onClick={onRefresh}
          disabled={refreshing}
          title={translateKey("holding_hub", "navbar.refresh")}
          aria-label={translateKey("holding_hub", "navbar.refresh")}
          className="flex h-10 w-10 items-center justify-center rounded-xl border border-border/70 bg-card/60 text-muted-foreground transition hover:bg-muted/70 hover:text-foreground disabled:opacity-50"
        >
          <RefreshCw
            className={`h-4 w-4 ${refreshing ? "animate-spin text-primary" : ""}`}
            aria-hidden="true"
          />
        </button>

        {/* Theme Switcher Toggle */}
        <button
          type="button"
          data-testid="holding-theme-toggle"
          onClick={toggleTheme}
          title={translateKey("holding_hub", "navbar.theme_toggle")}
          aria-label={translateKey("holding_hub", "navbar.theme_toggle")}
          className="flex h-10 w-10 items-center justify-center rounded-xl border border-border/70 bg-card/60 text-muted-foreground transition hover:bg-muted/70 hover:text-foreground"
        >
          {theme === "ocean-blue" ? (
            <Waves className="h-4 w-4 text-cyan-400" />
          ) : theme === "dark" ? (
            <Moon className="h-4 w-4 text-indigo-400" />
          ) : (
            <Sun className="h-4 w-4 text-amber-500" />
          )}
        </button>

        {/* Notifications Popover Trigger */}
        <div className="relative">
          <button
            type="button"
            data-testid="holding-notifications-btn"
            onClick={() => setShowNotifications((prev) => !prev)}
            aria-label={translateKey("holding_hub", "navbar.notifications")}
            className="relative flex h-10 w-10 items-center justify-center rounded-xl border border-border/70 bg-card/60 text-muted-foreground transition hover:bg-muted/70 hover:text-foreground"
          >
            <Bell className="h-4 w-4" />
            <span className="absolute top-2 right-2 flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
              <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-500" />
            </span>
          </button>

          {showNotifications && (
            <div
              data-testid="holding-notifications-dropdown"
              className="absolute right-0 mt-2 w-80 rounded-2xl border border-border bg-card/95 p-4 shadow-xl backdrop-blur-xl animate-in fade-in zoom-in-95 duration-150 z-50"
            >
              <div className="flex items-center justify-between border-b border-border/60 pb-3">
                <span className="font-semibold text-sm">
                  {translateKey("holding_hub", "navbar.notifications")}
                </span>
                <span className="text-[11px] font-mono text-emerald-500 bg-emerald-500/10 px-2 py-0.5 rounded-full">
                  {holdingData.safety_status}
                </span>
              </div>
              <div className="py-3 text-xs text-muted-foreground space-y-2">
                <div className="rounded-lg bg-muted/40 p-2.5">
                  <p className="font-medium text-foreground">
                    {translateKey("holding_hub", "navbar.notification_quota_title", {
                      pct: holdingData.usage_pct,
                    })}
                  </p>
                  <p className="text-[11px] text-muted-foreground mt-0.5">
                    {translateKey("holding_hub", "navbar.notification_quota_desc", {
                      credits: holdingData.credit_balance.toLocaleString(),
                    })}
                  </p>
                </div>
                <div className="rounded-lg bg-muted/40 p-2.5">
                  <p className="font-medium text-foreground">
                    {translateKey("holding_hub", "navbar.notification_all_branches_ok", {
                      count: holdingData.tenants.length,
                    })}
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* User Profile Dropdown */}
        <div className="relative">
          <button
            type="button"
            data-testid="holding-user-menu-btn"
            onClick={() => setShowUserMenu((prev) => !prev)}
            aria-label={translateKey("holding_hub", "navbar.user_menu")}
            className="flex items-center gap-2.5 rounded-xl border border-border/70 bg-card/60 p-1.5 pr-3 text-left transition hover:bg-muted/70 focus:outline-none"
          >
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/20 text-primary font-bold text-xs uppercase">
              {displayName.charAt(0) || "D"}
            </div>
            <div className="hidden md:block">
              <p className="text-xs font-semibold leading-tight text-foreground truncate max-w-[120px]">
                {displayName}
              </p>
              <p className="text-[10px] text-muted-foreground font-medium">
                {translateKey("holding_hub", "navbar.role_owner")}
              </p>
            </div>
          </button>

          {showUserMenu && (
            <div
              data-testid="holding-user-dropdown"
              className="absolute right-0 mt-2 w-56 rounded-2xl border border-border bg-card/95 p-2 shadow-xl backdrop-blur-xl animate-in fade-in zoom-in-95 duration-150 z-50"
            >
              <div className="px-3 py-2 border-b border-border/60">
                <p className="text-sm font-semibold text-foreground truncate">{displayName}</p>
                <p className="text-xs text-muted-foreground font-mono truncate">
                  {user?.email || "director@oppytec.cl"}
                </p>
              </div>

              <div className="py-1">
                <button
                  type="button"
                  data-testid="holding-back-to-app-btn"
                  onClick={() => {
                    setShowUserMenu(false);
                    navigate("/");
                  }}
                  className="flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-xs font-medium text-foreground hover:bg-muted/70 transition"
                >
                  <Globe2 className="h-4 w-4 text-primary" />
                  <span>{translateKey("holding_hub", "navbar.back_to_app")}</span>
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setShowUserMenu(false);
                    navigate("/perfil");
                  }}
                  className="flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-xs font-medium text-foreground hover:bg-muted/70 transition"
                >
                  <User className="h-4 w-4 text-muted-foreground" />
                  <span>{translateKey("profile", "title")}</span>
                </button>
              </div>

              <div className="border-t border-border/60 pt-1">
                <button
                  type="button"
                  data-testid="holding-logout-btn"
                  onClick={async () => {
                    setShowUserMenu(false);
                    await signOut();
                    navigate("/login");
                  }}
                  className="flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-xs font-medium text-destructive hover:bg-destructive/10 transition"
                >
                  <LogOut className="h-4 w-4" />
                  <span>{translateKey("holding_hub", "navbar.logout")}</span>
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
