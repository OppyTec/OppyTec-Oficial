import { useState } from "react";
import { useTranslation } from "react-i18next";
import {
  Check,
  CheckCheck,
  Clock,
  Edit2,
  Eye,
  Flame,
  Layers,
  MoreVertical,
  Tag,
  Trash2,
  Utensils,
  ChefHat,
  ConciergeBell,
  Banknote,
  Box,
  Sparkles,
  Wine,
  Shield,
  BadgeCheck,
  AlertTriangle,
  Package,
} from "lucide-react";
import { cn } from "@/shared/lib";
import type { NotaEquipo, NotaPersonal } from "../types";

export interface NotaCardProps {
  readonly nota: NotaEquipo | NotaPersonal;
  readonly isPersonal?: boolean;
  readonly onEdit?: (nota: NotaEquipo | NotaPersonal) => void;
  readonly onDelete?: (id: number) => void;
  readonly onMarkRead?: (id: number) => void;
  readonly onTagClick?: (tag: string) => void;
  readonly onMentionClick?: (mention: string) => void;
}

export function getRoleIcon(roleName?: string) {
  const normalized = (roleName ?? "").toLowerCase().trim();
  if (normalized.includes("chef")) return ChefHat;
  if (normalized.includes("cocin")) return Utensils;
  if (normalized.includes("garz") || normalized.includes("mozo")) return ConciergeBell;
  if (normalized.includes("cajer")) return Banknote;
  if (normalized.includes("bodeg")) return Box;
  if (normalized.includes("steward") || normalized.includes("limp")) return Sparkles;
  if (normalized.includes("bar") || normalized.includes("sommel")) return Wine;
  if (normalized.includes("dueñ") || normalized.includes("prop")) return BadgeCheck;
  return Shield;
}

export function formatRelativeTime(dateString: string | null, t: (key: string, opts?: any) => string): string {
  if (!dateString) return t("activities.notas.time_now", { defaultValue: "Hace un momento" });
  const diffMs = Date.now() - new Date(dateString).getTime();
  const diffMinutes = Math.floor(diffMs / 60000);
  if (diffMinutes < 1) return t("activities.notas.time_now", { defaultValue: "Hace un momento" });
  if (diffMinutes < 60) return t("activities.notas.time_minutes", { count: diffMinutes, defaultValue: `Hace ${diffMinutes} min` });
  const diffHours = Math.floor(diffMinutes / 60);
  if (diffHours < 24) return t("activities.notas.time_hours", { count: diffHours, defaultValue: `Hace ${diffHours} h` });
  const diffDays = Math.floor(diffHours / 24);
  return t("activities.notas.time_days", { count: diffDays, defaultValue: `Hace ${diffDays} d` });
}

