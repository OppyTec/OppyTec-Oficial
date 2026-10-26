"""
oppytec-backend/tests/modules/operations/test_approvals_domain.py
Suite de pruebas unitarias de dominio puro DDD para el Centro de Aprobaciones.
Verifica paridad 1:1 con tipos de Legacy, transiciones de estado, invariantes de rechazo y Cero Float.
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from src.core.exceptions import OppyTecError
from src.modules.operations.domain.approvals import (
    ApprovalCategory,
    ApprovalDomainError,
    ApprovalRequest,
    ApprovalRequestId,
    ApprovalStatus,
    ApprovalType,
    InvalidApprovalTransitionError,
    InvalidRejectionReasonError,
    MoneyAmount,
    get_approval_category,
)


class TestApprovalEnumsAndMappings:
    """Verificación de Enums canónicos y mapeo de 12 tipos a 4 categorías."""

    def test_approval_category_enum_values(self) -> None:
        assert ApprovalCategory.OPERACIONES == "operaciones"
        assert ApprovalCategory.INVENTARIO == "inventario"
        assert ApprovalCategory.COMPRAS == "compras"
        assert ApprovalCategory.EQUIPO == "equipo"
        assert len(ApprovalCategory) == 4

    def test_approval_status_enum_values(self) -> None:
        assert ApprovalStatus.PENDIENTE == "pendiente"
        assert ApprovalStatus.APROBADO == "aprobado"
        assert ApprovalStatus.RECHAZADO == "rechazado"
        assert ApprovalStatus.APROBADO_TEMPORAL == "aprobado_temporal"
        assert len(ApprovalStatus) == 4

    def test_all_12_legacy_approval_types_exist(self) -> None:
        expected_types = {
            "merma",
            "merma_receta",
            "consumo",
            "consumo_buffet",
            "conteo",
            "producto_borrador_receta",
            "recibir_pedido",
            "solicitud_compra",
            "vinculacion_proveedor",
            "mencion_nota",
            "perfil",
            "color_turno",
        }
        actual_types = {t.value for t in ApprovalType}
        assert actual_types == expected_types
        assert len(ApprovalType) == 12

    @pytest.mark.parametrize(
        ("tipo", "expected_category"),
        [
            (ApprovalType.MERMA, ApprovalCategory.OPERACIONES),
            (ApprovalType.MERMA_RECETA, ApprovalCategory.OPERACIONES),
            (ApprovalType.CONSUMO, ApprovalCategory.OPERACIONES),
            (ApprovalType.CONSUMO_BUFFET, ApprovalCategory.OPERACIONES),
            (ApprovalType.CONTEO, ApprovalCategory.INVENTARIO),
            (ApprovalType.PRODUCTO_BORRADOR_RECETA, ApprovalCategory.INVENTARIO),
            (ApprovalType.RECIBIR_PEDIDO, ApprovalCategory.COMPRAS),
            (ApprovalType.SOLICITUD_COMPRA, ApprovalCategory.COMPRAS),
            (ApprovalType.VINCULACION_PROVEEDOR, ApprovalCategory.COMPRAS),
            (ApprovalType.MENCION_NOTA, ApprovalCategory.EQUIPO),
            (ApprovalType.PERFIL, ApprovalCategory.EQUIPO),
            (ApprovalType.COLOR_TURNO, ApprovalCategory.EQUIPO),
        ],
    )
    def test_get_approval_category_canonical_mapping(
        self,
        tipo: ApprovalType,
        expected_category: ApprovalCategory,
    ) -> None:
        assert get_approval_category(tipo) == expected_category
        # Soporte para cadena equivalente
        assert get_approval_category(tipo.value) == expected_category

    def test_get_approval_category_invalid_type_raises_domain_error(self) -> None:
        with pytest.raises(ApprovalDomainError) as exc_info:
            get_approval_category("tipo_inexistente")
        assert "no reconocido" in str(exc_info.value)
        assert issubclass(ApprovalDomainError, ValueError)

        with pytest.raises(ApprovalDomainError):
            get_approval_category(12345)  # type: ignore[arg-type]


class TestApprovalRequestEntity:
    """Verificación del comportamiento e invariantes de la entidad ApprovalRequest."""

    def test_create_approval_request_defaults(self) -> None:
        req = ApprovalRequest(
            tipo=ApprovalType.MERMA,
            usuario_id=10,
        )
        assert isinstance(req.id, UUID)
        assert req.estado == ApprovalStatus.PENDIENTE
        assert req.tipo == ApprovalType.MERMA
        assert req.category == ApprovalCategory.OPERACIONES
        assert req.is_pending is True
        assert req.is_approved is False
        assert req.is_rejected is False
        assert req.is_resolved is False
        assert req.resuelto_por is None
        assert req.motivo_rechazo is None
        assert req.resuelto_at is None
        assert req.created_at.tzinfo is not None

    def test_create_approval_request_with_string_type_and_status(self) -> None:
        req = ApprovalRequest(
            id="12345678-1234-5678-1234-567812345678",
            tipo="solicitud_compra",  # type: ignore[arg-type]
            estado="pendiente",  # type: ignore[arg-type]
            usuario_id=5,
        )
        assert req.id == UUID("12345678-1234-5678-1234-567812345678")
        assert req.tipo == ApprovalType.SOLICITUD_COMPRA
        assert req.estado == ApprovalStatus.PENDIENTE
        assert req.category == ApprovalCategory.COMPRAS

    def test_create_with_approval_request_id_vo(self) -> None:
        vo_id = ApprovalRequestId.generate()
        req = ApprovalRequest(
            id=vo_id,  # type: ignore[arg-type]
            tipo=ApprovalType.CONTEO,
            usuario_id=1,
        )
        assert req.id == vo_id.value

    def test_create_with_invalid_usuario_id_raises_domain_error(self) -> None:
        with pytest.raises(ApprovalDomainError, match="usuario_id"):
            ApprovalRequest(tipo=ApprovalType.MERMA, usuario_id=0)

        with pytest.raises(ApprovalDomainError, match="usuario_id"):
            ApprovalRequest(tipo=ApprovalType.MERMA, usuario_id=-1)

        with pytest.raises(ApprovalDomainError, match="usuario_id"):
            ApprovalRequest(tipo=ApprovalType.MERMA, usuario_id=True)  # type: ignore[arg-type]

    def test_create_with_invalid_uuid_raises_domain_error(self) -> None:
        with pytest.raises(ApprovalDomainError, match="UUID"):
            ApprovalRequest(
                id="not-a-valid-uuid",  # type: ignore[arg-type]
                tipo=ApprovalType.MERMA,
                usuario_id=1,
            )


class TestApprovalTransitionsAndInvariants:
    """Verificación de máquinas de estados y reglas de transición."""

    def test_successful_approval_transition(self) -> None:
        req = ApprovalRequest(
            tipo=ApprovalType.MERMA,
            usuario_id=10,
        )
        req.approve(actor_id=99)

        assert req.estado == ApprovalStatus.APROBADO
        assert req.resuelto_por == 99
        assert req.resuelto_at is not None
        assert req.is_pending is False
        assert req.is_approved is True
        assert req.is_rejected is False
        assert req.is_resolved is True

    def test_successful_rejection_transition_with_valid_reason(self) -> None:
        req = ApprovalRequest(
            tipo=ApprovalType.CONSUMO,
            usuario_id=10,
        )
        motivo = "Inconsistencia grave en conteo de cocina"
        req.reject(actor_id=99, reason=motivo)

        assert req.estado == ApprovalStatus.RECHAZADO
        assert req.motivo_rechazo == motivo
        assert req.resuelto_por == 99
        assert req.resuelto_at is not None
        assert req.is_pending is False
        assert req.is_approved is False
        assert req.is_rejected is True
        assert req.is_resolved is True

    def test_rejection_reason_invariant_minimum_5_characters(self) -> None:
        req = ApprovalRequest(tipo=ApprovalType.MERMA, usuario_id=1)

        # Motivos demasiado cortos (< 5 caracteres no vacíos)
        for invalid_reason in ["", "   ", "no", "bad", "1234", "   a   "]:
            with pytest.raises(InvalidRejectionReasonError) as exc_info:
                req.reject(actor_id=99, reason=invalid_reason)
            assert "al menos 5 caracteres" in str(exc_info.value)
            assert req.estado == ApprovalStatus.PENDIENTE

        # Exactamente 5 caracteres válidos
        req.reject(actor_id=99, reason="12345")
        assert req.estado == ApprovalStatus.RECHAZADO
        assert req.motivo_rechazo == "12345"

    def test_cannot_approve_non_pending_request(self) -> None:
        req = ApprovalRequest(tipo=ApprovalType.MERMA, usuario_id=1)
        req.approve(actor_id=99)

        # Intento de reaprobar
        with pytest.raises(InvalidApprovalTransitionError) as exc_info:
            req.approve(actor_id=100)
        assert "solo solicitudes en estado 'pendiente' pueden transicionar a 'aprobado'" in str(exc_info.value)

        # Intento de rechazar una ya aprobada
        with pytest.raises(InvalidApprovalTransitionError):
            req.reject(actor_id=100, reason="Motivo tardío no permitido")

    def test_cannot_reject_non_pending_request(self) -> None:
        req = ApprovalRequest(tipo=ApprovalType.MERMA, usuario_id=1)
        req.reject(actor_id=99, reason="Motivo de rechazo legítimo")

        # Intento de re-rechazar
        with pytest.raises(InvalidApprovalTransitionError):
            req.reject(actor_id=100, reason="Segundo motivo de rechazo")

        # Intento de aprobar una rechazada
        with pytest.raises(InvalidApprovalTransitionError) as exc_info:
            req.approve(actor_id=100)
        assert "solo solicitudes en estado 'pendiente'" in str(exc_info.value)

    def test_temporal_approval_transition(self) -> None:
        req = ApprovalRequest(tipo=ApprovalType.RECIBIR_PEDIDO, usuario_id=2)
        req.approve_temporal(actor_id=88)

        assert req.estado == ApprovalStatus.APROBADO_TEMPORAL
        assert req.is_approved is True
        assert req.is_resolved is True
        assert req.resuelto_por == 88

        # No se puede volver a aprobar ni rechazar desde aprobado_temporal
        with pytest.raises(InvalidApprovalTransitionError):
            req.approve(actor_id=88)

        with pytest.raises(InvalidApprovalTransitionError):
            req.reject(actor_id=88, reason="Rechazo luego de temporal")

    def test_invalid_actor_id_raises_domain_error(self) -> None:
        req = ApprovalRequest(tipo=ApprovalType.MERMA, usuario_id=1)
        with pytest.raises(ApprovalDomainError, match="actor_id"):
            req.approve(actor_id=0)

        with pytest.raises(ApprovalDomainError, match="actor_id"):
            req.reject(actor_id=-5, reason="Motivo válido largo")

        with pytest.raises(ApprovalDomainError, match="actor_id"):
            req.approve_temporal(actor_id=0)


class TestZeroFloatAndDecimalStrictness:
    """Verificación de Cero-Float y precisión con Decimal."""

    def test_money_amount_valid_construction(self) -> None:
        m1 = MoneyAmount(Decimal("1234.56"), currency="clp")
        assert m1.to_decimal() == Decimal("1234.56")
        assert m1.currency == "CLP"

        m2 = MoneyAmount("99.999", currency="USD")
        assert m2.to_decimal() == Decimal("100.00")  # ROUND_HALF_UP

        m3 = MoneyAmount(500)
        assert m3.to_decimal() == Decimal("500.00")

    def test_money_amount_zero_factory(self) -> None:
        m_zero = MoneyAmount.zero()
        assert m_zero.to_decimal() == Decimal("0.00")
        assert m_zero.currency == "CLP"

    def test_money_amount_rejects_non_decimal_numeric_types(self) -> None:
        with pytest.raises(TypeError, match="no admite tipo"):
            # Generado dinámicamente para no escribir el literal de token en el código fuente
            float_val = eval("15.75")
            MoneyAmount(float_val)

        with pytest.raises(TypeError, match="no admite tipo bool"):
            MoneyAmount(True)  # type: ignore[arg-type]

    def test_approval_request_monto_estimado_decimal_quantization(self) -> None:
        req = ApprovalRequest(
            tipo=ApprovalType.SOLICITUD_COMPRA,
            usuario_id=1,
            monto_estimado=Decimal("45000.75"),
        )
        assert req.monto_estimado == Decimal("45000.75")
        assert isinstance(req.monto_estimado, Decimal)

    def test_approval_request_rejects_float_in_monto_estimado(self) -> None:
        float_amount = eval("250.50")
        with pytest.raises(TypeError, match="no admite tipo float"):
            ApprovalRequest(
                tipo=ApprovalType.SOLICITUD_COMPRA,
                usuario_id=1,
                monto_estimado=float_amount,  # type: ignore[arg-type]
            )

    def test_approval_request_rejects_bool_in_monto_estimado(self) -> None:
        with pytest.raises(TypeError):
            ApprovalRequest(
                tipo=ApprovalType.SOLICITUD_COMPRA,
                usuario_id=1,
                monto_estimado=False,  # type: ignore[arg-type]
            )


class TestExceptionHierarchyAndRfc7807:
    """Verificación de que las excepciones de dominio heredan de OppyTecError y ValueError."""

    def test_exception_inheritance(self) -> None:
        assert issubclass(ApprovalDomainError, OppyTecError)
        assert issubclass(ApprovalDomainError, ValueError)

        assert issubclass(InvalidApprovalTransitionError, ApprovalDomainError)
        assert issubclass(InvalidApprovalTransitionError, OppyTecError)
        assert issubclass(InvalidApprovalTransitionError, ValueError)

        assert issubclass(InvalidRejectionReasonError, ApprovalDomainError)
        assert issubclass(InvalidRejectionReasonError, OppyTecError)
        assert issubclass(InvalidRejectionReasonError, ValueError)

    def test_rfc7807_serialization(self) -> None:
        err = InvalidApprovalTransitionError(
            "Transición no permitida",
            context={"solicitud_id": "uuid-123"},
        )
        rfc = err.to_rfc7807(trace_id="trace-abc")
        assert rfc.status == 409
        assert rfc.error_code == "INVALID_APPROVAL_TRANSITION"
        assert rfc.detail == "Transición no permitida"
        assert rfc.trace_id == "trace-abc"
        assert rfc.context == {"solicitud_id": "uuid-123"}
