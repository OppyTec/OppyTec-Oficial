import { type ElementType } from "react";
import { Sun, Moon, Waves, Check } from "lucide-react";
import { useTheme } from "@/shared/hooks";
import { cn } from "@/shared/lib";
import { translateKey, useLanguage } from "@/shared/i18n";

interface ThemePreviewData {
  bg: string;
  sidebar: string;
  card: string;
  accent: string;
  text: string;
  subtext: string;
  border: string;
  glow?: string;
}

interface ThemeOptionItem {
  id: "light" | "dark" | "ocean-blue";
  label: string;
  description: string;
  icon: ElementType;
  preview: ThemePreviewData;
  badge?: string;
}

const THEMES: ThemeOptionItem[] = [
  {
    id: "light",
    label: "Modo Claro",
    description: "Interfaz limpia y luminosa con primario esmeralda gastronómico. Ideal para turnos diurnos.",
    icon: Sun,
    preview: {
      bg: "#f0f4ff",
      sidebar: "#ffffff",
      card: "#ffffff",
      accent: "#1a9e6e",
      text: "#0d1525",
      subtext: "#6b7280",
      border: "#e5e7eb",
    },
  },
  {
    id: "dark",
    label: "Modo Oscuro",
    description: "Fondo azul noche profundo (#0a0f1e) que descansa la vista en turnos nocturnos.",
    icon: Moon,
    preview: {
      bg: "#0a0f1e",
      sidebar: "#0d1526",
      card: "#0f1a2e",
      accent: "#2ecc8f",
      text: "#e8f0fe",
      subtext: "#7c8fb0",
      border: "#1e2d48",
    },
  },
  {
    id: "ocean-blue",
    label: "Ocean Blue",
    description: "Océano abisal con acentos neón cian (#00e5ff) y resplandor glow de alta inmersión.",
    icon: Waves,
    badge: "NUEVO",
    preview: {
      bg: "#060d1c",
      sidebar: "#080f1e",
      card: "#0a1326",
      accent: "#00e5ff",
      text: "#d4eeff",
      subtext: "#6699bb",
      border: "#0e2040",
      glow: "#00e5ff",
    },
  },
];

function MiniPreview({ p }: { readonly p: ThemePreviewData }) {
  return (
    <div
      className="w-full h-28 rounded-xl overflow-hidden border relative shadow-sm"
      style={{ backgroundColor: p.bg, borderColor: p.border }}
    >
      {/* Mini Sidebar Strip */}
      <div
        className="absolute left-0 top-0 bottom-0 w-10 flex flex-col items-center gap-1.5 pt-2"
        style={{ backgroundColor: p.sidebar, borderRight: `1px solid ${p.border}` }}
      >
        {[0, 1, 2, 3].map((i) => (
          <div
            key={i}
            className="rounded-full"
            style={{
              width: i === 1 ? 22 : 14,
              height: 5,
              backgroundColor: i === 1 ? p.accent : p.border,
              boxShadow: i === 1 && p.glow ? `0 0 6px ${p.glow}88` : undefined,
            }}
          />
        ))}
      </div>

      {/* Main Area */}
      <div className="ml-10 p-2.5 flex flex-col gap-1.5">
        {/* Header Bar */}
        <div className="flex items-center justify-between mb-1">
          <div className="rounded" style={{ width: 40, height: 6, backgroundColor: p.text + "cc" }} />
          <div
            className="rounded-full"
            style={{
              width: 22,
              height: 6,
              backgroundColor: p.accent,
              boxShadow: p.glow ? `0 0 5px ${p.glow}88` : undefined,
            }}
          />
        </div>

        {/* Cards Row */}
        <div className="flex gap-1.5">
          {[p.accent, p.subtext, p.subtext].map((c, i) => (
            <div
              key={i}
              className="flex-1 rounded-lg"
              style={{
                backgroundColor: p.card,
                border: `1px solid ${p.border}`,
                height: 32,
                boxShadow: i === 0 && p.glow ? `0 0 8px ${p.glow}44` : undefined,
              }}
            >
              <div className="p-1">
                <div
                  className="rounded"
                  style={{ width: "60%", height: 4, backgroundColor: c, opacity: i === 0 ? 0.9 : 0.5 }}
                />
                <div
                  className="rounded mt-1"
                  style={{ width: "80%", height: 3, backgroundColor: p.text, opacity: 0.25 }}
                />
              </div>
            </div>
          ))}
        </div>

        {/* Mini Table Rows */}
        {[0, 1].map((i) => (
          <div
            key={i}
            className="flex items-center gap-1 rounded"
            style={{ backgroundColor: p.card, border: `1px solid ${p.border}`, padding: "3px 5px" }}
          >
            <div className="rounded-full" style={{ width: 7, height: 7, backgroundColor: p.accent, opacity: 0.7 }} />
            <div className="flex-1 rounded" style={{ height: 3, backgroundColor: p.text, opacity: 0.2 }} />
            <div className="rounded" style={{ width: 16, height: 3, backgroundColor: p.subtext, opacity: 0.4 }} />
          </div>
        ))}
      </div>

      {/* Glow marine overlay for ocean */}
      {p.glow && (
        <div
          className="absolute inset-0 pointer-events-none"
          style={{
            background: `radial-gradient(ellipse at 80% 20%, ${p.glow}14 0%, transparent 55%),
                         radial-gradient(ellipse at 20% 80%, #8855ff14 0%, transparent 50%)`,
          }}
        />
      )}
    </div>
  );
}

