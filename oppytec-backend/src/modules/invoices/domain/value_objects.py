"""
oppytec-backend/src/modules/invoices/domain/value_objects.py
Value Objects inmutables del dominio de Facturas, DTE y Contabilidad.
Cumple Regla 02 (Clean Architecture: 0 imports de infraestructura) y paridad con Decimal estricto (0% float).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum, IntEnum

from src.modules.invoices.domain.exceptions import (
    InvalidPackagingFactorError,
    InvalidRUTError,
)

CHILEAN_RUT_FACTORS = (2, 3, 4, 5, 6, 7)
INTL_TAX_ID_PATTERN = re.compile(r"^[A-Za-z0-9.\-_]{3,64}$")
DECIMAL_QUANT_4 = Decimal("0.0001")


def calculate_chilean_dv(body: str | int) -> str:
    """
    Calcula el dígito verificador chileno para un cuerpo de RUT mediante el algoritmo Módulo 11.
    Retorna '0'-'9' o 'K'.
    """
    body_str = str(body).strip()
    if not body_str.isdigit():
        raise InvalidRUTError(f"RUT body must contain only digits, received: '{body_str}'")

    total = sum(
        int(digit) * CHILEAN_RUT_FACTORS[idx % len(CHILEAN_RUT_FACTORS)]
        for idx, digit in enumerate(reversed(body_str))
    )
    remainder = total % 11
    dv_val = 11 - remainder
    if dv_val == 11:
        return "0"
    if dv_val == 10:
        return "K"
    return str(dv_val)


@dataclass(frozen=True)
class TaxId:
    """
    Value Object inmutable que representa un identificador tributario (RUT chileno o Tax ID internacional).
    Asegura validación rigurosa por algoritmo Módulo 11 para RUTs chilenos.
    """

    value: str
    country: str = "CL"

    def __init__(self, raw_value: str, country: str = "CL") -> None:
        if not isinstance(raw_value, str):
            raise InvalidRUTError(f"TaxId must be a string, got {type(raw_value).__name__}")

        stripped = raw_value.strip()
        if not stripped:
            raise InvalidRUTError("TaxId cannot be empty or whitespace")

        norm_country = country.strip().upper()

        if norm_country == "CL":
            clean_str = stripped.replace(".", "").replace(" ", "").upper()
            if "-" in clean_str:
                parts = clean_str.rsplit("-", 1)
                body_candidate, dv_candidate = parts[0], parts[1]
            else:
                if len(clean_str) < 2:
                    raise InvalidRUTError(f"Chilean RUT '{raw_value}' is too short")
                body_candidate, dv_candidate = clean_str[:-1], clean_str[-1]

            if not body_candidate.isdigit():
                raise InvalidRUTError(
                    f"Chilean RUT body must contain only digits: '{body_candidate}' from '{raw_value}'"
                )

            if not (1 <= len(body_candidate) <= 9):
                raise InvalidRUTError(
                    f"Chilean RUT body length must be between 1 and 9 digits, got {len(body_candidate)}"
                )

            expected_dv = calculate_chilean_dv(body_candidate)
            if dv_candidate != expected_dv:
                raise InvalidRUTError(
                    f"Invalid Chilean RUT check digit for '{raw_value}': expected '{expected_dv}', got '{dv_candidate}'"
                )

            formatted_body = f"{int(body_candidate):,}".replace(",", ".")
            canonical_value = f"{formatted_body}-{dv_candidate}"
        else:
            if not INTL_TAX_ID_PATTERN.match(stripped):
                raise InvalidRUTError(
                    f"Invalid international Tax ID format for '{stripped}' (country: {norm_country})"
                )
            canonical_value = stripped.upper()

        object.__setattr__(self, "value", canonical_value)
        object.__setattr__(self, "country", norm_country)

    @classmethod
    def from_chilean(cls, rut: str) -> TaxId:
        """Fabrica un TaxId chileno validando módulo 11."""
        return cls(raw_value=rut, country="CL")

    @classmethod
    def from_clean(cls, clean_rut: str) -> TaxId:
        """Fabrica un TaxId a partir de un string limpio sin puntos."""
        return cls(raw_value=clean_rut, country="CL")

    @property
    def is_chilean(self) -> bool:
        """Indica si el identificador corresponde a un RUT de Chile."""
        return self.country == "CL"

    @property
    def clean(self) -> str:
        """Retorna el RUT chileno sin puntos (ej. '76543210-K') o el identificador sin cambios."""
        if self.is_chilean:
            return self.value.replace(".", "")
        return self.value

    @property
    def clean_tax_id(self) -> str:
        """Alias para interoperabilidad con esquemas de persistencia e interfaces."""
        return self.clean

    @property
    def formatted(self) -> str:
        """Retorna el formato canónico formateado con puntos y guion."""
        return self.value

    @property
    def body(self) -> str:
        """Retorna el cuerpo numérico del RUT."""
        if self.is_chilean and "-" in self.value:
            return self.clean.split("-")[0]
        return self.clean

    @property
    def dv(self) -> str:
        """Retorna el dígito verificador del RUT."""
        if self.is_chilean and "-" in self.value:
            return self.value.split("-")[-1]
        return ""

    def __str__(self) -> str:
        return self.value


class DTEType(IntEnum):
    """
    Tipos de Documentos Tributarios Electrónicos (DTE) reconocidos por el SII de Chile.
    """

    FACTURA_ELECTRONICA = 33
    FACTURA_EXENTA = 34
    BOLETA_ELECTRONICA = 39
    GUIA_DESPACHO = 52
    NOTA_DEBITO = 56
    NOTA_CREDITO = 61

    @classmethod
    def from_code(cls, code: int | str) -> DTEType:
        """Resuelve el DTEType a partir de un entero o string representativo."""
        try:
            return cls(int(code))
        except (ValueError, TypeError):
            # Intentar mapeo por nombre
            if isinstance(code, str):
                normalized = code.strip().upper().replace(" ", "_")
                for item in cls:
                    if item.name == normalized or str(item.value) == normalized:
                        return item
            raise ValueError(f"Unknown DTE type code: {code}")

    @property
    def description(self) -> str:
        """Descripción legible en español del tipo de documento."""
        descriptions = {
            DTEType.FACTURA_ELECTRONICA: "Factura Electrónica",
            DTEType.FACTURA_EXENTA: "Factura No Afecta o Exenta Electrónica",
            DTEType.BOLETA_ELECTRONICA: "Boleta Electrónica",
            DTEType.GUIA_DESPACHO: "Guía de Despacho Electrónica",
            DTEType.NOTA_DEBITO: "Nota de Débito Electrónica",
            DTEType.NOTA_CREDITO: "Nota de Crédito Electrónica",
        }
        return descriptions.get(self, f"DTE Tipo {self.value}")

    @property
    def requires_vat(self) -> bool:
        """Determina si el documento tributario está afecto a IVA (19%)."""
        return self in (
            DTEType.FACTURA_ELECTRONICA,
            DTEType.BOLETA_ELECTRONICA,
            DTEType.NOTA_DEBITO,
            DTEType.NOTA_CREDITO,
        )


class InvoiceStatus(str, Enum):
    """Ciclo de vida y estado de procesamiento de una factura en OppyTec."""

    PENDING = "PENDING"
    UPLOADED = "UPLOADED"
    PARSED = "PARSED"
    ANALYZED = "ANALYZED"
    REVIEWING = "REVIEWING"
    READY_FOR_REVIEW = "READY_FOR_REVIEW"
    APPROVED = "APPROVED"
    CONFIRMED_STOCK = "CONFIRMED_STOCK"
    INGESTED = "INGESTED"
    REJECTED = "REJECTED"
    ERROR = "ERROR"

    @property
    def is_terminal(self) -> bool:
        """Indica si el estado es final y no admite más transiciones."""
        return self in (InvoiceStatus.CONFIRMED_STOCK, InvoiceStatus.INGESTED, InvoiceStatus.REJECTED)

    @property
    def is_reviewable(self) -> bool:
        """Indica si la factura está en una fase donde un humano puede revisar y corregir líneas."""
        return self in (
            InvoiceStatus.PARSED,
            InvoiceStatus.ANALYZED,
            InvoiceStatus.REVIEWING,
            InvoiceStatus.READY_FOR_REVIEW,
            InvoiceStatus.APPROVED,
        )


class MatchStatus(str, Enum):
    """Estado de conciliación de una línea de factura con el catálogo de productos."""

    EXACT_ALIAS = "exact_alias"
    SUGGESTED = "suggested"
    UNMATCHED = "unmatched"


class AuditSeverity(str, Enum):
    """Nivel de severidad de un hallazgo o flag de auditoría contable."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AuditRuleCode(str, Enum):
    """Códigos estandarizados de reglas de auditoría tributaria y matemática."""

    RUT_MISMATCH = "RUT_MISMATCH"
    VAT_19_DISCREPANCY = "VAT_19_DISCREPANCY"
    TOTAL_NET_MISMATCH = "TOTAL_NET_MISMATCH"
    PRICE_DRIFT_HIGH = "PRICE_DRIFT_HIGH"
    DUPLICATE_FOLIO = "DUPLICATE_FOLIO"


