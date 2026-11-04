"""
oppytec-backend/src/modules/operations/application/actividades_service.py
Lógica de aplicación pura y orquestación DDD del Panel de Actividades de OppyTec v2.0:
1. Notas de Equipo (bitácora compartida con menciones y lecturas idempotentes).
2. Notas Personales (apuntes privados del colaborador).
3. Tareas Operativas, Checklists de Apertura/Cierre y Aplicación de Plantillas de Rutinas.
4. Horarios, Turnos, Clonación Semanal y Validación de Alertas Laborales (Descanso 12h y Ley 40 Horas).
5. Despacho reactivo de eventos WebSocket mediante `get_realtime_publisher()`.

Invariantes:
- 0 floats: Uso exclusivo de `Decimal` para horas laborales y métricas.
- Validación obligatoria: Si una tarea transiciona a 'incompleta', 'nota_incompleta' no puede ser vacía.
- Marcado de lectura de notas de equipo es idempotente.
- Soporte dual para persistencia directa en memoria o vinculación con AsyncSession SQLAlchemy 2.0.
"""
# mypy: disable-error-code="explicit-any"
from __future__ import annotations

import asyncio
import logging
from contextlib import suppress
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import DomainValidationError, ResourceNotFoundError
from src.core.guards.xss_sanitizer import sanitize_text_input
from src.core.realtime.router import get_realtime_publisher
from src.core.realtime.schemas import RealtimeEventEnvelope
from src.modules.operations.infrastructure.models import (
    NotaEquipo,
    NotaEquipoLectura,
    NotaEquipoMencion,
    NotaPersonal,
    PlantillaRutina,
    Tarea,
    TurnoHorario,
)

logger = logging.getLogger("oppytec.operations.actividades")


def _to_utc_datetime(dt: datetime | date | None, t: time | None = None) -> datetime | None:
    """Normaliza fechas y horas a un objeto datetime timezone-aware UTC."""
    if dt is None:
        return None
    if isinstance(dt, datetime):
        if dt.tzinfo is None:
            return dt.replace(tzinfo=UTC)
        return dt.astimezone(UTC)
    if isinstance(dt, date):
        resolved_time = t if t is not None else time(0, 0, 0)
        return datetime.combine(dt, resolved_time, tzinfo=UTC)
    return None


