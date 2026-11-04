"""
oppytec-backend/src/modules/operations/presentation/schemas_actividades.py
Contratos Pydantic v2 para el Panel de Actividades de OppyTec v2.0:
- Notas de Equipo y Personales (con menciones y lecturas)
- Tareas Operativas, Checklists y Plantillas de Rutinas
- Horarios, Turnos, Clonación Semanal y Alertas Laborales (Ley 40 Horas / Descanso 12h)

Cumple:
- ConfigDict(extra="forbid") en todos los requests.
- Tipado estricto mypy --strict.
- 0 floats (Decimal para horas y métricas).
"""
# mypy: disable-error-code="explicit-any"
from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator
from src.core.guards.xss_sanitizer import sanitize_text_input


# ==============================================================================
# SCHEMAS: NOTAS DE EQUIPO Y PERSONALES
# ==============================================================================


class NotaMencionResponse(BaseModel):
    """Representación de una mención de colaborador en una nota."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    nota_id: int
    user_id: int


class NotaLecturaResponse(BaseModel):
    """Registro de visto / lectura confirmada de una nota."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    nota_id: int
    user_id: int
    read_at: datetime


class NotaEquipoCreateRequest(BaseModel):
    """Payload para crear una nueva nota en la bitácora compartida del equipo."""

    model_config = ConfigDict(extra="forbid")

    titulo: str = Field(..., min_length=1, max_length=160, description="Título descriptivo de la novedad")
    contenido: str = Field(..., min_length=1, description="Cuerpo detallado de la nota de equipo")
    area_id: str | None = Field(default=None, max_length=64, description="Área operativa asociada")
    categoria: str = Field(default="general", max_length=40, description="Categoría (ej: general, cocina, mantención)")
    fecha: datetime | None = Field(default=None, description="Fecha/hora de la nota (por defecto actual)")
    insumo_id: str | None = Field(default=None, max_length=64, description="Insumo relacionado si aplica")
    receta_id: int | None = Field(default=None, description="Receta relacionada si aplica")
    foto_url: str | None = Field(default=None, max_length=500, description="URL en Cloudflare R2 de evidencia fotográfica")
    menciones_user_ids: list[int] = Field(default_factory=list, description="Lista de IDs de usuarios mencionados")

    @field_validator("titulo")
    @classmethod
    def _sanitize_titulo(cls, value: str) -> str:
        return sanitize_text_input(value, field_name="titulo")

    @field_validator("contenido")
    @classmethod
    def _sanitize_contenido(cls, value: str) -> str:
        return sanitize_text_input(value, field_name="contenido")


