"""
oppytec-backend/src/modules/inventory/application/history_service.py
Servicio de Aplicación de Historial y Auditoría de Kardex (/historial):
- Consulta paginada server-side con conteo determinista y filtros multi-criterio.
- Proyección enriquecida: nombres de producto, unidad, bodega y usuario con fallback inteligente.
- Cálculo riguroso de deltas before/after mediante `compute_audit_delta`.
- Protección de privacidad: anonimización a 'Operador Autorizado' si falta `inventory.history.view_users`.
- Exportación streaming CSV con UTF-8 BOM y sanitización contra Formula Injection (CWE-1236).
- Purga histórica restringida a Propietario del tenant.
"""
# mypy: disable-error-code="explicit-any"
from __future__ import annotations

import csv
import io
import logging
import re
from collections.abc import Iterable, Mapping
from contextlib import suppress
from datetime import UTC, date, datetime
from decimal import Decimal

from opentelemetry import trace

from src.core.exceptions import DomainValidationError
from src.core.guards.file_magic_guard import sanitize_spreadsheet_export_value
from src.core.observability import (
    REDACTED_MARKER,
    format_structured_log,
    get_tenant_telemetry_context,
    scrub_telemetry_payload,
    trace_span,
)
from src.modules.inventory.application.inventory_service import InventoryService, KardexEntry
from src.modules.inventory.domain.kardex_math import compute_audit_delta
from src.modules.inventory.presentation.schemas import (
    KardexHistoryItemResponse,
    PaginatedKardexHistoryResponse,
)

logger = logging.getLogger("oppytec.inventory.history")
tracer = trace.get_tracer("oppytec.inventory.history")

AUDIT_USER_PII_KEYS: tuple[str, ...] = (
    "email",
    "mail",
    "correo",
    "username",
    "user_name",
    "nombre_usuario",
    "user_display_name",
    "nombre_visible",
)
_EMAIL_REGEX: re.Pattern[str] = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
)


def scrub_audit_payload(payload: dict[str, object]) -> dict[str, object]:
    """
    Aplica redacción PII determinista sobre correos y nombres de usuario
    en los logs de auditoría de Kardex además de los secretos estándar.
    """
    base = scrub_telemetry_payload(payload)

    def _scrub_entry(val: object) -> object:
        if isinstance(val, Mapping):
            return {
                str(k): (
                    REDACTED_MARKER
                    if any(t in str(k).lower() for t in AUDIT_USER_PII_KEYS)
                    else _scrub_entry(v)
                )
                for k, v in val.items()
            }
        if isinstance(val, list):
            return [_scrub_entry(x) for x in val]
        if isinstance(val, tuple):
            return tuple(_scrub_entry(x) for x in val)
        if isinstance(val, str) and _EMAIL_REGEX.search(val):
            return _EMAIL_REGEX.sub(REDACTED_MARKER, val)
        return val

    scrubbed: dict[str, object] = {}
    for k, v in base.items():
        if any(t in str(k).lower() for t in AUDIT_USER_PII_KEYS):
            scrubbed[str(k)] = REDACTED_MARKER
        else:
            scrubbed[str(k)] = _scrub_entry(v)
    return scrubbed


def format_history_audit_log(
    level: str,
    action: str,
    details: dict[str, object] | None = None,
) -> str:
    """Genera log estructurado JSON de auditoría de Kardex con redacción PII determinista."""
    safe_data = scrub_audit_payload(details or {})
    return format_structured_log(level, f"kardex.history.{action}", safe_data)


