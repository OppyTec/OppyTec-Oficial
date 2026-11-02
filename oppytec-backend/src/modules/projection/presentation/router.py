"""
oppytec-backend/src/modules/projection/presentation/router.py
Enrutador FastAPI del Módulo de Proyección de Demandas, Curvas FEFO y Traspasos Preventivos.
Cumple Regla 02 (Clean Architecture), Regla 06 (Paridad Legacy), RBAC 3-Niveles y RFC 7807.
"""
from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from contextlib import suppress
from datetime import date
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_tenant_db_session
from src.core.exceptions import DomainValidationError, ResourceNotFoundError
from src.core.guards.rbac_dependencies import (
    AuthenticatedPrincipal,
    RequireTenantPermission,
)
from src.core.observability import trace_span
from src.modules.projection.application.projection_engine import ProjectionEngine
from src.modules.projection.application.snapshot_service import ProjectionSnapshotService
from src.modules.projection.presentation.schemas import (
    PaginatedProjectionSnapshotsResponse,
    ProductCurveDetailResponse,
    ProjectionAlertResponse,
    ProjectionCardItemResponse,
    RecomputeRequest,
    RecomputeResponse,
    TransferRecommendationResponse,
)

logger = logging.getLogger("oppytec.projection.router")

router = APIRouter(prefix="/api/v1/projection", tags=["Projection"])

_snapshot_service = ProjectionSnapshotService()
_engine = ProjectionEngine()


def _format_tenant_schema_proj(tenant_id: str | None) -> str:
    if not tenant_id:
        return "tenant_default"
    cleaned = str(tenant_id).strip().lower().replace("-", "_")
    if not cleaned.startswith("tenant_"):
        cleaned = f"tenant_{cleaned}"
    return cleaned


async def get_projection_tenant_db(request: Request) -> AsyncGenerator[AsyncSession | None, None]:
    """
    Sesión tenant derivada EXCLUSIVAMENTE del principal autenticado por `RequireTenantPermission`.

    Red Team (fail-closed): no se lee `X-Tenant-ID` crudo ni se cae a `tenant_default`;
    el guard RBAC ya validó el header contra `accessible_tenants` y lo dejó en el principal.
    """
    principal: AuthenticatedPrincipal | None = getattr(request.state, "principal", None)
    tenant_id = principal.tenant_id if principal else None
    if not tenant_id:
        yield None
        return
    schema = _format_tenant_schema_proj(tenant_id)
    session_gen = get_tenant_db_session(schema)
    try:
        session = await anext(session_gen)
    except Exception as exc:
        logger.warning("No se pudo abrir la sesión tenant de proyección: %s", type(exc).__name__)
        yield None
        return

    try:
        yield session
    finally:
        with suppress(Exception):
            await session_gen.aclose()


