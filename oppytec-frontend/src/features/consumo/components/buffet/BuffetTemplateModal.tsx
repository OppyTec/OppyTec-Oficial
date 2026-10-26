// oppytec-frontend/src/features/consumo/components/buffet/BuffetTemplateModal.tsx
import { useState, useEffect } from "react";
import {
  Bookmark,
  X,
  Lock,
  Globe,
  Layers,
  Check,
} from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/shared/lib/utils";
import type { BuffetTemplate } from "../../types";

export interface BuffetTemplateModalProps {
  open: boolean;
  onClose: () => void;
  initialTemplate?: BuffetTemplate | null;
  onSaveTemplate: (data: {
    nombre: string;
    descripcion?: string;
    comensales_estimados?: number;
    estaciones_json: string[];
    is_public?: boolean;
    is_system?: boolean;
  }) => Promise<any> | any;
}

const COMMON_STATIONS = [
  "Estación Calientes",
  "Estación Fríos",
  "Barra de Ensaladas",
  "Panadería & Bollería",
  "Cafetería & Jugos",
  "Mesa de Postres",
  "Charcutería & Quesos",
  "Bebidas & Coctelería",
];

export function BuffetTemplateModal({
  open,
  onClose,
  initialTemplate,
  onSaveTemplate,
}: BuffetTemplateModalProps) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [paxEstimados, setPaxEstimados] = useState("50");
  const [stations, setStations] = useState<string[]>([]);
  const [newStationInput, setNewStationInput] = useState("");
  const [isPublic, setIsPublic] = useState(false);
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    if (open) {
      if (initialTemplate) {
        setName(initialTemplate.nombre || "");
        setDescription(initialTemplate.descripcion || "");
        setPaxEstimados(String(initialTemplate.comensales_estimados || 50));
        const mappedStations: string[] = initialTemplate.estaciones
          ? initialTemplate.estaciones.map((e) => (typeof e === "string" ? e : e.nombre_estacion))
          : ["Estación Calientes", "Estación Fríos"];
        setStations(mappedStations);
        setIsPublic(initialTemplate.isPublic ?? false);
      } else {
        setName("");
        setDescription("");
        setPaxEstimados("50");
        setStations(["Estación Calientes", "Estación Fríos", "Panadería & Bollería"]);
        setIsPublic(false);
      }
      setNewStationInput("");
    }
  }, [open, initialTemplate]);

  const handleAddStation = (stationName: string) => {
    const clean = stationName.trim();
    if (!clean) return;
    if (stations.includes(clean)) {
      toast.info(`La estación "${clean}" ya está en la lista`);
      return;
    }
    setStations((prev) => [...prev, clean]);
    setNewStationInput("");
  };

  const handleRemoveStation = (index: number) => {
    setStations((prev) => prev.filter((_, idx) => idx !== index));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) {
      toast.error("Debes ingresar un nombre para la plantilla");
      return;
    }
    if (stations.length === 0) {
      toast.error("Debes incluir al menos una estación en la plantilla");
      return;
    }

    setIsSaving(true);
    try {
      await onSaveTemplate({
        nombre: name.trim(),
        descripcion: description.trim() || undefined,
        comensales_estimados: parseInt(paxEstimados, 10) || 50,
        estaciones_json: stations,
        is_public: isPublic,
      });
      toast.success("Plantilla de buffet guardada exitosamente");
      onClose();
    } catch {
      toast.error("Error al guardar plantilla");
    } finally {
      setIsSaving(false);
    }
  };

  if (!open) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Gestor de Plantillas de Buffet"
      data-testid="buffet-template-modal"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4 overflow-y-auto"
    >
      <div className="w-full max-w-lg rounded-3xl bg-card border border-border text-foreground shadow-2xl overflow-hidden my-auto flex flex-col">
        {/* Encabezado */}
        <div className="px-6 py-4 border-b border-border bg-muted/40 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center text-cyan-400">
              <Bookmark className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-foreground">
                {initialTemplate ? "Editar Plantilla de Buffet" : "Nueva Plantilla de Buffet"}
              </h3>
              <p className="text-xs text-muted-foreground">
                Estandariza estaciones y bandejas gastronorm de servicio
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            disabled={isSaving}
            data-testid="close-buffet-template-btn"
            className="touch-target px-3 py-1.5 rounded-xl bg-secondary text-secondary-foreground text-xs font-semibold cursor-pointer"
          >
            Cerrar
          </button>
        </div>

        {/* Formulario */}
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div>
            <label htmlFor="buffet-tpl-name" className="block text-xs font-bold text-foreground mb-1.5">
              Nombre del Menú / Servicio
            </label>
            <input
              id="buffet-tpl-name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Ej. 🥐 Desayuno Buffet Ejecutivo"
              required
              data-testid="buffet-tpl-name-input"
              className="w-full px-3.5 py-2.5 rounded-xl bg-background border border-border text-foreground text-sm focus:border-cyan-500 focus:outline-none"
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label htmlFor="buffet-tpl-pax" className="block text-xs font-bold text-foreground mb-1.5">
                Comensales Estimados (Pax)
              </label>
              <input
                id="buffet-tpl-pax"
                type="number"
                min="1"
                value={paxEstimados}
                onChange={(e) => setPaxEstimados(e.target.value)}
                data-testid="buffet-tpl-pax-input"
                className="w-full px-3.5 py-2.5 rounded-xl bg-background border border-border text-foreground text-sm focus:border-cyan-500 focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-foreground mb-1.5">
                Visibilidad
              </label>
              <button
                type="button"
                onClick={() => setIsPublic(!isPublic)}
                data-testid="buffet-tpl-public-toggle"
                className={cn(
                  "w-full px-3.5 py-2.5 rounded-xl border text-xs font-semibold flex items-center justify-center gap-2 cursor-pointer transition-colors",
                  isPublic
                    ? "bg-cyan-500/10 border-cyan-500/40 text-cyan-400"
                    : "bg-muted border-border text-muted-foreground"
                )}
              >
                {isPublic ? (
                  <>
                    <Globe className="w-3.5 h-3.5" />
                    Pública (Todo el equipo)
                  </>
                ) : (
                  <>
                    <Lock className="w-3.5 h-3.5" />
                    Privada (Solo tú)
                  </>
                )}
              </button>
            </div>
          </div>

          <div>
            <label htmlFor="buffet-tpl-desc" className="block text-xs font-bold text-foreground mb-1.5">
              Descripción Operativa (Opcional)
            </label>
            <input
              id="buffet-tpl-desc"
              type="text"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Ej. Montaje estándar matutino: calientes, fríos y panadería"
              data-testid="buffet-tpl-desc-input"
              className="w-full px-3.5 py-2 rounded-xl bg-background border border-border text-foreground text-sm focus:border-cyan-500 focus:outline-none"
            />
          </div>

          {/* Selector de Estaciones */}
          <div>
            <label className="block text-xs font-bold text-foreground mb-1.5 flex items-center gap-1.5">
              <Layers className="w-3.5 h-3.5 text-cyan-500" />
              Estaciones Incluidas ({stations.length})
            </label>

            {/* Chips sugeridos */}
            <div className="flex flex-wrap gap-1.5 mb-2.5">
              {COMMON_STATIONS.map((st) => (
                <button
                  key={st}
                  type="button"
                  onClick={() => handleAddStation(st)}
                  className="px-2 py-1 rounded-lg bg-muted hover:bg-muted/80 text-muted-foreground hover:text-foreground text-[10px] font-semibold border border-border cursor-pointer transition-colors"
                >
                  + {st}
                </button>
              ))}
            </div>

            {/* Input para estación personalizada */}
            <div className="flex items-center gap-2 mb-3">
              <input
                type="text"
                value={newStationInput}
                onChange={(e) => setNewStationInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    e.preventDefault();
                    handleAddStation(newStationInput);
                  }
                }}
                placeholder="Nombre de otra estación..."
                data-testid="custom-station-input"
                className="flex-1 px-3 py-1.5 rounded-xl bg-background border border-border text-xs text-foreground focus:outline-none focus:border-cyan-500"
              />
              <button
                type="button"
                onClick={() => handleAddStation(newStationInput)}
                data-testid="add-custom-station-btn"
                className="px-3 py-1.5 rounded-xl bg-secondary hover:bg-secondary/80 text-secondary-foreground text-xs font-bold cursor-pointer"
              >
                Agregar
              </button>
            </div>

            {/* Lista de estaciones activas en la plantilla */}
            <div className="space-y-1.5 max-h-[140px] overflow-y-auto pr-1">
              {stations.map((st, idx) => (
                <div
                  key={st}
                  data-testid={`active-station-${idx}`}
                  className="px-3 py-2 rounded-xl bg-muted/40 border border-border/60 flex items-center justify-between text-xs"
                >
                  <span className="font-semibold text-foreground flex items-center gap-2">
                    <span className="w-5 h-5 rounded-md bg-cyan-500/20 text-cyan-400 text-[10px] font-mono font-bold flex items-center justify-center">
                      {idx + 1}
                    </span>
                    {st}
                  </span>
                  <button
                    type="button"
                    onClick={() => handleRemoveStation(idx)}
                    data-testid={`remove-station-${idx}`}
                    className="text-muted-foreground hover:text-rose-400 p-1 cursor-pointer"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                </div>
              ))}
            </div>
          </div>

          {/* Botones de acción */}
          <div className="flex items-center justify-end gap-3 pt-3 border-t border-border">
            <button
              type="button"
              onClick={onClose}
              disabled={isSaving}
              className="px-4 py-2.5 rounded-xl bg-secondary text-secondary-foreground text-xs font-semibold cursor-pointer"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={isSaving}
              data-testid="save-buffet-template-btn"
              className="touch-target px-5 py-2.5 rounded-xl bg-gradient-to-r from-cyan-500 to-teal-500 hover:from-cyan-400 hover:to-teal-400 text-black font-bold text-xs flex items-center gap-2 shadow-lg shadow-cyan-500/20 cursor-pointer disabled:opacity-50"
            >
              <Check className="w-4 h-4 stroke-[3]" />
              Guardar Plantilla
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