@dataclass(frozen=True)
class PackagingFactor:
    """
    Value Object inmutable que representa la relación de desacoplamiento de empaque
    entre la unidad de compra mayorista y la unidad canónica de inventario de cocina.
    Invariante: value > 0 (ej. 18.0 kg/caja, 24.0 unidades/bandeja).
    """

    value: Decimal
    packaging_unit: str = "caja"
    inventory_unit: str = "unidad"

    def __init__(
        self,
        value: Decimal | str | int,
        packaging_unit: str = "caja",
        inventory_unit: str = "unidad",
    ) -> None:
        if isinstance(value, Decimal):
            dec_val = value
        else:
            try:
                dec_val = Decimal(str(value))
            except Exception as e:
                raise InvalidPackagingFactorError(f"Invalid decimal value for PackagingFactor: {value}") from e

        if dec_val <= Decimal("0"):
            raise InvalidPackagingFactorError(
                f"Packaging factor must be strictly greater than 0, got {dec_val}"
            )

        object.__setattr__(self, "value", dec_val)
        object.__setattr__(self, "packaging_unit", packaging_unit.strip() if packaging_unit else "caja")
        object.__setattr__(self, "inventory_unit", inventory_unit.strip() if inventory_unit else "unidad")

    def to_physical_stock(self, raw_quantity: Decimal) -> Decimal:
        """Convierte una cantidad comprada a existencias físicas de inventario."""
        return (raw_quantity * self.value).quantize(DECIMAL_QUANT_4, rounding=ROUND_HALF_UP)

    def calculate_inventory_unit_cost(self, line_total: Decimal, raw_quantity: Decimal) -> Decimal:
        """Calcula el costo por unidad de inventario a partir del total de la línea."""
        stock = self.to_physical_stock(raw_quantity)
        if stock <= Decimal("0"):
            return Decimal("0.0000")
        return (line_total / stock).quantize(DECIMAL_QUANT_4, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class PriceDrift:
    """
    Value Object inmutable que calcula la variación porcentual entre el costo unitario nuevo
    y el costo unitario histórico de compra, determinando la severidad de la alerta de sobreprecio.
    Fórmula: ((new_price - last_price) / last_price) * 100
    """

    new_price: Decimal
    last_price: Decimal

    def __init__(self, new_price: Decimal | str | int, last_price: Decimal | str | int) -> None:
        dec_new = Decimal(str(new_price)) if not isinstance(new_price, Decimal) else new_price
        dec_last = Decimal(str(last_price)) if not isinstance(last_price, Decimal) else last_price
        object.__setattr__(self, "new_price", dec_new)
        object.__setattr__(self, "last_price", dec_last)

    @property
    def drift_percentage(self) -> Decimal:
        """Calcula el porcentaje de variación respecto al último precio registrado."""
        if self.last_price <= Decimal("0"):
            return Decimal("0.0000") if self.new_price <= Decimal("0") else Decimal("100.0000")
        diff = self.new_price - self.last_price
        pct = (diff / self.last_price) * Decimal("100")
        return pct.quantize(DECIMAL_QUANT_4, rounding=ROUND_HALF_UP)

    @property
    def severity(self) -> AuditSeverity:
        """Determina la severidad semafórica según umbrales de negocio (10% advertencia, 25% crítico)."""
        abs_drift = abs(self.drift_percentage)
        if abs_drift >= Decimal("25.0"):
            return AuditSeverity.CRITICAL
        if abs_drift >= Decimal("10.0"):
            return AuditSeverity.WARNING
        return AuditSeverity.INFO

    @property
    def is_drift(self) -> bool:
        """Indica si existe una variación apreciable (>= 10%)."""
        return abs(self.drift_percentage) >= Decimal("10.0")

    @property
    def is_critical(self) -> bool:
        """Indica si la variación supera el límite crítico de sobreprecio (>= 25%)."""
        return abs(self.drift_percentage) >= Decimal("25.0")