@router.get(
    "/snapshots",
    response_model=PaginatedProjectionSnapshotsResponse,
    status_code=status.HTTP_200_OK,
    summary="Listado paginado de proyección server-side",
)
async def get_paginated_snapshots_endpoint(
    request: Request,
    _principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("projection.demand.read", fallback_permission="inventory.kardex.read")),
    ],
    db: Annotated[AsyncSession | None, Depends(get_projection_tenant_db)],
    page: int = Query(1, ge=1, description="Número de página (1..N)"),
    page_size: int = Query(30, ge=1, le=100, description="Tamaño de página (10, 30, 50, 100)"),
    search: str | None = Query(None, max_length=100, description="Término de búsqueda por nombre o SKU"),
    category_id: int | None = Query(None, description="Filtro opcional por ID de categoría"),
    bodega_id: int | None = Query(None, description="Filtro opcional por ID de bodega"),
    status_filter: str | None = Query(
        None,
        alias="status",
        pattern=r"^(?i:all|normal|warning|critical)$",
        description="Filtro por semáforo: all, normal, warning, critical",
    ),
    sort_by: str | None = Query(
        None,
        pattern=r"^(?i:urgency_desc|name_asc|name_desc|projected_asc|current_desc)$",
        description="Criterio de orden: urgency_desc, name_asc, name_desc, projected_asc, current_desc",
    ),
    horizon_days: int = Query(30, ge=7, le=90, description="Horizonte de días simulado (7, 15, 30, 60, 90)"),
) -> PaginatedProjectionSnapshotsResponse:
    """Devuelve las tarjetas del Grid de Proyección con paginación server-side de alto rendimiento (< 25 ms)."""
    if db is None:
        raise DomainValidationError("No se pudo establecer la sesión de base de datos del inquilino.")

    with trace_span(
        "projection.get_snapshots_paginated.endpoint",
        attributes={
            "page": page,
            "page_size": page_size,
            "search": search or "",
            "category_id": category_id,
            "bodega_id": bodega_id,
            "status": status_filter or "",
            "sort_by": sort_by or "",
            "horizon_days": horizon_days,
            "tenant_id": _principal.tenant_id,
        },
        tracer_name="oppytec.projection",
    ) as span_attrs:
        data = await _snapshot_service.get_paginated_snapshots(
            db=db,
            page=page,
            page_size=page_size,
            search=search,
            category_id=category_id,
            bodega_id=bodega_id,
            status_filter=status_filter,
            sort_by=sort_by,
            horizon_days=horizon_days,
        )
        span_attrs["total_items"] = data.get("total_items", 0)

        return PaginatedProjectionSnapshotsResponse(
            items=[ProjectionCardItemResponse(**item) for item in data["items"]],
            total_items=data["total_items"],
            page=data["page"],
            page_size=data["page_size"],
            total_pages=data["total_pages"],
            has_next=data["has_next"],
            has_prev=data["has_prev"],
        )


@router.post(
    "/recompute",
    response_model=RecomputeResponse,
    status_code=status.HTTP_200_OK,
    summary="Forzar recálculo inmediato de snapshots del tenant",
)
async def recompute_snapshots_endpoint(
    request: Request,
    _principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("projection.recompute.execute", fallback_permission="inventory.kardex.write")),
    ],
    db: Annotated[AsyncSession | None, Depends(get_projection_tenant_db)],
    payload: RecomputeRequest | None = None,
) -> RecomputeResponse:
    """Ejecuta el recálculo masivo por lotes con bloqueo anti-concurrencia (Advisory lock)."""
    if db is None:
        raise DomainValidationError("No se pudo establecer la sesión de base de datos del inquilino.")

    horizon = payload.horizon_days if payload else 30
    tenant_id = _principal.tenant_id

    with trace_span(
        "projection.recompute_snapshots.endpoint",
        attributes={
            "tenant_id": tenant_id,
            "horizon_days": horizon,
        },
        tracer_name="oppytec.projection",
    ) as span_attrs:
        result = await _snapshot_service.recompute_tenant_snapshots(
            db=db,
            tenant_id=tenant_id,
            horizon_days=horizon,
        )
        span_attrs["projection.products_processed"] = result.get("processed", 0)
        span_attrs["status"] = result.get("status", "completed")

        return RecomputeResponse(
            status=result.get("status", "completed"),
            processed=result.get("processed", 0),
            horizon_days=result.get("horizon_days", horizon),
            message=result.get("message", "Recálculo finalizado"),
        )


@router.get(
    "/products/{product_id}/curve",
    response_model=ProductCurveDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Serie temporal de proyección día a día para Recharts",
)
async def get_product_curve_endpoint(
    product_id: int,
    request: Request,
    _principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("projection.demand.read", fallback_permission="inventory.kardex.read")),
    ],
    db: Annotated[AsyncSession | None, Depends(get_projection_tenant_db)],
    bodega_id: int | None = Query(None, description="Bodega específica o consolidado si se omite"),
    horizon_days: int = Query(30, ge=7, le=90, description="Horizonte temporal de la curva"),
) -> ProductCurveDetailResponse:
    """Devuelve los puntos de simulación día a día (0..horizon_days) para graficar en Recharts."""
    if db is None:
        raise DomainValidationError("No se pudo establecer la sesión de base de datos del inquilino.")

    with trace_span(
        "projection.get_product_curve.endpoint",
        attributes={
            "product_id": product_id,
            "bodega_id": bodega_id,
            "horizon_days": horizon_days,
            "tenant_id": _principal.tenant_id,
        },
        tracer_name="oppytec.projection",
    ):
        detail = await _snapshot_service.get_product_curve_detail(
            db=db,
            producto_id=product_id,
            bodega_id=bodega_id,
            horizon_days=horizon_days,
        )

        return ProductCurveDetailResponse(**detail)


