"""
oppytec-backend/src/modules/operations/application/approval_service.py
Servicios de Aplicación Transaccionales ACID para el Centro de Aprobaciones y Matriz de Gobernanza:
- `ApprovalService`: Ciclo de vida de solicitudes, bloqueo pesimista FOR UPDATE, impacto en Kardex y WebSockets.
- `BuffetApprovalService`: Auditoría de sesiones de buffet, balance, fotos y split de sobrantes (retorno vs merma).
- `NotificationMatrixService`: Matriz de suscripción y reglas de despacho de alertas por cargo.
Cumple Regla 01 (Clean Architecture), Regla 02 (Zero-Float con Decimal) y Regla 15 (RFC 7807 e i18n).
"""
# mypy: disable-error-code="explicit-any"
from __future__ import annotations

import logging
from collections.abc import AsyncGenerator, Sequence
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from opentelemetry import trace

from src.core.database import get_tenant_db_session, validate_tenant_schema_name
from src.core.exceptions import (
    DomainValidationError,
    OppyTecError,
    ResourceNotFoundError,
)
from src.core.observability import get_tenant_telemetry_context, trace_span
from src.core.realtime.router import get_realtime_publisher
from src.core.realtime.schemas import RealtimeEventEnvelope
from src.modules.inventory.application.inventory_service import InventoryService
from src.modules.inventory.application.physical_count_service import PhysicalCountService
from src.modules.inventory.domain.kardex_math import canonical_lock_order
from src.modules.operations.domain.approvals import (
    APPROVAL_TYPE_TO_CATEGORY,
    ApprovalCategory,
    ApprovalDomainError,
    ApprovalStatus,
    ApprovalType,
    InvalidApprovalTransitionError,
    InvalidRejectionReasonError,
    get_approval_category,
)
from src.modules.operations.infrastructure.approval_models import (
    NotificationMatrixRuleModel,
    SolicitudAprobacionModel,
)

logger = logging.getLogger("oppytec.operations.approval_service")
tracer = trace.get_tracer("oppytec.operations.approvals")

# Catálogo descriptivo canónico de los 12 tipos de solicitudes de OppyTec
NOTIFICATION_CATALOG: list[dict[str, Any]] = [
    {
        "type": ApprovalType.MERMA.value,
        "label": "Merma de Inventario",
        "category": ApprovalCategory.OPERACIONES.value,
        "description": "Bajas directas de insumos por deterioro, vencimiento o merma de bodega.",
    },
    {
        "type": ApprovalType.MERMA_RECETA.value,
        "label": "Merma en Producción / Receta",
        "category": ApprovalCategory.OPERACIONES.value,
        "description": "Mermas detectadas durante la preparación de recetas o producciones intermedias.",
    },
    {
        "type": ApprovalType.CONSUMO.value,
        "label": "Consumo Interno / Colación",
        "category": ApprovalCategory.OPERACIONES.value,
        "description": "Consumo de insumos por personal, colaciones autorizadas o degustación.",
    },
    {
        "type": ApprovalType.CONSUMO_BUFFET.value,
        "label": "Cierre de Servicio Buffet",
        "category": ApprovalCategory.OPERACIONES.value,
        "description": "Auditoría de sesión de buffet, balance apertura/cierre y split de sobrantes.",
    },
    {
        "type": ApprovalType.CONTEO.value,
        "label": "Recuento Físico de Inventario",
        "category": ApprovalCategory.INVENTARIO.value,
        "description": "Cuadratura periódica de existencias físicas versus Kardex teórico del sistema.",
    },
    {
        "type": ApprovalType.PRODUCTO_BORRADOR_RECETA.value,
        "label": "Insumo Borrador Receta",
        "category": ApprovalCategory.INVENTARIO.value,
        "description": "Creación rápida de insumos preliminares generados durante el costeo de escandallos.",
    },
    {
        "type": ApprovalType.SOLICITUD_COMPRA.value,
        "label": "Solicitud de Orden de Compra",
        "category": ApprovalCategory.COMPRAS.value,
        "description": "Requerimientos de abastecimiento de insumos emitidos por jefaturas operativas.",
    },
    {
        "type": ApprovalType.RECIBIR_PEDIDO.value,
        "label": "Recepción de Mercadería",
        "category": ApprovalCategory.COMPRAS.value,
        "description": "Recepción de órdenes de compra con discrepancias de cantidad o precio respecto a factura.",
    },
    {
        "type": ApprovalType.VINCULACION_PROVEEDOR.value,
        "label": "Vinculación de Proveedor",
        "category": ApprovalCategory.COMPRAS.value,
        "description": "Homologación y mapeo de alias de proveedor detectados en facturas electrónicas.",
    },
    {
        "type": ApprovalType.MENCION_NOTA.value,
        "label": "Mención en Nota Operativa",
        "category": ApprovalCategory.EQUIPO.value,
        "description": "Notificaciones directas de comunicación inter-turnos y notas de supervisión.",
    },
    {
        "type": ApprovalType.PERFIL.value,
        "label": "Actualización de Perfil / Cargo",
        "category": ApprovalCategory.EQUIPO.value,
        "description": "Solicitudes de cambio en información del trabajador o asignación de cargo.",
    },
    {
        "type": ApprovalType.COLOR_TURNO.value,
        "label": "Color y Turno Operativo",
        "category": ApprovalCategory.EQUIPO.value,
        "description": "Asignación o cambio en la personalización visual de turnos de trabajo.",
    },
]

DEFAULT_CARGOS: list[dict[str, Any]] = [
    {"id": 1, "cargo": "administrador", "nombre": "Administrador General", "es_aprobador_default": True},
    {"id": 2, "cargo": "supervisor", "nombre": "Supervisor de Operaciones", "es_aprobador_default": True},
    {"id": 3, "cargo": "chef", "nombre": "Chef Ejecutivo / Cocina", "es_aprobador_default": True},
    {"id": 4, "cargo": "bodeguero", "nombre": "Encargado de Bodega", "es_aprobador_default": False},
    {"id": 5, "cargo": "cocinero", "nombre": "Cocinero", "es_aprobador_default": False},
    {"id": 6, "cargo": "garzon", "nombre": "Garzón / Salonero", "es_aprobador_default": False},
    {"id": 7, "cargo": "cajero", "nombre": "Cajero", "es_aprobador_default": False},
]


def _format_tenant_schema(tenant_id: str | UUID | None) -> str:
    """Normaliza y valida el esquema de inquilino `tenant_*`."""
    if not tenant_id:
        return "tenant_default"
    cleaned = str(tenant_id).strip().lower().replace("-", "_")
    if not cleaned.startswith("tenant_"):
        cleaned = f"tenant_{cleaned}"
    return validate_tenant_schema_name(cleaned)


