import { useState, useRef, useEffect, type ChangeEvent } from "react";
import { Store, Upload, Check, Eye, Code, Bold, Italic, List, Link as LinkIcon } from "lucide-react";
import { toast } from "sonner";
import { apiRequest } from "@/shared/api/httpClient";
import { getImageUrl } from "@/shared/lib";
import { translateKey, useLanguage } from "@/shared/i18n";

export interface RestaurantSettings {
  nombre: string;
  tipo_negocio?: string | null;
  logo_url?: string | null;
  correo_respuestas?: string | null;
  firma_email_html?: string | null;
  dias_alerta_vencimiento?: number;
}

const TIPO_NEGOCIO_OPTIONS = [
  "Almacén",
  "Bar",
  "Bazar",
  "Cafetería",
  "Hostal",
  "Hotel",
  "Motel",
  "Pub",
  "Restobar",
  "Restaurante",
].sort();

const DEFAULT_SETTINGS: RestaurantSettings = {
  nombre: "Mi Restaurante",
  tipo_negocio: "Restaurante",
  logo_url: null,
  correo_respuestas: "contacto@oppytec.cl",
  firma_email_html: "<p><strong>Administración</strong><br/>Sistema de Gestión OppyTec</p>",
  dias_alerta_vencimiento: 5,
};

export interface RestauranteConfigProps {
  readonly initialSettings?: RestaurantSettings;
  readonly onUpdate?: () => void;
}

