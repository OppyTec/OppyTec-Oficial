export type NotaCategoria =
  | "incidente"
  | "stock"
  | "produccion"
  | "servicio"
  | "general";

export interface NotaMencion {
  id: number;
  nota_id: number;
  user_id: number;
  username?: string;
}

export interface NotaLectura {
  id: number;
  nota_id: number;
  user_id: number;
  read_at: string;
  user_name?: string;
}

export interface NotaEquipo {
  id: number;
  autor_user_id: number;
  autor_name?: string;
  autor_role?: string;
  autor_avatar?: string;
  titulo: string;
  contenido: string;
  area_id: string | null;
  categoria: NotaCategoria | string;
  fecha: string | null;
  insumo_id: string | null;
  receta_id: number | null;
  foto_url: string | null;
  menciones: NotaMencion[];
  lecturas: NotaLectura[];
  leido_por_mi: boolean;
  total_lecturas: number;
  created_at: string | null;
}

export interface NotaPersonal {
  id: number;
  user_id: number;
  titulo: string;
  contenido: string;
  area_id: string | null;
  fecha: string | null;
  created_at: string | null;
}

export type TareaEstado = "pendiente" | "progreso" | "completada" | "incompleta";
export type TareaUrgencia = "alta" | "media" | "baja";

export interface Tarea {
  id: number;
  titulo: string;
  descripcion: string | null;
  creador_user_id: number | null;
  asignado_a_user_id: number | null;
  asignado_a_name?: string;
  asignado_a_role?: string;
  asignado_a_avatar?: string;
  area_id: string | null;
  estado: TareaEstado;
  urgencia: TareaUrgencia;
  fecha_limite: string | null;
  nota_incompleta: string | null;
  compra_id: string | null;
  foto_evidencia_url: string | null;
  plantilla_id: number | null;
  completada: boolean;
  created_at: string | null;
}

export interface PlantillaRutinaItem {
  titulo: string;
  descripcion?: string;
  urgencia?: TareaUrgencia;
}

export interface PlantillaRutina {
  id: number;
  nombre: string;
  descripcion: string | null;
  area_id: string | null;
  tipo_rutina: "APERTURA" | "CIERRE" | "LIMPIEZA" | "MANTENIMIENTO";
  frecuencia: "DIARIA" | "SEMANAL" | "MENSUAL";
  items_json: PlantillaRutinaItem[];
  is_active: boolean;
  usuario_creador_id?: number | null;
  created_at: string | null;
}

export interface TurnoHorario {
  id: number;
  user_id: number;
  user_name?: string;
  user_role?: string;
  user_avatar?: string;
  area_id: string | null;
  fecha_inicio: string | null; // YYYY-MM-DD
  fecha_fin: string | null;
  hora_inicio: string | null; // HH:MM or HH:MM:SS
  hora_fin: string | null;
  inicio_turno: string | null;
  fin_turno: string | null;
  nota: string | null;
  color: string | null;
  creado_por: number | null;
  created_at: string | null;
}

export interface AlertaLaboral {
  tipo: string;
  mensaje: string;
  severidad: "advertencia" | "bloqueo";
  detalle: Record<string, unknown>;
}

export interface ValidacionLaboral {
  tiene_alertas: boolean;
  total_horas_semanales: number | string;
  alertas: AlertaLaboral[];
}

export interface Collaborator {
  id: number;
  username: string;
  name: string;
  role: string;
  avatar?: string;
  area_id?: string;
  color?: string;
}

export interface MinutaPuntosClave {
  incidentes: string[];
  produccion: string[];
  tareas_pendientes: Array<{
    id: number;
    titulo: string;
    urgencia: string;
    asignado_a_user_id: number | null;
    estado: string;
    nota_incompleta: string;
  }>;
  dotacion: {
    total_colaboradores: number;
    colaboradores_ids: number[];
    total_turnos: number;
    turnos: Array<{
      id: number;
      user_id: number;
      hora_inicio: string | null;
      hora_fin: string | null;
      area_id: string | null;
    }>;
  };
}

export interface MinutaEstadisticas {
  total_notas: number;
  total_tareas: number;
  tareas_completadas: number;
  tareas_incompletas: number;
  total_turnos: number;
}

export interface MinutaTraspasoResponse {
  fecha: string;
  area_id: string | null;
  resumen_ejecutivo: string;
  puntos_clave: MinutaPuntosClave;
  estadisticas: MinutaEstadisticas;
  generado_en: string;
}

