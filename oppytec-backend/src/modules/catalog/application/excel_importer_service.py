"""
oppytec-backend/src/modules/catalog/application/excel_importer_service.py
Importador Excel del catálogo con mapeo de columnas delegado al contrato JEV (Sistema 1).
Confianza por debajo del umbral => requiere confirmación humana (nunca se importa a ciegas).
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Protocol

from src.modules.catalog.domain.unit_conversion import UnitLayers

JEV_CONFIDENCE_THRESHOLD = Decimal("0.85")
REQUIRED_FIELDS: tuple[str, ...] = ("sku", "nombre", "unidad_compra", "costo_compra_neto")


@dataclass(frozen=True)
class JevColumnMapping:
    """Resultado JEV tipo Choice: columna Excel -> campo canónico, con confianza Decimal."""

    mapping: Mapping[str, str]
    confidence: Decimal


class JevColumnMapper(Protocol):
    """Contrato JEV para mapear encabezados de Excel a campos canónicos del catálogo."""

    def map_columns(self, headers: Sequence[str]) -> JevColumnMapping:
        """Retorna el mapeo propuesto con su nivel de confianza."""
        ...


@dataclass(frozen=True)
class ImportedProduct:
    """Producto normalizado listo para persistir."""

    sku: str
    nombre: str
    unidad_compra: str
    costo_compra_neto: Decimal
    layers: UnitLayers


@dataclass(frozen=True)
class ImportReport:
    """Reporte de importación: productos válidos, errores por fila y necesidad de revisión."""

    products: tuple[ImportedProduct, ...]
    errors: tuple[str, ...]
    requires_human_review: bool
    confidence: Decimal
    skus_seen: frozenset[str] = field(default_factory=frozenset)


class ExcelImporterService:
    """Normaliza filas de Excel usando el mapeo JEV y valida con Decimal."""

    def __init__(self, mapper: JevColumnMapper) -> None:
        self._mapper = mapper

    def import_rows(self, headers: Sequence[str], rows: Sequence[Mapping[str, str]]) -> ImportReport:
        """Mapea columnas, valida cada fila y reporta; confianza baja => revisión humana."""
        decision = self._mapper.map_columns(headers)
        needs_review = decision.confidence < JEV_CONFIDENCE_THRESHOLD
        missing = [f for f in REQUIRED_FIELDS if f not in decision.mapping.values()]
        if missing:
            return ImportReport((), (f"missing_columns:{','.join(missing)}",), True, decision.confidence)
        inverse = {canon: col for col, canon in decision.mapping.items()}
        products: list[ImportedProduct] = []
        errors: list[str] = []
        seen: set[str] = set()
        for idx, row in enumerate(rows, start=1):
            try:
                sku = row[inverse["sku"]].strip()
                if not sku or sku in seen:
                    raise ValueError("duplicate_or_empty_sku")
                factor_c = Decimal(row.get(inverse.get("factor_compra_a_almacen", ""), "1") or "1")
                factor_r = Decimal(row.get(inverse.get("factor_almacen_a_receta", ""), "1") or "1")
                products.append(
                    ImportedProduct(
                        sku=sku,
                        nombre=row[inverse["nombre"]].strip(),
                        unidad_compra=row[inverse["unidad_compra"]].strip(),
                        costo_compra_neto=Decimal(row[inverse["costo_compra_neto"]]),
                        layers=UnitLayers(factor_c, factor_r),
                    )
                )
                seen.add(sku)
            except (KeyError, ValueError, InvalidOperation) as exc:
                errors.append(f"row_{idx}:{exc}")
        return ImportReport(tuple(products), tuple(errors), needs_review, decision.confidence, frozenset(seen))
