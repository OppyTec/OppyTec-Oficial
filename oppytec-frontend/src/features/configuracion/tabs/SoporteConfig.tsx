import { useState } from "react";
import { MessageSquare, Send, Heart, Coffee, CheckCircle2 } from "lucide-react";
import { toast } from "sonner";
import { apiRequest } from "@/shared/api/httpClient";
import { translateKey, useLanguage } from "@/shared/i18n";

export function SoporteConfig() {
  useLanguage();
  const [mensaje, setMensaje] = useState("");
  const [sending, setSending] = useState(false);
  const [enviado, setEnviado] = useState(false);

  const handleSend = async () => {
    if (!mensaje.trim()) {
      toast.error(translateKey("configuracion", "soporte.toast_mensaje_requerido"));
      return;
    }
    setSending(true);
    try {
      await apiRequest("/operations/support-ticket", {
        method: "POST",
        body: {
          contenido: mensaje.trim(),
          origen: "Configuracion/Soporte",
          fechaIso: new Date().toISOString(),
        },
        fallbackData: { success: true },
      });
      toast.success(translateKey("configuracion", "soporte.toast_exito"));
      setMensaje("");
      setEnviado(true);
      setTimeout(() => setEnviado(false), 5000);
    } catch {
      toast.error(translateKey("configuracion", "soporte.toast_error"));
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="space-y-6" data-testid="soporte-config-section">
      <div className="space-y-1">
        <h3 className="text-sm font-black uppercase tracking-tight flex items-center gap-2">
          <MessageSquare className="h-4 w-4 text-primary" />{" "}
          {translateKey("configuracion", "soporte.header_title")}
        </h3>
        <p className="text-[10px] text-muted-foreground font-medium uppercase tracking-widest">
          {translateKey("configuracion", "soporte.header_subtitle")}
        </p>
      </div>

      <div className="space-y-4 rounded-2xl border-2 border-dashed border-border p-5 bg-card/40">
        <div className="space-y-2">
          <label className="text-xs font-bold uppercase tracking-widest text-muted-foreground block">
            {translateKey("configuracion", "soporte.mensaje_label")}
          </label>
          <textarea
            value={mensaje}
            onChange={(e) => setMensaje(e.target.value)}
            placeholder={translateKey("configuracion", "soporte.mensaje_placeholder")}
            rows={5}
            className="w-full p-3 rounded-xl border border-border bg-background text-sm outline-none focus:border-primary resize-none leading-relaxed"
          />
        </div>

        {enviado && (
          <div className="flex items-center gap-2 p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-600 text-xs font-bold">
            <CheckCircle2 className="h-4 w-4 shrink-0" />
            <span>{translateKey("configuracion", "soporte.success_banner")}</span>
          </div>
        )}

        <button
          type="button"
          onClick={handleSend}
          disabled={sending || !mensaje.trim()}
          className="w-full rounded-xl gap-2 font-black text-xs uppercase tracking-wider bg-primary hover:bg-primary/90 text-primary-foreground h-12 flex items-center justify-center cursor-pointer transition-all active:scale-[0.99] disabled:opacity-50 shadow-md"
        >
          <Send className="h-4 w-4" />
          {sending
            ? translateKey("configuracion", "soporte.boton_enviando")
            : translateKey("configuracion", "soporte.boton_enviar")}
        </button>
      </div>

      {/* Insignia Oficial OppyTec */}
      <div className="flex flex-col items-center justify-center pt-2 space-y-2 opacity-50 hover:opacity-100 transition-opacity">
        <p className="text-[9px] font-black uppercase tracking-widest text-center text-muted-foreground">
          {translateKey("configuracion", "soporte.credits")}
        </p>
        <div className="flex items-center gap-3">
          <Heart className="h-4 w-4 text-rose-500 fill-rose-500" />
          <Coffee className="h-4 w-4 text-amber-600" />
        </div>
      </div>
    </div>
  );
}

export default SoporteConfig;