def _parse_uuid(val: UUID | str) -> UUID:
    """Convierte de forma segura a UUID."""
    if isinstance(val, UUID):
        return val
    try:
        return UUID(str(val))
    except Exception as exc:
        raise DomainValidationError(
            f"Identificador inválido '{val}': se esperaba UUID.",
            i18n_key="operations:errors.invalid_uuid",
        ) from exc


class ApprovalService:
    """
    Servicio de aplicación transaccional de Solicitudes de Aprobación.
    Orquesta persistencia en `solicitudes_aprobacion`, validación de dominio,
    bloqueos pesimistas para anti-concurrencia, mutaciones en Kardex y eventos WebSocket.
    """

    def __init__(
        self,
        inventory_service: InventoryService | None = None,
        physical_count_service: PhysicalCountService | None = None,
        session_or_none: AsyncSession | None = None,
        use_in_memory: bool = False,
    ) -> None:
        self._inventory = inventory_service or InventoryService()
        self._physical_count = physical_count_service or PhysicalCountService(inventory=self._inventory)
        self._injected_session = session_or_none
        self._use_in_memory = use_in_memory
        self._memory_store: dict[UUID, SolicitudAprobacionModel] = {}

    def enable_in_memory_mode(self) -> None:
        """Activa el modo en memoria para aislamiento y testing sin base de datos."""
        self._use_in_memory = True

    def reset_in_memory_store(self) -> None:
        """Limpia el almacenamiento en memoria."""
        self._memory_store.clear()
        self._inventory.reset()
        self._physical_count.reset()

    def set_session(self, session: AsyncSession | None) -> None:
        """Asigna una sesión SQLAlchemy explícita (útil en testing)."""
        self._injected_session = session
        if session is not None:
            self._use_in_memory = False

    async def _get_session_ctx(self, tenant_id: str | UUID | None) -> AsyncGenerator[AsyncSession, None]:
        """Obtiene una sesión asíncrona gestionada para el tenant."""
        if self._injected_session is not None:
            yield self._injected_session
            return

        schema = _format_tenant_schema(tenant_id)
        async for s in get_tenant_db_session(schema):
            yield s

    async def _emit_websocket_event(
        self,
        *,
        event_type: str,
        tenant_id: str | UUID | None,
        payload: dict[str, Any],
        query_keys_to_invalidate: list[list[str]] | None = None,
    ) -> None:
        """Emite un evento de tiempo real vía Redis Pub/Sub."""
        try:
            publisher = get_realtime_publisher()
            tenant_uuid = None
            if tenant_id:
                try:
                    tenant_uuid = UUID(str(tenant_id)) if not isinstance(tenant_id, UUID) else tenant_id
                except Exception:
                    tenant_uuid = None

            envelope = RealtimeEventEnvelope(
                event_type=event_type,
                tenant_id=tenant_uuid,
                payload=payload,
                query_keys_to_invalidate=query_keys_to_invalidate
                or [["approvals"], ["pending-count"], ["approvals", "pending-count"]],
            )
            await publisher.publish_event(envelope)
        except Exception as exc:
            logger.warning("Fallo al emitir evento websocket '%s': %s", event_type, exc)

    async def create_request(
        self,
        *,
        tipo: str | ApprovalType,
        usuario_id: int,
        detalles: dict[str, Any] | None = None,
        bodega_id: int | None = None,
        area_operativa_id: int | None = None,
        tenant_id: str | UUID | None = None,
        session: AsyncSession | None = None,
    ) -> SolicitudAprobacionModel:
        """
        Crea de forma atómica una nueva solicitud de aprobación en estado 'pendiente'
        y notifica en tiempo real vía WebSocket `notification.created`.
        """
        tipo_str = tipo.value if isinstance(tipo, ApprovalType) else str(tipo).strip()
        try:
            approval_type = ApprovalType(tipo_str)
        except ValueError as exc:
            raise ApprovalDomainError(
                f"Tipo de solicitud no válido: '{tipo_str}'",
                i18n_key="operations:errors.invalid_approval_type",
                context={"tipo": tipo_str},
            ) from exc

        if not isinstance(usuario_id, int) or isinstance(usuario_id, bool) or usuario_id <= 0:
            raise ApprovalDomainError(
                "usuario_id debe ser un entero positivo válido.",
                i18n_key="operations:errors.invalid_user_id",
            )

        solicitud_id = uuid4()
        clean_detalles = dict(detalles or {})

        model = SolicitudAprobacionModel(
            id=solicitud_id,
            tipo=approval_type.value,
            estado=ApprovalStatus.PENDIENTE.value,
            usuario_id=usuario_id,
            bodega_id=bodega_id,
            area_operativa_id=area_operativa_id,
            detalles=clean_detalles,
            resuelto_por=None,
            motivo_rechazo=None,
            resuelto_at=None,
        )
        model.created_at = datetime.now(timezone.utc)

        if self._use_in_memory:
            self._memory_store[model.id] = model
            created = model
        else:
            async def _do_create(s: AsyncSession) -> SolicitudAprobacionModel:
                s.add(model)
                await s.flush()
                return model

            if session is not None:
                created = await _do_create(session)
            else:
                async for s in self._get_session_ctx(tenant_id):
                    created = await _do_create(s)
                    await s.commit()

        # Emisión de evento WebSocket
        categoria = get_approval_category(approval_type).value
        await self._emit_websocket_event(
            event_type="notification.created",
            tenant_id=tenant_id,
            payload={
                "solicitud_id": str(created.id),
                "tipo": created.tipo,
                "categoria": categoria,
                "estado": created.estado,
                "usuario_id": created.usuario_id,
                "bodega_id": created.bodega_id,
                "area_operativa_id": created.area_operativa_id,
                "detalles": created.detalles,
            },
        )

        return created

    async def list_requests(
        self,
        *,
        estado: str | None = None,
        categoria: str | None = None,
        area_id: str | int | None = None,
        bodega_id: int | None = None,
        page: int = 1,
        page_size: int = 20,
        q: str | None = None,
        tenant_id: str | UUID | None = None,
        session: AsyncSession | None = None,
    ) -> tuple[list[SolicitudAprobacionModel], int]:
        """
        Lista solicitudes de aprobación con filtrado múltiple, búsqueda textual y paginación.
        """
        page = max(1, page)
        page_size = max(1, min(100, page_size))
        offset = (page - 1) * page_size

        if self._use_in_memory:
            all_items = [
                m for m in self._memory_store.values() if getattr(m, "deleted_at", None) is None
            ]

            # Filtro por estado
            if estado and estado.lower() not in ("all", "todos"):
                all_items = [m for m in all_items if m.estado.lower() == estado.strip().lower()]

            # Filtro por categoría
            if categoria and categoria.lower() not in ("all", "todos"):
                cat_lower = categoria.strip().lower()
                all_items = [
                    m for m in all_items if get_approval_category(m.tipo).value == cat_lower
                ]

            # Filtro por área operativa
            if area_id is not None and str(area_id).lower() not in ("all", "todos", ""):
                try:
                    area_int = int(area_id)
                    all_items = [m for m in all_items if m.area_operativa_id == area_int]
                except ValueError:
                    pass

            # Filtro por bodega
            if bodega_id is not None:
                all_items = [m for m in all_items if m.bodega_id == bodega_id]

            # Filtro por búsqueda textual q
            if q and q.strip():
                clean_q = q.strip().lower()
                all_items = [
                    m for m in all_items
                    if clean_q in m.tipo.lower() or clean_q in str(m.detalles).lower()
                ]

            # Orden descendente por created_at
            all_items.sort(key=lambda x: x.created_at, reverse=True)
            total = len(all_items)
            paginated = all_items[offset : offset + page_size]
            return paginated, total

        async def _do_list(s: AsyncSession) -> tuple[list[SolicitudAprobacionModel], int]:
            stmt = select(SolicitudAprobacionModel).where(SolicitudAprobacionModel.deleted_at.is_(None))

            if estado and estado.lower() not in ("all", "todos"):
                stmt = stmt.where(SolicitudAprobacionModel.estado == estado.strip().lower())

            if categoria and categoria.lower() not in ("all", "todos"):
                cat_lower = categoria.strip().lower()
                matching_types = [
                    t.value for t, cat in APPROVAL_TYPE_TO_CATEGORY.items() if cat.value == cat_lower
                ]
                if matching_types:
                    stmt = stmt.where(SolicitudAprobacionModel.tipo.in_(matching_types))
                else:
                    stmt = stmt.where(SolicitudAprobacionModel.tipo == "__NONE__")

            if area_id is not None and str(area_id).lower() not in ("all", "todos", ""):
                try:
                    area_int = int(area_id)
                    stmt = stmt.where(SolicitudAprobacionModel.area_operativa_id == area_int)
                except ValueError:
                    pass

            if bodega_id is not None:
                stmt = stmt.where(SolicitudAprobacionModel.bodega_id == bodega_id)

            if q and q.strip():
                clean_q = f"%{q.strip().lower()}%"
                stmt = stmt.where(
                    func.lower(SolicitudAprobacionModel.tipo).like(clean_q)
                )

            count_stmt = select(func.count()).select_from(stmt.subquery())
            total = (await s.execute(count_stmt)).scalar() or 0

            data_stmt = stmt.order_by(SolicitudAprobacionModel.created_at.desc()).offset(offset).limit(page_size)
            result = await s.execute(data_stmt)
            items = list(result.scalars().all())
            return items, total

        if session is not None:
            return await _do_list(session)

        async for s in self._get_session_ctx(tenant_id):
            return await _do_list(s)
        return [], 0

    async def get_pending_count(
        self,
        *,
        area_id: str | int | None = None,
        tenant_id: str | UUID | None = None,
        session: AsyncSession | None = None,
    ) -> dict[str, Any]:
        """
        Conteo optimizado (< 5ms) de solicitudes pendientes agrupadas por categoría y desglosadas por área.
        """
        if self._use_in_memory:
            pending_items = [
                m for m in self._memory_store.values()
                if getattr(m, "deleted_at", None) is None and m.estado == ApprovalStatus.PENDIENTE.value
            ]
            if area_id is not None and str(area_id).lower() not in ("all", "todos", ""):
                try:
                    area_int = int(area_id)
                    pending_items = [m for m in pending_items if m.area_operativa_id == area_int]
                except ValueError:
                    pass

            counts_by_category = {
                ApprovalCategory.OPERACIONES.value: 0,
                ApprovalCategory.INVENTARIO.value: 0,
                ApprovalCategory.COMPRAS.value: 0,
                ApprovalCategory.EQUIPO.value: 0,
            }
            total_pending = len(pending_items)
            for m in pending_items:
                cat = get_approval_category(m.tipo).value
                counts_by_category[cat] = counts_by_category.get(cat, 0) + 1

            return {
                "total_pending": total_pending,
                "by_category": counts_by_category,
                "area_id": str(area_id) if area_id else None,
            }

        async def _do_count(s: AsyncSession) -> dict[str, Any]:
            stmt = select(SolicitudAprobacionModel.tipo, func.count(SolicitudAprobacionModel.id)).where(
                SolicitudAprobacionModel.deleted_at.is_(None),
                SolicitudAprobacionModel.estado == ApprovalStatus.PENDIENTE.value,
            )

            if area_id is not None and str(area_id).lower() not in ("all", "todos", ""):
                try:
                    area_int = int(area_id)
                    stmt = stmt.where(SolicitudAprobacionModel.area_operativa_id == area_int)
                except ValueError:
                    pass

            stmt = stmt.group_by(SolicitudAprobacionModel.tipo)
            rows = (await s.execute(stmt)).all()

            counts_by_category = {
                ApprovalCategory.OPERACIONES.value: 0,
                ApprovalCategory.INVENTARIO.value: 0,
                ApprovalCategory.COMPRAS.value: 0,
                ApprovalCategory.EQUIPO.value: 0,
            }

            total_pending = 0
            for tipo_val, count in rows:
                try:
                    cat = get_approval_category(tipo_val).value
                    counts_by_category[cat] = counts_by_category.get(cat, 0) + count
                    total_pending += count
                except Exception:
                    total_pending += count

            return {
                "total_pending": total_pending,
                "by_category": counts_by_category,
                "area_id": str(area_id) if area_id else None,
            }

        if session is not None:
            return await _do_count(session)

        async for s in self._get_session_ctx(tenant_id):
            return await _do_count(s)
        return {
            "total_pending": 0,
            "by_category": {
                "operaciones": 0,
                "inventario": 0,
                "compras": 0,
                "equipo": 0,
            },
            "area_id": str(area_id) if area_id else None,
        }

    async def get_request_by_id(
        self,
        request_id: UUID | str,
        *,
        tenant_id: str | UUID | None = None,
        session: AsyncSession | None = None,
    ) -> SolicitudAprobacionModel:
        """Obtiene una solicitud por su ID UUID o lanza ResourceNotFoundError (404)."""
        clean_uuid = _parse_uuid(request_id)

        if self._use_in_memory:
            model = self._memory_store.get(clean_uuid)
            if model is None or getattr(model, "deleted_at", None) is not None:
                raise ResourceNotFoundError(
                    f"Solicitud de aprobación con ID '{request_id}' no fue encontrada.",
                    i18n_key="operations:errors.approval_not_found",
                    context={"solicitud_id": str(request_id)},
                )
            return model

        async def _do_get(s: AsyncSession) -> SolicitudAprobacionModel:
            stmt = select(SolicitudAprobacionModel).where(
                SolicitudAprobacionModel.id == clean_uuid,
                SolicitudAprobacionModel.deleted_at.is_(None),
            )
            result = await s.execute(stmt)
            obj = result.scalar_one_or_none()
            if obj is None:
                raise ResourceNotFoundError(
                    f"Solicitud de aprobación con ID '{request_id}' no fue encontrada.",
                    i18n_key="operations:errors.approval_not_found",
                    context={"solicitud_id": str(request_id)},
                )
            return obj

        if session is not None:
            return await _do_get(session)

        async for s in self._get_session_ctx(tenant_id):
            return await _do_get(s)

        raise ResourceNotFoundError(
            f"Solicitud con ID '{request_id}' no encontrada.",
            i18n_key="operations:errors.approval_not_found",
        )

    def _execute_kardex_impact(
        self,
        model: SolicitudAprobacionModel,
        actor_id: int,
        tenant_id: str | UUID | None,
    ) -> None:
        """Aplica el impacto en existencias según el tipo de solicitud."""
        detalles = model.detalles or {}
        bodega_id = model.bodega_id or int(detalles.get("bodega_id", 1))

        if model.tipo in (ApprovalType.MERMA.value, ApprovalType.MERMA_RECETA.value):
            items = detalles.get("items")
            if isinstance(items, list) and len(items) > 0:
                prod_ids = [int(it.get("producto_id", 0)) for it in items if int(it.get("producto_id", 0)) > 0]
                ordered_pids = canonical_lock_order(prod_ids)
                item_map = {int(it.get("producto_id", 0)): it for it in items}
                for pid in ordered_pids:
                    it = item_map[pid]
                    qty = Decimal(str(it.get("quantity") or it.get("cantidad", 0)))
                    cost = Decimal(str(it.get("unit_cost") or it.get("costo_unitario", 0)))
                    if qty > 0:
                        self._inventory.register_movement(
                            producto_id=pid,
                            bodega_id=int(it.get("bodega_id", bodega_id)),
                            movement_type="MERMA",
                            quantity=qty,
                            unit_cost=cost,
                            actor_user_id=actor_id,
                            tenant_id=str(tenant_id) if tenant_id else None,
                        )
            else:
                pid = int(detalles.get("producto_id", 0))
                qty = Decimal(str(detalles.get("quantity") or detalles.get("cantidad", 0)))
                cost = Decimal(str(detalles.get("unit_cost") or detalles.get("costo_unitario", 0)))
                if pid > 0 and qty > 0:
                    self._inventory.register_movement(
                        producto_id=pid,
                        bodega_id=bodega_id,
                        movement_type="MERMA",
                        quantity=qty,
                        unit_cost=cost,
                        actor_user_id=actor_id,
                        tenant_id=str(tenant_id) if tenant_id else None,
                    )

        elif model.tipo in (ApprovalType.CONSUMO.value,):
            items = detalles.get("items")
            if isinstance(items, list) and len(items) > 0:
                prod_ids = [int(it.get("producto_id", 0)) for it in items if int(it.get("producto_id", 0)) > 0]
                ordered_pids = canonical_lock_order(prod_ids)
                item_map = {int(it.get("producto_id", 0)): it for it in items}
                for pid in ordered_pids:
                    it = item_map[pid]
                    qty = Decimal(str(it.get("quantity") or it.get("cantidad", 0)))
                    cost = Decimal(str(it.get("unit_cost") or it.get("costo_unitario", 0)))
                    if qty > 0:
                        self._inventory.register_movement(
                            producto_id=pid,
                            bodega_id=int(it.get("bodega_id", bodega_id)),
                            movement_type="CONSUMO",
                            quantity=qty,
                            unit_cost=cost,
                            actor_user_id=actor_id,
                            tenant_id=str(tenant_id) if tenant_id else None,
                        )
            else:
                pid = int(detalles.get("producto_id", 0))
                qty = Decimal(str(detalles.get("quantity") or detalles.get("cantidad", 0)))
                cost = Decimal(str(detalles.get("unit_cost") or detalles.get("costo_unitario", 0)))
                if pid > 0 and qty > 0:
                    self._inventory.register_movement(
                        producto_id=pid,
                        bodega_id=bodega_id,
                        movement_type="CONSUMO",
                        quantity=qty,
                        unit_cost=cost,
                        actor_user_id=actor_id,
                        tenant_id=str(tenant_id) if tenant_id else None,
                    )

        elif model.tipo == ApprovalType.CONTEO.value:
            conteo_id = detalles.get("conteo_id")
            if conteo_id is not None:
                try:
                    self._physical_count.approve_and_reconcile(
                        conteo_id=int(conteo_id),
                        aprobador_user_id=actor_id,
                        tenant_id=str(tenant_id) if tenant_id else None,
                    )
                except Exception as err:
                    logger.warning("No se reconcilió PhysicalCountService automáticamente: %s", err)

        elif model.tipo == ApprovalType.RECIBIR_PEDIDO.value:
            items = detalles.get("items")
            if isinstance(items, list):
                for it in items:
                    pid = int(it.get("producto_id", 0))
                    qty = Decimal(str(it.get("quantity") or it.get("cantidad", 0)))
                    cost = Decimal(str(it.get("unit_cost") or it.get("costo_unitario", 0)))
                    if pid > 0 and qty > 0:
                        self._inventory.register_movement(
                            producto_id=pid,
                            bodega_id=int(it.get("bodega_id", bodega_id)),
                            movement_type="ENTRADA",
                            quantity=qty,
                            unit_cost=cost,
                            actor_user_id=actor_id,
                            tenant_id=str(tenant_id) if tenant_id else None,
                        )

    async def approve_request(
        self,
        request_id: UUID | str,
        actor_id: int,
        edited_details: dict[str, Any] | None = None,
        *,
        tenant_id: str | UUID | None = None,
        session: AsyncSession | None = None,
    ) -> SolicitudAprobacionModel:
        """
        Aprueba atómicamente la solicitud bajo bloqueo pesimista `SELECT ... FOR UPDATE`,
        ejecuta el impacto correspondiente en Kardex / Inventario / Compras
        y emite el evento WebSocket `notification.resolved`.
        """
        clean_uuid = _parse_uuid(request_id)
        if not isinstance(actor_id, int) or isinstance(actor_id, bool) or actor_id <= 0:
            raise ApprovalDomainError("actor_id debe ser un entero positivo válido de resolutor.")

        resolved_tenant = str(tenant_id) if tenant_id else (get_tenant_telemetry_context().tenant_id or "")
        with trace_span(
            "operations.approvals.approve",
            attributes={
                "tenant_id": resolved_tenant,
                "solicitud_id": str(clean_uuid),
                "actor_id": actor_id,
            },
            tracer_name="oppytec.operations.approvals",
        ):
            if self._use_in_memory:
                model = self._memory_store.get(clean_uuid)
                if model is None or getattr(model, "deleted_at", None) is not None:
                    raise ResourceNotFoundError(
                        f"Solicitud de aprobación '{request_id}' no encontrada.",
                        i18n_key="operations:errors.approval_not_found",
                    )

                if model.estado != ApprovalStatus.PENDIENTE.value:
                    raise InvalidApprovalTransitionError(
                        f"Transición inválida: la solicitud {request_id} está en estado '{model.estado}' "
                        "y solo solicitudes en estado 'pendiente' pueden transicionar a 'aprobado'.",
                        context={"solicitud_id": str(request_id), "estado_actual": model.estado},
                    )

                if edited_details is not None:
                    merged = dict(model.detalles)
                    merged.update(edited_details)
                    model.detalles = merged

                self._execute_kardex_impact(model, actor_id, tenant_id)

                model.estado = ApprovalStatus.APROBADO.value
                model.resuelto_por = actor_id
                model.resuelto_at = datetime.now(timezone.utc)
                resolved_model = model
            else:
                async def _do_approve(s: AsyncSession) -> SolicitudAprobacionModel:
                    stmt = select(SolicitudAprobacionModel).where(
                        SolicitudAprobacionModel.id == clean_uuid,
                        SolicitudAprobacionModel.deleted_at.is_(None),
                    )
                    bind = s.bind
                    if bind is not None and bind.dialect.name == "postgresql":
                        stmt = stmt.with_for_update()

                    res = await s.execute(stmt)
                    model = res.scalar_one_or_none()
                    if model is None:
                        raise ResourceNotFoundError(
                            f"Solicitud de aprobación '{request_id}' no encontrada.",
                            i18n_key="operations:errors.approval_not_found",
                        )

                    if model.estado != ApprovalStatus.PENDIENTE.value:
                        raise InvalidApprovalTransitionError(
                            f"Transición inválida: la solicitud {request_id} está en estado '{model.estado}' "
                            "y solo solicitudes en estado 'pendiente' pueden transicionar a 'aprobado'.",
                            context={"solicitud_id": str(request_id), "estado_actual": model.estado},
                        )

                    if edited_details is not None:
                        merged = dict(model.detalles)
                        merged.update(edited_details)
                        model.detalles = merged

                    self._execute_kardex_impact(model, actor_id, tenant_id)

                    model.estado = ApprovalStatus.APROBADO.value
                    model.resuelto_por = actor_id
                    model.resuelto_at = datetime.now(timezone.utc)
                    await s.flush()
                    return model

                if session is not None:
                    resolved_model = await _do_approve(session)
                else:
                    async for s in self._get_session_ctx(tenant_id):
                        resolved_model = await _do_approve(s)
                        await s.commit()

            # Emisión de WebSocket
            await self._emit_websocket_event(
                event_type="notification.resolved",
                tenant_id=tenant_id,
                payload={
                    "solicitud_id": str(resolved_model.id),
                    "estado": resolved_model.estado,
                    "resuelto_por": resolved_model.resuelto_por,
                    "tipo": resolved_model.tipo,
                    "accion": "aprobar",
                },
            )
            return resolved_model

    async def reject_request(
        self,
        request_id: UUID | str,
        actor_id: int,
        reason: str,
        *,
        tenant_id: str | UUID | None = None,
        session: AsyncSession | None = None,
    ) -> SolicitudAprobacionModel:
        """
        Rechaza la solicitud de aprobación requiriendo obligatoriamente un motivo
        de al menos 5 caracteres no vacíos y emite `notification.resolved`.
        """
        clean_uuid = _parse_uuid(request_id)
        clean_reason = reason.strip() if isinstance(reason, str) else ""
        if len(clean_reason) < 5:
            raise InvalidRejectionReasonError(
                "El motivo de rechazo debe contener al menos 5 caracteres no vacíos.",
                i18n_key="operations:errors.invalid_rejection_reason",
                context={"longitud": str(len(clean_reason))},
            )

        if not isinstance(actor_id, int) or isinstance(actor_id, bool) or actor_id <= 0:
            raise ApprovalDomainError("actor_id debe ser un entero positivo válido de resolutor.")

        resolved_tenant = str(tenant_id) if tenant_id else (get_tenant_telemetry_context().tenant_id or "")
        with trace_span(
            "operations.approvals.reject",
            attributes={
                "tenant_id": resolved_tenant,
                "solicitud_id": str(clean_uuid),
                "actor_id": actor_id,
                "reason_length": len(clean_reason),
            },
            tracer_name="oppytec.operations.approvals",
        ):
            if self._use_in_memory:
                model = self._memory_store.get(clean_uuid)
                if model is None or getattr(model, "deleted_at", None) is not None:
                    raise ResourceNotFoundError(
                        f"Solicitud '{request_id}' no encontrada.",
                        i18n_key="operations:errors.approval_not_found",
                    )

                if model.estado != ApprovalStatus.PENDIENTE.value:
                    raise InvalidApprovalTransitionError(
                        f"Transición inválida: la solicitud {request_id} está en estado '{model.estado}' "
                        "y solo solicitudes en estado 'pendiente' pueden transicionar a 'rechazado'.",
                        context={"solicitud_id": str(request_id), "estado_actual": model.estado},
                    )

                model.estado = ApprovalStatus.RECHAZADO.value
                model.motivo_rechazo = clean_reason
                model.resuelto_por = actor_id
                model.resuelto_at = datetime.now(timezone.utc)
                rejected_model = model
            else:
                async def _do_reject(s: AsyncSession) -> SolicitudAprobacionModel:
                    stmt = select(SolicitudAprobacionModel).where(
                        SolicitudAprobacionModel.id == clean_uuid,
                        SolicitudAprobacionModel.deleted_at.is_(None),
                    )
                    bind = s.bind
                    if bind is not None and bind.dialect.name == "postgresql":
                        stmt = stmt.with_for_update()

                    res = await s.execute(stmt)
                    model = res.scalar_one_or_none()
                    if model is None:
                        raise ResourceNotFoundError(
                            f"Solicitud '{request_id}' no encontrada.",
                            i18n_key="operations:errors.approval_not_found",
                        )

                    if model.estado != ApprovalStatus.PENDIENTE.value:
                        raise InvalidApprovalTransitionError(
                            f"Transición inválida: la solicitud {request_id} está en estado '{model.estado}' "
                            "y solo solicitudes en estado 'pendiente' pueden transicionar a 'rechazado'.",
                            context={"solicitud_id": str(request_id), "estado_actual": model.estado},
                        )

                    model.estado = ApprovalStatus.RECHAZADO.value
                    model.motivo_rechazo = clean_reason
                    model.resuelto_por = actor_id
                    model.resuelto_at = datetime.now(timezone.utc)
                    await s.flush()
                    return model

                if session is not None:
                    rejected_model = await _do_reject(session)
                else:
                    async for s in self._get_session_ctx(tenant_id):
                        rejected_model = await _do_reject(s)
                        await s.commit()

            await self._emit_websocket_event(
                event_type="notification.resolved",
                tenant_id=tenant_id,
                payload={
                    "solicitud_id": str(rejected_model.id),
                    "estado": rejected_model.estado,
                    "resuelto_por": rejected_model.resuelto_por,
                    "motivo_rechazo": rejected_model.motivo_rechazo,
                    "tipo": rejected_model.tipo,
                    "accion": "rechazar",
                },
            )
            return rejected_model


