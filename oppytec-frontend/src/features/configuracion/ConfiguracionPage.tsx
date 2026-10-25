import { useState, useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import {
  Settings,
  Store,
  Warehouse,
  Layers,
  Mail,
  Palette,
  HelpCircle,
  ChevronRight,
  type LucideIcon,
} from "lucide-react";
import { SectionHeader } from "@/shared/components/ui/SectionHeader";
import { cn } from "@/shared/lib";
import { translateKey, useLanguage } from "@/shared/i18n";
import {
  RestauranteConfig,
  BodegasConfig,
  AreasOperativasConfig,
  PlantillasEmailConfig,
  AparienciaConfig,
  SoporteConfig,
} from "./tabs";

interface ConfigSectionItem {
  readonly id: string;
  readonly label: string;
  readonly description: string;
  readonly icon: LucideIcon;
  readonly component: React.ReactNode;
}

export function ConfiguracionPage() {
  useLanguage();
  const [searchParams, setSearchParams] = useSearchParams();
  const tabParam = searchParams.get("tab");
  const [openSection, setOpenSection] = useState<string | null>(tabParam || "negocio");

  useEffect(() => {
    if (tabParam) {
      setOpenSection(tabParam);
    }
  }, [tabParam]);

  const handleToggle = (id: string) => {
    const next = openSection === id ? null : id;
    setOpenSection(next);
    if (next) {
      setSearchParams({ tab: next }, { replace: true });
    } else {
      setSearchParams({}, { replace: true });
    }
  };

  const sections: readonly ConfigSectionItem[] = [
    {
      id: "negocio",
      label: translateKey("configuracion", "page.sections.negocio.label"),
      description: translateKey("configuracion", "page.sections.negocio.description"),
      icon: Store,
      component: <RestauranteConfig />,
    },
    {
      id: "bodegas",
      label: translateKey("configuracion", "page.sections.bodegas.label"),
      description: translateKey("configuracion", "page.sections.bodegas.description"),
      icon: Warehouse,
      component: <BodegasConfig />,
    },
    {
      id: "areas",
      label: translateKey("configuracion", "page.sections.areas.label"),
      description: translateKey("configuracion", "page.sections.areas.description"),
      icon: Layers,
      component: <AreasOperativasConfig />,
    },
    {
      id: "plantillas_email",
      label: translateKey("configuracion", "page.sections.plantillas_email.label"),
      description: translateKey("configuracion", "page.sections.plantillas_email.description"),
      icon: Mail,
      component: <PlantillasEmailConfig />,
    },
    {
      id: "tema",
      label: translateKey("configuracion", "page.sections.tema.label"),
      description: translateKey("configuracion", "page.sections.tema.description"),
      icon: Palette,
      component: <AparienciaConfig />,
    },
    {
      id: "soporte",
      label: translateKey("configuracion", "page.sections.soporte.label"),
      description: translateKey("configuracion", "page.sections.soporte.description"),
      icon: HelpCircle,
      component: <SoporteConfig />,
    },
  ];

  return (
    <div className="space-y-6 max-w-4xl mx-auto py-4 px-2 md:px-4" data-testid="configuracion-page">
      <SectionHeader
        title={translateKey("configuracion", "page.title")}
        subtitle={translateKey("configuracion", "page.subtitle")}
        icon={Settings}
        color="#64748b"
      />

      <div className="space-y-3">
        {sections.map((section) => {
          const isOpen = openSection === section.id;
          const SectionIcon = section.icon;

          return (
            <div
              key={section.id}
              data-testid={`config-section-${section.id}`}
              className={cn(
                "rounded-2xl border transition-all duration-200 overflow-hidden bg-card/60",
                isOpen
                  ? "border-primary/50 shadow-lg shadow-primary/5 bg-card ring-1 ring-primary/20"
                  : "border-border hover:border-primary/30 hover:bg-card/90"
              )}
            >
              {/* Trigger Acordeón */}
              <button
                type="button"
                onClick={() => handleToggle(section.id)}
                className="flex w-full items-center justify-between p-4 md:p-5 text-left transition-colors cursor-pointer min-h-[52px]"
                aria-expanded={isOpen}
              >
                <div className="flex items-center gap-3.5 min-w-0">
                  <div
                    className={cn(
                      "h-10 w-10 rounded-xl flex items-center justify-center shrink-0 transition-colors",
                      isOpen
                        ? "bg-primary text-primary-foreground shadow-sm"
                        : "bg-secondary text-muted-foreground"
                    )}
                  >
                    <SectionIcon className="h-5 w-5" />
                  </div>
                  <div className="min-w-0">
                    <span className="font-extrabold text-sm block truncate">{section.label}</span>
                    <span className="text-[11px] text-muted-foreground block truncate">
                      {section.description}
                    </span>
                  </div>
                </div>
                <div className="ml-3 shrink-0">
                  <ChevronRight
                    className={cn(
                      "h-5 w-5 text-muted-foreground transition-transform duration-300",
                      isOpen && "rotate-90 text-primary"
                    )}
                  />
                </div>
              </button>

              {/* Contenido Expandible */}
              {isOpen && (
                <div className="px-4 pb-5 pt-1 md:px-6 md:pb-6 border-t border-border/60 bg-card/30 animate-in fade-in duration-200">
                  {section.component}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default ConfiguracionPage;