class KardexHistoryService:
    """
    Servicio de consulta, proyección enriquecida y exportación streaming
    del historial de auditoría inmutable del Kardex.
    """

    def __init__(self, inventory: InventoryService | None = None) -> None:
        self._inventory: InventoryService = inventory or InventoryService()
        self._products_meta: dict[str, tuple[str, str]] = {}
        self._warehouses_meta: dict[str, str] = {}
        self._users_meta: dict[int, dict[str, str]] = {}

    def set_inventory_service(self, inventory: InventoryService) -> None:
        """Inyecta la instancia del servicio transaccional de inventario."""
        self._inventory = inventory

    def reset(self) -> None:
        """Limpia los metadatos registrados para aislamiento de pruebas."""
        self._products_meta.clear()
        self._warehouses_meta.clear()
        self._users_meta.clear()

    def set_product_info(self, producto_id: int | str, nombre: str, unidad: str = "UN") -> None:
        """Registra metadatos descriptivos de un producto para proyecciones de auditoría."""
        self._products_meta[str(producto_id)] = (nombre.strip(), unidad.strip() or "UN")

    def set_warehouse_info(self, bodega_id: int | str, nombre: str) -> None:
        """Registra metadatos descriptivos de una bodega."""
        self._warehouses_meta[str(bodega_id)] = nombre.strip()

    def set_user_info(
        self,
        user_id: int,
        *,
        nombre_visible: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
        username: str | None = None,
        email: str | None = None,
    ) -> None:
        """Registra información de identidad de un usuario para proyecciones de auditoría."""
        data: dict[str, str] = {}
        if nombre_visible:
            data["nombre_visible"] = nombre_visible.strip()
        if first_name:
            data["first_name"] = first_name.strip()
        if last_name:
            data["last_name"] = last_name.strip()
        if username:
            data["username"] = username.strip()
        if email:
            data["email"] = email.strip()
        self._users_meta[user_id] = data

    def resolve_product(self, producto_id: int | str) -> tuple[str, str]:
        """
        Resuelve el nombre y unidad de medida de un producto con fallback inteligente.
        Orden: _products_meta -> catálogo en memoria (_products_store) -> 'Producto {id}', 'UN'.
        """
        pid_str = str(producto_id).strip()
        if pid_str in self._products_meta:
            return self._products_meta[pid_str]

        # Intento de resolución desde el almacén de catálogo si está cargado
        with suppress(Exception):
            from src.modules.catalog.presentation.router import _products_store

            int_id = int(pid_str)
            if int_id in _products_store:
                prod = _products_store[int_id]
                name = prod.nombre or f"Producto {pid_str}"
                unit = prod.unidad_almacen or "UN"
                return (name, unit)

        return (f"Producto {pid_str}", "UN")

    def resolve_warehouse(self, bodega_id: int | str) -> str:
        """
        Resuelve el nombre de la bodega con fallback inteligente.
        Orden: _warehouses_meta -> 'Bodega Principal' (si id 1 o 101) -> 'Bodega {id}'.
        """
        bid_str = str(bodega_id).strip()
        if bid_str in self._warehouses_meta:
            return self._warehouses_meta[bid_str]
        if bid_str in ("1", "101"):
            return "Bodega Principal"
        return f"Bodega {bid_str}"

    def resolve_user_display_name(self, actor_user_id: int, can_view_users: bool = True) -> str:
        """
        Resuelve el nombre visible del usuario con fallback inteligente de 5 niveles
        y anonimización automática si falta el permiso de privacidad `inventory.history.view_users`.
        Fallback canónico:
        1. 'Operador Autorizado' (si can_view_users es False)
        2. 'Sistema' (si actor_user_id <= 0)
        3. nombre_visible
        4. first_name + ' ' + last_name
        5. username
        6. local part de email
        7. 'Usuario {id}'
        """
        if not can_view_users:
            return "Operador Autorizado"

        if actor_user_id <= 0:
            return "Sistema"

        meta = self._users_meta.get(actor_user_id)
        if meta:
            if meta.get("nombre_visible"):
                return meta["nombre_visible"]
            fn = meta.get("first_name", "")
            ln = meta.get("last_name", "")
            full = f"{fn} {ln}".strip()
            if full:
                return full
            if meta.get("username"):
                return meta["username"]
            if meta.get("email"):
                return meta["email"].split("@")[0]

        return f"Usuario {actor_user_id}"

    def _filter_ledger(
        self,
        *,
        tenant_id: str | None = None,
        bodega_id: str | int = "all",
        producto_id: str | int = "all",
        tipo_movimiento: str = "all",
        fecha_desde: date | None = None,
        fecha_hasta: date | None = None,
        user_search: str | None = None,
    ) -> list[KardexEntry]:
        """Filtra los registros del libro mayor de acuerdo a los criterios provistos."""
        all_entries = list(self._inventory.ledger(tenant_id=tenant_id))

        filtered: list[KardexEntry] = []

        # Parseo de bodegas permitidas
        allowed_bodegas: set[str] | None = None
        if bodega_id is not None and str(bodega_id).strip() not in ("all", "", "None"):
            allowed_bodegas = {b.strip() for b in str(bodega_id).split(",") if b.strip()}

        # Parseo de productos permitidos
        allowed_products: set[str] | None = None
        if producto_id is not None and str(producto_id).strip() not in ("all", "", "None"):
            allowed_products = {p.strip() for p in str(producto_id).split(",") if p.strip()}

        # Normalización de tipo de movimiento
        norm_tipo: str | None = None
        if tipo_movimiento is not None and str(tipo_movimiento).strip() not in ("all", "", "None"):
            norm_tipo = str(tipo_movimiento).strip().lower()

        search_term: str | None = None
        if user_search is not None and str(user_search).strip():
            search_term = str(user_search).strip().lower()

        for entry in all_entries:
            # 1. Filtro de bodega
            if allowed_bodegas is not None and str(entry.bodega_id) not in allowed_bodegas:
                continue

            # 2. Filtro de producto
            if allowed_products is not None and str(entry.producto_id) not in allowed_products:
                continue

            # 3. Filtro de tipo de movimiento
            if norm_tipo is not None:
                entry_tipo = entry.movement_type.strip().lower()
                if norm_tipo == "ajuste":
                    if entry_tipo not in (
                        "ajuste",
                        "ajuste_positivo",
                        "ajuste_negativo",
                        "ajuste_auditoria",
                    ):
                        continue
                elif norm_tipo == "transferencia":
                    if entry_tipo not in ("transferencia", "traspaso_in", "traspaso_out"):
                        continue
                elif entry_tipo != norm_tipo:
                    continue

            # 4. Filtro de fechas (comparando fecha_recuento o date(created_at))
            entry_date = getattr(entry, "fecha_recuento", None) or entry.created_at.date()
            if fecha_desde is not None and entry_date < fecha_desde:
                continue
            if fecha_hasta is not None and entry_date > fecha_hasta:
                continue

            # 5. Búsqueda por usuario (predictiva en display name, email, username o ID)
            if search_term is not None:
                raw_user_name = self.resolve_user_display_name(entry.actor_user_id, can_view_users=True)
                user_match = (
                    search_term in raw_user_name.lower()
                    or search_term in str(entry.actor_user_id)
                )
                if not user_match:
                    meta = self._users_meta.get(entry.actor_user_id, {})
                    user_match = any(
                        search_term in str(v).lower() for v in meta.values()
                    )
                if not user_match:
                    continue

            filtered.append(entry)

        # Ordenamiento determinista: más recientes primero (created_at DESC, id DESC)
        filtered.sort(
            key=lambda e: (
                e.created_at if isinstance(e.created_at, datetime) else datetime.min.replace(tzinfo=UTC),
                e.id,
            ),
            reverse=True,
        )
        return filtered

    def get_filtered_history(
        self,
        *,
        tenant_id: str | None = None,
        bodega_id: str | int = "all",
        producto_id: str | int = "all",
        tipo_movimiento: str = "all",
        fecha_desde: date | None = None,
        fecha_hasta: date | None = None,
        user_search: str | None = None,
        skip: int = 0,
        limit: int = 50,
        can_view_users: bool = True,
        actor_user_id: int | None = None,
    ) -> PaginatedKardexHistoryResponse:
        """
        Retorna la consulta paginada y filtrada del historial de Kardex
        con cálculo determinista de total, páginas y proyección enriquecida.
        Instrumentado con OpenTelemetry span 'kardex.history.query'.
        """
        ctx = get_tenant_telemetry_context()
        resolved_tenant = tenant_id or ctx.tenant_id
        resolved_actor = (
            actor_user_id
            if actor_user_id is not None
            else (
                int(ctx.user_id)
                if ctx.user_id and str(ctx.user_id).isdigit()
                else 0
            )
        )
        clamped_limit = min(max(1, limit), 100)
        clamped_skip = max(0, skip)

        norm_bodega: str | int = int(bodega_id) if str(bodega_id).isdigit() else bodega_id
        norm_producto: str | int = int(producto_id) if str(producto_id).isdigit() else producto_id

        initial_attrs: dict[str, object] = {
            "oppytec.tenant_id": str(resolved_tenant or ""),
            "tenant_id": str(resolved_tenant or ""),
            "bodega_id": norm_bodega,
            "producto_id": norm_producto,
            "tipo_movimiento": str(tipo_movimiento or "all"),
            "page_size": clamped_limit,
            "actor_user_id": resolved_actor,
            "user_id": str(resolved_actor),
        }

        with trace_span(
            "kardex.history.query",
            attributes=initial_attrs,
            tracer_name="oppytec.inventory.history",
        ) as span_attrs:
            if not resolved_tenant:
                raise DomainValidationError(
                    "El identificador de tenant (tenant_id) es obligatorio",
                    i18n_key="common:errors.tenant_required",
                )

            if fecha_desde is not None and fecha_hasta is not None and fecha_desde > fecha_hasta:
                raise DomainValidationError(
                    f"Rango de fechas inválido: fecha_desde ({fecha_desde}) no puede ser posterior a fecha_hasta ({fecha_hasta})",
                    i18n_key="inventory:history.invalid_date_range",
                )

            filtered = self._filter_ledger(
                tenant_id=resolved_tenant,
                bodega_id=bodega_id,
                producto_id=producto_id,
                tipo_movimiento=tipo_movimiento,
                fecha_desde=fecha_desde,
                fecha_hasta=fecha_hasta,
                user_search=user_search,
            )

            total = len(filtered)
            span_attrs["total_records"] = total

            page = (clamped_skip // clamped_limit) + 1
            total_pages = max(1, (total + clamped_limit - 1) // clamped_limit) if total > 0 else 1

            page_entries = filtered[clamped_skip : clamped_skip + clamped_limit]

            items: list[KardexHistoryItemResponse] = []
            for entry in page_entries:
                nombre_producto, unidad_medida = self.resolve_product(entry.producto_id)
                nombre_bodega = self.resolve_warehouse(entry.bodega_id)
                user_display = self.resolve_user_display_name(
                    entry.actor_user_id,
                    can_view_users=can_view_users,
                )

                # Cálculo algebraico de deltas before/after mediante compute_audit_delta
                delta_res = compute_audit_delta(
                    resulting_balance=entry.resulting_balance,
                    quantity=entry.quantity,
                    movement_type=entry.movement_type,
                    unit=unidad_medida,
                )

                costo_ppp = getattr(entry, "costo_unitario_ppp", entry.unit_cost)
                costo_total = getattr(
                    entry,
                    "costo_total_movimiento",
                    (abs(entry.quantity) * costo_ppp).quantize(Decimal("0.01")),
                )
                fecha_rec = getattr(entry, "fecha_recuento", None) or entry.created_at.date()
                desc_merma = getattr(entry, "descripcion_merma", None) or entry.documento_referencia

                items.append(
                    KardexHistoryItemResponse(
                        id=entry.id,
                        created_at=entry.created_at,
                        fecha_recuento=fecha_rec,
                        producto_id=entry.producto_id,
                        nombre_producto=nombre_producto,
                        unidad_medida=unidad_medida,
                        bodega_id=entry.bodega_id,
                        nombre_bodega=nombre_bodega,
                        tipo_movimiento=entry.movement_type,
                        cantidad=entry.quantity,
                        saldo_resultante=entry.resulting_balance,
                        costo_unitario_ppp=costo_ppp,
                        costo_total_movimiento=costo_total,
                        lote_codigo=entry.lote_codigo,
                        fecha_vencimiento_lote=entry.fecha_vencimiento_lote,
                        actor_user_id=entry.actor_user_id,
                        user_display_name=user_display,
                        motivo_merma=getattr(entry, "motivo_merma", None),
                        descripcion_merma=desc_merma,
                        transfer_id=str(entry.transfer_id) if entry.transfer_id else None,
                        delta_before=delta_res.before,
                        delta_after=delta_res.after,
                    )
                )

            return PaginatedKardexHistoryResponse(
                total=total,
                skip=clamped_skip,
                limit=clamped_limit,
                page=page,
                total_pages=total_pages,
                items=items,
            )

    def generate_csv_stream(
        self,
        *,
        tenant_id: str | None = None,
        bodega_id: str | int = "all",
        producto_id: str | int = "all",
        tipo_movimiento: str = "all",
        fecha_desde: date | None = None,
        fecha_hasta: date | None = None,
        user_search: str | None = None,
        can_view_users: bool = True,
        actor_user_id: int | None = None,
    ) -> Iterable[str]:
        """
        Generador streaming de CSV:
        - Inicia obligatoriamente con UTF-8 BOM ('\\uFEFF') para compatibilidad Excel.
        - Sanitiza cada celda contra CSV Injection / DDE (prefijo comilla simple).
        - Instrumentado con OpenTelemetry span 'kardex.history.export_csv'.
        """
        ctx = get_tenant_telemetry_context()
        resolved_tenant = tenant_id or ctx.tenant_id
        resolved_actor = (
            actor_user_id
            if actor_user_id is not None
            else (
                int(ctx.user_id)
                if ctx.user_id and str(ctx.user_id).isdigit()
                else 0
            )
        )

        norm_bodega: str | int = int(bodega_id) if str(bodega_id).isdigit() else bodega_id
        norm_producto: str | int = int(producto_id) if str(producto_id).isdigit() else producto_id

        initial_attrs: dict[str, object] = {
            "oppytec.tenant_id": str(resolved_tenant or ""),
            "tenant_id": str(resolved_tenant or ""),
            "file_format": "csv",
            "bodega_id": norm_bodega,
            "producto_id": norm_producto,
            "tipo_movimiento": str(tipo_movimiento or "all"),
            "actor_user_id": resolved_actor,
            "user_id": str(resolved_actor),
        }

        with trace_span(
            "kardex.history.export_csv",
            attributes=initial_attrs,
            tracer_name="oppytec.inventory.history",
        ) as span_attrs:
            if not resolved_tenant:
                raise DomainValidationError(
                    "El identificador de tenant (tenant_id) es obligatorio",
                    i18n_key="common:errors.tenant_required",
                )

            if fecha_desde is not None and fecha_hasta is not None and fecha_desde > fecha_hasta:
                raise DomainValidationError(
                    f"Rango de fechas inválido: fecha_desde ({fecha_desde}) no puede ser posterior a fecha_hasta ({fecha_hasta})",
                    i18n_key="inventory:history.invalid_date_range",
                )

            # 1. Emitir UTF-8 BOM
            yield "\ufeff"

            # 2. Cabecera normalizada
            header = [
                "ID",
                "Fecha y Hora",
                "Fecha Recuento",
                "Bodega ID",
                "Bodega",
                "Producto ID",
                "Producto",
                "Unidad",
                "Tipo Movimiento",
                "Cantidad",
                "Saldo Anterior",
                "Saldo Resultante",
                "Costo Unitario PPP",
                "Costo Total",
                "Lote Código",
                "Fecha Vencimiento Lote",
                "Usuario ID",
                "Usuario",
                "Motivo Merma",
                "Descripción Merma",
                "Transfer ID",
            ]

            buffer = io.StringIO()
            writer = csv.writer(buffer)
            writer.writerow(header)
            yield buffer.getvalue()
            buffer.seek(0)
            buffer.truncate(0)

            # 3. Obtener el lote completo filtrado
            all_filtered = self._filter_ledger(
                tenant_id=resolved_tenant,
                bodega_id=bodega_id,
                producto_id=producto_id,
                tipo_movimiento=tipo_movimiento,
                fecha_desde=fecha_desde,
                fecha_hasta=fecha_hasta,
                user_search=user_search,
            )

            records_exported = len(all_filtered)
            span_attrs["records_exported"] = records_exported

            # 4. Emitir filas sanitizadas
            for entry in all_filtered:
                p_nom, p_uni = self.resolve_product(entry.producto_id)
                b_nom = self.resolve_warehouse(entry.bodega_id)
                u_dis = self.resolve_user_display_name(entry.actor_user_id, can_view_users=can_view_users)
                delta_res = compute_audit_delta(
                    resulting_balance=entry.resulting_balance,
                    quantity=entry.quantity,
                    movement_type=entry.movement_type,
                    unit=p_uni,
                )
                costo_ppp = getattr(entry, "costo_unitario_ppp", entry.unit_cost)
                costo_tot = getattr(
                    entry,
                    "costo_total_movimiento",
                    (abs(entry.quantity) * costo_ppp).quantize(Decimal("0.01")),
                )
                fecha_rec = getattr(entry, "fecha_recuento", None) or entry.created_at.date()
                desc_merma = getattr(entry, "descripcion_merma", None) or entry.documento_referencia

                row = [
                    sanitize_spreadsheet_export_value(entry.id),
                    sanitize_spreadsheet_export_value(entry.created_at.isoformat() if entry.created_at else ""),
                    sanitize_spreadsheet_export_value(fecha_rec.isoformat() if fecha_rec else ""),
                    sanitize_spreadsheet_export_value(entry.bodega_id),
                    sanitize_spreadsheet_export_value(b_nom),
                    sanitize_spreadsheet_export_value(entry.producto_id),
                    sanitize_spreadsheet_export_value(p_nom),
                    sanitize_spreadsheet_export_value(p_uni),
                    sanitize_spreadsheet_export_value(entry.movement_type),
                    sanitize_spreadsheet_export_value(str(entry.quantity)),
                    sanitize_spreadsheet_export_value(str(delta_res.before) if delta_res.before is not None else ""),
                    sanitize_spreadsheet_export_value(str(entry.resulting_balance)),
                    sanitize_spreadsheet_export_value(str(costo_ppp)),
                    sanitize_spreadsheet_export_value(str(costo_tot)),
                    sanitize_spreadsheet_export_value(entry.lote_codigo or ""),
                    sanitize_spreadsheet_export_value(entry.fecha_vencimiento_lote.isoformat() if entry.fecha_vencimiento_lote else ""),
                    sanitize_spreadsheet_export_value(entry.actor_user_id),
                    sanitize_spreadsheet_export_value(u_dis),
                    sanitize_spreadsheet_export_value(getattr(entry, "motivo_merma", None) or ""),
                    sanitize_spreadsheet_export_value(desc_merma or ""),
                    sanitize_spreadsheet_export_value(str(entry.transfer_id) if entry.transfer_id else ""),
                ]
                writer.writerow(row)
                yield buffer.getvalue()
                buffer.seek(0)
                buffer.truncate(0)

    def purge_history(self, tenant_id: str | None = None) -> int:
        """
        Purga todos los registros históricos del tenant en el servicio subyacente.
        Solo permitido para el rol Propietario bajo auditoría crítica.
        """
        ctx = get_tenant_telemetry_context()
        resolved_tenant = tenant_id or ctx.tenant_id
        with trace_span(
            "kardex.history.purge",
            attributes={
                "oppytec.tenant_id": str(resolved_tenant or ""),
                "tenant_id": str(resolved_tenant or ""),
            },
            tracer_name="oppytec.inventory.history",
        ) as span_attrs:
            purged = self._inventory.purge_history(tenant_id=resolved_tenant)
            span_attrs["purged_records"] = purged
            format_history_audit_log(
                "CRITICAL",
                "purged",
                {
                    "tenant_id": resolved_tenant,
                    "purged_records": purged,
                },
            )
            return purged


__all__ = [
    "KardexHistoryService",
    "format_history_audit_log",
    "scrub_audit_payload",
]
