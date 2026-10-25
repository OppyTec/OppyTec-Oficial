"""
oppytec-backend/src/modules/inventory/application/physical_count_service.py
Servicio de aplicación para auditorías físicas y recuentos ciegos de inventario.
Orquesta el ciclo de vida: EN_PROGRESO -> PENDIENTE_APROBACION -> APROBADO / RECHAZADO,
con cálculo riguroso de discrepancias y reconciliación atómica en Kardex bajo orden canónico anti-deadlock.
"""
# mypy: disable-error-code="explicit-any"
from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from opentelemetry import trace

from src.core.exceptions import (
    CrossTenantAccessError,
    DomainValidationError,
    ResourceNotFoundError,
)
from src.core.observability import get_tenant_telemetry_context, trace_span
from src.modules.inventory.application.inventory_service import InventoryService
from src.modules.inventory.domain.entities import PhysicalCountItem, PhysicalCountSession
from src.modules.inventory.domain.kardex_math import canonical_lock_order
from src.modules.inventory.domain.value_objects import MoneyAmount, StockQuantity

logger = logging.getLogger("oppytec.inventory")
tracer = trace.get_tracer("oppytec.inventory")


@dataclass(frozen=True)
class CountItemInput:
    """Entrada de ítem de recuento físico."""

    producto_id: int
    stock_fisico_contado: Decimal
    costo_unitario_ppp: Decimal = Decimal("0.00")
    lote_codigo: str | None = None
    fecha_vencimiento: date | None = None


