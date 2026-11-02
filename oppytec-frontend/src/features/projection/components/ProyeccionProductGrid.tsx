/**
 * oppytec-frontend/src/features/projection/components/ProyeccionProductGrid.tsx
 * Grid Adaptativo de Productos para el Módulo de Proyección de OppyTec v2.0.
 * Layout responsive: 1 col móvil (grid-cols-1), 2 en tablet (md:grid-cols-2), 3 en desktop (lg:grid-cols-3), 4 en pantallas amplias (xl:grid-cols-4).
 * Animación fluida de entrada y reordenamiento con Framer Motion (layoutId, springs).
 * Soporte opcional para agrupación por categorías con separadores estilizados.
 * Estado vacío visual elegante y skeletons de carga durante recálculo.
 * TypeScript estricto, 0 any, 0 hardcoded strings.
 */
import { useMemo, type FC } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  PackageSearch,
  RotateCcw,
  Tag,
} from "lucide-react";
import { useTranslation } from "react-i18next";
import { cn } from "@/shared/lib";
import type { ProjectionProductOverview } from "../types";
import {
  ProyeccionProductCard,
  ProyeccionProductCardSkeleton,
} from "./ProyeccionProductCard";

export interface ProyeccionProductGridProps {
  readonly products: readonly ProjectionProductOverview[];
  readonly isLoading?: boolean;
  readonly skeletonCount?: number;
  readonly groupByCategory?: boolean;
  readonly onProductClick?: (product: ProjectionProductOverview) => void;
  readonly onResetFilters?: () => void;
  readonly className?: string;
}

const containerVariants = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: {
      staggerChildren: 0.03,
    },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 12 },
  show: {
    opacity: 1,
    y: 0,
    transition: {
      type: "spring" as const,
      stiffness: 350,
      damping: 25,
      mass: 0.8,
    },
  },
  exit: {
    opacity: 0,
    scale: 0.95,
    transition: { duration: 0.15 },
  },
};

export const ProyeccionProductGrid: FC<ProyeccionProductGridProps> = ({
  products,
  isLoading = false,
  skeletonCount = 8,
  groupByCategory = false,
  onProductClick,
  onResetFilters,
  className,
}) => {
  const { t } = useTranslation("projection");

  // Group products by category when requested
  const groupedProducts = useMemo(() => {
    if (!groupByCategory) return null;

    const map = new Map<string, ProjectionProductOverview[]>();
    for (const item of products) {
      const categoryKey =
        item.categoria_nombre && item.categoria_nombre.trim().length > 0
          ? item.categoria_nombre.trim()
          : t("grid.uncategorized", { defaultValue: "Sin Categoría" });

      const existing = map.get(categoryKey);
      if (existing) {
        existing.push(item);
      } else {
        map.set(categoryKey, [item]);
      }
    }

    // Sort categories alphabetically
    return Array.from(map.entries()).sort(([a], [b]) => a.localeCompare(b));
  }, [groupByCategory, products, t]);

  // Loading Skeleton State
  if (isLoading) {
    return (
      <div
        data-testid="proyeccion-product-grid-loading"
        className={cn(
          "grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 w-full",
          className
        )}
      >
        {Array.from({ length: skeletonCount }).map((_, index) => (
          <ProyeccionProductCardSkeleton key={`product-grid-skeleton-${index}`} />
        ))}
      </div>
    );
  }

  // Empty State
  if (products.length === 0) {
    return (
      <div
        data-testid="proyeccion-product-grid-empty"
        className={cn(
          "flex flex-col items-center justify-center gap-4 rounded-3xl border border-dashed border-border/80 bg-card/40 p-10 sm:p-14 text-center my-6 backdrop-blur-sm",
          className
        )}
      >
        <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-secondary/80 text-muted-foreground shadow-inner">
          <PackageSearch className="h-8 w-8 opacity-80" aria-hidden="true" />
        </div>
        <div className="max-w-md space-y-1">
          <h4 className="text-base sm:text-lg font-bold text-foreground tracking-tight">
            {t("grid.empty_title", {
              defaultValue: "No se encontraron productos",
            })}
          </h4>
          <p className="text-xs sm:text-sm text-muted-foreground">
            {t("grid.empty_description", {
              defaultValue:
                "No hay insumos que coincidan con la búsqueda o filtros de urgencia aplicados.",
            })}
          </p>
        </div>
        {onResetFilters && (
          <button
            type="button"
            data-testid="btn-reset-projection-filters"
            onClick={onResetFilters}
            className="inline-flex items-center gap-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white px-4 py-2 text-xs sm:text-sm font-semibold shadow-md transition-all active:scale-95"
          >
            <RotateCcw className="h-3.5 w-3.5" aria-hidden="true" />
            <span>
              {t("grid.btn_reset_filters", {
                defaultValue: "Restablecer filtros",
              })}
            </span>
          </button>
        )}
      </div>
    );
  }

  // Render grouped by categories
  if (groupByCategory && groupedProducts) {
    return (
      <div
        data-testid="proyeccion-product-grid-grouped"
        className={cn("space-y-8 w-full", className)}
      >
        {groupedProducts.map(([categoryName, categoryItems]) => (
          <section
            key={`category-group-${categoryName}`}
            data-testid={`category-group-${categoryName}`}
            className="space-y-3"
          >
            {/* Category Section Header */}
            <div className="flex items-center gap-2 border-b border-border/40 pb-2">
              <Tag className="h-4 w-4 text-emerald-500 opacity-80" aria-hidden="true" />
              <h3 className="text-sm sm:text-base font-black tracking-tight text-foreground">
                {categoryName}
              </h3>
              <span className="rounded-full bg-secondary px-2 py-0.5 text-[11px] font-bold text-muted-foreground">
                {categoryItems.length}
              </span>
            </div>

            {/* Responsive grid for this category */}
            <motion.div
              variants={containerVariants}
              initial="hidden"
              animate="show"
              className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4"
            >
              <AnimatePresence mode="popLayout">
                {categoryItems.map((product) => (
                  <motion.div
                    key={`grouped-product-${product.id}-${product.producto_id}`}
                    layout
                    variants={itemVariants}
                    initial="hidden"
                    animate="show"
                    exit="exit"
                  >
                    <ProyeccionProductCard
                      product={product}
                      onClick={onProductClick}
                    />
                  </motion.div>
                ))}
              </AnimatePresence>
            </motion.div>
          </section>
        ))}
      </div>
    );
  }

  // Direct Flat Responsive Grid with Framer Motion
  return (
    <motion.div
      data-testid="proyeccion-product-grid"
      variants={containerVariants}
      initial="hidden"
      animate="show"
      className={cn(
        "grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 w-full",
        className
      )}
    >
      <AnimatePresence mode="popLayout">
        {products.map((product) => (
          <motion.div
            key={`flat-product-${product.id}-${product.producto_id}`}
            layout
            variants={itemVariants}
            initial="hidden"
            animate="show"
            exit="exit"
          >
            <ProyeccionProductCard
              product={product}
              onClick={onProductClick}
            />
          </motion.div>
        ))}
      </AnimatePresence>
    </motion.div>
  );
};