class BuffetApprovalService:
    """
    Servicio de Auditoría y Resolución de Sesiones de Buffet.
    Audita el balance apertura/reposiciones/cierre e impacta de forma granular
    en Kardex: retornos a bodega (`ENTRADA`) vs mermas operativas (`MERMA`).
    """

    def __init__(
        self,
        approval_service: ApprovalService,
        inventory_service: InventoryService | None = None,
        session_or_none: AsyncSession | None = None,
    ) -> None:
        self._approvals = approval_service
        self._inventory = inventory_service or approval_service._inventory
        self._injected_session = session_or_none

    def set_session(self, session: AsyncSession | None) -> None:
        self._injected_session = session
        self._approvals.set_session(session)

    async def get_buffet_approval_detail(
        self,
        solicitud_id: UUID | str,
        *,
        tenant_id: str | UUID | None = None,
        session: AsyncSession | None = None,
    ) -> dict[str, Any]:
        """Obtiene la auditoría completa de una sesión de buffet para inspección pre-resolución."""
        active_session = session or self._injected_session
        model = await self._approvals.get_request_by_id(
            solicitud_id,
            tenant_id=tenant_id,
            session=active_session,
        )

        detalles = dict(model.detalles or {})
        items = detalles.get("items", [])

        formatted_items = []
        for it in items:
            ap = Decimal(str(it.get("cantidad_apertura", 0)))
            rep = Decimal(str(it.get("cantidad_reposiciones", 0)))
            cie = Decimal(str(it.get("cantidad_cierre", 0)))
            consumida = Decimal(str(it.get("cantidad_consumida", max(Decimal(0), ap + rep - cie))))
            sobrante = Decimal(str(it.get("cantidad_sobrante", cie)))
            costo_unit = Decimal(str(it.get("costo_unitario", 0)))

            formatted_items.append(
                {
                    "id": it.get("id") or it.get("item_id"),
                    "producto_id": it.get("producto_id"),
                    "item_type": it.get("item_type", "insumo"),
                    "nombre": it.get("nombre", "Item Buffet"),
                    "cantidad_apertura": ap,
                    "cantidad_reposiciones": rep,
                    "cantidad_cierre": cie,
                    "cantidad_consumida": consumida,
                    "cantidad_sobrante": sobrante,
                    "unidad_medida": it.get("unidad_medida", "un"),
                    "costo_unitario": costo_unit,
                    "costo_total": (consumida * costo_unit).quantize(Decimal("0.01")),
                    "accion_sobrante": it.get("accion_sobrante", "retornar"),
                    "motivo_merma": it.get("motivo_merma"),
                    "estacion_id": it.get("estacion_id"),
                    "estacion_nombre": it.get("estacion_nombre"),
                }
            )

        detalles["items"] = formatted_items

        return {
            "id": model.id,
            "tipo": model.tipo,
            "estado": model.estado,
            "usuario_id": model.usuario_id,
            "bodega_id": model.bodega_id,
            "area_operativa_id": model.area_operativa_id,
            "detalles": detalles,
            "resuelto_por": model.resuelto_por,
            "motivo_rechazo": model.motivo_rechazo,
            "created_at": model.created_at,
            "resuelto_at": model.resuelto_at,
        }

    def _process_buffet_items(
        self,
        items_to_process: list[dict[str, Any]],
        bodega_id: int,
        actor_id: int,
        solicitud_id: UUID | str,
        detalles: dict[str, Any],
        tenant_id: str | UUID | None,
    ) -> None:
        """Descarga consumos y distribuye sobrantes en Kardex."""
        prod_ids: list[int] = []
        for it in items_to_process:
            pid = int(it.get("producto_id") or it.get("item_id") or 0)
            if pid > 0:
                prod_ids.append(pid)

        ordered_pids = canonical_lock_order(prod_ids)
        item_map = {int(it.get("producto_id") or it.get("item_id") or 0): it for it in items_to_process}

        for pid in ordered_pids:
            it = item_map.get(pid)
            if not it:
                continue
            accion_sobrante = str(it.get("accion_sobrante", "retornar")).lower()
            sobrante_qty = Decimal(str(it.get("cantidad_sobrante", 0)))
            consumida_qty = Decimal(str(it.get("cantidad") or it.get("cantidad_consumida", 0)))
            unit_cost = Decimal(str(it.get("costo_unitario", 0)))
            motivo_merma = it.get("motivo_merma") or "Merma operativa de buffet"

            if consumida_qty > 0:
                self._inventory.register_movement(
                    producto_id=pid,
                    bodega_id=bodega_id,
                    movement_type="CONSUMO",
                    quantity=consumida_qty,
                    unit_cost=unit_cost,
                    actor_user_id=actor_id,
                    documento_referencia=f"BUFFET-SESION-{detalles.get('session_id', str(solicitud_id)[:8])}",
                    tenant_id=str(tenant_id) if tenant_id else None,
                )

            if sobrante_qty > 0:
                if accion_sobrante == "retornar":
                    self._inventory.register_movement(
                        producto_id=pid,
                        bodega_id=bodega_id,
                        movement_type="ENTRADA",
                        quantity=sobrante_qty,
                        unit_cost=unit_cost,
                        actor_user_id=actor_id,
                        documento_referencia=f"RETORNO-BUFFET-{solicitud_id}",
                        tenant_id=str(tenant_id) if tenant_id else None,
                    )
                else:
                    self._inventory.register_movement(
                        producto_id=pid,
                        bodega_id=bodega_id,
                        movement_type="MERMA",
                        quantity=sobrante_qty,
                        unit_cost=unit_cost,
                        actor_user_id=actor_id,
                        documento_referencia=motivo_merma,
                        tenant_id=str(tenant_id) if tenant_id else None,
                    )

    async def resolve_buffet_approval(
        self,
        solicitud_id: UUID | str,
        *,
        action: str = "aprobar",
        actor_id: int,
        resolutions: list[dict[str, Any]] | None = None,
        reason: str | None = None,
        tenant_id: str | UUID | None = None,
        session: AsyncSession | None = None,
    ) -> SolicitudAprobacionModel:
        """
        Resuelve la auditoría de buffet de forma atómica:
        - Si action == 'rechazar', ejecuta rechazo con motivo obligatorio.
        - Si action == 'aprobar', procesa cada insumo del buffet.
        """
        action_clean = action.strip().lower()
        active_session = session or self._injected_session

        if action_clean == "rechazar":
            return await self._approvals.reject_request(
                solicitud_id,
                actor_id=actor_id,
                reason=reason or "",
                tenant_id=tenant_id,
                session=active_session,
            )

        if action_clean != "aprobar":
            raise ApprovalDomainError(
                f"Acción '{action}' no válida en resolución de buffet. Use 'aprobar' o 'rechazar'.",
                i18n_key="operations:errors.invalid_buffet_resolution_action",
            )

        clean_uuid = _parse_uuid(solicitud_id)
        resolved_tenant = str(tenant_id) if tenant_id else (get_tenant_telemetry_context().tenant_id or "")

        with trace_span(
            "operations.buffet.resolve",
            attributes={
                "tenant_id": resolved_tenant,
                "solicitud_id": str(clean_uuid),
                "actor_id": actor_id,
                "action": action_clean,
            },
            tracer_name="oppytec.operations.approvals",
        ):
            if self._approvals._use_in_memory:
                model = self._approvals._memory_store.get(clean_uuid)
                if model is None or getattr(model, "deleted_at", None) is not None:
                    raise ResourceNotFoundError(
                        f"Solicitud '{solicitud_id}' no encontrada.",
                        i18n_key="operations:errors.approval_not_found",
                    )
                if model.estado != ApprovalStatus.PENDIENTE.value:
                    raise InvalidApprovalTransitionError(
                        f"Transición inválida: buffet en estado '{model.estado}'. Solo 'pendiente' puede resolverse.",
                    )

                detalles = dict(model.detalles or {})
                existing_items = detalles.get("items", [])
                items_to_process = resolutions if resolutions is not None else existing_items
                bodega_id = model.bodega_id or int(detalles.get("bodega_id", 1))

                self._process_buffet_items(
                    items_to_process, bodega_id, actor_id, solicitud_id, detalles, tenant_id
                )

                detalles["items_resolved"] = items_to_process
                model.detalles = detalles
                model.estado = ApprovalStatus.APROBADO.value
                model.resuelto_por = actor_id
                model.resuelto_at = datetime.now(timezone.utc)
                resolved_model = model
            else:
                async def _do_resolve(s: AsyncSession) -> SolicitudAprobacionModel:
                    stmt = select(SolicitudAprobacionModel).where(
                        SolicitudAprobacionModel.id == clean_uuid,
                        SolicitudAprobacionModel.deleted_at.is_(None),
                    )
                    bind = s.bind
                    if bind is not None and bind.dialect.name == "postgresql":
                        stmt = stmt.with_for_update()

                    res = await s.execute(stmt)
                    model = res.scalar_one_or_none()
                    if model is None:
                        raise ResourceNotFoundError(
                            f"Solicitud '{solicitud_id}' no encontrada.",
                            i18n_key="operations:errors.approval_not_found",
                        )

                    if model.estado != ApprovalStatus.PENDIENTE.value:
                        raise InvalidApprovalTransitionError(
                            f"Transición inválida: buffet en estado '{model.estado}'. Solo 'pendiente' puede resolverse.",
                        )

                    detalles = dict(model.detalles or {})
                    existing_items = detalles.get("items", [])
                    items_to_process = resolutions if resolutions is not None else existing_items
                    bodega_id = model.bodega_id or int(detalles.get("bodega_id", 1))

                    self._process_buffet_items(
                        items_to_process, bodega_id, actor_id, solicitud_id, detalles, tenant_id
                    )

                    detalles["items_resolved"] = items_to_process
                    model.detalles = detalles
                    model.estado = ApprovalStatus.APROBADO.value
                    model.resuelto_por = actor_id
                    model.resuelto_at = datetime.now(timezone.utc)
                    await s.flush()
                    return model

                if active_session is not None:
                    resolved_model = await _do_resolve(active_session)
                else:
                    async for s in self._approvals._get_session_ctx(tenant_id):
                        resolved_model = await _do_resolve(s)
                        await s.commit()

            await self._approvals._emit_websocket_event(
                event_type="notification.resolved",
                tenant_id=tenant_id,
                payload={
                    "solicitud_id": str(resolved_model.id),
                    "estado": resolved_model.estado,
                    "resuelto_por": resolved_model.resuelto_por,
                    "tipo": resolved_model.tipo,
                    "accion": "buffet_resolved",
                },
            )
            return resolved_model