class NotaEquipoUpdateRequest(BaseModel):
    """Payload para actualizar una nota existente."""

    model_config = ConfigDict(extra="forbid")

    titulo: str | None = Field(default=None, min_length=1, max_length=160)
    contenido: str | None = Field(default=None, min_length=1)
    area_id: str | None = Field(default=None, max_length=64)
    categoria: str | None = Field(default=None, max_length=40)
    insumo_id: str | None = Field(default=None, max_length=64)
    receta_id: int | None = None
    foto_url: str | None = Field(default=None, max_length=500)
    menciones_user_ids: list[int] | None = None

    @field_validator("titulo")
    @classmethod
    def _sanitize_titulo(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return sanitize_text_input(value, field_name="titulo")

    @field_validator("contenido")
    @classmethod
    def _sanitize_contenido(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return sanitize_text_input(value, field_name="contenido")


class NotaEquipoResponse(BaseModel):
    """Respuesta con el detalle enriquecido de una nota de equipo."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    autor_user_id: int
    titulo: str
    contenido: str
    area_id: str | None = None
    categoria: str = "general"
    fecha: datetime | None = None
    insumo_id: str | None = None
    receta_id: int | None = None
    foto_url: str | None = None
    menciones: list[NotaMencionResponse] = Field(default_factory=list)
    lecturas: list[NotaLecturaResponse] = Field(default_factory=list)
    leido_por_mi: bool = False
    total_lecturas: int = 0
    created_at: datetime | None = None


class NotaPersonalCreateRequest(BaseModel):
    """Payload para crear una nota privada individual del colaborador."""

    model_config = ConfigDict(extra="forbid")

    titulo: str = Field(..., min_length=1, max_length=160, description="Título de la nota personal")
    contenido: str = Field(..., min_length=1, description="Contenido de la nota personal")
    area_id: str | None = Field(default=None, max_length=64, description="Área asociada")
    fecha: datetime | None = Field(default=None, description="Fecha de recordatorio")

    @field_validator("titulo")
    @classmethod
    def _sanitize_titulo(cls, value: str) -> str:
        return sanitize_text_input(value, field_name="titulo")

    @field_validator("contenido")
    @classmethod
    def _sanitize_contenido(cls, value: str) -> str:
        return sanitize_text_input(value, field_name="contenido")


class NotaPersonalUpdateRequest(BaseModel):
    """Payload para editar una nota privada individual."""

    model_config = ConfigDict(extra="forbid")

    titulo: str | None = Field(default=None, min_length=1, max_length=160)
    contenido: str | None = Field(default=None, min_length=1)
    area_id: str | None = Field(default=None, max_length=64)
    fecha: datetime | None = None

    @field_validator("titulo")
    @classmethod
    def _sanitize_titulo(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return sanitize_text_input(value, field_name="titulo")

    @field_validator("contenido")
    @classmethod
    def _sanitize_contenido(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return sanitize_text_input(value, field_name="contenido")


class NotaPersonalResponse(BaseModel):
    """Respuesta con los datos de una nota privada."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    titulo: str
    contenido: str
    area_id: str | None = None
    fecha: datetime | None = None
    created_at: datetime | None = None


# ==============================================================================
# SCHEMAS: TAREAS, CHECKLISTS Y PLANTILLAS DE RUTINAS
# ==============================================================================


class TareaCreateRequest(BaseModel):
    """Payload para dar de alta una nueva tarea operativa."""

    model_config = ConfigDict(extra="forbid")

    titulo: str = Field(..., min_length=1, max_length=180, description="Título de la tarea")
    descripcion: str | None = Field(default=None, description="Descripción detallada")
    asignado_a_user_id: int | None = Field(default=None, description="Colaborador responsable")
    area_id: str | None = Field(default=None, max_length=64, description="Área asignada")
    estado: str = Field(
        default="pendiente",
        pattern=r"^(pendiente|progreso|completada|incompleta)$",
        description="Estado inicial ('pendiente', 'progreso', 'completada', 'incompleta')",
    )
    urgencia: str = Field(
        default="media",
        pattern=r"^(alta|media|baja)$",
        description="Nivel de urgencia ('alta', 'media', 'baja')",
    )
    fecha_limite: datetime | None = Field(default=None, description="Fecha y hora límite de ejecución")
    nota_incompleta: str | None = Field(default=None, description="Justificación si se crea incompleta")
    compra_id: str | None = Field(default=None, max_length=64, description="Orden de compra asociada")
    foto_evidencia_url: str | None = Field(default=None, max_length=500, description="Foto de cumplimiento")
    plantilla_id: int | None = Field(default=None, description="Plantilla originaria")
    completada: bool = Field(default=False, description="Flag booleano de completitud")

    @field_validator("titulo")
    @classmethod
    def _sanitize_titulo(cls, value: str) -> str:
        return sanitize_text_input(value, field_name="titulo")

    @field_validator("descripcion")
    @classmethod
    def _sanitize_descripcion(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return sanitize_text_input(value, field_name="descripcion")

    @field_validator("nota_incompleta")
    @classmethod
    def _sanitize_nota_incompleta(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return sanitize_text_input(value, field_name="nota_incompleta")


class TareaEstadoUpdateRequest(BaseModel):
    """
    Payload exclusivo para la transición de estado de una tarea.
    Regla Crítica: Si 'estado' pasa a 'incompleta', 'nota_incompleta' es estrictamente requerida.
    """

    model_config = ConfigDict(extra="forbid")

    estado: str = Field(
        ...,
        pattern=r"^(pendiente|progreso|completada|incompleta)$",
        description="Nuevo estado de la tarea",
    )
    nota_incompleta: str | None = Field(
        default=None,
        description="Motivo obligatorio cuando el estado cambia a 'incompleta'",
    )
    foto_evidencia_url: str | None = Field(default=None, max_length=500)
    completada: bool | None = Field(default=None)

    @field_validator("nota_incompleta")
    @classmethod
    def _sanitize_nota_incompleta(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return sanitize_text_input(value, field_name="nota_incompleta")


class TareaUpdateRequest(BaseModel):
    """Payload para actualizar datos generales de una tarea."""

    model_config = ConfigDict(extra="forbid")

    titulo: str | None = Field(default=None, min_length=1, max_length=180)
    descripcion: str | None = None
    asignado_a_user_id: int | None = None
    area_id: str | None = Field(default=None, max_length=64)
    estado: str | None = Field(default=None, pattern=r"^(pendiente|progreso|completada|incompleta)$")
    urgencia: str | None = Field(default=None, pattern=r"^(alta|media|baja)$")
    fecha_limite: datetime | None = None
    nota_incompleta: str | None = None
    compra_id: str | None = Field(default=None, max_length=64)
    foto_evidencia_url: str | None = Field(default=None, max_length=500)
    completada: bool | None = None

    @field_validator("titulo")
    @classmethod
    def _sanitize_titulo(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return sanitize_text_input(value, field_name="titulo")

    @field_validator("descripcion")
    @classmethod
    def _sanitize_descripcion(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return sanitize_text_input(value, field_name="descripcion")

    @field_validator("nota_incompleta")
    @classmethod
    def _sanitize_nota_incompleta(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return sanitize_text_input(value, field_name="nota_incompleta")


class TareaResponse(BaseModel):
    """Respuesta con los datos completos de una tarea operativa."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    titulo: str
    descripcion: str | None = None
    creador_user_id: int | None = None
    asignado_a_user_id: int | None = None
    area_id: str | None = None
    estado: str
    urgencia: str
    fecha_limite: datetime | None = None
    nota_incompleta: str | None = None
    compra_id: str | None = None
    foto_evidencia_url: str | None = None
    plantilla_id: int | None = None
    completada: bool
    created_at: datetime | None = None


class PlantillaRutinaCreateRequest(BaseModel):
    """Payload para crear una plantilla reutilizable de apertura, cierre o limpieza."""

    model_config = ConfigDict(extra="forbid")

    nombre: str = Field(..., min_length=1, max_length=160, description="Nombre de la rutina")
    descripcion: str | None = Field(default=None, description="Detalles o instrucciones generales")
    area_id: str | None = Field(default=None, max_length=64, description="Área asociada")
    tipo_rutina: str = Field(
        default="APERTURA",
        pattern=r"^(APERTURA|CIERRE|LIMPIEZA|MANTENIMIENTO)$",
        description="Tipo de rutina ('APERTURA', 'CIERRE', 'LIMPIEZA', 'MANTENIMIENTO')",
    )
    frecuencia: str = Field(
        default="DIARIA",
        pattern=r"^(DIARIA|SEMANAL|MENSUAL)$",
        description="Frecuencia ('DIARIA', 'SEMANAL', 'MENSUAL')",
    )
    items_json: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Lista de tareas del checklist (título, descripción, urgencia)",
    )
    is_active: bool = Field(default=True, description="Estado activo de la plantilla")

    @field_validator("nombre")
    @classmethod
    def _sanitize_nombre(cls, value: str) -> str:
        return sanitize_text_input(value, field_name="nombre")

    @field_validator("descripcion")
    @classmethod
    def _sanitize_descripcion(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return sanitize_text_input(value, field_name="descripcion")


class PlantillaRutinaUpdateRequest(BaseModel):
    """Payload para actualizar una plantilla de rutina."""

    model_config = ConfigDict(extra="forbid")

    nombre: str | None = Field(default=None, min_length=1, max_length=160)
    descripcion: str | None = None
    area_id: str | None = Field(default=None, max_length=64)
    tipo_rutina: str | None = Field(default=None, pattern=r"^(APERTURA|CIERRE|LIMPIEZA|MANTENIMIENTO)$")
    frecuencia: str | None = Field(default=None, pattern=r"^(DIARIA|SEMANAL|MENSUAL)$")
    items_json: list[dict[str, Any]] | None = None
    is_active: bool | None = None

    @field_validator("nombre")
    @classmethod
    def _sanitize_nombre(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return sanitize_text_input(value, field_name="nombre")

    @field_validator("descripcion")
    @classmethod
    def _sanitize_descripcion(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return sanitize_text_input(value, field_name="descripcion")


class PlantillaRutinaResponse(BaseModel):
    """Respuesta con los datos de una plantilla de rutina."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    descripcion: str | None = None
    area_id: str | None = None
    tipo_rutina: str
    frecuencia: str
    items_json: list[dict[str, Any]] = Field(default_factory=list)
    is_active: bool
    usuario_creador_id: int | None = None
    created_at: datetime | None = None


class AplicarPlantillaRequest(BaseModel):
    """Payload para instanciar las tareas operativas a partir de una plantilla."""

    model_config = ConfigDict(extra="forbid")

    asignado_a_user_id: int | None = Field(default=None, description="Usuario al que se asignan las tareas")
    fecha_limite: datetime | None = Field(default=None, description="Fecha límite para el lote de tareas")
    area_id: str | None = Field(default=None, max_length=64, description="Sobrescribir área si aplica")


# ==============================================================================
# SCHEMAS: HORARIOS, TURNOS, ALERTAS LABORALES Y CLONACIÓN
# ==============================================================================


class TurnoHorarioCreateRequest(BaseModel):
    """Payload para registrar un turno horario."""

    model_config = ConfigDict(extra="forbid")

    user_id: int = Field(..., description="ID del colaborador asignado")
    usuario_id: int | None = Field(default=None, description="Alias compatible")
    area_id: str | None = Field(default=None, max_length=64, description="Área operativa")
    fecha_inicio: date | None = Field(default=None, description="Fecha de inicio")
    fecha_fin: date | None = Field(default=None, description="Fecha de fin")
    hora_inicio: time | None = Field(default=None, description="Hora de entrada")
    hora_fin: time | None = Field(default=None, description="Hora de salida")
    inicio_turno: datetime | None = Field(default=None, description="Timestamp UTC exacto de entrada")
    fin_turno: datetime | None = Field(default=None, description="Timestamp UTC exacto de salida")
    nota: str | None = Field(default=None, max_length=500, description="Observaciones del turno")
    color: str | None = Field(default=None, max_length=20, description="Color visual para el calendario")

    @field_validator("nota")
    @classmethod
    def _sanitize_nota(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return sanitize_text_input(value, field_name="nota")


class TurnoHorarioUpdateRequest(BaseModel):
    """Payload para modificar un turno horario existente."""

    model_config = ConfigDict(extra="forbid")

    user_id: int | None = None
    area_id: str | None = Field(default=None, max_length=64)
    fecha_inicio: date | None = None
    fecha_fin: date | None = None
    hora_inicio: time | None = None
    hora_fin: time | None = None
    inicio_turno: datetime | None = None
    fin_turno: datetime | None = None
    nota: str | None = Field(default=None, max_length=500)
    color: str | None = Field(default=None, max_length=20)

    @field_validator("nota")
    @classmethod
    def _sanitize_nota(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return sanitize_text_input(value, field_name="nota")


class TurnoHorarioResponse(BaseModel):
    """Respuesta con los datos de un turno horario."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    usuario_id: int | None = None
    area_id: str | None = None
    fecha_inicio: date | None = None
    fecha_fin: date | None = None
    hora_inicio: time | None = None
    hora_fin: time | None = None
    inicio_turno: datetime | None = None
    fin_turno: datetime | None = None
    nota: str | None = None
    color: str | None = None
    creado_por: int | None = None
    created_at: datetime | None = None


class ClonarSemanaRequest(BaseModel):
    """Payload para clonar la grilla de turnos de una semana a otra."""

    model_config = ConfigDict(extra="forbid")

    fecha_lunes_origen: date = Field(..., description="Fecha del lunes de la semana que se desea copiar")
    fecha_lunes_destino: date = Field(..., description="Fecha del lunes de la semana donde se pegará")
    area_id: str | None = Field(default=None, max_length=64, description="Filtrar por área específica")


class AlertaLaboralItem(BaseModel):
    """Representación de una alerta laboral detectada (Ley 40 Horas / Descanso 12h)."""

    model_config = ConfigDict(extra="forbid")

    tipo: str = Field(..., description="'DESCANSO_INSUFICIENTE' | 'EXCESO_40_HORAS'")
    mensaje: str = Field(..., description="Mensaje explicativo para el administrador")
    severidad: str = Field(default="advertencia", description="'advertencia' | 'bloqueo'")
    detalle: dict[str, Any] = Field(default_factory=dict, description="Metadatos numéricos del cálculo")


class ValidacionLaboralResponse(BaseModel):
    """Respuesta de la auditoría de jornadas y descansos obligatorios."""

    model_config = ConfigDict(extra="forbid")

    tiene_alertas: bool
    total_horas_semanales: Decimal = Field(default=Decimal("0.00"), description="Horas proyectadas en la semana")
    alertas: list[AlertaLaboralItem] = Field(default_factory=list)


class ValidarTurnoAlertaRequest(BaseModel):
    """Payload para simular si un turno planificado genera alertas laborales antes de guardarlo."""

    model_config = ConfigDict(extra="forbid")

    user_id: int = Field(..., description="ID del colaborador a evaluar")
    fecha_inicio: date | None = None
    fecha_fin: date | None = None
    hora_inicio: time | None = None
    hora_fin: time | None = None
    inicio_turno: datetime | None = None
    fin_turno: datetime | None = None
    turno_id_excluir: int | None = Field(default=None, description="ID del turno si se está editando")


# ==============================================================================
# SCHEMAS: MINUTA EJECUTIVA DE TRASPASO DE TURNO (OPPYFY AI)
# ==============================================================================


class MinutaTraspasoRequest(BaseModel):
    """Payload para solicitar la síntesis ejecutiva de traspaso de turno con OppyFy."""

    model_config = ConfigDict(extra="forbid")

    fecha: date | None = Field(default=None, description="Fecha del turno a consolidar (por defecto hoy)")
    area_id: str | None = Field(default=None, max_length=64, description="Área operativa específica o None para global")


class MinutaPuntosClave(BaseModel):
    """4 Puntos Clave de la minuta ejecutiva para Chef / Gerente."""

    model_config = ConfigDict(extra="forbid")

    incidentes: list[str] = Field(default_factory=list, description="Incidentes y novedades críticas reportadas")
    produccion: list[str] = Field(default_factory=list, description="Avances de producción, mermas o quiebres de stock")
    tareas_pendientes: list[dict[str, Any]] = Field(default_factory=list, description="Tareas no completadas con su justificación")
    dotacion: dict[str, Any] = Field(default_factory=dict, description="Resumen de dotación y colaboradores del turno")


class MinutaEstadisticas(BaseModel):
    """Métricas cuantitativas del turno."""

    model_config = ConfigDict(extra="forbid")

    total_notas: int = 0
    total_tareas: int = 0
    tareas_completadas: int = 0
    tareas_incompletas: int = 0
    total_turnos: int = 0


class MinutaTraspasoResponse(BaseModel):
    """Minuta ejecutiva generada por OppyFy lista para traspaso de turno."""

    model_config = ConfigDict(extra="forbid")

    fecha: date = Field(..., description="Fecha consolidada")
    area_id: str | None = Field(default=None, description="Área operativa")
    resumen_ejecutivo: str = Field(..., description="Síntesis narrativa estructurada en Markdown lista para lectura o copiado")
    puntos_clave: MinutaPuntosClave = Field(..., description="4 Puntos clave estructurados")
    estadisticas: MinutaEstadisticas = Field(..., description="Estadísticas cuantitativas")
    generado_en: datetime = Field(..., description="Timestamp de generación UTC")