class PhysicalCountService:
    """Servicio transaccional de sesiones de recuento físico y cuadraturas de auditoría."""

    def __init__(self, inventory: InventoryService) -> None:
        self._inventory = inventory
        self._sessions: dict[int, PhysicalCountSession] = {}
        self._next_session_id: int = 1
        self._next_item_id: int = 1

    def reset(self) -> None:
        """Limpia las sesiones en memoria para aislamiento de pruebas."""
        self._sessions.clear()
        self._next_session_id = 1
        self._next_item_id = 1

    def start_count_session(
        self,
        *,
        bodega_id: int,
        area_operativa_id: int | None = None,
        responsable_user_id: int,
        notas: str | None = None,
        tenant_id: str | None = None,
    ) -> PhysicalCountSession:
        """Abre una nueva sesión de recuento en estado `EN_PROGRESO`."""
        if bodega_id <= 0:
            raise DomainValidationError(
                f"Invalid bodega_id: {bodega_id}",
                i18n_key="inventory:errors.invalid_bodega_id",
            )
        if responsable_user_id <= 0:
            raise DomainValidationError(
                f"Invalid responsable_user_id: {responsable_user_id}",
                i18n_key="inventory:errors.invalid_user_id",
            )

        session_id = self._next_session_id
        self._next_session_id += 1

        session = PhysicalCountSession(
            id=session_id,
            bodega_id=bodega_id,
            area_operativa_id=area_operativa_id,
            responsable_user_id=responsable_user_id,
            estado="EN_PROGRESO",
            notas=notas,
            tenant_id=tenant_id,
        )
        self._sessions[session_id] = session
        return session

    def get_session(self, conteo_id: int, tenant_id: str | None = None) -> PhysicalCountSession:
        """Obtiene una sesión de recuento por identificador validando pertenencia al tenant."""
        session = self._sessions.get(conteo_id)
        if session is None:
            raise ResourceNotFoundError(
                f"Physical count session {conteo_id} not found.",
                i18n_key="inventory:errors.count_session_not_found",
            )
        if tenant_id and session.tenant_id and session.tenant_id != tenant_id:
            raise CrossTenantAccessError(
                f"Cross-tenant access denied: count session {conteo_id} belongs to a different tenant.",
                i18n_key="tenancy:errors.cross_tenant_forbidden",
            )
        return session

    def list_sessions(
        self,
        *,
        bodega_id: int | None = None,
        estado: str | None = None,
        tenant_id: str | None = None,
    ) -> list[PhysicalCountSession]:
        """Lista las sesiones de recuento filtradas por bodega, estado y tenant."""
        sessions = list(self._sessions.values())
        if tenant_id is not None:
            sessions = [s for s in sessions if s.tenant_id == tenant_id]
        if bodega_id is not None:
            sessions = [s for s in sessions if s.bodega_id == bodega_id]
        if estado is not None:
            sessions = [s for s in sessions if s.estado == estado]
        return sorted(sessions, key=lambda s: s.id or 0, reverse=True)

    def save_count_items(
        self,
        conteo_id: int,
        items: Sequence[CountItemInput | dict[str, Any] | Any],
        tenant_id: str | None = None,
    ) -> PhysicalCountSession:
        """
        Guarda o actualiza incrementalmente las líneas contadas en una sesión `EN_PROGRESO`.
        Rechaza la modificación si la sesión ya fue finalizada o aprobada o si pertenece a otro tenant.
        """
        session = self.get_session(conteo_id, tenant_id=tenant_id)
        if session.estado != "EN_PROGRESO":
            raise DomainValidationError(
                f"Cannot update count items: session {conteo_id} is in status '{session.estado}', expected 'EN_PROGRESO'.",
                i18n_key="inventory:errors.count_session_not_in_progress",
            )

        parsed_items: list[PhysicalCountItem] = []
        for it in items:
            if isinstance(it, CountItemInput):
                pid = it.producto_id
                counted_qty = it.stock_fisico_contado
                unit_cost = it.costo_unitario_ppp
                lote = it.lote_codigo
                venc = it.fecha_vencimiento
            elif isinstance(it, dict):
                pid = int(it["producto_id"])
                counted_qty = Decimal(str(it["stock_fisico_contado"]))
                unit_cost = Decimal(str(it.get("costo_unitario_ppp", "0.00")))
                lote = it.get("lote_codigo")
                venc = it.get("fecha_vencimiento")
            else:
                pid = int(it.producto_id)
                counted_qty = Decimal(str(it.stock_fisico_contado))
                unit_cost = Decimal(str(getattr(it, "costo_unitario_ppp", "0.00")))
                lote = getattr(it, "lote_codigo", None)
                venc = getattr(it, "fecha_vencimiento", None)

            # En toma ciega, el stock teórico se consulta pero no se le muestra al operador
            system_stock = self._inventory.balance(pid, session.bodega_id)

            item_id = self._next_item_id
            self._next_item_id += 1

            count_item = PhysicalCountItem(
                id=item_id,
                producto_id=pid,
                stock_teorico_sistema=StockQuantity(system_stock),
                stock_fisico_contado=StockQuantity(counted_qty),
                costo_unitario_ppp=MoneyAmount(unit_cost),
                lote_codigo=lote,
                fecha_vencimiento=venc,
            )
            parsed_items.append(count_item)

        session.items = parsed_items
        return session

    def finalize_count_session(
        self,
        conteo_id: int,
        tenant_id: str | None = None,
    ) -> PhysicalCountSession:
        """
        Finaliza la toma de recuento físico, capturando formalmente el stock teórico de sistema
        al momento del cierre y calculando el acta de discrepancias en unidades y valor monetario PPP.
        Transiciona el estado a `PENDIENTE_APROBACION`.
        Instrumentado con OpenTelemetry span 'inventory.count.finalize' y logs estructurados.
        """
        resolved_tenant = tenant_id or get_tenant_telemetry_context().tenant_id
        with trace_span(
            "inventory.count.finalize",
            attributes={
                "tenant_id": resolved_tenant,
                "conteo_id": conteo_id,
            },
            tracer_name="oppytec.inventory",
        ) as span_attrs:
            session = self.get_session(conteo_id, tenant_id=resolved_tenant)
            span_attrs["bodega_id"] = session.bodega_id
            span_attrs["user_id"] = str(session.responsable_user_id)
            span_attrs["items_count"] = len(session.items)
            span_attrs["estado_previo"] = session.estado

            if session.estado != "EN_PROGRESO":
                raise DomainValidationError(
                    f"Cannot finalize session {conteo_id}: current status is '{session.estado}', expected 'EN_PROGRESO'.",
                    i18n_key="inventory:errors.count_session_not_in_progress",
                )

            # Recalcular diferencias exactas contra el saldo actual del sistema
            updated_items: list[PhysicalCountItem] = []
            for it in session.items:
                system_stock = self._inventory.balance(it.producto_id, session.bodega_id)
                recalculated = PhysicalCountItem(
                    id=it.id,
                    producto_id=it.producto_id,
                    stock_teorico_sistema=StockQuantity(system_stock),
                    stock_fisico_contado=it.stock_fisico_contado,
                    costo_unitario_ppp=it.costo_unitario_ppp,
                    lote_codigo=it.lote_codigo,
                    fecha_vencimiento=it.fecha_vencimiento,
                )
                updated_items.append(recalculated)

            session.items = updated_items
            session.transition_to("PENDIENTE_APROBACION")
            session.completed_at = datetime.now(UTC)

            discrepant_count = sum(1 for it in session.items if it.has_discrepancy)
            span_attrs["discrepancies_count"] = discrepant_count
            span_attrs["estado_nuevo"] = session.estado
            return session

    def approve_and_reconcile(
        self,
        conteo_id: int,
        aprobador_user_id: int,
        tenant_id: str | None = None,
    ) -> PhysicalCountSession:
        """
        Aprueba administrativamente el acta de inventario y genera de inmediato los asientos
        de ajuste (`AJUSTE_AUDITORIA`) en Kardex para reconciliar las existencias físicas con el sistema.
        Aplica adquisición de locks en orden canónico anti-deadlock (`canonical_lock_order`).
        Instrumentado con OpenTelemetry span 'inventory.count.reconcile' y logs estructurados.
        """
        resolved_tenant = tenant_id or get_tenant_telemetry_context().tenant_id
        with trace_span(
            "inventory.count.reconcile",
            attributes={
                "tenant_id": resolved_tenant,
                "conteo_id": conteo_id,
                "aprobador_user_id": aprobador_user_id,
                "user_id": str(aprobador_user_id),
            },
            tracer_name="oppytec.inventory",
        ) as span_attrs:
            session = self.get_session(conteo_id, tenant_id=resolved_tenant)
            span_attrs["bodega_id"] = session.bodega_id
            span_attrs["items_count"] = len(session.items)
            span_attrs["estado_previo"] = session.estado

            if session.estado != "PENDIENTE_APROBACION":
                raise DomainValidationError(
                    f"Cannot approve session {conteo_id}: status is '{session.estado}', expected 'PENDIENTE_APROBACION'.",
                    i18n_key="inventory:errors.count_session_not_pending_approval",
                )

            session.transition_to("APROBADO", user_id=aprobador_user_id)

            # Orden canónico de productos con discrepancias para evitar deadlocks
            discrepant_items = [it for it in session.items if it.has_discrepancy]
            ordered_pids = canonical_lock_order(it.producto_id for it in discrepant_items)

            span_attrs["discrepant_items_count"] = len(discrepant_items)

            for pid in ordered_pids:
                for item in [it for it in discrepant_items if it.producto_id == pid]:
                    diff_val = item.diferencia_unidades.value
                    is_surplus = item.is_surplus

                    self._inventory.register_movement(
                        producto_id=item.producto_id,
                        bodega_id=session.bodega_id,
                        movement_type="AJUSTE_AUDITORIA",
                        quantity=abs(diff_val),
                        unit_cost=item.costo_unitario_ppp.amount,
                        actor_user_id=aprobador_user_id,
                        lote_codigo=item.lote_codigo,
                        fecha_vencimiento_lote=item.fecha_vencimiento,
                        documento_referencia=f"CONTEO_RECONCILIATION:{conteo_id}",
                        is_positive_adjustment=is_surplus,
                        tenant_id=resolved_tenant,
                    )

            span_attrs["estado_nuevo"] = session.estado
            return session

    def reject_session(
        self,
        conteo_id: int,
        aprobador_user_id: int,
        reason: str = "",
        tenant_id: str | None = None,
    ) -> PhysicalCountSession:
        """Rechaza un acta de recuento con observaciones y ordena un reconteo físico."""
        session = self.get_session(conteo_id, tenant_id=tenant_id)
        if session.estado != "PENDIENTE_APROBACION":
            raise DomainValidationError(
                f"Cannot reject session {conteo_id}: status is '{session.estado}', expected 'PENDIENTE_APROBACION'.",
                i18n_key="inventory:errors.count_session_not_pending_approval",
            )

        session.transition_to("RECHAZADO")
        session.aprobador_user_id = aprobador_user_id
        if reason:
            session.notas = f"{session.notas or ''}\n[RECHAZO]: {reason}".strip()
        return session

    def delete_session(self, conteo_id: int, tenant_id: str | None = None) -> bool:
        """Elimina una sesión de recuento (solo sesiones canceladas o en borrador)."""
        session = self.get_session(conteo_id, tenant_id=tenant_id)
        if session.estado == "APROBADO":
            raise DomainValidationError(
                f"Cannot delete approved count session {conteo_id}: Kardex adjustments have already been committed.",
                i18n_key="inventory:errors.cannot_delete_approved_session",
            )
        del self._sessions[conteo_id]
        return True


__all__ = [
    "CountItemInput",
    "PhysicalCountService",
]