export function RestauranteConfig({ initialSettings, onUpdate }: RestauranteConfigProps) {
  useLanguage();
  const [nombre, setNombre] = useState(initialSettings?.nombre || DEFAULT_SETTINGS.nombre);
  const [tipoNegocio, setTipoNegocio] = useState(
    initialSettings?.tipo_negocio || DEFAULT_SETTINGS.tipo_negocio || "Restaurante"
  );
  const [correoRespuestas, setCorreoRespuestas] = useState(
    initialSettings?.correo_respuestas || DEFAULT_SETTINGS.correo_respuestas || ""
  );
  const [firmaEmail, setFirmaEmail] = useState(
    initialSettings?.firma_email_html || DEFAULT_SETTINGS.firma_email_html || ""
  );
  const [diasAlerta, setDiasAlerta] = useState(
    initialSettings?.dias_alerta_vencimiento || DEFAULT_SETTINGS.dias_alerta_vencimiento || 5
  );
  const [logoPreview, setLogoPreview] = useState<string | null>(initialSettings?.logo_url || null);
  const [saving, setSaving] = useState(false);
  const [activeFirmaTab, setActiveFirmaTab] = useState<"edit" | "preview">("edit");

  const fileInputRef = useRef<HTMLInputElement>(null);
  const firmaTextareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (initialSettings) {
      if (initialSettings.nombre) setNombre(initialSettings.nombre);
      if (initialSettings.tipo_negocio) setTipoNegocio(initialSettings.tipo_negocio);
      if (initialSettings.correo_respuestas !== undefined) {
        setCorreoRespuestas(initialSettings.correo_respuestas || "");
      }
      if (initialSettings.firma_email_html !== undefined) {
        setFirmaEmail(initialSettings.firma_email_html || "");
      }
      if (initialSettings.dias_alerta_vencimiento !== undefined) {
        setDiasAlerta(initialSettings.dias_alerta_vencimiento);
      }
      if (initialSettings.logo_url !== undefined) {
        setLogoPreview(initialSettings.logo_url);
      }
    }
  }, [initialSettings]);

  const handleSave = async () => {
    if (!nombre.trim()) {
      toast.error(translateKey("configuracion", "negocio.toast_nombre_obligatorio"));
      return;
    }
    setSaving(true);
    try {
      await apiRequest("/settings/restaurant", {
        method: "PUT",
        body: {
          nombre: nombre.trim(),
          tipo_negocio: tipoNegocio,
          dias_alerta_vencimiento: diasAlerta,
          correo_respuestas: correoRespuestas.trim() || null,
          firma_email_html: firmaEmail.trim() || null,
        },
        fallbackData: { success: true },
      });
      toast.success(translateKey("configuracion", "negocio.toast_exito"));
      window.dispatchEvent(new CustomEvent("restaurant-config-changed"));
      if (onUpdate) onUpdate();
    } catch {
      toast.error(translateKey("configuracion", "negocio.toast_error"));
    } finally {
      setSaving(false);
    }
  };

  const handleLogoUpload = (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!file.type.startsWith("image/")) {
      toast.error(translateKey("configuracion", "negocio.toast_formato_imagen"));
      return;
    }

    const localUrl = URL.createObjectURL(file);
    setLogoPreview(localUrl);
    toast.success(translateKey("configuracion", "negocio.toast_logo_actualizado"));
  };

  const insertTag = (openTag: string, closeTag: string) => {
    const textarea = firmaTextareaRef.current;
    if (!textarea) return;
    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const selected = firmaEmail.substring(start, end);
    const replacement = `${openTag}${selected || "texto"}${closeTag}`;
    const nextText = firmaEmail.substring(0, start) + replacement + firmaEmail.substring(end);
    setFirmaEmail(nextText);
    setTimeout(() => {
      textarea.focus();
      textarea.setSelectionRange(start + openTag.length, start + openTag.length + (selected.length || 5));
    }, 0);
  };

  return (
    <div className="space-y-6 py-2" data-testid="restaurante-config-form">
      <div className="flex flex-col md:flex-row gap-6">
        {/* Left Side: Business Info */}
        <div className="flex-1 space-y-4">
          <div className="space-y-2">
            <label className="text-xs font-bold uppercase text-muted-foreground tracking-widest block">
              {translateKey("configuracion", "negocio.tipo_negocio_label")}
            </label>
            <select
              value={tipoNegocio}
              onChange={(e) => setTipoNegocio(e.target.value)}
              className="w-full h-11 rounded-xl border border-border bg-background px-3 text-sm font-medium focus:border-primary transition-colors outline-none cursor-pointer"
            >
              <option value="" disabled>
                {translateKey("configuracion", "negocio.tipo_negocio_placeholder")}
              </option>
              {TIPO_NEGOCIO_OPTIONS.map((opt) => (
                <option key={opt} value={opt}>
                  {translateKey("configuracion", `negocio.tipos.${opt}`) || opt}
                </option>
              ))}
            </select>
            <p className="text-[10px] text-muted-foreground font-medium uppercase italic">
              {translateKey("configuracion", "negocio.tipo_negocio_help")}
            </p>
          </div>

          <div className="space-y-2">
            <label className="text-xs font-bold uppercase text-muted-foreground tracking-widest block">
              {translateKey("configuracion", "negocio.nombre_label")}
            </label>
            <input
              type="text"
              value={nombre}
              onChange={(e) => setNombre(e.target.value)}
              placeholder={translateKey("configuracion", "negocio.nombre_placeholder")}
              className="w-full h-11 rounded-xl border border-border bg-background px-3 font-bold text-lg focus:border-primary transition-colors outline-none"
            />
          </div>

          <div className="space-y-2">
            <label className="text-xs font-bold uppercase text-muted-foreground tracking-widest block">
              {translateKey("configuracion", "negocio.dias_alerta_label")}
            </label>
            <input
              type="number"
              min={1}
              max={60}
              value={diasAlerta}
              onChange={(e) => setDiasAlerta(Number(e.target.value))}
              className="w-full h-11 rounded-xl border border-border bg-background px-3 text-sm font-medium focus:border-primary transition-colors outline-none"
            />
            <p className="text-[10px] text-muted-foreground font-medium uppercase italic">
              {translateKey("configuracion", "negocio.dias_alerta_help")}
            </p>
          </div>
        </div>

        {/* Right Side: Logo Upload */}
        <div className="w-full md:w-52 space-y-2 shrink-0">
          <label className="text-xs font-bold uppercase text-muted-foreground tracking-widest block">
            {translateKey("configuracion", "negocio.logo_label")}
          </label>
          <div className="flex flex-row md:flex-col items-center gap-4 bg-muted/20 p-4 rounded-2xl border-2 border-dashed border-border">
            <div className="h-24 w-24 rounded-xl border border-border bg-background flex items-center justify-center overflow-hidden shrink-0 shadow-inner">
              {logoPreview ? (
                <img
                  src={logoPreview.startsWith("blob:") ? logoPreview : getImageUrl(logoPreview)}
                  className="h-full w-full object-contain p-1"
                  alt={translateKey("configuracion", "negocio.logo_alt")}
                />
              ) : (
                <Store className="h-10 w-10 text-muted-foreground/40" />
              )}
            </div>
            <div className="flex flex-col gap-2 w-full">
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                className="w-full rounded-xl border border-border hover:bg-secondary transition-colors font-bold text-[10px] uppercase tracking-widest h-9 bg-background flex items-center justify-center gap-2 cursor-pointer"
              >
                <Upload className="h-3.5 w-3.5" /> {translateKey("configuracion", "negocio.cambiar_logo")}
              </button>
              <input
                ref={fileInputRef}
                type="file"
                className="hidden"
                accept="image/*"
                onChange={handleLogoUpload}
              />
            </div>
          </div>
        </div>
      </div>

      {/* Communications / Reply-To & HTML Signature */}
      <div className="space-y-4 pt-4 border-t border-border">
        <h3 className="text-sm font-bold uppercase text-muted-foreground tracking-widest">
          {translateKey("configuracion", "negocio.seccion_correos")}
        </h3>

        <div className="space-y-2">
          <label className="text-xs font-bold uppercase text-muted-foreground tracking-widest block">
            {translateKey("configuracion", "negocio.correo_respuestas_label")}
          </label>
          <input
            type="email"
            value={correoRespuestas}
            onChange={(e) => setCorreoRespuestas(e.target.value)}
            placeholder={translateKey("configuracion", "negocio.correo_respuestas_placeholder")}
            className="w-full h-11 rounded-xl border border-border bg-background px-3 text-sm font-medium focus:border-primary transition-colors outline-none"
          />
          <p className="text-[10px] text-muted-foreground font-medium uppercase italic">
            {translateKey("configuracion", "negocio.correo_respuestas_help")}
          </p>
        </div>

        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <label className="text-xs font-bold uppercase text-muted-foreground tracking-widest">
              {translateKey("configuracion", "negocio.firma_label")}
            </label>
            <div className="flex rounded-lg border border-border p-0.5 bg-secondary/30">
              <button
                type="button"
                onClick={() => setActiveFirmaTab("edit")}
                className={`flex items-center gap-1.5 px-2.5 py-1 text-xs font-semibold rounded-md transition-colors ${
                  activeFirmaTab === "edit"
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                <Code className="h-3 w-3" /> {translateKey("configuracion", "negocio.tab_editor")}
              </button>
              <button
                type="button"
                onClick={() => setActiveFirmaTab("preview")}
                className={`flex items-center gap-1.5 px-2.5 py-1 text-xs font-semibold rounded-md transition-colors ${
                  activeFirmaTab === "preview"
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                <Eye className="h-3 w-3" /> {translateKey("configuracion", "negocio.tab_preview")}
              </button>
            </div>
          </div>

          {activeFirmaTab === "edit" ? (
            <div className="rounded-xl border border-border overflow-hidden bg-background">
              {/* Simple HTML Toolbar */}
              <div className="flex items-center gap-1 p-2 border-b border-border bg-secondary/20">
                <button
                  type="button"
                  title={translateKey("configuracion", "negocio.toolbar_bold")}
                  onClick={() => insertTag("<strong>", "</strong>")}
                  className="p-1.5 rounded hover:bg-secondary text-muted-foreground hover:text-foreground cursor-pointer"
                >
                  <Bold className="h-3.5 w-3.5" />
                </button>
                <button
                  type="button"
                  title={translateKey("configuracion", "negocio.toolbar_italic")}
                  onClick={() => insertTag("<em>", "</em>")}
                  className="p-1.5 rounded hover:bg-secondary text-muted-foreground hover:text-foreground cursor-pointer"
                >
                  <Italic className="h-3.5 w-3.5" />
                </button>
                <button
                  type="button"
                  title={translateKey("configuracion", "negocio.toolbar_list")}
                  onClick={() => insertTag("<ul><li>", "</li></ul>")}
                  className="p-1.5 rounded hover:bg-secondary text-muted-foreground hover:text-foreground cursor-pointer"
                >
                  <List className="h-3.5 w-3.5" />
                </button>
                <button
                  type="button"
                  title={translateKey("configuracion", "negocio.toolbar_link")}
                  onClick={() => insertTag('<a href="https://">', "</a>")}
                  className="p-1.5 rounded hover:bg-secondary text-muted-foreground hover:text-foreground cursor-pointer"
                >
                  <LinkIcon className="h-3.5 w-3.5" />
                </button>
              </div>
              <textarea
                ref={firmaTextareaRef}
                value={firmaEmail}
                onChange={(e) => setFirmaEmail(e.target.value)}
                placeholder={translateKey("configuracion", "negocio.firma_placeholder")}
                rows={5}
                className="w-full p-3 font-mono text-xs bg-background outline-none resize-none"
              />
            </div>
          ) : (
            <div
              className="rounded-xl border border-border p-4 bg-card/60 min-h-[140px] text-sm"
              dangerouslySetInnerHTML={{
                __html:
                  firmaEmail ||
                  `<p class='text-muted-foreground'>${translateKey(
                    "configuracion",
                    "negocio.firma_vacia"
                  )}</p>`,
              }}
            />
          )}

          <p className="text-[10px] text-muted-foreground font-medium uppercase italic">
            {translateKey("configuracion", "negocio.firma_help")}
          </p>
        </div>
      </div>

      <div className="pt-2">
        <button
          type="button"
          onClick={handleSave}
          disabled={saving}
          className="w-full h-12 rounded-xl font-black text-xs uppercase tracking-widest bg-primary hover:bg-primary/90 text-primary-foreground shadow-lg shadow-primary/20 transition-all active:scale-[0.98] flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50"
        >
          <Check className="h-4 w-4" />
          {saving
            ? translateKey("configuracion", "negocio.guardando")
            : translateKey("configuracion", "negocio.guardar")}
        </button>
      </div>
    </div>
  );
}

export default RestauranteConfig;