class NotificationMatrixService:
    """
    Servicio de Aplicación de Matriz de Gobernanza y Configuración de Alertas por Cargo.
    Administra qué cargos reciben alertas en canales (in-app, email, push) y quiénes son aprobadores.
    """

    def __init__(self, session_or_none: AsyncSession | None = None, use_in_memory: bool = False) -> None:
        self._injected_session = session_or_none
        self._use_in_memory = use_in_memory
        self._rules_store: dict[tuple[str, str], NotificationMatrixRuleModel] = {}

    def enable_in_memory_mode(self) -> None:
        self._use_in_memory = True

    def reset_in_memory_store(self) -> None:
        self._rules_store.clear()

    def set_session(self, session: AsyncSession | None) -> None:
        self._injected_session = session
        self._use_in_memory = False

    async def _get_session_ctx(self, tenant_id: str | UUID | None) -> AsyncGenerator[AsyncSession, None]:
        if self._injected_session is not None:
            yield self._injected_session
            return
        schema = _format_tenant_schema(tenant_id)
        async for s in get_tenant_db_session(schema):
            yield s

    async def get_matrix(
        self,
        *,
        tenant_id: str | UUID | None = None,
        session: AsyncSession | None = None,
    ) -> dict[str, Any]:
        """
        Obtiene la matriz completa de notificaciones y cargos para la vista de gobernanza.
        """
        if self._use_in_memory:
            rules = list(self._rules_store.values())
            rules_map = {(r.cargo.lower(), r.tipo_solicitud): r for r in rules}

            cargos_payload = []
            for default_cargo in DEFAULT_CARGOS:
                cargo_slug = default_cargo["cargo"]
                perms: dict[str, bool] = {}
                for cat_item in NOTIFICATION_CATALOG:
                    t = cat_item["type"]
                    existing_rule = rules_map.get((cargo_slug, t))
                    if existing_rule:
                        perms[t] = existing_rule.canal_in_app
                    else:
                        perms[t] = True

                cargos_payload.append(
                    {
                        "id": default_cargo["id"],
                        "name": default_cargo["nombre"],
                        "role_name": cargo_slug,
                        "description": f"Configuración de alertas para {default_cargo['nombre']}",
                        "is_system": True,
                        "notification_permissions": perms,
                    }
                )

            formatted_rules = [
                {
                    "cargo": r.cargo,
                    "tipo_solicitud": r.tipo_solicitud,
                    "canal_in_app": r.canal_in_app,
                    "canal_email": r.canal_email,
                    "canal_push": r.canal_push,
                    "es_aprobador": r.es_aprobador,
                }
                for r in rules
            ]

            return {
                "catalog": NOTIFICATION_CATALOG,
                "cargos": cargos_payload,
                "rules": formatted_rules,
                "is_admin": True,
            }

        async def _do_get_matrix(s: AsyncSession) -> dict[str, Any]:
            try:
                stmt = select(NotificationMatrixRuleModel).where(
                    NotificationMatrixRuleModel.deleted_at.is_(None)
                )
                res = await s.execute(stmt)
                rules = list(res.scalars().all())
            except Exception:
                rules = []

            rules_map: dict[tuple[str, str], NotificationMatrixRuleModel] = {
                (r.cargo.lower(), r.tipo_solicitud): r for r in rules
            }

            cargos_payload = []
            for default_cargo in DEFAULT_CARGOS:
                cargo_slug = default_cargo["cargo"]
                perms = {}
                for cat_item in NOTIFICATION_CATALOG:
                    t = cat_item["type"]
                    existing_rule = rules_map.get((cargo_slug, t))
                    if existing_rule:
                        perms[t] = existing_rule.canal_in_app
                    else:
                        perms[t] = True

                cargos_payload.append(
                    {
                        "id": default_cargo["id"],
                        "name": default_cargo["nombre"],
                        "role_name": cargo_slug,
                        "description": f"Configuración de alertas para {default_cargo['nombre']}",
                        "is_system": True,
                        "notification_permissions": perms,
                    }
                )

            formatted_rules = [
                {
                    "cargo": r.cargo,
                    "tipo_solicitud": r.tipo_solicitud,
                    "canal_in_app": r.canal_in_app,
                    "canal_email": r.canal_email,
                    "canal_push": r.canal_push,
                    "es_aprobador": r.es_aprobador,
                }
                for r in rules
            ]

            return {
                "catalog": NOTIFICATION_CATALOG,
                "cargos": cargos_payload,
                "rules": formatted_rules,
                "is_admin": True,
            }

        active_s = session or self._injected_session
        if active_s is not None:
            return await _do_get_matrix(active_s)

        async for s in self._get_session_ctx(tenant_id):
            return await _do_get_matrix(s)
        return {"catalog": NOTIFICATION_CATALOG, "cargos": [], "rules": [], "is_admin": False}

    async def update_matrix(
        self,
        rules: list[dict[str, Any]],
        actor_id: int,
        *,
        tenant_id: str | UUID | None = None,
        session: AsyncSession | None = None,
    ) -> list[NotificationMatrixRuleModel]:
        """
        Actualiza o crea masivamente y de forma atómica las reglas de gobernanza por cargo.
        Emite el evento WebSocket `notification.matrix_updated`.
        """
        if not isinstance(actor_id, int) or isinstance(actor_id, bool) or actor_id <= 0:
            raise ApprovalDomainError("actor_id debe ser un entero positivo válido.")

        if self._use_in_memory:
            persisted: list[NotificationMatrixRuleModel] = []
            for r_data in rules:
                cargo_val = str(r_data.get("cargo", "")).strip().lower()
                tipo_val = str(r_data.get("tipo_solicitud", "")).strip()
                if not cargo_val or not tipo_val:
                    continue

                key = (cargo_val, tipo_val)
                in_app = bool(r_data.get("canal_in_app", True))
                email = bool(r_data.get("canal_email", False))
                push = bool(r_data.get("canal_push", False))
                es_aprobador = bool(r_data.get("es_aprobador", False))

                existing = self._rules_store.get(key)
                if existing:
                    existing.canal_in_app = in_app
                    existing.canal_email = email
                    existing.canal_push = push
                    existing.es_aprobador = es_aprobador
                    persisted.append(existing)
                else:
                    new_rule = NotificationMatrixRuleModel(
                        id=len(self._rules_store) + 1,
                        cargo=cargo_val,
                        tipo_solicitud=tipo_val,
                        canal_in_app=in_app,
                        canal_email=email,
                        canal_push=push,
                        es_aprobador=es_aprobador,
                    )
                    self._rules_store[key] = new_rule
                    persisted.append(new_rule)
            updated_rules = persisted
        else:
            async def _do_update(s: AsyncSession) -> list[NotificationMatrixRuleModel]:
                persisted_db: list[NotificationMatrixRuleModel] = []
                for r_data in rules:
                    cargo_val = str(r_data.get("cargo", "")).strip().lower()
                    tipo_val = str(r_data.get("tipo_solicitud", "")).strip()
                    if not cargo_val or not tipo_val:
                        continue

                    stmt = select(NotificationMatrixRuleModel).where(
                        NotificationMatrixRuleModel.cargo == cargo_val,
                        NotificationMatrixRuleModel.tipo_solicitud == tipo_val,
                        NotificationMatrixRuleModel.deleted_at.is_(None),
                    )
                    res = await s.execute(stmt)
                    existing = res.scalar_one_or_none()

                    in_app = bool(r_data.get("canal_in_app", True))
                    email = bool(r_data.get("canal_email", False))
                    push = bool(r_data.get("canal_push", False))
                    es_aprobador = bool(r_data.get("es_aprobador", False))

                    if existing:
                        existing.canal_in_app = in_app
                        existing.canal_email = email
                        existing.canal_push = push
                        existing.es_aprobador = es_aprobador
                        persisted_db.append(existing)
                    else:
                        new_rule = NotificationMatrixRuleModel(
                            cargo=cargo_val,
                            tipo_solicitud=tipo_val,
                            canal_in_app=in_app,
                            canal_email=email,
                            canal_push=push,
                            es_aprobador=es_aprobador,
                        )
                        s.add(new_rule)
                        persisted_db.append(new_rule)

                await s.flush()
                return persisted_db

            active_s = session or self._injected_session
            if active_s is not None:
                updated_rules = await _do_update(active_s)
            else:
                async for s in self._get_session_ctx(tenant_id):
                    updated_rules = await _do_update(s)
                    await s.commit()

        # Emitir evento WebSocket
        try:
            publisher = get_realtime_publisher()
            tenant_uuid = None
            if tenant_id:
                try:
                    tenant_uuid = UUID(str(tenant_id)) if not isinstance(tenant_id, UUID) else tenant_id
                except Exception:
                    tenant_uuid = None
            await publisher.publish_event(
                RealtimeEventEnvelope(
                    event_type="notification.matrix_updated",
                    tenant_id=tenant_uuid,
                    payload={"action": "matrix_updated", "rules_count": len(updated_rules)},
                    query_keys_to_invalidate=[["notification-matrix"], ["approvals"]],
                )
            )
        except Exception as exc:
            logger.warning("Fallo al emitir notification.matrix_updated: %s", exc)

        return updated_rules


__all__ = [
    "ApprovalService",
    "BuffetApprovalService",
    "NotificationMatrixService",
    "NOTIFICATION_CATALOG",
    "DEFAULT_CARGOS",
]