export function NotaCard({
  nota,
  isPersonal = false,
  onEdit,
  onDelete,
  onMarkRead,
  onTagClick,
  onMentionClick,
}: NotaCardProps) {
  const { t } = useTranslation("operations");
  const [menuOpen, setMenuOpen] = useState(false);

  const isEquipo = !isPersonal && "categoria" in nota;
  const notaEquipo = isEquipo ? (nota as NotaEquipo) : null;
  const RoleIcon = getRoleIcon(notaEquipo?.autor_role);

  // Formateador interactivo de menciones (@usuario) y tags (#insumo)
  const renderFormattedContent = (text: string) => {
    const parts = text.split(/(@\w+|#[\w-]+)/g);
    return parts.map((part, idx) => {
      if (part.startsWith("@")) {
        return (
          <button
            key={idx}
            type="button"
            onClick={() => onMentionClick?.(part.slice(1))}
            className="inline-flex items-center rounded-md bg-blue-500/10 px-1.5 py-0.5 text-xs font-bold text-blue-500 hover:bg-blue-500/20 transition-colors mx-0.5"
          >
            {part}
          </button>
        );
      }
      if (part.startsWith("#")) {
        return (
          <button
            key={idx}
            type="button"
            onClick={() => onTagClick?.(part.slice(1))}
            className="inline-flex items-center rounded-md bg-amber-500/10 px-1.5 py-0.5 text-xs font-bold text-amber-500 hover:bg-amber-500/20 transition-colors mx-0.5"
          >
            <Tag className="mr-0.5 h-2.5 w-2.5 inline" />
            {part}
          </button>
        );
      }
      return <span key={idx}>{part}</span>;
    });
  };

  const getCategoryBadge = (categoria?: string) => {
    switch (categoria) {
      case "incidente":
        return {
          label: t("activities.notas.categories.incidente", { defaultValue: "Incidente" }),
          className: "bg-red-500/10 text-red-500 border-red-500/30",
          icon: AlertTriangle,
        };
      case "stock":
        return {
          label: t("activities.notas.categories.stock", { defaultValue: "Stock" }),
          className: "bg-amber-500/10 text-amber-500 border-amber-500/30",
          icon: Package,
        };
      case "produccion":
        return {
          label: t("activities.notas.categories.produccion", { defaultValue: "Producción" }),
          className: "bg-blue-500/10 text-blue-500 border-blue-500/30",
          icon: Flame,
        };
      case "servicio":
        return {
          label: t("activities.notas.categories.servicio", { defaultValue: "Servicio" }),
          className: "bg-pink-500/10 text-pink-500 border-pink-500/30",
          icon: ConciergeBell,
        };
      default:
        return {
          label: t("activities.notas.categories.general", { defaultValue: "General" }),
          className: "bg-zinc-500/10 text-muted-foreground border-zinc-500/20",
          icon: Layers,
        };
    }
  };

  const catBadge = notaEquipo ? getCategoryBadge(notaEquipo.categoria) : null;
  const CatIcon = catBadge?.icon;

  return (
    <article
      data-testid="nota-card"
      className={cn(
        "group relative flex flex-col rounded-2xl border border-border bg-card p-4 shadow-sm transition-all duration-200 hover:shadow-md hover:border-primary/40",
        isPersonal ? "border-l-4 border-l-purple-500" : "border-l-4 border-l-blue-500"
      )}
    >
      {/* Header: Autor, Cargo gastronómico, Fecha relativa y Menú */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-3 min-w-0">
          {notaEquipo?.autor_avatar ? (
            <img
              src={notaEquipo.autor_avatar}
              alt={notaEquipo.autor_name ?? t("activities.notas.author_fallback", { defaultValue: "Autor" })}
              className="h-10 w-10 shrink-0 rounded-full object-cover border-2 border-border shadow-sm"
            />
          ) : (
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary font-bold text-sm">
              {(notaEquipo?.autor_name ?? (isPersonal ? "Tú" : "Op"))[0]?.toUpperCase()}
            </div>
          )}

          <div className="min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="font-semibold text-sm text-foreground truncate">
                {notaEquipo?.autor_name ?? (isPersonal ? t("activities.notas.personal_note", { defaultValue: "Nota Personal" }) : t("activities.notas.collaborator_fallback", { defaultValue: "Colaborador" }))}
              </span>

              {/* Badge de Cargo Gastronómico */}
              {notaEquipo?.autor_role && (
                <span className="inline-flex items-center gap-1 rounded-full bg-secondary px-2 py-0.5 text-[11px] font-medium text-secondary-foreground border border-border">
                  <RoleIcon className="h-3 w-3 text-primary" />
                  <span>{notaEquipo.autor_role}</span>
                </span>
              )}

              {/* Badge de Categoría */}
              {catBadge && CatIcon && (
                <span
                  className={cn(
                    "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-bold border",
                    catBadge.className
                  )}
                >
                  <CatIcon className="h-3 w-3" />
                  <span>{catBadge.label}</span>
                </span>
              )}
            </div>

            <div className="flex items-center gap-1.5 text-xs text-muted-foreground mt-0.5">
              <Clock className="h-3 w-3" />
              <span>{formatRelativeTime(nota.created_at ?? nota.fecha, t)}</span>
              {nota.area_id && (
                <>
                  <span>•</span>
                  <span className="capitalize">{nota.area_id.replace("-", " ")}</span>
                </>
              )}
            </div>
          </div>
        </div>

        {/* Acciones */}
        <div className="relative">
          <button
            type="button"
            aria-label={t("activities.common.actions", { defaultValue: "Acciones" })}
            onClick={() => setMenuOpen((prev) => !prev)}
            className="flex h-8 w-8 items-center justify-center rounded-lg text-muted-foreground hover:bg-secondary hover:text-foreground transition-colors"
          >
            <MoreVertical className="h-4 w-4" />
          </button>

          {menuOpen && (
            <>
              <div className="fixed inset-0 z-30" onClick={() => setMenuOpen(false)} />
              <div className="absolute right-0 top-full mt-1 z-40 w-36 rounded-xl border border-border bg-popover p-1 shadow-xl">
                {onEdit && (
                  <button
                    type="button"
                    onClick={() => {
                      setMenuOpen(false);
                      onEdit(nota);
                    }}
                    className="flex w-full items-center gap-2 rounded-lg px-2.5 py-1.5 text-xs font-medium text-foreground hover:bg-secondary transition-colors"
                  >
                    <Edit2 className="h-3.5 w-3.5" />
                    <span>{t("activities.common.edit", { defaultValue: "Editar" })}</span>
                  </button>
                )}
                {onDelete && (
                  <button
                    type="button"
                    onClick={() => {
                      setMenuOpen(false);
                      onDelete(nota.id);
                    }}
                    className="flex w-full items-center gap-2 rounded-lg px-2.5 py-1.5 text-xs font-medium text-red-500 hover:bg-red-500/10 transition-colors"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                    <span>{t("activities.common.delete", { defaultValue: "Eliminar" })}</span>
                  </button>
                )}
              </div>
            </>
          )}
        </div>
      </div>

      {/* Título de la Nota */}
      <h4 className="mt-3 text-base font-bold text-foreground tracking-tight">
        {nota.titulo}
      </h4>

      {/* Cuerpo de Contenido */}
      <p className="mt-1.5 text-sm leading-relaxed text-muted-foreground whitespace-pre-line">
        {renderFormattedContent(nota.contenido)}
      </p>

      {/* Imagen Adjunta R2 si existe */}
      {notaEquipo?.foto_url && (
        <div className="mt-3 overflow-hidden rounded-xl border border-border">
          <img
            src={notaEquipo.foto_url}
            alt={nota.titulo}
            className="h-48 w-full object-cover transition-transform hover:scale-105 duration-300"
          />
        </div>
      )}

      {/* Footer: Lecturas, 'Visto por X' y botón de confirmar lectura */}
      {isEquipo && notaEquipo && (
        <div className="mt-4 flex items-center justify-between border-t border-border pt-3 text-xs">
          <div className="flex items-center gap-2 text-muted-foreground">
            <Eye className="h-3.5 w-3.5" />
            <span>
              {t("activities.notas.seen_by", {
                count: notaEquipo.total_lecturas,
                defaultValue: `Visto por ${notaEquipo.total_lecturas}`,
              })}
            </span>
          </div>

          <div>
            {notaEquipo.leido_por_mi ? (
              <span className="inline-flex items-center gap-1 font-semibold text-emerald-500 text-xs">
                <CheckCheck className="h-4 w-4" />
                <span>{t("activities.notas.read_by_me", { defaultValue: "Leído" })}</span>
              </span>
            ) : (
              <button
                type="button"
                onClick={() => onMarkRead?.(nota.id)}
                className="inline-flex items-center gap-1.5 rounded-lg border border-primary/30 bg-primary/10 px-2.5 py-1 font-semibold text-primary text-xs hover:bg-primary/20 transition-all active:scale-95 cursor-pointer"
              >
                <Check className="h-3.5 w-3.5" />
                <span>{t("activities.notas.mark_read", { defaultValue: "Marcar como leído" })}</span>
              </button>
            )}
          </div>
        </div>
      )}
    </article>
  );
}
