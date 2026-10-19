import type { Config } from "tailwindcss";
import tailwindcssAnimate from "tailwindcss-animate";

/**
 * Paleta Gastronómica Oficial de 42 Colores Predefinidos (Grilla 6 x 7)
 * Rescatada de OppyTec-Legacy (categoriaUI.ts) y congelada en specs/04-DESIGN-SYSTEM.md.
 */
export const PRESET_COLORS = [
  // Fila 1: Rojos y Rosados
  "#EF4444",
  "#DC2626",
  "#B91C1C",
  "#F43F5E",
  "#E11D48",
  "#EC4899",
  "#DB2777",
  // Fila 2: Naranjas y Amarillos
  "#F97316",
  "#EA580C",
  "#D97706",
  "#F59E0B",
  "#EAB308",
  "#FACC15",
  "#CA8A04",
  // Fila 3: Verdes y Limas
  "#84CC16",
  "#65A30D",
  "#22C55E",
  "#16A34A",
  "#15803D",
  "#10B981",
  "#059669",
  // Fila 4: Turquesas, Cians y Azules
  "#14B8A6",
  "#06B6D4",
  "#0891B2",
  "#0EA5E9",
  "#0284C7",
  "#3B82F6",
  "#2563EB",
  // Fila 5: Índigos, Púrpuras y Violetas
  "#6366F1",
  "#4F46E5",
  "#A855F7",
  "#9333EA",
  "#8B5CF6",
  "#7C3AED",
  "#C026D3",
  // Fila 6: Grises y Neutros
  "#94A3B8",
  "#64748B",
  "#475569",
  "#78716C",
  "#57534E",
  "#525252",
  "#334155",
] as const;

export const OFFICIAL_THEMES = ["light", "dark", "ocean-blue"] as const;
export type OppyTecTheme = (typeof OFFICIAL_THEMES)[number];

const config: Config = {
  darkMode: ["class"],
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    container: {
      center: true,
      padding: "2rem",
      screens: {
        "2xl": "1400px",
      },
    },
    extend: {
      fontFamily: {
        sans: ["'Outfit'", "system-ui", "-apple-system", "sans-serif"],
        outfit: ["'Outfit'", "sans-serif"],
      },
      minHeight: {
        touch: "44px",
      },
      minWidth: {
        touch: "44px",
      },
      colors: {
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        popover: {
          DEFAULT: "hsl(var(--popover))",
          foreground: "hsl(var(--popover-foreground))",
        },
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
        success: {
          DEFAULT: "hsl(var(--success))",
          foreground: "hsl(var(--success-foreground))",
        },
        warning: {
          DEFAULT: "hsl(var(--warning))",
          foreground: "hsl(var(--warning-foreground))",
        },
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
      animation: {
        "pulse-slow": "pulse 4s cubic-bezier(0.4, 0, 0.6, 1) infinite",
        "fade-in": "fade-in 0.5s ease-out",
        "slide-up": "slide-up 0.5s ease-out",
        marquee: "marquee 5s linear infinite",
        "blink-orange": "blink-orange 2.0s ease-in-out infinite",
        "blink-red": "blink-red 2.0s ease-in-out infinite",
        "blink-green": "blink-green 2.5s ease-in-out infinite",
        "perimeter-glow": "perimeter-glow 1.8s ease-in-out infinite",
      },
      keyframes: {
        "fade-in": {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
        "slide-up": {
          "0%": { transform: "translateY(10px)", opacity: "0" },
          "100%": { transform: "translateY(0)", opacity: "1" },
        },
        marquee: {
          "0%": { transform: "translateX(0)" },
          "100%": { transform: "translateX(-100%)" },
        },
      },
    },
  },
  plugins: [tailwindcssAnimate],
};

export default config;