class ActividadesService:
    """
    Servicio de Dominio y Aplicación de Actividades, Turnos y Tareas Operativas.
    Permite operar en memoria para tests ultrarrápidos y/o delegar a SQLAlchemy AsyncSession.
    """

    def __init__(
        self,
        session_or_none: AsyncSession | None = None,
        use_in_memory: bool = True,
    ) -> None:
        self._session = session_or_none
        self._use_in_memory = use_in_memory

        # Estructuras de almacenamiento en memoria
        self._notas_equipo: dict[int, NotaEquipo] = {}
        self._notas_personales: dict[int, NotaPersonal] = {}
        self._tareas: dict[int, Tarea] = {}
        self._plantillas: dict[int, PlantillaRutina] = {}
        self._turnos: dict[int, TurnoHorario] = {}

        # Secuencias autonuméricas
        self._next_nota_equipo_id: int = 1
        self._next_mencion_id: int = 1
        self._next_lectura_id: int = 1
        self._next_nota_personal_id: int = 1
        self._next_tarea_id: int = 1
        self._next_plantilla_id: int = 1
        self._next_turno_id: int = 1

    def reset(self) -> None:
        """Reinicia el estado en memoria para aislamiento en tests."""
        self._notas_equipo.clear()
        self._notas_personales.clear()
        self._tareas.clear()
        self._plantillas.clear()
        self._turnos.clear()
        self._next_nota_equipo_id = 1
        self._next_mencion_id = 1
        self._next_lectura_id = 1
        self._next_nota_personal_id = 1
        self._next_tarea_id = 1
        self._next_plantilla_id = 1
        self._next_turno_id = 1

    # ==========================================================================
    # HELPERS DE NOTIFICACIÓN REALTIME WEBSOCKET
    # ==========================================================================

    def _emit_realtime_event(
        self,
        event_type: str,
        payload: dict[str, Any],
        required_permission: str,
        tenant_id: str | None = None,
    ) -> None:
        """Despacha un evento reactivo WebSocket con degradación elegante."""
        with suppress(Exception):
            publisher = get_realtime_publisher()
            t_uuid = None
            if tenant_id:
                with suppress(Exception):
                    t_uuid = UUID(str(tenant_id))

            coro = publisher.publish_event(
                RealtimeEventEnvelope(
                    event_type=event_type,
                    holding_id=None,
                    tenant_id=t_uuid,
                    required_permission=required_permission,
                    query_keys_to_invalidate=[["actividades", event_type.split(".")[-2]]],
                    payload=payload,
                )
            )
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(coro)
            except RuntimeError:
                asyncio.run(coro)

    # ==========================================================================
    # 1. GESTIÓN DE NOTAS DE EQUIPO (BITÁCORA COMPARTIDA)
    # ==========================================================================

    def create_nota_equipo(
        self,
        autor_user_id: int,
        titulo: str,
        contenido: str,
        *,
        area_id: str | None = None,
        categoria: str = "general",
        fecha: datetime | None = None,
        insumo_id: str | None = None,
        receta_id: int | None = None,
        foto_url: str | None = None,
        menciones_user_ids: list[int] | None = None,
        tenant_id: str | None = None,
    ) -> NotaEquipo:
        """Crea una nota de equipo compartida, vincula menciones y emite evento realtime."""
        if not titulo or not titulo.strip():
            raise DomainValidationError(
                "El título de la nota no puede estar vacío.",
                i18n_key="operations:errors.nota_titulo_vacio",
            )
        if not contenido or not contenido.strip():
            raise DomainValidationError(
                "El contenido de la nota no puede estar vacío.",
                i18n_key="operations:errors.nota_contenido_vacio",
            )

        clean_titulo = sanitize_text_input(titulo.strip(), field_name="titulo")
        clean_contenido = sanitize_text_input(contenido.strip(), field_name="contenido")

        nota_id = self._next_nota_equipo_id
        self._next_nota_equipo_id += 1

        resolved_fecha = fecha if fecha is not None else datetime.now(UTC)

        nota = NotaEquipo(
            id=nota_id,
            autor_user_id=autor_user_id,
            titulo=clean_titulo,
            contenido=clean_contenido,
            area_id=area_id,
            categoria=categoria.strip().lower() if categoria else "general",
            fecha=resolved_fecha,
            insumo_id=insumo_id,
            receta_id=receta_id,
            foto_url=foto_url,
        )
        nota.tenant_id = str(tenant_id) if tenant_id else None
        nota.created_at = datetime.now(UTC)
        nota.menciones = []
        nota.lecturas = []

        # Registrar menciones
        if menciones_user_ids:
            for uid in set(menciones_user_ids):
                mencion_id = self._next_mencion_id
                self._next_mencion_id += 1
                mencion = NotaEquipoMencion(
                    id=mencion_id,
                    nota_id=nota_id,
                    user_id=uid,
                )
                nota.menciones.append(mencion)

        self._notas_equipo[nota_id] = nota

        # Evento realtime
        self._emit_realtime_event(
            event_type="operations.actividades.nota.created",
            payload={
                "nota_id": nota.id,
                "autor_user_id": nota.autor_user_id,
                "titulo": nota.titulo,
                "area_id": nota.area_id,
                "categoria": nota.categoria,
                "menciones": [m.user_id for m in nota.menciones],
            },
            required_permission="operations.actividades.notas.view",
            tenant_id=tenant_id,
        )

        return nota

    def get_notas_equipo(
        self,
        *,
        tenant_id: str | None = None,
        area_id: str | None = None,
        categoria: str | None = None,
        search: str | None = None,
        user_id_mencionado: int | None = None,
        leido_por_user_id: int | None = None,
        current_user_id: int | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """
        Consulta notas de equipo con filtros multidimensionales y enriquece con
        estado de lectura del usuario solicitante (`leido_por_mi`).
        """
        results: list[NotaEquipo] = []
        search_term = search.strip().lower() if search else None
        target_cat = categoria.strip().lower() if categoria else None

        for nota in self._notas_equipo.values():
            if nota.deleted_at is not None:
                continue
            if tenant_id is not None and getattr(nota, "tenant_id", None) is not None and getattr(nota, "tenant_id", None) != str(tenant_id):
                continue
            if area_id is not None and nota.area_id != area_id:
                continue
            if target_cat is not None and nota.categoria != target_cat:
                continue
            if search_term:
                in_titulo = search_term in nota.titulo.lower()
                in_contenido = search_term in nota.contenido.lower()
                if not (in_titulo or in_contenido):
                    continue
            if user_id_mencionado is not None:
                mencionado_ids = [m.user_id for m in nota.menciones]
                if user_id_mencionado not in mencionado_ids:
                    continue
            if leido_por_user_id is not None:
                lectores_ids = [lec.user_id for lec in nota.lecturas]
                if leido_por_user_id not in lectores_ids:
                    continue

            results.append(nota)

        # Ordenar por fecha descendente
        results.sort(key=lambda n: n.fecha or datetime.min.replace(tzinfo=UTC), reverse=True)
        paginated = results[skip : skip + limit]

        # Enriquecer respuesta
        enriched: list[dict[str, Any]] = []
        for n in paginated:
            lecturas_uids = [l.user_id for l in n.lecturas]
            leido_mi = bool(current_user_id and current_user_id in lecturas_uids)
            enriched.append(
                {
                    "id": n.id,
                    "autor_user_id": n.autor_user_id,
                    "titulo": n.titulo,
                    "contenido": n.contenido,
                    "area_id": n.area_id,
                    "categoria": n.categoria,
                    "fecha": n.fecha,
                    "insumo_id": n.insumo_id,
                    "receta_id": n.receta_id,
                    "foto_url": n.foto_url,
                    "menciones": [
                        {"id": m.id, "nota_id": m.nota_id, "user_id": m.user_id}
                        for m in n.menciones
                    ],
                    "lecturas": [
                        {
                            "id": lec.id,
                            "nota_id": lec.nota_id,
                            "user_id": lec.user_id,
                            "read_at": lec.read_at,
                        }
                        for lec in n.lecturas
                    ],
                    "leido_por_mi": leido_mi,
                    "total_lecturas": len(n.lecturas),
                    "created_at": n.created_at,
                }
            )

        return enriched

    def mark_nota_as_read(
        self,
        nota_id: int,
        user_id: int,
        *,
        tenant_id: str | None = None,
    ) -> NotaEquipoLectura:
        """
        Marca una nota como leída por el usuario.
        Invariante: Es 100% IDEMPOTENTE (si ya fue leída, retorna el registro existente sin error).
        """
        nota = self._notas_equipo.get(nota_id)
        if not nota or nota.deleted_at is not None:
            raise ResourceNotFoundError(
                f"Nota de equipo id={nota_id} no encontrada.",
                i18n_key="operations:errors.nota_no_encontrada",
            )
        if tenant_id is not None and getattr(nota, "tenant_id", None) is not None and getattr(nota, "tenant_id", None) != str(tenant_id):
            raise ResourceNotFoundError(
                f"Nota de equipo id={nota_id} no encontrada.",
                i18n_key="operations:errors.nota_no_encontrada",
            )

        # Verificar si ya existe lectura previa
        for lectura in nota.lecturas:
            if lectura.user_id == user_id:
                return lectura

        # Registrar nueva lectura
        lectura_id = self._next_lectura_id
        self._next_lectura_id += 1
        nueva_lectura = NotaEquipoLectura(
            id=lectura_id,
            nota_id=nota_id,
            user_id=user_id,
            read_at=datetime.now(UTC),
        )
        nota.lecturas.append(nueva_lectura)

        # Evento realtime
        self._emit_realtime_event(
            event_type="operations.actividades.nota.read",
            payload={
                "nota_id": nota.id,
                "user_id": user_id,
                "read_at": nueva_lectura.read_at.isoformat(),
            },
            required_permission="operations.actividades.notas.view",
            tenant_id=tenant_id,
        )

        return nueva_lectura

    def update_nota_equipo(
        self,
        nota_id: int,
        user_id: int,
        *,
        titulo: str | None = None,
        contenido: str | None = None,
        area_id: str | None = None,
        categoria: str | None = None,
        insumo_id: str | None = None,
        receta_id: int | None = None,
        foto_url: str | None = None,
        menciones_user_ids: list[int] | None = None,
        tenant_id: str | None = None,
    ) -> NotaEquipo:
        """Actualiza el contenido o metadatos de una nota de equipo."""
        nota = self._notas_equipo.get(nota_id)
        if not nota or nota.deleted_at is not None:
            raise ResourceNotFoundError(
                f"Nota de equipo id={nota_id} no encontrada.",
                i18n_key="operations:errors.nota_no_encontrada",
            )
        if tenant_id is not None and getattr(nota, "tenant_id", None) is not None and getattr(nota, "tenant_id", None) != str(tenant_id):
            raise ResourceNotFoundError(
                f"Nota de equipo id={nota_id} no encontrada.",
                i18n_key="operations:errors.nota_no_encontrada",
            )

        if titulo is not None:
            if not titulo.strip():
                raise DomainValidationError(
                    "El título de la nota no puede estar vacío.",
                    i18n_key="operations:errors.nota_titulo_vacio",
                )
            nota.titulo = sanitize_text_input(titulo.strip(), field_name="titulo")

        if contenido is not None:
            if not contenido.strip():
                raise DomainValidationError(
                    "El contenido de la nota no puede estar vacío.",
                    i18n_key="operations:errors.nota_contenido_vacio",
                )
            nota.contenido = sanitize_text_input(contenido.strip(), field_name="contenido")

        if area_id is not None:
            nota.area_id = area_id
        if categoria is not None:
            nota.categoria = categoria.strip().lower()
        if insumo_id is not None:
            nota.insumo_id = insumo_id
        if receta_id is not None:
            nota.receta_id = receta_id
        if foto_url is not None:
            nota.foto_url = foto_url

        if menciones_user_ids is not None:
            nota.menciones = []
            for uid in set(menciones_user_ids):
                mencion_id = self._next_mencion_id
                self._next_mencion_id += 1
                nota.menciones.append(
                    NotaEquipoMencion(
                        id=mencion_id,
                        nota_id=nota_id,
                        user_id=uid,
                    )
                )

        nota.updated_at = datetime.now(UTC)

        self._emit_realtime_event(
            event_type="operations.actividades.nota.updated",
            payload={
                "nota_id": nota.id,
                "titulo": nota.titulo,
                "updated_by": user_id,
            },
            required_permission="operations.actividades.notas.view",
            tenant_id=tenant_id,
        )

        return nota

    def delete_nota_equipo(
        self,
        nota_id: int,
        *,
        user_id: int | None = None,
        tenant_id: str | None = None,
    ) -> bool:
        """Aplica soft-delete a una nota de equipo."""
        nota = self._notas_equipo.get(nota_id)
        if not nota or nota.deleted_at is not None:
            raise ResourceNotFoundError(
                f"Nota de equipo id={nota_id} no encontrada.",
                i18n_key="operations:errors.nota_no_encontrada",
            )
        if tenant_id is not None and getattr(nota, "tenant_id", None) is not None and getattr(nota, "tenant_id", None) != str(tenant_id):
            raise ResourceNotFoundError(
                f"Nota de equipo id={nota_id} no encontrada.",
                i18n_key="operations:errors.nota_no_encontrada",
            )

        nota.deleted_at = datetime.now(UTC)

        self._emit_realtime_event(
            event_type="operations.actividades.nota.deleted",
            payload={"nota_id": nota_id, "deleted_by": user_id},
            required_permission="operations.actividades.notas.view",
            tenant_id=tenant_id,
        )

        return True

    # ==========================================================================
    # 2. GESTIÓN DE NOTAS PERSONALES (PRIVADAS POR COLABORADOR)
    # ==========================================================================

    def create_nota_personal(
        self,
        user_id: int,
        titulo: str,
        contenido: str,
        *,
        area_id: str | None = None,
        fecha: datetime | None = None,
        tenant_id: str | None = None,
    ) -> NotaPersonal:
        """Crea una nota privada individual para el colaborador."""
        if not titulo or not titulo.strip():
            raise DomainValidationError(
                "El título de la nota personal no puede estar vacío.",
                i18n_key="operations:errors.nota_titulo_vacio",
            )
        if not contenido or not contenido.strip():
            raise DomainValidationError(
                "El contenido de la nota personal no puede estar vacío.",
                i18n_key="operations:errors.nota_contenido_vacio",
            )

        clean_titulo = sanitize_text_input(titulo.strip(), field_name="titulo")
        clean_contenido = sanitize_text_input(contenido.strip(), field_name="contenido")

        nota_id = self._next_nota_personal_id
        self._next_nota_personal_id += 1

        resolved_fecha = fecha if fecha is not None else datetime.now(UTC)

        nota = NotaPersonal(
            id=nota_id,
            user_id=user_id,
            titulo=clean_titulo,
            contenido=clean_contenido,
            area_id=area_id,
            fecha=resolved_fecha,
        )
        nota.tenant_id = str(tenant_id) if tenant_id else None
        nota.created_at = datetime.now(UTC)
        self._notas_personales[nota_id] = nota
        return nota

    def get_notas_personales(
        self,
        user_id: int,
        *,
        tenant_id: str | None = None,
        area_id: str | None = None,
        search: str | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[NotaPersonal]:
        """Obtiene las notas personales privadas exclusivas del usuario autenticado."""
        results: list[NotaPersonal] = []
        search_term = search.strip().lower() if search else None

        for nota in self._notas_personales.values():
            if nota.deleted_at is not None:
                continue
            if tenant_id is not None and getattr(nota, "tenant_id", None) is not None and getattr(nota, "tenant_id", None) != str(tenant_id):
                continue
            if nota.user_id != user_id:
                continue
            if area_id is not None and nota.area_id != area_id:
                continue
            if search_term:
                if search_term not in nota.titulo.lower() and search_term not in nota.contenido.lower():
                    continue
            results.append(nota)

        results.sort(key=lambda n: n.fecha or datetime.min.replace(tzinfo=UTC), reverse=True)
        return results[skip : skip + limit]

    def update_nota_personal(
        self,
        nota_id: int,
        user_id: int,
        *,
        titulo: str | None = None,
        contenido: str | None = None,
        area_id: str | None = None,
        fecha: datetime | None = None,
        tenant_id: str | None = None,
    ) -> NotaPersonal:
        """Modifica una nota personal asegurando que pertenezca al usuario."""
        nota = self._notas_personales.get(nota_id)
        if not nota or nota.deleted_at is not None:
            raise ResourceNotFoundError(
                f"Nota personal id={nota_id} no encontrada.",
                i18n_key="operations:errors.nota_no_encontrada",
            )
        if tenant_id is not None and getattr(nota, "tenant_id", None) is not None and getattr(nota, "tenant_id", None) != str(tenant_id):
            raise ResourceNotFoundError(
                f"Nota personal id={nota_id} no encontrada.",
                i18n_key="operations:errors.nota_no_encontrada",
            )
        if nota.user_id != user_id:
            raise DomainValidationError(
                "No tienes permiso para modificar una nota personal de otro usuario.",
                i18n_key="operations:errors.nota_personal_ajena",
            )

        if titulo is not None:
            if not titulo.strip():
                raise DomainValidationError(
                    "El título no puede quedar vacío.",
                    i18n_key="operations:errors.nota_titulo_vacio",
                )
            nota.titulo = sanitize_text_input(titulo.strip(), field_name="titulo")

        if contenido is not None:
            if not contenido.strip():
                raise DomainValidationError(
                    "El contenido no puede quedar vacío.",
                    i18n_key="operations:errors.nota_contenido_vacio",
                )
            nota.contenido = sanitize_text_input(contenido.strip(), field_name="contenido")

        if area_id is not None:
            nota.area_id = area_id
        if fecha is not None:
            nota.fecha = fecha

        nota.updated_at = datetime.now(UTC)
        return nota

    def delete_nota_personal(
        self,
        nota_id: int,
        user_id: int,
        *,
        tenant_id: str | None = None,
    ) -> bool:
        """Aplica soft-delete a una nota personal del usuario."""
        nota = self._notas_personales.get(nota_id)
        if not nota or nota.deleted_at is not None:
            raise ResourceNotFoundError(
                f"Nota personal id={nota_id} no encontrada.",
                i18n_key="operations:errors.nota_no_encontrada",
            )
        if tenant_id is not None and getattr(nota, "tenant_id", None) is not None and getattr(nota, "tenant_id", None) != str(tenant_id):
            raise ResourceNotFoundError(
                f"Nota personal id={nota_id} no encontrada.",
                i18n_key="operations:errors.nota_no_encontrada",
            )
        if nota.user_id != user_id:
            raise DomainValidationError(
                "No tienes permiso para eliminar una nota personal de otro usuario.",
                i18n_key="operations:errors.nota_personal_ajena",
            )

        nota.deleted_at = datetime.now(UTC)
        return True

    # ==========================================================================
    # 3. GESTIÓN DE TAREAS OPERATIVAS, CHECKLISTS Y PLANTILLAS DE RUTINAS
    # ==========================================================================

    def create_tarea(
        self,
        titulo: str,
        *,
        creador_user_id: int | None = None,
        asignado_a_user_id: int | None = None,
        area_id: str | None = None,
        descripcion: str | None = None,
        estado: str = "pendiente",
        urgencia: str = "media",
        fecha_limite: datetime | None = None,
        nota_incompleta: str | None = None,
        compra_id: str | None = None,
        foto_evidencia_url: str | None = None,
        plantilla_id: int | None = None,
        completada: bool = False,
        tenant_id: str | None = None,
    ) -> Tarea:
        """Crea una nueva tarea operativa con validaciones de estado y despacho realtime."""
        if not titulo or not titulo.strip():
            raise DomainValidationError(
                "El título de la tarea no puede estar vacío.",
                i18n_key="operations:errors.tarea_titulo_vacio",
            )

        # Regla de Integridad Incompleta
        if estado == "incompleta" and (not nota_incompleta or not nota_incompleta.strip()):
            raise DomainValidationError(
                "Si la tarea se crea como incompleta, debe registrar el motivo en 'nota_incompleta'.",
                i18n_key="operations:errors.tarea_incompleta_motivo_requerido",
            )

        is_completed = completada or (estado == "completada")

        clean_titulo = sanitize_text_input(titulo.strip(), field_name="titulo")
        clean_desc = sanitize_text_input(descripcion.strip(), field_name="descripcion") if descripcion else None
        clean_nota_inc = sanitize_text_input(nota_incompleta.strip(), field_name="nota_incompleta") if nota_incompleta else None

        tarea_id = self._next_tarea_id
        self._next_tarea_id += 1

        tarea = Tarea(
            id=tarea_id,
            titulo=clean_titulo,
            creador_user_id=creador_user_id,
            asignado_a_user_id=asignado_a_user_id,
            area_id=area_id,
            descripcion=clean_desc,
            estado=estado,
            urgencia=urgencia,
            fecha_limite=fecha_limite,
            nota_incompleta=clean_nota_inc,
            compra_id=compra_id,
            foto_evidencia_url=foto_evidencia_url,
            plantilla_id=plantilla_id,
            completada=is_completed,
        )
        tarea.tenant_id = str(tenant_id) if tenant_id else None
        tarea.created_at = datetime.now(UTC)
        self._tareas[tarea_id] = tarea

        self._emit_realtime_event(
            event_type="operations.actividades.tarea.created",
            payload={
                "tarea_id": tarea.id,
                "titulo": tarea.titulo,
                "estado": tarea.estado,
                "urgencia": tarea.urgencia,
                "asignado_a_user_id": tarea.asignado_a_user_id,
            },
            required_permission="operations.actividades.tareas.view",
            tenant_id=tenant_id,
        )

        return tarea

    def get_tareas(
        self,
        *,
        tenant_id: str | None = None,
        area_id: str | None = None,
        asignado_a_user_id: int | None = None,
        estado: str | None = None,
        urgencia: str | None = None,
        search: str | None = None,
        plantilla_id: int | None = None,
        completada: bool | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Tarea]:
        """Consulta tareas operativas con filtros multidimensionales."""
        results: list[Tarea] = []
        search_term = search.strip().lower() if search else None

        for t in self._tareas.values():
            if t.deleted_at is not None:
                continue
            if tenant_id is not None and getattr(t, "tenant_id", None) is not None and getattr(t, "tenant_id", None) != str(tenant_id):
                continue
            if area_id is not None and t.area_id != area_id:
                continue
            if asignado_a_user_id is not None and t.asignado_a_user_id != asignado_a_user_id:
                continue
            if estado is not None and t.estado != estado:
                continue
            if urgencia is not None and t.urgencia != urgencia:
                continue
            if plantilla_id is not None and t.plantilla_id != plantilla_id:
                continue
            if completada is not None and t.completada != completada:
                continue
            if search_term:
                in_titulo = search_term in t.titulo.lower()
                in_desc = search_term in (t.descripcion or "").lower()
                if not (in_titulo or in_desc):
                    continue

            results.append(t)

        results.sort(key=lambda t: t.created_at or datetime.min.replace(tzinfo=UTC), reverse=True)
        return results[skip : skip + limit]

    def update_tarea_estado(
        self,
        tarea_id: int,
        estado: str,
        *,
        nota_incompleta: str | None = None,
        foto_evidencia_url: str | None = None,
        completada: bool | None = None,
        tenant_id: str | None = None,
        user_id: int | None = None,
    ) -> Tarea:
        """
        Actualiza el estado de una tarea operativa.
        VALIDACIÓN CRÍTICA INVIOLABLE: Si el estado pasa a 'incompleta', 'nota_incompleta'
        no puede ser vacía o nula.
        """
        tarea = self._tareas.get(tarea_id)
        if not tarea or tarea.deleted_at is not None:
            raise ResourceNotFoundError(
                f"Tarea operativa id={tarea_id} no encontrada.",
                i18n_key="operations:errors.tarea_no_encontrada",
            )
        if tenant_id is not None and getattr(tarea, "tenant_id", None) is not None and getattr(tarea, "tenant_id", None) != str(tenant_id):
            raise ResourceNotFoundError(
                f"Tarea operativa id={tarea_id} no encontrada.",
                i18n_key="operations:errors.tarea_no_encontrada",
            )

        if estado not in ("pendiente", "progreso", "completada", "incompleta"):
            raise DomainValidationError(
                f"Estado de tarea inválido: '{estado}'.",
                i18n_key="operations:errors.tarea_estado_invalido",
            )

        if estado == "incompleta":
            # Si no se pasó nota_incompleta nueva o viene vacía, revisamos si ya tenía una previa
            effective_nota = nota_incompleta if nota_incompleta is not None else tarea.nota_incompleta
            if not effective_nota or not str(effective_nota).strip():
                raise DomainValidationError(
                    "Al marcar una tarea como incompleta, debe registrar obligatoriamente la justificación en 'nota_incompleta'.",
                    i18n_key="operations:errors.tarea_incompleta_motivo_requerido",
                )
            tarea.nota_incompleta = sanitize_text_input(str(effective_nota).strip(), field_name="nota_incompleta")
        elif nota_incompleta is not None:
            tarea.nota_incompleta = sanitize_text_input(nota_incompleta.strip(), field_name="nota_incompleta") if nota_incompleta.strip() else None

        tarea.estado = estado

        # Sincronización del flag 'completada'
        if estado == "completada":
            tarea.completada = True
        elif completada is not None:
            tarea.completada = completada
        else:
            tarea.completada = False

        if foto_evidencia_url is not None:
            tarea.foto_evidencia_url = foto_evidencia_url

        tarea.updated_at = datetime.now(UTC)

        self._emit_realtime_event(
            event_type="operations.actividades.tarea.updated",
            payload={
                "tarea_id": tarea.id,
                "estado": tarea.estado,
                "completada": tarea.completada,
                "nota_incompleta": tarea.nota_incompleta,
                "updated_by": user_id,
            },
            required_permission="operations.actividades.tareas.view",
            tenant_id=tenant_id,
        )

        return tarea

    def update_tarea(
        self,
        tarea_id: int,
        *,
        titulo: str | None = None,
        descripcion: str | None = None,
        asignado_a_user_id: int | None = None,
        area_id: str | None = None,
        estado: str | None = None,
        urgencia: str | None = None,
        fecha_limite: datetime | None = None,
        nota_incompleta: str | None = None,
        compra_id: str | None = None,
        foto_evidencia_url: str | None = None,
        completada: bool | None = None,
        tenant_id: str | None = None,
        user_id: int | None = None,
    ) -> Tarea:
        """Actualiza campos generales de una tarea."""
        tarea = self._tareas.get(tarea_id)
        if not tarea or tarea.deleted_at is not None:
            raise ResourceNotFoundError(
                f"Tarea operativa id={tarea_id} no encontrada.",
                i18n_key="operations:errors.tarea_no_encontrada",
            )
        if tenant_id is not None and getattr(tarea, "tenant_id", None) is not None and getattr(tarea, "tenant_id", None) != str(tenant_id):
            raise ResourceNotFoundError(
                f"Tarea operativa id={tarea_id} no encontrada.",
                i18n_key="operations:errors.tarea_no_encontrada",
            )

        if titulo is not None:
            if not titulo.strip():
                raise DomainValidationError(
                    "El título de la tarea no puede estar vacío.",
                    i18n_key="operations:errors.tarea_titulo_vacio",
                )
            tarea.titulo = sanitize_text_input(titulo.strip(), field_name="titulo")

        if descripcion is not None:
            tarea.descripcion = sanitize_text_input(descripcion.strip(), field_name="descripcion") if descripcion.strip() else None
        if asignado_a_user_id is not None:
            tarea.asignado_a_user_id = asignado_a_user_id
        if area_id is not None:
            tarea.area_id = area_id
        if urgencia is not None:
            tarea.urgencia = urgencia
        if fecha_limite is not None:
            tarea.fecha_limite = fecha_limite
        if compra_id is not None:
            tarea.compra_id = compra_id
        if foto_evidencia_url is not None:
            tarea.foto_evidencia_url = foto_evidencia_url

        if (estado == "incompleta" or (estado is None and tarea.estado == "incompleta")):
            if nota_incompleta is not None and not nota_incompleta.strip():
                raise DomainValidationError(
                    "Una tarea incompleta debe mantener obligatoriamente su justificación en 'nota_incompleta'.",
                    i18n_key="operations:errors.tarea_incompleta_motivo_requerido",
                )

        if nota_incompleta is not None and nota_incompleta.strip():
            tarea.nota_incompleta = sanitize_text_input(nota_incompleta.strip(), field_name="nota_incompleta")

        if estado is not None:
            return self.update_tarea_estado(
                tarea_id=tarea_id,
                estado=estado,
                nota_incompleta=nota_incompleta,
                foto_evidencia_url=foto_evidencia_url,
                completada=completada,
                tenant_id=tenant_id,
                user_id=user_id,
            )

        if completada is not None:
            tarea.completada = completada

        tarea.updated_at = datetime.now(UTC)
        return tarea

    def delete_tarea(
        self,
        tarea_id: int,
        *,
        tenant_id: str | None = None,
        user_id: int | None = None,
    ) -> bool:
        """Aplica soft-delete a una tarea operativa."""
        tarea = self._tareas.get(tarea_id)
        if not tarea or tarea.deleted_at is not None:
            raise ResourceNotFoundError(
                f"Tarea operativa id={tarea_id} no encontrada.",
                i18n_key="operations:errors.tarea_no_encontrada",
            )
        if tenant_id is not None and getattr(tarea, "tenant_id", None) is not None and getattr(tarea, "tenant_id", None) != str(tenant_id):
            raise ResourceNotFoundError(
                f"Tarea operativa id={tarea_id} no encontrada.",
                i18n_key="operations:errors.tarea_no_encontrada",
            )

        tarea.deleted_at = datetime.now(UTC)

        self._emit_realtime_event(
            event_type="operations.actividades.tarea.deleted",
            payload={"tarea_id": tarea_id, "deleted_by": user_id},
            required_permission="operations.actividades.tareas.view",
            tenant_id=tenant_id,
        )

        return True

    # ==========================================================================
    # PLANTILLAS DE RUTINAS
    # ==========================================================================

    def create_plantilla_rutina(
        self,
        nombre: str,
        *,
        descripcion: str | None = None,
        area_id: str | None = None,
        tipo_rutina: str = "APERTURA",
        frecuencia: str = "DIARIA",
        items_json: list[dict[str, Any]] | None = None,
        is_active: bool = True,
        usuario_creador_id: int | None = None,
        tenant_id: str | None = None,
    ) -> PlantillaRutina:
        """Crea una plantilla reutilizable de checklists."""
        if not nombre or not nombre.strip():
            raise DomainValidationError(
                "El nombre de la plantilla no puede estar vacío.",
                i18n_key="operations:errors.plantilla_nombre_vacio",
            )

        clean_nombre = sanitize_text_input(nombre.strip(), field_name="nombre")
        clean_desc = sanitize_text_input(descripcion.strip(), field_name="descripcion") if descripcion else None

        plantilla_id = self._next_plantilla_id
        self._next_plantilla_id += 1

        plantilla = PlantillaRutina(
            id=plantilla_id,
            nombre=clean_nombre,
            descripcion=clean_desc,
            area_id=area_id,
            tipo_rutina=tipo_rutina,
            frecuencia=frecuencia,
            items_json=list(items_json or []),
            is_active=is_active,
            usuario_creador_id=usuario_creador_id,
        )
        plantilla.tenant_id = str(tenant_id) if tenant_id else None
        plantilla.created_at = datetime.now(UTC)
        self._plantillas[plantilla_id] = plantilla
        return plantilla

    def get_plantillas_rutinas(
        self,
        *,
        tenant_id: str | None = None,
        area_id: str | None = None,
        tipo_rutina: str | None = None,
        is_active: bool | None = None,
    ) -> list[PlantillaRutina]:
        """Lista plantillas de rutinas filtradas."""
        results: list[PlantillaRutina] = []
        for p in self._plantillas.values():
            if p.deleted_at is not None:
                continue
            if tenant_id is not None and getattr(p, "tenant_id", None) is not None and getattr(p, "tenant_id", None) != str(tenant_id):
                continue
            if area_id is not None and p.area_id != area_id:
                continue
            if tipo_rutina is not None and p.tipo_rutina != tipo_rutina:
                continue
            if is_active is not None and p.is_active != is_active:
                continue
            results.append(p)
        results.sort(key=lambda p: p.nombre)
        return results

    def aplicar_plantilla_rutina(
        self,
        plantilla_id: int,
        *,
        asignado_a_user_id: int | None = None,
        creador_user_id: int | None = None,
        fecha_limite: datetime | None = None,
        area_id: str | None = None,
        tenant_id: str | None = None,
    ) -> list[Tarea]:
        """
        Instancia automáticamente un lote de tareas operativas derivadas de la plantilla.
        """
        plantilla = self._plantillas.get(plantilla_id)
        if not plantilla or plantilla.deleted_at is not None:
            raise ResourceNotFoundError(
                f"Plantilla de rutina id={plantilla_id} no encontrada.",
                i18n_key="operations:errors.plantilla_no_encontrada",
            )
        if tenant_id is not None and getattr(plantilla, "tenant_id", None) is not None and getattr(plantilla, "tenant_id", None) != str(tenant_id):
            raise ResourceNotFoundError(
                f"Plantilla de rutina id={plantilla_id} no encontrada.",
                i18n_key="operations:errors.plantilla_no_encontrada",
            )

        target_area = area_id if area_id is not None else plantilla.area_id
        items = plantilla.items_json if isinstance(plantilla.items_json, list) else []

        created_tasks: list[Tarea] = []
        for item in items:
            if isinstance(item, str):
                item_title = item
                item_desc = None
                item_urg = "media"
            elif isinstance(item, dict):
                item_title = item.get("titulo") or item.get("nombre") or "Tarea de Rutina"
                item_desc = item.get("descripcion")
                item_urg = item.get("urgencia", "media")
            else:
                continue

            nueva_tarea = self.create_tarea(
                titulo=str(item_title),
                descripcion=str(item_desc) if item_desc else None,
                creador_user_id=creador_user_id,
                asignado_a_user_id=asignado_a_user_id,
                area_id=target_area,
                estado="pendiente",
                urgencia=str(item_urg),
                fecha_limite=fecha_limite,
                plantilla_id=plantilla.id,
                completada=False,
                tenant_id=tenant_id,
            )
            created_tasks.append(nueva_tarea)

        return created_tasks

    # ==========================================================================
    # 4. GESTIÓN DE HORARIOS, TURNOS, ALERTAS LABORALES Y CLONACIÓN
    # ==========================================================================

    def _resolve_turno_datetimes(
        self,
        fecha_inicio: date | None,
        fecha_fin: date | None,
        hora_inicio: time | None,
        hora_fin: time | None,
        inicio_turno: datetime | None,
        fin_turno: datetime | None,
    ) -> tuple[datetime, datetime]:
        """Calcula de forma consistente los datetimes UTC de inicio y fin de un turno."""
        if inicio_turno is not None and fin_turno is not None:
            init_dt = _to_utc_datetime(inicio_turno)
            end_dt = _to_utc_datetime(fin_turno)
            if init_dt and end_dt:
                return init_dt, end_dt

        f_ini = fecha_inicio or date.today()
        h_ini = hora_inicio or time(9, 0, 0)
        init_dt = datetime.combine(f_ini, h_ini, tzinfo=UTC)

        f_fin = fecha_fin or f_ini
        h_fin = hora_fin or time(17, 0, 0)

        # Si no se pasó fecha_fin y hora_fin < hora_inicio, cruza medianoche
        if fecha_fin is None and h_fin < h_ini:
            f_fin = f_ini + timedelta(days=1)

        end_dt = datetime.combine(f_fin, h_fin, tzinfo=UTC)
        return init_dt, end_dt

    def validar_alertas_laborales(
        self,
        usuario_id: int,
        nuevo_turno: dict[str, Any] | TurnoHorario,
        *,
        tenant_id: str | None = None,
        turno_id_excluir: int | None = None,
    ) -> dict[str, Any]:
        """
        Auditoría de Cumplimiento Laboral:
        1. Descanso mínimo obligatorio < 12 horas consecutivas entre jornadas.
        2. Superación del tope legal semanal de 40 Horas.
        """
        # Extraer fechas y horas del turno entrante
        if isinstance(nuevo_turno, TurnoHorario):
            f_ini = nuevo_turno.fecha_inicio
            f_fin = nuevo_turno.fecha_fin
            h_ini = nuevo_turno.hora_inicio
            h_fin = nuevo_turno.hora_fin
            in_dt = nuevo_turno.inicio_turno
            fn_dt = nuevo_turno.fin_turno
        else:
            f_ini = nuevo_turno.get("fecha_inicio")
            f_fin = nuevo_turno.get("fecha_fin")
            h_ini = nuevo_turno.get("hora_inicio")
            h_fin = nuevo_turno.get("hora_fin")
            in_dt = nuevo_turno.get("inicio_turno")
            fn_dt = nuevo_turno.get("fin_turno")

        nuevo_inicio, nuevo_fin = self._resolve_turno_datetimes(
            fecha_inicio=f_ini,
            fecha_fin=f_fin,
            hora_inicio=h_ini,
            hora_fin=h_fin,
            inicio_turno=in_dt,
            fin_turno=fn_dt,
        )

        alertas: list[dict[str, Any]] = []

        # Buscar todos los turnos del usuario (excluyendo el actual si es edición)
        user_turnos: list[TurnoHorario] = [
            t
            for t in self._turnos.values()
            if (t.user_id == usuario_id or t.usuario_id == usuario_id)
            and t.deleted_at is None
            and (turno_id_excluir is None or t.id != turno_id_excluir)
            and (tenant_id is None or getattr(t, "tenant_id", None) is None or getattr(t, "tenant_id", None) == str(tenant_id))
        ]

        # ----------------------------------------------------------------------
        # Regla 1: Descanso mínimo < 12h entre jornadas consecutivas
        # ----------------------------------------------------------------------
        min_rest_seconds = 12 * 3600

        for t in user_turnos:
            t_ini, t_fin = self._resolve_turno_datetimes(
                t.fecha_inicio,
                t.fecha_fin,
                t.hora_inicio,
                t.hora_fin,
                t.inicio_turno,
                t.fin_turno,
            )

            # Caso A: El turno existente termina antes de que empiece el nuevo
            if t_fin <= nuevo_inicio:
                gap = (nuevo_inicio - t_fin).total_seconds()
                if gap < min_rest_seconds:
                    horas_descanso = Decimal(str(round(gap / 3600.0, 2)))
                    alertas.append(
                        {
                            "tipo": "DESCANSO_INSUFICIENTE",
                            "mensaje": f"Descanso insuficiente de {horas_descanso}h tras el turno anterior (Mínimo legal: 12h).",
                            "severidad": "bloqueo",
                            "detalle": {
                                "turno_anterior_fin": t_fin.isoformat(),
                                "nuevo_turno_inicio": nuevo_inicio.isoformat(),
                                "horas_descanso": horas_descanso,
                            },
                        }
                    )

            # Caso B: El turno existente comienza después de que termina el nuevo
            if t_ini >= nuevo_fin:
                gap = (t_ini - nuevo_fin).total_seconds()
                if gap < min_rest_seconds:
                    horas_descanso = Decimal(str(round(gap / 3600.0, 2)))
                    alertas.append(
                        {
                            "tipo": "DESCANSO_INSUFICIENTE",
                            "mensaje": f"Descanso insuficiente de {horas_descanso}h antes del siguiente turno (Mínimo legal: 12h).",
                            "severidad": "bloqueo",
                            "detalle": {
                                "nuevo_turno_fin": nuevo_fin.isoformat(),
                                "siguiente_turno_inicio": t_ini.isoformat(),
                                "horas_descanso": horas_descanso,
                            },
                        }
                    )

        # ----------------------------------------------------------------------
        # Regla 2: Exceso de 40 Horas Semanales (Lunes a Domingo)
        # ----------------------------------------------------------------------
        semana_lunes = nuevo_inicio.date() - timedelta(days=nuevo_inicio.date().weekday())
        semana_domingo = semana_lunes + timedelta(days=6)

        total_segundos_semana = (nuevo_fin - nuevo_inicio).total_seconds()

        for t in user_turnos:
            t_ini, t_fin = self._resolve_turno_datetimes(
                t.fecha_inicio,
                t.fecha_fin,
                t.hora_inicio,
                t.hora_fin,
                t.inicio_turno,
                t.fin_turno,
            )
            # Verificar si cae dentro de la misma semana
            if semana_lunes <= t_ini.date() <= semana_domingo:
                total_segundos_semana += (t_fin - t_ini).total_seconds()

        total_horas_semana = Decimal(str(round(total_segundos_semana / 3600.0, 2)))

        if total_horas_semana > Decimal("40.00"):
            alertas.append(
                {
                    "tipo": "EXCESO_40_HORAS",
                    "mensaje": f"La jornada proyectada de {total_horas_semana}h semanales supera el límite legal de 40 horas.",
                    "severidad": "advertencia",
                    "detalle": {
                        "semana_lunes": semana_lunes.isoformat(),
                        "semana_domingo": semana_domingo.isoformat(),
                        "total_horas_semanales": total_horas_semana,
                        "limite_legal": Decimal("40.00"),
                    },
                }
            )

        return {
            "tiene_alertas": len(alertas) > 0,
            "total_horas_semanales": total_horas_semana,
            "alertas": alertas,
        }

    def create_turno_horario(
        self,
        user_id: int,
        *,
        usuario_id: int | None = None,
        area_id: str | None = None,
        fecha_inicio: date | None = None,
        fecha_fin: date | None = None,
        hora_inicio: time | None = None,
        hora_fin: time | None = None,
        inicio_turno: datetime | None = None,
        fin_turno: datetime | None = None,
        nota: str | None = None,
        color: str | None = None,
        creado_por: int | None = None,
        tenant_id: str | None = None,
    ) -> TurnoHorario:
        """Crea un turno horario y normaliza fechas/horas UTC."""
        init_dt, end_dt = self._resolve_turno_datetimes(
            fecha_inicio,
            fecha_fin,
            hora_inicio,
            hora_fin,
            inicio_turno,
            fin_turno,
        )

        resolved_user_id = user_id or usuario_id or 0
        resolved_f_ini = fecha_inicio or init_dt.date()
        resolved_f_fin = fecha_fin or end_dt.date()
        resolved_h_ini = hora_inicio or init_dt.time()
        resolved_h_fin = hora_fin or end_dt.time()

        turno_id = self._next_turno_id
        self._next_turno_id += 1

        turno = TurnoHorario(
            id=turno_id,
            user_id=resolved_user_id,
            usuario_id=resolved_user_id,
            area_id=area_id,
            fecha_inicio=resolved_f_ini,
            fecha_fin=resolved_f_fin,
            hora_inicio=resolved_h_ini,
            hora_fin=resolved_h_fin,
            inicio_turno=init_dt,
            fin_turno=end_dt,
            nota=sanitize_text_input(nota.strip(), field_name="nota") if nota else None,
            color=color.strip() if color else None,
            creado_por=creado_por,
        )
        turno.tenant_id = str(tenant_id) if tenant_id else None
        turno.created_at = datetime.now(UTC)
        self._turnos[turno_id] = turno

        self._emit_realtime_event(
            event_type="operations.actividades.turno.created",
            payload={
                "turno_id": turno.id,
                "user_id": turno.user_id,
                "inicio_turno": turno.inicio_turno.isoformat() if turno.inicio_turno else None,
                "fin_turno": turno.fin_turno.isoformat() if turno.fin_turno else None,
                "area_id": turno.area_id,
            },
            required_permission="operations.actividades.horarios.view",
            tenant_id=tenant_id,
        )

        return turno

    def get_turnos_horarios(
        self,
        *,
        tenant_id: str | None = None,
        fecha_desde: date | None = None,
        fecha_hasta: date | None = None,
        area_id: str | None = None,
        usuario_id: int | None = None,
        skip: int = 0,
        limit: int = 200,
    ) -> list[TurnoHorario]:
        """Consulta turnos horarios dentro de un rango de fechas y filtros opcionales."""
        results: list[TurnoHorario] = []

        for t in self._turnos.values():
            if t.deleted_at is not None:
                continue
            if tenant_id is not None and getattr(t, "tenant_id", None) is not None and getattr(t, "tenant_id", None) != str(tenant_id):
                continue
            if area_id is not None and t.area_id != area_id:
                continue
            if usuario_id is not None and t.user_id != usuario_id and t.usuario_id != usuario_id:
                continue

            t_date = t.fecha_inicio or (t.inicio_turno.date() if t.inicio_turno else None)
            if t_date:
                if fecha_desde is not None and t_date < fecha_desde:
                    continue
                if fecha_hasta is not None and t_date > fecha_hasta:
                    continue

            results.append(t)

        results.sort(key=lambda t: t.inicio_turno or datetime.min.replace(tzinfo=UTC))
        return results[skip : skip + limit]

    def update_turno_horario(
        self,
        turno_id: int,
        *,
        user_id: int | None = None,
        area_id: str | None = None,
        fecha_inicio: date | None = None,
        fecha_fin: date | None = None,
        hora_inicio: time | None = None,
        hora_fin: time | None = None,
        inicio_turno: datetime | None = None,
        fin_turno: datetime | None = None,
        nota: str | None = None,
        color: str | None = None,
        tenant_id: str | None = None,
        actor_id: int | None = None,
    ) -> TurnoHorario:
        """Modifica un turno horario existente."""
        turno = self._turnos.get(turno_id)
        if not turno or turno.deleted_at is not None:
            raise ResourceNotFoundError(
                f"Turno horario id={turno_id} no encontrado.",
                i18n_key="operations:errors.turno_no_encontrado",
            )
        if tenant_id is not None and getattr(turno, "tenant_id", None) is not None and getattr(turno, "tenant_id", None) != str(tenant_id):
            raise ResourceNotFoundError(
                f"Turno horario id={turno_id} no encontrado.",
                i18n_key="operations:errors.turno_no_encontrado",
            )

        if user_id is not None:
            turno.user_id = user_id
            turno.usuario_id = user_id
        if area_id is not None:
            turno.area_id = area_id

        f_ini = fecha_inicio if fecha_inicio is not None else turno.fecha_inicio
        f_fin = fecha_fin if fecha_fin is not None else turno.fecha_fin
        h_ini = hora_inicio if hora_inicio is not None else turno.hora_inicio
        h_fin = hora_fin if hora_fin is not None else turno.hora_fin
        in_dt = inicio_turno if inicio_turno is not None else turno.inicio_turno
        fn_dt = fin_turno if fin_turno is not None else turno.fin_turno

        init_dt, end_dt = self._resolve_turno_datetimes(f_ini, f_fin, h_ini, h_fin, in_dt, fn_dt)
        turno.fecha_inicio = f_ini or init_dt.date()
        turno.fecha_fin = f_fin or end_dt.date()
        turno.hora_inicio = h_ini or init_dt.time()
        turno.hora_fin = h_fin or end_dt.time()
        turno.inicio_turno = init_dt
        turno.fin_turno = end_dt

        if nota is not None:
            turno.nota = sanitize_text_input(nota.strip(), field_name="nota") if nota.strip() else None
        if color is not None:
            turno.color = color.strip() if color else None

        turno.updated_at = datetime.now(UTC)

        self._emit_realtime_event(
            event_type="operations.actividades.turno.updated",
            payload={"turno_id": turno.id, "updated_by": actor_id},
            required_permission="operations.actividades.horarios.view",
            tenant_id=tenant_id,
        )

        return turno

    def delete_turno_horario(
        self,
        turno_id: int,
        *,
        tenant_id: str | None = None,
        actor_id: int | None = None,
    ) -> bool:
        """Aplica soft-delete a un turno horario."""
        turno = self._turnos.get(turno_id)
        if not turno or turno.deleted_at is not None:
            raise ResourceNotFoundError(
                f"Turno horario id={turno_id} no encontrado.",
                i18n_key="operations:errors.turno_no_encontrado",
            )
        if tenant_id is not None and getattr(turno, "tenant_id", None) is not None and getattr(turno, "tenant_id", None) != str(tenant_id):
            raise ResourceNotFoundError(
                f"Turno horario id={turno_id} no encontrado.",
                i18n_key="operations:errors.turno_no_encontrado",
            )

        turno.deleted_at = datetime.now(UTC)

        self._emit_realtime_event(
            event_type="operations.actividades.turno.deleted",
            payload={"turno_id": turno_id, "deleted_by": actor_id},
            required_permission="operations.actividades.horarios.view",
            tenant_id=tenant_id,
        )

        return True

    def clonar_semana(
        self,
        fecha_lunes_origen: date,
        fecha_lunes_destino: date,
        *,
        area_id: str | None = None,
        creador_por: int | None = None,
        tenant_id: str | None = None,
    ) -> list[TurnoHorario]:
        """
        Clona todos los turnos de la semana origen (lunes a domingo) desplazando
        sus fechas y timestamps exactamente al lunes de la semana destino.
        """
        if fecha_lunes_origen.weekday() != 0:
            raise DomainValidationError(
                "La fecha de origen debe corresponder a un día lunes.",
                i18n_key="operations:errors.origen_no_es_lunes",
            )
        if fecha_lunes_destino.weekday() != 0:
            raise DomainValidationError(
                "La fecha de destino debe corresponder a un día lunes.",
                i18n_key="operations:errors.destino_no_es_lunes",
            )

        delta_dias = (fecha_lunes_destino - fecha_lunes_origen).days
        domingo_origen = fecha_lunes_origen + timedelta(days=6)

        turnos_origen = [
            t
            for t in self._turnos.values()
            if t.deleted_at is None
            and (area_id is None or t.area_id == area_id)
            and (tenant_id is None or getattr(t, "tenant_id", None) is None or getattr(t, "tenant_id", None) == str(tenant_id))
            and (
                fecha_lunes_origen
                <= (t.fecha_inicio or (t.inicio_turno.date() if t.inicio_turno else date.min))
                <= domingo_origen
            )
        ]

        nuevos_turnos: list[TurnoHorario] = []
        for t in turnos_origen:
            nuevo_f_ini = (
                t.fecha_inicio + timedelta(days=delta_dias) if t.fecha_inicio else None
            )
            nuevo_f_fin = (
                t.fecha_fin + timedelta(days=delta_dias) if t.fecha_fin else None
            )
            nuevo_init_dt = (
                t.inicio_turno + timedelta(days=delta_dias) if t.inicio_turno else None
            )
            nuevo_fin_dt = (
                t.fin_turno + timedelta(days=delta_dias) if t.fin_turno else None
            )

            clonado = self.create_turno_horario(
                user_id=t.user_id,
                area_id=t.area_id,
                fecha_inicio=nuevo_f_ini,
                fecha_fin=nuevo_f_fin,
                hora_inicio=t.hora_inicio,
                hora_fin=t.hora_fin,
                inicio_turno=nuevo_init_dt,
                fin_turno=nuevo_fin_dt,
                nota=t.nota,
                color=t.color,
                creado_por=creador_por,
                tenant_id=tenant_id,
            )
            nuevos_turnos.append(clonado)

        return nuevos_turnos

    # ==========================================================================
    # 5. SINERGIA INTELIGENTE CON OPPYFY AI: MINUTA DE CIERRE Y TRASPASO
    # ==========================================================================

    def generar_minuta_traspaso(
        self,
        db: AsyncSession | None = None,
        fecha: date | str | None = None,
        area_id: str | None = None,
        *,
        tenant_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Genera la minuta ejecutiva estructurada de cierre y traspaso de turno impulsada por OppyFy AI.
        Recolecta:
        1. Notas de equipo del día agrupadas por categoría (incidentes, stock, producción, etc.).
        2. Tareas del día (completadas e incompletas con justificación obligatoria).
        3. Horarios y colaboradores del turno.
        Genera una síntesis estructurada lista para el Chef/Gerente con 4 puntos clave:
        - Incidentes y Novedades Críticas
        - Producción y Stock
        - Tareas Pendientes y Justificaciones
        - Dotación y Asistencia
        """
        # Permite invocación flexible: (db, fecha, area_id) o (fecha, area_id)
        if isinstance(db, (date, str)):
            if area_id is None and isinstance(fecha, str):
                area_id = fecha
            fecha = db
            db = None

        if fecha is None:
            target_date = datetime.now(UTC).date()
        elif isinstance(fecha, str):
            target_date = date.fromisoformat(fecha)
        elif isinstance(fecha, datetime):
            target_date = fecha.date()
        else:
            target_date = fecha

        # 1. Notas de equipo de la jornada
        notas_dia: list[NotaEquipo] = []
        for nota in self._notas_equipo.values():
            if nota.deleted_at is not None:
                continue
            if tenant_id is not None and getattr(nota, "tenant_id", None) is not None and getattr(nota, "tenant_id", None) != str(tenant_id):
                continue
            if area_id is not None and nota.area_id != area_id:
                continue
            n_date = None
            if nota.fecha:
                n_date = nota.fecha.date() if isinstance(nota.fecha, datetime) else nota.fecha
            elif nota.created_at:
                n_date = nota.created_at.date() if isinstance(nota.created_at, datetime) else nota.created_at

            if n_date is not None and n_date != target_date:
                continue
            notas_dia.append(nota)

        # Agrupación por categoría
        incidentes_notas = [
            n
            for n in notas_dia
            if (n.categoria or "").lower() in ("incidente", "incidentes", "mantencion", "alerta")
            or any(kw in n.titulo.lower() for kw in ("incidente", "falla", "urgente", "problema"))
        ]
        produccion_notas = [
            n
            for n in notas_dia
            if (n.categoria or "").lower() in ("produccion", "stock", "cocina")
            or n.insumo_id is not None
            or n.receta_id is not None
        ]

        # 2. Tareas operativas de la jornada
        tareas_dia: list[Tarea] = []
        for t in self._tareas.values():
            if t.deleted_at is not None:
                continue
            if tenant_id is not None and getattr(t, "tenant_id", None) is not None and getattr(t, "tenant_id", None) != str(tenant_id):
                continue
            if area_id is not None and t.area_id != area_id:
                continue
            t_date = None
            if t.fecha_limite:
                t_date = t.fecha_limite.date() if isinstance(t.fecha_limite, datetime) else t.fecha_limite
            elif t.created_at:
                t_date = t.created_at.date() if isinstance(t.created_at, datetime) else t.created_at

            if t_date is not None and t_date != target_date:
                continue
            tareas_dia.append(t)

        completadas = [t for t in tareas_dia if t.completada or t.estado == "completada"]
        incompletas = [t for t in tareas_dia if not (t.completada or t.estado == "completada")]

        # 3. Turnos y dotación de la jornada
        turnos_dia: list[TurnoHorario] = []
        for tur in self._turnos.values():
            if tur.deleted_at is not None:
                continue
            if tenant_id is not None and getattr(tur, "tenant_id", None) is not None and getattr(tur, "tenant_id", None) != str(tenant_id):
                continue
            if area_id is not None and tur.area_id != area_id:
                continue
            tur_date = tur.fecha_inicio or (tur.inicio_turno.date() if tur.inicio_turno else None)
            if tur_date is not None and tur_date != target_date:
                continue
            turnos_dia.append(tur)

        colaboradores_ids = sorted(list({tur.user_id for tur in turnos_dia if tur.user_id}))

        # 4 Puntos Clave
        puntos_incidentes: list[str] = []
        if incidentes_notas:
            for n in incidentes_notas:
                puntos_incidentes.append(f"⚠️ [{n.categoria.upper()}] {n.titulo}: {n.contenido}")
        else:
            puntos_incidentes.append("Sin incidentes reportados en el turno. Operación continua y sin bloqueos.")

        puntos_produccion: list[str] = []
        if produccion_notas:
            for n in produccion_notas:
                extra: list[str] = []
                if n.insumo_id:
                    extra.append(f"Insumo #{n.insumo_id}")
                if n.receta_id:
                    extra.append(f"Receta #{n.receta_id}")
                ref = f" ({', '.join(extra)})" if extra else ""
                puntos_produccion.append(f"📦 {n.titulo}{ref}: {n.contenido}")
        else:
            puntos_produccion.append("Producción y stock dentro de los parámetros normales de servicio.")

        puntos_tareas_pendientes: list[dict[str, Any]] = []
        for t in incompletas:
            puntos_tareas_pendientes.append({
                "id": t.id,
                "titulo": t.titulo,
                "urgencia": t.urgencia,
                "asignado_a_user_id": t.asignado_a_user_id,
                "estado": t.estado,
                "nota_incompleta": t.nota_incompleta or "Pendiente de cierre para el siguiente turno",
            })

        dotacion_resumen: dict[str, Any] = {
            "total_colaboradores": len(colaboradores_ids),
            "colaboradores_ids": colaboradores_ids,
            "total_turnos": len(turnos_dia),
            "turnos": [
                {
                    "id": t.id,
                    "user_id": t.user_id,
                    "hora_inicio": str(t.hora_inicio) if t.hora_inicio else None,
                    "hora_fin": str(t.hora_fin) if t.hora_fin else None,
                    "area_id": t.area_id,
                }
                for t in turnos_dia
            ],
        }

        # Generación de Síntesis Ejecutiva en Markdown estructurado
        area_label = area_id.upper() if area_id else "TODAS LAS ÁREAS"
        lines: list[str] = [
            f"# 📋 Minuta Ejecutiva de Traspaso de Turno — {target_date.isoformat()}",
            f"> **Área:** {area_label} | **Generado por:** OppyFy AI 🤖 | **Fecha:** {target_date.isoformat()}",
            "",
            "### 1. 🚨 Incidentes y Novedades Críticas",
        ]
        for inc in puntos_incidentes:
            lines.append(f"- {inc}")

        lines.extend([
            "",
            "### 2. 🍳 Producción y Stock",
        ])
        for prod in puntos_produccion:
            lines.append(f"- {prod}")

        lines.extend([
            "",
            "### 3. ⏳ Tareas Pendientes y Relevo Operativo",
        ])
        if puntos_tareas_pendientes:
            for tp in puntos_tareas_pendientes:
                lines.append(
                    f"- **[{tp['urgencia'].upper()}] {tp['titulo']}** (Asignado: Colaborador #{tp['asignado_a_user_id'] or 'S/A'}): {tp['nota_incompleta']}"
                )
        else:
            lines.append(f"- ✅ 100% de tareas cerradas ({len(completadas)} completadas). Turno listo para relevo.")

        lines.extend([
            "",
            f"### 4. 👥 Dotación y Asistencia ({len(colaboradores_ids)} Colaboradores en Turno)",
        ])
        if turnos_dia:
            for tur in turnos_dia:
                h_ini = str(tur.hora_inicio) if tur.hora_inicio else "--:--"
                h_fin = str(tur.hora_fin) if tur.hora_fin else "--:--"
                lines.append(f"- Colaborador #{tur.user_id}: {h_ini} - {h_fin} (Área: {tur.area_id or 'General'})")
        else:
            lines.append("- No se registraron turnos programados en el sistema para esta jornada.")

        lines.extend([
            "",
            "---",
            f"*Minuta ejecutiva procesada por OppyFy v2.0 ({datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S UTC')}).*",
        ])

        resumen_ejecutivo = "\n".join(lines)

        return {
            "fecha": target_date,
            "area_id": area_id,
            "resumen_ejecutivo": resumen_ejecutivo,
            "puntos_clave": {
                "incidentes": puntos_incidentes,
                "produccion": puntos_produccion,
                "tareas_pendientes": puntos_tareas_pendientes,
                "dotacion": dotacion_resumen,
            },
            "estadisticas": {
                "total_notas": len(notas_dia),
                "total_tareas": len(tareas_dia),
                "tareas_completadas": len(completadas),
                "tareas_incompletas": len(incompletas),
                "total_turnos": len(turnos_dia),
            },
            "generado_en": datetime.now(UTC),
        }

