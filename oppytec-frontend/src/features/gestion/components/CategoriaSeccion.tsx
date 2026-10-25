import { useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { CategoryIcon } from "@/shared/components/ui/CategoryIcon";
import { cn } from "@/shared/lib";
import type { Categoria } from "../types";

export interface CategoriaSeccionProps {
  readonly categorias: readonly Categoria[];
  readonly selectedIds: ReadonlySet<string> | Set<string>;
  readonly onToggle: (id: string) => void;
  readonly onUpdate?: () => void;
  readonly className?: string;
}

export function CategoriaSeccion({
  categorias = [],
  selectedIds,
  onToggle,
  className,
}: CategoriaSeccionProps) {
  const uniqueCategorias = useMemo(() => {
    if (!Array.isArray(categorias) || categorias.length === 0) {
      return [];
    }
    const seen = new Set<string>();
    return categorias.filter((cat) => {
      if (!cat || !cat.nombre) return false;
      const key = cat.nombre.trim().toLowerCase();
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });
  }, [categorias]);

  if (uniqueCategorias.length === 0) {
    return null;
  }

  return (
    <div
      data-testid="categoria-seccion"
      className={cn(
        "w-full overflow-x-auto pb-2 custom-scrollbar md:overflow-visible text-center",
        className
      )}
    >
      <div className="flex justify-center md:flex-wrap items-center gap-2 py-3 px-4 min-w-max md:min-w-0 mx-auto">
        <div className="grid grid-flow-col grid-rows-2 gap-2 md:contents">
          <AnimatePresence mode="popLayout">
            {uniqueCategorias.map((cat) => {
              const isSelected = selectedIds.has(cat.id);
              const hexColor = cat.color || "#6366F1";

              return (
                <motion.div
                  key={cat.id}
                  layout
                  initial={{ scale: 0.8, opacity: 0 }}
                  animate={{ scale: 1, opacity: 1 }}
                  exit={{ scale: 0.8, opacity: 0 }}
                  transition={{
                    type: "spring",
                    stiffness: 350,
                    damping: 25,
                    mass: 1.2,
                  }}
                  className="group relative"
                >
                  <button
                    type="button"
                    onClick={() => onToggle(cat.id)}
                    data-testid={`category-badge-${cat.id}`}
                    aria-pressed={isSelected}
                    style={{
                      backgroundColor: isSelected
                        ? hexColor
                        : cat.color
                        ? `${cat.color}18`
                        : undefined,
                      color: isSelected ? "#ffffff" : cat.color || undefined,
                      borderColor: cat.color ? `${cat.color}40` : undefined,
                      boxShadow:
                        isSelected && cat.color
                          ? `0 0 12px ${cat.color}50`
                          : undefined,
                    }}
                    className={cn(
                      "flex items-center justify-center gap-1.5 md:gap-2 px-3 md:px-4 py-1.5 h-9 md:h-10 min-h-[36px] border cursor-pointer select-none transition-all duration-200 whitespace-nowrap rounded-xl text-left",
                      isSelected
                        ? "scale-105 font-black ring-2 ring-primary/20"
                        : "hover:scale-105 hover:bg-secondary/50 font-bold"
                    )}
                  >
                    <CategoryIcon
                      name={cat.icono}
                      className="h-3.5 w-3.5 md:h-4 md:w-4 shrink-0"
                    />
                    <span className="text-[10px] md:text-[11px] font-bold md:font-black uppercase tracking-wide md:tracking-wider">
                      {cat.nombre}
                    </span>
                  </button>
                </motion.div>
              );
            })}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}

export default CategoriaSeccion;
