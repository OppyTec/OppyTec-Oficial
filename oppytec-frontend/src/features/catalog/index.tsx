import { useState } from "react";
import { Can } from "@/shared/auth/Can";
import {
  GASTRONOMIC_ICONS,
  PRESET_COLORS,
  QuotaProgressIndicator,
} from "@/shared/components/ui";
import { MoneyBadge } from "@/shared/currency";
import {
  getActiveLanguage,
  resolveDynamicFieldI18n,
  translateKey,
} from "@/shared/i18n";
import { convertThreeLayerQuantity } from "@/shared/lib";

interface CatalogItemRecord {
  readonly sku: string;
  readonly name: string;
  readonly is_proper_noun: boolean;
  readonly name_i18n: Readonly<Record<string, string>>;
  readonly baseCostClp: string;
  readonly categoryColor: string;
  readonly categoryIcon: string;
}

const CATALOG_PRODUCTS: readonly CatalogItemRecord[] = [
  {
    sku: "PRD-PK-001",
    name: "Pollo King",
    is_proper_noun: true,
    name_i18n: { es: "Pollo King", en: "Pollo King" },
    baseCostClp: "4890",
    categoryColor: PRESET_COLORS[0] ?? "#EF4444",
    categoryIcon: GASTRONOMIC_ICONS[6] ?? "drumstick",
  },
  {
    sku: "INS-SALM-002",
    name: "Filete de Salmón Austral",
    is_proper_noun: false,
    name_i18n: {
      es: "Filete de Salmón Austral",
      en: "Southern Salmon Fillet",
    },
    baseCostClp: "14500",
    categoryColor: PRESET_COLORS[23] ?? "#0891B2",
    categoryIcon: GASTRONOMIC_ICONS[5] ?? "fish",
  },
];

const WIZARD_STEPS = [
  "1. Identidad & Marca Propia",
  "2. Familia, Color (42) & Ícono (49)",
  "3. Unidades 3-Capas (Compra/Bodega/Receta)",
  "4. Costo Base & Media WebP Cloudflare R2",
] as const;

const IMPORTER_STAGES = [
  "Stage 1: Ingesta & Detección SHA-256",
  "Stage 2: Mapeo Semántico de Columnas IA",
  "Stage 3: Normalización de Unidades 3-Capas",
  "Stage 4: Reconciliación de Duplicados & Marcas",
  "Stage 5: Commit Transaccional Auditado",
] as const;