export function AparienciaConfig() {
  useLanguage();
  const { theme, setTheme } = useTheme();

  return (
    <div className="space-y-6 py-2" data-testid="apariencia-config-section">
      <div>
        <h3 className="text-sm font-black uppercase tracking-tight">
          {translateKey("configuracion", "apariencia.header_title")}
        </h3>
        <p className="text-[10px] text-muted-foreground font-medium uppercase tracking-widest">
          {translateKey("configuracion", "apariencia.header_subtitle")}
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {THEMES.map((t) => {
          const IconComp = t.icon;
          const isActive = theme === t.id;
          const label =
            translateKey("configuracion", `apariencia.themes.${t.id}.label`) || t.label;
          const description =
            translateKey("configuracion", `apariencia.themes.${t.id}.description`) ||
            t.description;
          const badgeText = t.badge
            ? translateKey("configuracion", "apariencia.badge_nuevo")
            : undefined;

          return (
            <button
              key={t.id}
              type="button"
              onClick={() => setTheme(t.id)}
              className={cn(
                "relative text-left rounded-2xl border-2 p-4 transition-all duration-200 outline-none cursor-pointer min-h-[44px]",
                isActive
                  ? t.id === "ocean-blue"
                    ? "border-[#00e5ff] shadow-[0_0_20px_#00e5ff35] bg-card"
                    : "border-primary shadow-md shadow-primary/20 bg-card"
                  : "border-border hover:border-primary/40 bg-card/50 hover:bg-card"
              )}
            >
              {/* Badge NUEVO / NEW */}
              {badgeText && (
                <span
                  className="absolute top-3 right-3 text-[8px] font-black uppercase tracking-widest px-1.5 py-0.5 rounded-full"
                  style={{
                    backgroundColor: `${t.preview.accent}22`,
                    color: t.preview.accent,
                    border: `1px solid ${t.preview.accent}44`,
                  }}
                >
                  {badgeText}
                </span>
              )}

              {/* Mini Preview Mockup */}
              <MiniPreview p={t.preview} />

              {/* Labels & Checkmark */}
              <div className="mt-3 flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <div className="flex items-center gap-1.5 mb-1">
                    <IconComp
                      className="h-4 w-4 shrink-0"
                      style={{ color: isActive ? t.preview.accent : undefined }}
                    />
                    <span className="text-sm font-bold truncate">{label}</span>
                  </div>
                  <p className="text-[10px] text-muted-foreground leading-snug">{description}</p>
                </div>

                {isActive && (
                  <div
                    className="shrink-0 h-5 w-5 rounded-full flex items-center justify-center mt-0.5 shadow-sm"
                    style={{ backgroundColor: t.preview.accent }}
                  >
                    <Check className="h-3 w-3 stroke-[3px]" style={{ color: t.preview.bg }} />
                  </div>
                )}
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}

export default AparienciaConfig;
