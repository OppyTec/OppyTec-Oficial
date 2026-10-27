import React from "react";
import {
  Wheat,
  Egg,
  Fish,
  Milk,
  Nut,
  Bean,
  Soup,
  Wine,
  Sprout,
  Carrot,
  Sparkles,
  Shell,
  ShieldAlert,
} from "lucide-react";
import { useTranslation } from "react-i18next";
import { cn } from "@/shared/lib";
import type { AllergenInfo } from "../types";

export interface AllergenBadgeProps {
  allergen: AllergenInfo | string;
  size?: "sm" | "md" | "lg";
  showLabel?: boolean;
  className?: string;
}

interface AllergenStyleConfig {
  icon: React.ComponentType<{ className?: string }>;
  colorClasses: string;
}

const ALLERGEN_STYLES: Record<string, AllergenStyleConfig> = {
  GLUTEN: {
    icon: Wheat,
    colorClasses:
      "bg-amber-500/15 text-amber-700 dark:text-amber-400 border-amber-500/30",
  },
  CRUSTACEANS: {
    icon: Fish,
    colorClasses:
      "bg-orange-500/15 text-orange-700 dark:text-orange-400 border-orange-500/30",
  },
  EGGS: {
    icon: Egg,
    colorClasses:
      "bg-yellow-500/15 text-yellow-700 dark:text-yellow-400 border-yellow-500/30",
  },
  FISH: {
    icon: Fish,
    colorClasses:
      "bg-cyan-500/15 text-cyan-700 dark:text-cyan-400 border-cyan-500/30",
  },
  PEANUTS: {
    icon: Nut,
    colorClasses:
      "bg-amber-700/15 text-amber-800 dark:text-amber-300 border-amber-700/30",
  },
  SOYBEANS: {
    icon: Bean,
    colorClasses:
      "bg-emerald-500/15 text-emerald-700 dark:text-emerald-400 border-emerald-500/30",
  },
  MILK: {
    icon: Milk,
    colorClasses:
      "bg-blue-500/15 text-blue-700 dark:text-blue-400 border-blue-500/30",
  },
  NUTS: {
    icon: Nut,
    colorClasses:
      "bg-amber-600/15 text-amber-700 dark:text-amber-400 border-amber-600/30",
  },
  CELERY: {
    icon: Carrot,
    colorClasses:
      "bg-green-500/15 text-green-700 dark:text-green-400 border-green-500/30",
  },
  MUSTARD: {
    icon: Soup,
    colorClasses:
      "bg-yellow-600/15 text-yellow-700 dark:text-yellow-400 border-yellow-600/30",
  },
  SESAME: {
    icon: Sparkles,
    colorClasses:
      "bg-stone-500/15 text-stone-700 dark:text-stone-300 border-stone-500/30",
  },
  SULPHITES: {
    icon: Wine,
    colorClasses:
      "bg-purple-500/15 text-purple-700 dark:text-purple-400 border-purple-500/30",
  },
  LUPIN: {
    icon: Sprout,
    colorClasses:
      "bg-lime-500/15 text-lime-700 dark:text-lime-400 border-lime-500/30",
  },
  MOLLUSCS: {
    icon: Shell,
    colorClasses:
      "bg-teal-500/15 text-teal-700 dark:text-teal-400 border-teal-500/30",
  },
};

const DEFAULT_STYLE: AllergenStyleConfig = {
  icon: ShieldAlert,
  colorClasses:
    "bg-rose-500/15 text-rose-700 dark:text-rose-400 border-rose-500/30",
};

export function AllergenBadge({
  allergen,
  size = "md",
  showLabel = true,
  className,
}: AllergenBadgeProps) {
  const { t, i18n } = useTranslation("recipes");

  const allergenObj: AllergenInfo =
    typeof allergen === "string"
      ? { code: allergen.toUpperCase(), nombre: allergen }
      : allergen;

  const code = (allergenObj.code || "").toUpperCase();
  const styleConfig = ALLERGEN_STYLES[code] || DEFAULT_STYLE;
  const IconComponent = styleConfig.icon;

  const displayName =
    i18n.language.startsWith("en") && allergenObj.nombre_en
      ? allergenObj.nombre_en
      : t(`allergens.${code}`, {
          defaultValue: allergenObj.nombre || code,
        });

  const tooltipText = allergenObj.descripcion || displayName;

  const sizeClasses = {
    sm: "px-2 py-0.5 text-[10px] gap-1",
    md: "px-2.5 py-1 text-xs gap-1.5",
    lg: "px-3 py-1.5 text-sm gap-2",
  }[size];

  const iconSizes = {
    sm: "h-3 w-3",
    md: "h-3.5 w-3.5",
    lg: "h-4 w-4",
  }[size];

  return (
    <span
      data-testid={`allergen-badge-${code.toLowerCase()}`}
      title={tooltipText}
      className={cn(
        "inline-flex items-center font-extrabold rounded-full border transition-colors shadow-xs select-none",
        styleConfig.colorClasses,
        sizeClasses,
        className
      )}
    >
      <IconComponent className={cn(iconSizes, "shrink-0")} />
      {showLabel && <span>{displayName}</span>}
    </span>
  );
}

export default AllergenBadge;
