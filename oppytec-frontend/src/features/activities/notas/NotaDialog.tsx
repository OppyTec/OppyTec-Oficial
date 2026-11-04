import { useState, useEffect, useRef } from "react";
import { useTranslation } from "react-i18next";
import { ResponsiveDialog } from "@/shared/components/ui/ResponsiveDialog";
import { OFFICIAL_AREAS } from "@/shared/components/layout/AreaSelector";
import { useCollaborators } from "../hooks/useCollaborators";
import { useIsMobile } from "@/shared/hooks/useIsMobile";
import type { Collaborator, NotaCategoria, NotaEquipo, NotaPersonal } from "../types";
import { X } from "lucide-react";

export interface NotaDialogProps {
  readonly open: boolean;
  readonly isPersonal?: boolean;
  readonly initialData?: NotaEquipo | NotaPersonal | null;
  readonly onClose: () => void;
  readonly onSave: (data: {
    titulo: string;
    contenido: string;
    area_id?: string | null;
    categoria?: NotaCategoria | string;
    foto_url?: string | null;
    menciones_user_ids?: number[];
  }) => Promise<void>;
}

export function NotaDialog({
  open,
  isPersonal = false,
  initialData,
  onClose,
  onSave,
}: NotaDialogProps) {
  const { t } = useTranslation("operations");
  const isMobile = useIsMobile();
  const { collaborators } = useCollaborators();

  const [titulo, setTitulo] = useState("");
  const [contenido, setContenido] = useState("");
  const [areaId, setAreaId] = useState<string>("all");
  const [categoria, setCategoria] = useState<NotaCategoria>("general");
  const [fotoUrl, setFotoUrl] = useState<string>("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Autocompletado reactivo de menciones @
  const [mentionQuery, setMentionQuery] = useState<string | null>(null);
  const [mentionPosition, setMentionPosition] = useState<number>(-1);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (initialData) {
      setTitulo(initialData.titulo);
      setContenido(initialData.contenido);
      setAreaId(initialData.area_id ?? "all");
      if ("categoria" in initialData && initialData.categoria) {
        setCategoria(initialData.categoria as NotaCategoria);
      }
      if ("foto_url" in initialData && initialData.foto_url) {
        setFotoUrl(initialData.foto_url);
      }
    } else {
      setTitulo("");
      setContenido("");
      setAreaId("all");
      setCategoria("general");
      setFotoUrl("");
    }
  }, [initialData, open]);

  // Detector reactivo de '@'
  const handleContentChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const val = e.target.value;
    const pos = e.target.selectionStart;
    setContenido(val);

    const textBefore = val.slice(0, pos);
    const lastAt = textBefore.lastIndexOf("@");
    if (lastAt !== -1) {
      const query = textBefore.slice(lastAt + 1);
      if (!query.includes(" ")) {
        setMentionQuery(query.toLowerCase());
        setMentionPosition(lastAt);
        return;
      }
    }
    setMentionQuery(null);
    setMentionPosition(-1);
  };

  const handleSelectCollaborator = (collab: Collaborator) => {
    if (mentionPosition === -1) return;
    const textBefore = contenido.slice(0, mentionPosition);
    const textAfter = contenido.slice(textareaRef.current?.selectionStart ?? (mentionPosition + 1));
    const nextContent = `${textBefore}@${collab.username} ${textAfter}`;
    setContenido(nextContent);
    setMentionQuery(null);
    setMentionPosition(-1);
    textareaRef.current?.focus();
  };

  const filteredCollaborators = mentionQuery !== null
    ? collaborators.filter(
        (c) =>
          c.username.toLowerCase().includes(mentionQuery) ||
          c.name.toLowerCase().includes(mentionQuery)
      )
    : [];

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!titulo.trim() || !contenido.trim()) return;

    // Extraer menciones
    const mentionedUsernames = (contenido.match(/@\w+/g) || []).map((m) =>
      m.slice(1).toLowerCase()
    );
    const mencionesUserIds = collaborators
      .filter((c) => mentionedUsernames.includes(c.username.toLowerCase()))
      .map((c) => c.id);

    setIsSubmitting(true);
    try {
      await onSave({
        titulo: titulo.trim(),
        contenido: contenido.trim(),
        area_id: areaId === "all" ? null : areaId,
        categoria: isPersonal ? undefined : categoria,
        foto_url: fotoUrl.trim() || null,
        menciones_user_ids: mencionesUserIds,
      });
      onClose();
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <ResponsiveDialog
      open={open}
      onClose={onClose}
      isMobile={isMobile}
      maxWidth="max-w-xl"
      title={
        initialData
          ? t("activities.notas.edit_note", { defaultValue: "Editar Nota" })
          : t("activities.notas.new_note", { defaultValue: "Nueva Nota" })
      }
      description={
        isPersonal
          ? t("activities.notas.personal_badge", { defaultValue: "Nota Privada" })
          : t("activities.notas.subtitle", { defaultValue: "Muro de novedades y bitácora de turno" })
      }
    >
      <form onSubmit={handleSubmit} className="space-y-4 py-2">
        {/* Título */}
        <div>
          <label className="block text-xs font-bold text-foreground uppercase tracking-wider mb-1">
            {t("activities.notas.form.title_label", { defaultValue: "Título" })} *
          </label>
          <input
            type="text"
            required
            value={titulo}
            onChange={(e) => setTitulo(e.target.value)}
            placeholder={t("activities.notas.form.title_placeholder", {
              defaultValue: "Ej: Novedades del turno matutino",
            })}
            className="w-full rounded-xl border border-border bg-background px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-blue-500/50 shadow-sm"
          />
        </div>

        {/* Fila: Área y Categoría */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-bold text-foreground uppercase tracking-wider mb-1">
              {t("activities.notas.form.area_label", { defaultValue: "Área asignada" })}
            </label>
            <select
              value={areaId}
              onChange={(e) => setAreaId(e.target.value)}
              className="w-full rounded-xl border border-border bg-background px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-blue-500/50 shadow-sm"
            >
              {OFFICIAL_AREAS.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.nombre}
                </option>
              ))}
            </select>
          </div>

          {!isPersonal && (
            <div>
              <label className="block text-xs font-bold text-foreground uppercase tracking-wider mb-1">
                {t("activities.notas.form.category_label", { defaultValue: "Categoría" })}
              </label>
              <select
                value={categoria}
                onChange={(e) => setCategoria(e.target.value as NotaCategoria)}
                className="w-full rounded-xl border border-border bg-background px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-blue-500/50 shadow-sm"
              >
                <option value="general">
                  {t("activities.notas.categories.general", { defaultValue: "General" })}
                </option>
                <option value="incidente">
                  {t("activities.notas.categories.incidente", { defaultValue: "Incidente" })}
                </option>
                <option value="stock">
                  {t("activities.notas.categories.stock", { defaultValue: "Stock" })}
                </option>
                <option value="produccion">
                  {t("activities.notas.categories.produccion", { defaultValue: "Producción" })}
                </option>
                <option value="servicio">
                  {t("activities.notas.categories.servicio", { defaultValue: "Servicio" })}
                </option>
              </select>
            </div>
          )}
        </div>

        {/* Cuerpo de Contenido con Autocompletado @ */}
        <div className="relative">
          <div className="flex items-center justify-between mb-1">
            <label className="block text-xs font-bold text-foreground uppercase tracking-wider">
              {t("activities.notas.form.content_label", { defaultValue: "Contenido" })} *
            </label>
            <span className="text-[11px] text-muted-foreground">
              {t("activities.notas.form.mentions_hint", { defaultValue: "Menciona con @ o insumos con #" })}
            </span>
          </div>

          <textarea
            ref={textareaRef}
            required
            rows={4}
            value={contenido}
            onChange={handleContentChange}
            placeholder={t("activities.notas.form.content_placeholder", {
              defaultValue: "Escribe aquí la nota... Usa @usuario para mencionar o #insumo para etiquetar",
            })}
            className="w-full rounded-xl border border-border bg-background p-3 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-blue-500/50 shadow-sm resize-none"
          />

          {/* Menú flotante de menciones @ */}
          {mentionQuery !== null && filteredCollaborators.length > 0 && (
            <div className="absolute left-0 bottom-full mb-1 z-50 w-64 max-h-48 overflow-y-auto rounded-xl border border-border bg-card p-1 shadow-2xl">
              <div className="px-2 py-1 text-[10px] font-bold uppercase tracking-wider text-muted-foreground border-b border-border">
                {t("activities.notas.form.suggested_collaborators", { defaultValue: "Colaboradores sugeridos" })}
              </div>
              {filteredCollaborators.map((c) => (
                <button
                  key={c.id}
                  type="button"
                  onClick={() => handleSelectCollaborator(c)}
                  className="flex w-full items-center gap-2 rounded-lg px-2 py-1.5 text-xs text-foreground hover:bg-primary/10 transition-colors text-left"
                >
                  {c.avatar ? (
                    <img src={c.avatar} alt={c.name} className="h-6 w-6 rounded-full object-cover" />
                  ) : (
                    <div className="h-6 w-6 rounded-full bg-primary/20 text-primary flex items-center justify-center font-bold text-xs">
                      {c.name[0]}
                    </div>
                  )}
                  <div className="truncate">
                    <p className="font-semibold">{c.name}</p>
                    <p className="text-[10px] text-muted-foreground">@{c.username} • {c.role}</p>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Imagen adjunta en Cloudflare R2 */}
        {!isPersonal && (
          <div>
            <label className="block text-xs font-bold text-foreground uppercase tracking-wider mb-1">
              {t("activities.notas.form.attach_image", { defaultValue: "Adjuntar Foto R2 (URL)" })}
            </label>
            <div className="flex gap-2">
              <input
                type="url"
                value={fotoUrl}
                onChange={(e) => setFotoUrl(e.target.value)}
                placeholder="https://pub-r2.oppytec.cl/evidencias/..."
                className="w-full rounded-xl border border-border bg-background px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-blue-500/50 shadow-sm"
              />
              {fotoUrl && (
                <button
                  type="button"
                  onClick={() => setFotoUrl("")}
                  className="rounded-xl border border-border px-3 text-muted-foreground hover:bg-secondary hover:text-foreground"
                >
                  <X className="h-4 w-4" />
                </button>
              )}
            </div>
            {fotoUrl && (
              <div className="mt-2 h-24 w-36 overflow-hidden rounded-xl border border-border">
                <img src={fotoUrl} alt={t("activities.notas.form.image_preview", { defaultValue: "Vista previa" })} className="h-full w-full object-cover" />
              </div>
            )}
          </div>
        )}

        {/* Botones de acción */}
        <div className="flex items-center justify-end gap-2 border-t border-border pt-3">
          <button
            type="button"
            onClick={onClose}
            className="rounded-xl border border-border px-4 py-2 text-xs font-bold uppercase tracking-wider text-muted-foreground hover:bg-secondary transition-colors"
          >
            {t("activities.common.cancel", { defaultValue: "Cancelar" })}
          </button>
          <button
            type="submit"
            disabled={isSubmitting || !titulo.trim() || !contenido.trim()}
            className="rounded-xl bg-blue-600 px-5 py-2 text-xs font-bold uppercase tracking-wider text-white shadow-md shadow-blue-500/20 hover:bg-blue-700 disabled:opacity-50 transition-all cursor-pointer"
          >
            {isSubmitting
              ? t("activities.common.saving", { defaultValue: "Guardando..." })
              : t("activities.common.save", { defaultValue: "Guardar" })}
          </button>
        </div>
      </form>
    </ResponsiveDialog>
  );
}
