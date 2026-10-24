import { useNavigate } from "react-router-dom";
import { ArrowLeft, Clock, Sparkles } from "lucide-react";

export interface ModulePlaceholderViewProps {
  readonly title: string;
  readonly description?: string;
  readonly moduleSlug?: string;
}

export function ModulePlaceholderView({
  title,
  description = "Estamos sincronizando este módulo con el ADN Visual Legacy v2.0 y la infraestructura multi-tenant.",
  moduleSlug,
}: ModulePlaceholderViewProps) {
  const navigate = useNavigate();

  return (
    <div
      data-testid={`module-placeholder-${title.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`}
      className="p-6 md:p-10 space-y-6 animate-in fade-in slide-in-from-bottom-2 duration-300"
    >
      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={() => navigate("/")}
          className="touch-target inline-flex min-h-[44px] items-center gap-2 text-xs font-semibold text-muted-foreground hover:text-foreground transition-colors"
        >
          <ArrowLeft size={16} />
          <span>Volver al Inicio</span>
        </button>
      </div>

      <div className="rounded-3xl border border-dashed border-border bg-card/60 p-8 md:p-12 text-center space-y-4 shadow-sm backdrop-blur-sm">
        <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-primary/10 text-primary border border-primary/20 shadow-inner">
          <Clock className="h-7 w-7 animate-pulse" />
        </div>

        <div className="space-y-1.5 max-w-lg mx-auto">
          <div className="inline-flex items-center gap-1.5 rounded-full bg-primary/10 px-3 py-1 text-[11px] font-black uppercase tracking-wider text-primary border border-primary/20">
            <Sparkles size={12} />
            <span>Módulo en preparación</span>
          </div>
          <h2 className="text-2xl md:text-3xl font-black text-foreground tracking-tight pt-1">
            {title}
          </h2>
          <p className="text-xs md:text-sm text-muted-foreground leading-relaxed">
            {description}
          </p>
          {moduleSlug && (
            <span className="font-mono text-[10px] text-muted-foreground/80 block pt-1">
              Ref: {moduleSlug}
            </span>
          )}
        </div>

        <div className="pt-2">
          <button
            type="button"
            onClick={() => navigate("/")}
            className="touch-target inline-flex min-h-[44px] items-center justify-center gap-2 rounded-xl bg-primary px-5 py-2.5 text-xs font-bold text-primary-foreground shadow-md hover:bg-primary/90 transition-all"
          >
            <span>Ir al Inicio / HomeDashboard</span>
          </button>
        </div>
      </div>
    </div>
  );
}

export default ModulePlaceholderView;
