import { Layers } from "lucide-react";
import { cn } from "@/shared/lib";
import {
  CATEGORIES_CONFIG,
  type CategoryType,
  type PendingCounts,
} from "../types";

export interface CategoryTabsProps {
  readonly activeCategory: CategoryType | "all";
  readonly onSelectCategory: (category: CategoryType | "all") => void;
  readonly counts?: PendingCounts;
  readonly className?: string;
}

export function CategoryTabs({
  activeCategory,
  onSelectCategory,
  counts,
  className,
}: CategoryTabsProps) {
  const isAll = activeCategory === "all";

  const getCategoryCount = (categoryId: CategoryType): number => {
    if (!counts) return 0;
    return counts[categoryId] ?? 0;
  };

  const totalCount = counts?.total ?? 0;

  return (
    <div
      data-testid="category-tabs"
      className={cn(
        "flex items-center gap-2 overflow-x-auto no-scrollbar py-1 w-full justify-start md:justify-center",
        className
      )}
    >
      {/* Botón Todas */}
      <button
        type="button"
        data-testid="tab-category-all"
        onClick={() => onSelectCategory("all")}
        className={cn(
          "h-10 px-3.5 gap-2 inline-flex items-center justify-center rounded-xl transition-all active:scale-95 text-[10px] font-black uppercase tracking-wider shadow-sm shrink-0 cursor-pointer select-none border",
          isAll
            ? "bg-amber-500/15 text-amber-500 border-amber-500/40 shadow-amber-500/20"
            : "border-input bg-background/70 hover:bg-muted text-muted-foreground hover:text-foreground"
        )}
      >
        <Layers className="h-3.5 w-3.5 shrink-0 text-amber-500" />
        <span>Todas</span>
        {totalCount > 0 && (
          <span
            data-testid="badge-category-all"
            className="px-1.5 py-0.5 rounded-full text-[9px] bg-amber-500 text-black font-black"
          >
            {totalCount}
          </span>
        )}
      </button>

      {/* 4 Pestañas Operativas */}
      {CATEGORIES_CONFIG.map((cat) => {
        const Icon = cat.icon;
        const count = getCategoryCount(cat.id);
        const isActive = activeCategory === cat.id;

        return (
          <button
            key={cat.id}
            type="button"
            data-testid={`tab-category-${cat.id}`}
            onClick={() => onSelectCategory(isActive ? "all" : cat.id)}
            className={cn(
              "h-10 px-3.5 gap-2 inline-flex items-center justify-center rounded-xl transition-all active:scale-95 text-[10px] font-black uppercase tracking-wider shadow-sm shrink-0 cursor-pointer select-none border",
              isActive
                ? cat.activeClass
                : "border-input bg-background/70 hover:bg-muted text-muted-foreground hover:text-foreground"
            )}
          >
            <Icon className="h-3.5 w-3.5 shrink-0" style={{ color: cat.color }} />
            <span>{cat.label}</span>
            {count > 0 && (
              <span
                data-testid={`badge-category-${cat.id}`}
                className={cn("px-1.5 py-0.5 rounded-full text-[9px]", cat.badgeClass)}
              >
                {count}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}

export default CategoryTabs;