export function CatalogFeatureView() {
  const [wizardStep, setWizardStep] = useState<number>(0);
  const [importerStage, setImporterStage] = useState<number>(0);
  const lang = getActiveLanguage();

  const convertedRecipeGrams = convertThreeLayerQuantity("2", "purchase", "recipe", {
    code: "CAJA-KG-GR",
    purchaseUnit: "Caja (10 kg)",
    storageUnit: "kg",
    recipeUnit: "g",
    purchaseToStorageFactor: "10",
    storageToRecipeFactor: "1000",
  });

  return (
    <section
      data-testid="feature-catalog"
      className="glass-card space-y-4 rounded-xl p-4 md:p-6"
    >
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border pb-3">
        <div>
          <h2 className="text-lg font-bold text-foreground">
            {translateKey("catalog", "title")}
          </h2>
          <p className="text-xs text-muted-foreground">
            {translateKey("catalog", "categories.count", { count: 42 })}
          </p>
        </div>
        <Can perform="catalog.products.create">
          <span
            data-testid="catalog-r2-quota-badge"
            className="rounded-lg border border-border bg-secondary px-3 py-1 font-mono text-xs font-semibold text-foreground"
          >
            {translateKey("platform_admin", "tenants.r2_quota", {
              usedMb: 342,
              limitMb: 2048,
            })}
          </span>
        </Can>
      </div>

      {/* Semáforo de Cuotas del Plan Básico (Productos, Proveedores y Almacenamiento R2) */}
      <div
        data-testid="catalog-plan-quotas-grid"
        className="grid grid-cols-1 gap-3 md:grid-cols-3"
      >
        <QuotaProgressIndicator
          resourceKey="products"
          label="Cupo de Productos (Plan Básico)"
          activeCount={CATALOG_PRODUCTS.length}
          maxLimit={500}
          softDeletedCount={1}
          testId="catalog-quota-products"
        />
        <QuotaProgressIndicator
          resourceKey="suppliers"
          label="Cupo de Proveedores"
          activeCount={17}
          maxLimit={20}
          testId="catalog-quota-suppliers"
        />
        <QuotaProgressIndicator
          resourceKey="storage_mb"
          label="Almacenamiento R2 (Fotos WebP & Facturas PDF)"
          activeCount={342}
          maxLimit={512}
          unitSuffix="MB"
          testId="catalog-quota-storage"
        />
      </div>

      {/* 4-Step Product Wizard & 5-Stage AI Excel Importer */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <div
          data-testid="catalog-4step-wizard"
          className="space-y-2 rounded-xl border border-border bg-secondary/20 p-3"
        >
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-bold uppercase text-muted-foreground">
              Wizard de Producto (4 Pasos)
            </h3>
            <button
              type="button"
              data-testid="catalog-wizard-next"
              onClick={() =>
                setWizardStep((prev) => (prev + 1) % WIZARD_STEPS.length)
              }
              className="touch-target inline-flex min-h-[44px] items-center rounded-md bg-primary px-2.5 py-1 text-xs font-semibold text-primary-foreground"
            >
              Siguiente Paso
            </button>
          </div>
          <p className="font-mono text-xs font-bold text-primary">
            {WIZARD_STEPS[wizardStep]}
          </p>
          <p className="text-xs text-muted-foreground">
            {`Conversión 3-Capas Exacta (2 Cajas -> Receta): ${convertedRecipeGrams} g`}
          </p>
        </div>

        <div
          data-testid="catalog-5stage-importer"
          className="space-y-2 rounded-xl border border-border bg-secondary/20 p-3"
        >
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-bold uppercase text-muted-foreground">
              Importador Excel IA (5 Etapas)
            </h3>
            <button
              type="button"
              data-testid="catalog-importer-advance"
              onClick={() =>
                setImporterStage((prev) => (prev + 1) % IMPORTER_STAGES.length)
              }
              className="touch-target inline-flex min-h-[44px] items-center rounded-md bg-secondary px-2.5 py-1 text-xs font-semibold text-secondary-foreground"
            >
              Avanzar Etapa
            </button>
          </div>
          <p className="font-mono text-xs font-bold text-foreground">
            {IMPORTER_STAGES[importerStage]}
          </p>
          <p className="text-[11px] text-muted-foreground">
            {`42 Colores (${PRESET_COLORS[0]}) · 49 Íconos (${GASTRONOMIC_ICONS.length} registrados)`}
          </p>
        </div>
      </div>

      {/* Lista de Productos con Preservación de Nombre Propio ("Pollo King") */}
      <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
        {CATALOG_PRODUCTS.map((item) => {
          const displayName = resolveDynamicFieldI18n(item, lang);
          return (
            <div
              key={item.sku}
              data-testid={`catalog-product-${item.sku}`}
              className="flex flex-col justify-between gap-2 rounded-xl border border-border bg-card p-3"
            >
              <div className="flex items-center justify-between gap-2">
                <div>
                  <h4 className="text-sm font-bold text-foreground">
                    {displayName}
                  </h4>
                  <p className="font-mono text-xs text-muted-foreground">
                    {translateKey("catalog", "product.sku", { sku: item.sku })}
                  </p>
                </div>
                {item.is_proper_noun && (
                  <span
                    data-testid="proper-noun-badge"
                    className="rounded-full bg-primary/15 px-2.5 py-0.5 text-[10px] font-bold text-primary"
                  >
                    {translateKey("catalog", "product.proper_noun_badge")}
                  </span>
                )}
              </div>
              <div className="flex items-center justify-between border-t border-border pt-2">
                <span className="font-mono text-[11px] text-muted-foreground">
                  {`Icon: ${item.categoryIcon} · Hex: ${item.categoryColor}`}
                </span>
                <MoneyBadge amount={item.baseCostClp} baseCurrency="CLP" />
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}
