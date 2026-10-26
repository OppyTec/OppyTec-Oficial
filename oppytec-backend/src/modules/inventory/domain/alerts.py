"""
oppytec-backend/src/modules/inventory/domain/alerts.py
Arquitectura de Dominio DDD para el Módulo de Alertas de Stock Crítico, Vencimientos y FEFO (/alertas).

Cumple:
- Regla 02 (Clean Architecture: Dominio puro aislado de FastAPI, SQLAlchemy y Redis)
- Regla 15 (i18n / DDD)
- Certificación Decimal Estricta (0% float / IEEE 754)
- Paridad 1:1 con formulas analiticas de OppyTec-Legacy erradicando la deuda técnica del snapshot en cliente.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum
from typing import Protocol, runtime_checkable

ZERO = Decimal("0")
QTY_QUANT = Decimal("0.0001")
MONEY_QUANT = Decimal("0.01")
PERCENT_QUANT = Decimal("0.01")


class AlertSeverity(StrEnum):
    """Nivel de severidad para una alerta operativa de inventario."""

    CRITICAL = "CRITICAL"
    WARNING = "WARNING"
    INFO = "INFO"

    @property
    def is_critical(self) -> bool:
        return self == AlertSeverity.CRITICAL

    @property
    def is_warning(self) -> bool:
        return self == AlertSeverity.WARNING

    @property
    def is_info(self) -> bool:
        return self == AlertSeverity.INFO


class AlertType(StrEnum):
    """Tipo analítico de alerta de inventario."""

    STOCK_CRITICO = "STOCK_CRITICO"
    PRODUCTO_VENCIDO = "PRODUCTO_VENCIDO"
    PROXIMO_A_VENCER = "PROXIMO_A_VENCER"


def _check_not_float(value: object, name: str) -> None:
    """Certificación Decimal Estricta: Prohibe el uso de IEEE 754 float en cálculos de dominio."""
    if type(value).__name__ == "float":
        raise TypeError(
            f"Violación de Certificación Decimal Estricta: el campo '{name}' no admite tipo float (IEEE 754). "
            f"Utilice Decimal, int o str exacto."
        )


@dataclass(frozen=True)
class StockHealthRatio:
    """
    Value Object inmutable que modela la relación porcentual entre el stock actual
    y el stock mínimo de seguridad, junto a su clasificación cromática.

    Paridad exacta con fórmulas de barra de progreso en Legacy:
    - depleted: stock_actual <= 0 (bg-destructive / rojo coral #ef4444)
    - critical: stock_actual > 0 y ratio <= 50% (bg-orange-500)
    - warning: 50% < ratio <= 100% (bg-amber-500)
    - healthy: ratio > 100% (bg-emerald-500 / verde saludable)
    """

    stock_actual: Decimal
    stock_minimo: Decimal
    raw_ratio: Decimal
    clamped_ratio: Decimal
    status: str

    def __post_init__(self) -> None:
        _check_not_float(self.stock_actual, "stock_actual")
        _check_not_float(self.stock_minimo, "stock_minimo")
        _check_not_float(self.raw_ratio, "raw_ratio")
        _check_not_float(self.clamped_ratio, "clamped_ratio")

        if self.clamped_ratio < Decimal("0.00") or self.clamped_ratio > Decimal("100.00"):
            raise ValueError(
                f"Invariante violada: clamped_ratio ({self.clamped_ratio}) debe estar confinado entre 0.00 y 100.00"
            )

        allowed_statuses = {"depleted", "critical", "warning", "healthy"}
        if self.status not in allowed_statuses:
            raise ValueError(f"Estado cromático desconocido '{self.status}'. Válidos: {allowed_statuses}")

    @classmethod
    def calculate(
        cls,
        stock_actual: Decimal | int | str,
        stock_minimo: Decimal | int | str,
    ) -> StockHealthRatio:
        """
        Calcula de forma determinista el ratio de salud porcentual y la clasificación de alerta.
        Totalmente libre de float.
        """
        _check_not_float(stock_actual, "stock_actual")
        _check_not_float(stock_minimo, "stock_minimo")

        dec_actual = stock_actual if isinstance(stock_actual, Decimal) else Decimal(str(stock_actual))
        dec_minimo = stock_minimo if isinstance(stock_minimo, Decimal) else Decimal(str(stock_minimo))

        dec_actual = dec_actual.quantize(QTY_QUANT, rounding=ROUND_HALF_UP)
        dec_minimo = dec_minimo.quantize(QTY_QUANT, rounding=ROUND_HALF_UP)

        if dec_minimo > Decimal("0.0000"):
            raw = (dec_actual / dec_minimo) * Decimal("100")
            raw_ratio = raw.quantize(PERCENT_QUANT, rounding=ROUND_HALF_UP)
        else:
            raw_ratio = Decimal("0.00") if dec_actual <= Decimal("0.0000") else Decimal("100.00")

        clamped = min(max(raw_ratio, Decimal("0.00")), Decimal("100.00")).quantize(
            PERCENT_QUANT, rounding=ROUND_HALF_UP
        )

        # Clasificación cromática paritaria con Legacy
        if dec_actual <= Decimal("0.0000"):
            status = "depleted"
        elif dec_minimo <= Decimal("0.0000"):
            status = "healthy"
        else:
            half_minimum = (dec_minimo * Decimal("0.5")).quantize(QTY_QUANT, rounding=ROUND_HALF_UP)
            if dec_actual <= half_minimum:
                status = "critical"
            elif dec_actual <= dec_minimo:
                status = "warning"
            else:
                status = "healthy"

        return cls(
            stock_actual=dec_actual,
            stock_minimo=dec_minimo,
            raw_ratio=raw_ratio,
            clamped_ratio=clamped,
            status=status,
        )

    @property
    def is_depleted(self) -> bool:
        return self.status == "depleted"

    @property
    def is_critical(self) -> bool:
        return self.status == "critical"

    @property
    def is_warning(self) -> bool:
        return self.status == "warning"

    @property
    def is_healthy(self) -> bool:
        return self.status == "healthy"


@dataclass(frozen=True)
class ExpiryUrgency:
    """
    Value Object inmutable que evalúa la urgencia cronológica de un lote respecto a una fecha de corte.
    Determina si ya venció (días transcurridos) o si está próximo a expirar (días restantes),
    asignando la severidad de la alerta.
    """

    fecha_vencimiento: date
    reference_date: date
    days_diff: int
    is_expired: bool
    dias_vencido: int
    dias_restantes: int
    severity: AlertSeverity

    def __post_init__(self) -> None:
        if self.is_expired:
            if self.dias_vencido < 0 or self.dias_restantes != 0:
                raise ValueError("Invariante violada: producto vencido debe tener dias_vencido >= 0 y dias_restantes == 0")
        else:
            if self.dias_restantes < 0 or self.dias_vencido != 0:
                raise ValueError(
                    "Invariante violada: producto no vencido debe tener dias_restantes >= 0 y dias_vencido == 0"
                )

    @classmethod
    def calculate(
        cls,
        fecha_vencimiento: date,
        reference_date: date | None = None,
        warning_days_threshold: int = 30,
        critical_days_threshold: int = 7,
    ) -> ExpiryUrgency:
        """
        Calcula la urgencia de expiración FEFO respecto a reference_date (default: hoy).
        """
        ref = reference_date or date.today()
        days_diff = (fecha_vencimiento - ref).days

        if days_diff < 0:
            is_expired = True
            dias_vencido = abs(days_diff)
            dias_restantes = 0
            severity = AlertSeverity.CRITICAL
        else:
            is_expired = False
            dias_vencido = 0
            dias_restantes = days_diff
            if dias_restantes <= critical_days_threshold:
                severity = AlertSeverity.CRITICAL
            elif dias_restantes <= warning_days_threshold:
                severity = AlertSeverity.WARNING
            else:
                severity = AlertSeverity.INFO

        return cls(
            fecha_vencimiento=fecha_vencimiento,
            reference_date=ref,
            days_diff=days_diff,
            is_expired=is_expired,
            dias_vencido=dias_vencido,
            dias_restantes=dias_restantes,
            severity=severity,
        )


@dataclass(frozen=True)
class CriticalStockAlert:
    """
    Entidad de dominio inmutable que representa un insumo en situación de quiebre o stock crítico.
    """

    producto_id: int
    bodega_id: int
    bodega_nombre: str
    producto_nombre: str
    stock_actual: Decimal
    stock_minimo: Decimal
    unidad_medida: str
    ratio: StockHealthRatio
    is_depleted: bool
    bodega_color: str = "#3B82F6"
    bodega_icono: str = "warehouse"
    costo_promedio: Decimal = Decimal("0.00")

    def __post_init__(self) -> None:
        if self.producto_id <= 0:
            raise ValueError(f"producto_id debe ser un entero positivo, recibido {self.producto_id}")
        if self.bodega_id <= 0:
            raise ValueError(f"bodega_id debe ser un entero positivo, recibido {self.bodega_id}")

        _check_not_float(self.stock_actual, "stock_actual")
        _check_not_float(self.stock_minimo, "stock_minimo")
        _check_not_float(self.costo_promedio, "costo_promedio")

        # Comprobación de invariante de agotamiento
        expected_depleted = self.stock_actual <= Decimal("0.0000")
        if self.is_depleted != expected_depleted:
            raise ValueError(
                f"Invariante violada: is_depleted ({self.is_depleted}) difiere del cálculo de stock actual ({self.stock_actual})"
            )

        # Invariante de alerta crítica: stock_actual <= stock_minimo (o agotado)
        if self.stock_minimo > Decimal("0.0000") and self.stock_actual > self.stock_minimo:
            raise ValueError(
                f"Invariante violada: no constituye alerta de stock crítico si stock_actual ({self.stock_actual}) > stock_minimo ({self.stock_minimo})"
            )

    @classmethod
    def create(
        cls,
        producto_id: int,
        bodega_id: int,
        bodega_nombre: str,
        producto_nombre: str,
        stock_actual: Decimal | int | str,
        stock_minimo: Decimal | int | str,
        unidad_medida: str,
        bodega_color: str = "#3B82F6",
        bodega_icono: str = "warehouse",
        costo_promedio: Decimal | int | str = Decimal("0.00"),
    ) -> CriticalStockAlert:
        """Constructor factory de conveniencia con tipado Decimal estricto y cálculo automático de ratio."""
        _check_not_float(stock_actual, "stock_actual")
        _check_not_float(stock_minimo, "stock_minimo")
        _check_not_float(costo_promedio, "costo_promedio")

        dec_actual = stock_actual if isinstance(stock_actual, Decimal) else Decimal(str(stock_actual))
        dec_minimo = stock_minimo if isinstance(stock_minimo, Decimal) else Decimal(str(stock_minimo))
        dec_costo = costo_promedio if isinstance(costo_promedio, Decimal) else Decimal(str(costo_promedio))

        dec_actual = dec_actual.quantize(QTY_QUANT, rounding=ROUND_HALF_UP)
        dec_minimo = dec_minimo.quantize(QTY_QUANT, rounding=ROUND_HALF_UP)
        dec_costo = dec_costo.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)

        ratio = StockHealthRatio.calculate(dec_actual, dec_minimo)
        is_depleted = dec_actual <= Decimal("0.0000")

        return cls(
            producto_id=producto_id,
            bodega_id=bodega_id,
            bodega_nombre=bodega_nombre,
            producto_nombre=producto_nombre,
            stock_actual=dec_actual,
            stock_minimo=dec_minimo,
            unidad_medida=unidad_medida,
            ratio=ratio,
            is_depleted=is_depleted,
            bodega_color=bodega_color,
            bodega_icono=bodega_icono,
            costo_promedio=dec_costo,
        )


@dataclass(frozen=True)
class ExpiredLotAlert:
    """
    Entidad de dominio inmutable que representa un lote caducado que aún conserva saldo físico en bodega.
    Requiere acción inmediata de merma o descarte.
    """

    producto_id: int
    bodega_id: int
    bodega_nombre: str
    producto_nombre: str
    lote_codigo: str | None
    fecha_vencimiento: date
    cantidad_vencida: Decimal
    dias_vencido: int
    costo_ppp: Decimal
    unidad_medida: str
    bodega_color: str = "#3B82F6"
    bodega_icono: str = "warehouse"

    def __post_init__(self) -> None:
        if self.producto_id <= 0:
            raise ValueError(f"producto_id debe ser un entero positivo, recibido {self.producto_id}")
        if self.bodega_id <= 0:
            raise ValueError(f"bodega_id debe ser un entero positivo, recibido {self.bodega_id}")

        _check_not_float(self.cantidad_vencida, "cantidad_vencida")
        _check_not_float(self.costo_ppp, "costo_ppp")

        if self.cantidad_vencida <= Decimal("0.0000"):
            raise ValueError(f"Invariante violada: cantidad_vencida debe ser estrictamente positiva, recibido {self.cantidad_vencida}")
        if self.dias_vencido < 0:
            raise ValueError(f"Invariante violada: dias_vencido no puede ser negativo, recibido {self.dias_vencido}")
        if self.costo_ppp < Decimal("0.00"):
            raise ValueError(f"Invariante violada: costo_ppp no puede ser negativo, recibido {self.costo_ppp}")

    @property
    def valor_total_riesgo(self) -> Decimal:
        """Valor financiero total de la pérdida por lote vencido valorizado a costo PPP."""
        total = self.cantidad_vencida * self.costo_ppp
        return total.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)

    @classmethod
    def create(
        cls,
        producto_id: int,
        bodega_id: int,
        bodega_nombre: str,
        producto_nombre: str,
        lote_codigo: str | None,
        fecha_vencimiento: date,
        cantidad_vencida: Decimal | int | str,
        dias_vencido: int,
        costo_ppp: Decimal | int | str,
        unidad_medida: str,
        bodega_color: str = "#3B82F6",
        bodega_icono: str = "warehouse",
    ) -> ExpiredLotAlert:
        """Constructor factory de conveniencia con cuantización estricta Decimal."""
        _check_not_float(cantidad_vencida, "cantidad_vencida")
        _check_not_float(costo_ppp, "costo_ppp")

        dec_cant = cantidad_vencida if isinstance(cantidad_vencida, Decimal) else Decimal(str(cantidad_vencida))
        dec_costo = costo_ppp if isinstance(costo_ppp, Decimal) else Decimal(str(costo_ppp))

        dec_cant = dec_cant.quantize(QTY_QUANT, rounding=ROUND_HALF_UP)
        dec_costo = dec_costo.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)

        return cls(
            producto_id=producto_id,
            bodega_id=bodega_id,
            bodega_nombre=bodega_nombre,
            producto_nombre=producto_nombre,
            lote_codigo=lote_codigo,
            fecha_vencimiento=fecha_vencimiento,
            cantidad_vencida=dec_cant,
            dias_vencido=dias_vencido,
            costo_ppp=dec_costo,
            unidad_medida=unidad_medida,
            bodega_color=bodega_color,
            bodega_icono=bodega_icono,
        )


@dataclass(frozen=True)
class UpcomingExpiryAlert:
    """
    Entidad de dominio inmutable que representa un lote próximo a vencer dentro de la ventana de urgencia FEFO.
    Permite rotación prioritaria o consumo preferente en recetas.
    """

    producto_id: int
    bodega_id: int
    bodega_nombre: str
    producto_nombre: str
    lote_codigo: str | None
    fecha_vencimiento: date
    cantidad_en_riesgo: Decimal
    dias_restantes: int
    costo_ppp: Decimal
    unidad_medida: str
    bodega_color: str = "#3B82F6"
    bodega_icono: str = "warehouse"

    def __post_init__(self) -> None:
        if self.producto_id <= 0:
            raise ValueError(f"producto_id debe ser un entero positivo, recibido {self.producto_id}")
        if self.bodega_id <= 0:
            raise ValueError(f"bodega_id debe ser un entero positivo, recibido {self.bodega_id}")

        _check_not_float(self.cantidad_en_riesgo, "cantidad_en_riesgo")
        _check_not_float(self.costo_ppp, "costo_ppp")

        if self.cantidad_en_riesgo <= Decimal("0.0000"):
            raise ValueError(f"Invariante violada: cantidad_en_riesgo debe ser estrictamente positiva, recibido {self.cantidad_en_riesgo}")
        if self.dias_restantes < 0:
            raise ValueError(f"Invariante violada: dias_restantes no puede ser negativo, recibido {self.dias_restantes}")
        if self.costo_ppp < Decimal("0.00"):
            raise ValueError(f"Invariante violada: costo_ppp no puede ser negativo, recibido {self.costo_ppp}")

    @property
    def valor_total_riesgo(self) -> Decimal:
        """Valor financiero total del inventario en riesgo por caducidad inminente."""
        total = self.cantidad_en_riesgo * self.costo_ppp
        return total.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)

    @classmethod
    def create(
        cls,
        producto_id: int,
        bodega_id: int,
        bodega_nombre: str,
        producto_nombre: str,
        lote_codigo: str | None,
        fecha_vencimiento: date,
        cantidad_en_riesgo: Decimal | int | str,
        dias_restantes: int,
        costo_ppp: Decimal | int | str,
        unidad_medida: str,
        bodega_color: str = "#3B82F6",
        bodega_icono: str = "warehouse",
    ) -> UpcomingExpiryAlert:
        """Constructor factory de conveniencia con cuantización estricta Decimal."""
        _check_not_float(cantidad_en_riesgo, "cantidad_en_riesgo")
        _check_not_float(costo_ppp, "costo_ppp")

        dec_cant = cantidad_en_riesgo if isinstance(cantidad_en_riesgo, Decimal) else Decimal(str(cantidad_en_riesgo))
        dec_costo = costo_ppp if isinstance(costo_ppp, Decimal) else Decimal(str(costo_ppp))

        dec_cant = dec_cant.quantize(QTY_QUANT, rounding=ROUND_HALF_UP)
        dec_costo = dec_costo.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)

        return cls(
            producto_id=producto_id,
            bodega_id=bodega_id,
            bodega_nombre=bodega_nombre,
            producto_nombre=producto_nombre,
            lote_codigo=lote_codigo,
            fecha_vencimiento=fecha_vencimiento,
            cantidad_en_riesgo=dec_cant,
            dias_restantes=dias_restantes,
            costo_ppp=dec_costo,
            unidad_medida=unidad_medida,
            bodega_color=bodega_color,
            bodega_icono=bodega_icono,
        )


@dataclass(frozen=True)
class AlertBadgeSummary:
    """
    Agregado liviano especializado para el Sidebar institucional y la barra de cabecera.
    Diseñado para responder en < 5ms sin transportar colecciones pesadas.
    """

    total_count: int
    has_critical: bool
    critical_stock_count: int
    expired_count: int
    upcoming_count: int

    @classmethod
    def from_counts(
        cls,
        critical_stock_count: int,
        expired_count: int,
        upcoming_count: int,
    ) -> AlertBadgeSummary:
        tot = critical_stock_count + expired_count + upcoming_count
        has_crit = (critical_stock_count > 0) or (expired_count > 0)
        return cls(
            total_count=tot,
            has_critical=has_crit,
            critical_stock_count=critical_stock_count,
            expired_count=expired_count,
            upcoming_count=upcoming_count,
        )

    @classmethod
    def empty(cls) -> AlertBadgeSummary:
        return cls(
            total_count=0,
            has_critical=False,
            critical_stock_count=0,
            expired_count=0,
            upcoming_count=0,
        )


@dataclass(frozen=True)
class AlertsConsolidatedSummary:
    """
    Agregado raíz de Dominio que consolida las 3 dimensiones de alertas operativas:
    1. Stock Crítico / Quiebre bajo mínimo.
    2. Lotes caducados con existencias en almacén.
    3. Lotes próximos a vencer (ventana FEFO).

    Proporciona conteos agregados, banderas de criticidad y valorización total de riesgo financiero.
    """

    critical_stock: tuple[CriticalStockAlert, ...] = field(default_factory=tuple)
    expired_lots: tuple[ExpiredLotAlert, ...] = field(default_factory=tuple)
    upcoming_expiries: tuple[UpcomingExpiryAlert, ...] = field(default_factory=tuple)
    total_count: int = 0
    critical_count: int = 0
    expired_count: int = 0
    upcoming_count: int = 0
    has_critical: bool = False
    total_financial_risk: Decimal = Decimal("0.00")

    def __post_init__(self) -> None:
        _check_not_float(self.total_financial_risk, "total_financial_risk")

        # Invariante de coherencia en conteos
        if self.total_count != (self.critical_count + self.expired_count + self.upcoming_count):
            raise ValueError(
                f"Invariante violada: total_count ({self.total_count}) != suma de partes "
                f"({self.critical_count} + {self.expired_count} + {self.upcoming_count})"
            )

        if len(self.critical_stock) != self.critical_count:
            raise ValueError("Invariante violada: tamaño de critical_stock no coincide con critical_count")
        if len(self.expired_lots) != self.expired_count:
            raise ValueError("Invariante violada: tamaño de expired_lots no coincide con expired_count")
        if len(self.upcoming_expiries) != self.upcoming_count:
            raise ValueError("Invariante violada: tamaño de upcoming_expiries no coincide con upcoming_count")

    @classmethod
    def create(
        cls,
        critical_stock: Sequence[CriticalStockAlert],
        expired_lots: Sequence[ExpiredLotAlert],
        upcoming_expiries: Sequence[UpcomingExpiryAlert],
    ) -> AlertsConsolidatedSummary:
        """
        Crea el agregado raíz calculando automáticamente los conteos agregados,
        el indicador booleano has_critical y la valorización financiera total del inventario en riesgo.
        """
        c_tuple = tuple(critical_stock)
        e_tuple = tuple(expired_lots)
        u_tuple = tuple(upcoming_expiries)

        c_count = len(c_tuple)
        e_count = len(e_tuple)
        u_count = len(u_tuple)
        total_count = c_count + e_count + u_count

        has_critical = (c_count > 0) or (e_count > 0)

        total_risk = sum(
            (item.valor_total_riesgo for item in e_tuple),
            Decimal("0.00"),
        ) + sum(
            (item.valor_total_riesgo for item in u_tuple),
            Decimal("0.00"),
        )
        total_risk = total_risk.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)

        return cls(
            critical_stock=c_tuple,
            expired_lots=e_tuple,
            upcoming_expiries=u_tuple,
            total_count=total_count,
            critical_count=c_count,
            expired_count=e_count,
            upcoming_count=u_count,
            has_critical=has_critical,
            total_financial_risk=total_risk,
        )

    def to_badge_summary(self) -> AlertBadgeSummary:
        """Proyecta este agregado al resumen liviano del badge."""
        return AlertBadgeSummary(
            total_count=self.total_count,
            has_critical=self.has_critical,
            critical_stock_count=self.critical_count,
            expired_count=self.expired_count,
            upcoming_count=self.upcoming_count,
        )


@runtime_checkable
class AlertsRepositoryInterface(Protocol):
    """
    Contrato del Repositorio de Agregación Analítica de Alertas (Clean Architecture).

    Arquitectura y Rendimiento:
    - Ejecución 100% analítica en el motor de base de datos PostgreSQL dentro de esquemas `tenant_*`.
    - Tiempo de respuesta objetivo: < 20 milisegundos.
    - Elimina por diseño la deuda técnica histórica de Legacy, donde el navegador descargaba
      3 endpoints masivos (/inventory/products, /inventory/history, /operations/events/alerts)
      y reconstruía saldos en el cliente con bucles O(N*M).

    Estrategia de Consulta PostgreSQL Proyectada:
    1. Stock Crítico:
       ```sql
       SELECT
           pb.producto_id,
           pb.bodega_id,
           b.nombre AS bodega_nombre,
           p.nombre AS producto_nombre,
           pb.stock_actual,
           pb.stock_minimo,
           p.unidad_almacen AS unidad_medida,
           p.costo_promedio_almacen AS costo_promedio
       FROM {tenant_schema}.producto_bodegas pb
       JOIN {tenant_schema}.productos p ON p.id = pb.producto_id AND p.deleted_at IS NULL
       JOIN {tenant_schema}.bodegas b ON b.id = pb.bodega_id AND b.deleted_at IS NULL
       WHERE pb.stock_actual <= pb.stock_minimo
         AND (:bodega_ids IS NULL OR pb.bodega_id = ANY(:bodega_ids));
       ```
    2. Lotes Vencidos y Próximos a Vencer (Kardex Append-Only / Lotes activos):
       ```sql
       SELECT
           rs.producto_id,
           rs.bodega_id,
           b.nombre AS bodega_nombre,
           p.nombre AS producto_nombre,
           rs.lote_codigo,
           rs.fecha_vencimiento_lote,
           SUM(CASE WHEN rs.tipo_movimiento IN ('ENTRADA', 'COMPRA', 'TRASPASO_IN', 'AJUSTE_POSITIVO') THEN rs.cantidad
                    ELSE -rs.cantidad END) AS saldo_lote,
           p.costo_promedio_almacen AS costo_ppp,
           p.unidad_almacen AS unidad_medida
       FROM {tenant_schema}.registro_stock rs
       JOIN {tenant_schema}.productos p ON p.id = rs.producto_id AND p.deleted_at IS NULL
       JOIN {tenant_schema}.bodegas b ON b.id = rs.bodega_id AND b.deleted_at IS NULL
       WHERE rs.fecha_vencimiento_lote IS NOT NULL
         AND (:bodega_ids IS NULL OR rs.bodega_id = ANY(:bodega_ids))
       GROUP BY rs.producto_id, rs.bodega_id, b.nombre, p.nombre, rs.lote_codigo, rs.fecha_vencimiento_lote, p.costo_promedio_almacen, p.unidad_almacen
       HAVING SUM(CASE WHEN rs.tipo_movimiento IN ('ENTRADA', 'COMPRA', 'TRASPASO_IN', 'AJUSTE_POSITIVO') THEN rs.cantidad
                       ELSE -rs.cantidad END) > 0;
       ```
    """

    async def get_consolidated_alerts(
        self,
        tenant_schema: str,
        bodega_ids: Sequence[int] | None = None,
        area_operativa_id: int | None = None,
        tipo_filtro: str | None = None,
        dias_fefo_umbral: int = 30,
        reference_date: date | None = None,
    ) -> AlertsConsolidatedSummary:
        """
        Obtiene el resumen consolidado de alertas ejecutando consultas agregadas en < 20ms.
        """
        ...

    async def get_badge_summary(
        self,
        tenant_schema: str,
        bodega_ids: Sequence[int] | None = None,
    ) -> AlertBadgeSummary:
        """
        Obtiene el conteo analítico liviano para el Sidebar institucional en < 5ms.
        """
        ...


__all__ = [
    "MONEY_QUANT",
    "PERCENT_QUANT",
    "QTY_QUANT",
    "ZERO",
    "AlertBadgeSummary",
    "AlertSeverity",
    "AlertType",
    "AlertsConsolidatedSummary",
    "AlertsRepositoryInterface",
    "CriticalStockAlert",
    "ExpiredLotAlert",
    "ExpiryUrgency",
    "StockHealthRatio",
    "UpcomingExpiryAlert",
]