@router.get(
    "/alerts",
    response_model=list[ProjectionAlertResponse],
    status_code=status.HTTP_200_OK,
    summary="Consola de alertas de quiebre y riesgos de stock",
)
async def get_projection_alerts_endpoint(
    request: Request,
    _principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("projection.alerts.read", fallback_permission="inventory.kardex.read")),
    ],
    db: Annotated[AsyncSession | None, Depends(get_projection_tenant_db)],
    bodega_id: int | None = Query(None, description="Filtro opcional por bodega"),
    horizon_days: int = Query(30, ge=7, le=90, description="Horizonte de evaluación"),
) -> list[ProjectionAlertResponse]:
    """Lista los productos en estado crítico o warning con sus sugerencias de traspaso preventivo."""
    if db is None:
        raise DomainValidationError("No se pudo establecer la sesión de base de datos del inquilino.")

    with trace_span(
        "projection.get_projection_alerts.endpoint",
        attributes={
            "bodega_id": bodega_id,
            "horizon_days": horizon_days,
            "tenant_id": _principal.tenant_id,
        },
        tracer_name="oppytec.projection",
    ):
        alerts = await _snapshot_service.get_projection_alerts(
            db=db,
            bodega_id=bodega_id,
            horizon_days=horizon_days,
        )

        return [ProjectionAlertResponse(**al) for al in alerts]


@router.get(
    "/products/{product_id}/transfer-suggestions",
    response_model=list[TransferRecommendationResponse],
    status_code=status.HTTP_200_OK,
    summary="Sugerencias de traspaso preventivo inter-bodega",
)
async def get_transfer_suggestions_endpoint(
    product_id: int,
    request: Request,
    _principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("projection.transfers.read", fallback_permission="inventory.kardex.read")),
    ],
    db: Annotated[AsyncSession | None, Depends(get_projection_tenant_db)],
    bodega_id: int = Query(..., description="ID de la bodega en quiebre o déficit"),
    needed_qty: Decimal | None = Query(
        None, ge=0, le=Decimal("1000000000"), description="Cantidad requerida a suplir"
    ),
    date_needed: date | None = Query(None, description="Fecha en que se necesita el stock"),
) -> list[TransferRecommendationResponse]:
    """Calcula y devuelve recomendaciones de traspaso desde otras bodegas con superávit."""
    if db is None:
        raise DomainValidationError("No se pudo establecer la sesión de base de datos del inquilino.")

    qty = needed_qty if needed_qty is not None and needed_qty > Decimal("0") else Decimal("10.0000")
    d_needed = date_needed or date.today()

    with trace_span(
        "projection.get_transfer_suggestions.endpoint",
        attributes={
            "product_id": product_id,
            "bodega_id": bodega_id,
            "needed_qty": str(qty),
            "tenant_id": _principal.tenant_id,
        },
        tracer_name="oppytec.projection",
    ):
        recs = await _engine.find_alternative_stock(
            db=db,
            producto_id=product_id,
            bodega_id_quiebre=bodega_id,
            needed_qty=qty,
            date_needed=d_needed,
        )

        result: list[TransferRecommendationResponse] = []
        for r in recs:
            # Resolver nombre de bodega origen
            from src.modules.inventory.infrastructure.models import Bodega
            from sqlalchemy import select
            b_res = await db.execute(select(Bodega.nombre).where(Bodega.id == r.bodega_origen_id))
            b_row = b_res.first()
            b_orig_name = b_row[0] if b_row else f"Bodega #{r.bodega_origen_id}"

            result.append(
                TransferRecommendationResponse(
                    producto_id=r.producto_id,
                    bodega_origen_id=r.bodega_origen_id,
                    bodega_origen_nombre=b_orig_name,
                    bodega_destino_id=r.bodega_destino_id,
                    cantidad_sugerida=str(r.cantidad_sugerida),
                    dias_cobertura_restante_origen=r.dias_cobertura_restante_origen,
                    urgencia=r.urgencia.value,
                )
            )

        return result
