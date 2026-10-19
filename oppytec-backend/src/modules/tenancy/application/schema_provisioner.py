"""
oppytec-backend/src/modules/tenancy/application/schema_provisioner.py
Servicio de aprovisionamiento atómico de esquemas `tenant_<slug>` verificando cardinalidad `1:1`
con `LegalEntity` y prevención absoluta de SQL Injection mediante `validate_tenant_schema_name`.
"""
from __future__ import annotations

from dataclasses import dataclass

from src.core.bootstrap import TENANT_BASE_ROLES, RoleSeedSpec
from src.core.database import validate_tenant_schema_name
from src.core.exceptions import CrossTenantAccessError, OppyTecError
from src.modules.tenancy.domain.quotas import (
    TenantHierarchyAssignment,
    validate_holding_legal_entity_tenant_cardinality,
)


@dataclass(frozen=True)
class ProvisionedTenantSchema:
    """Manifiesto de un esquema `tenant_*` aprovisionado con sus sentencias DDL y semilla RBAC."""

    holding_id: str
    legal_entity_id: str
    tenant_id: str
    schema_name: str
    ddl_statements: tuple[str, ...]
    seeded_roles: tuple[RoleSeedSpec, ...]


class TenantSchemaProvisioner:
    """
    Aprovisiona esquemas aislados `tenant_<slug>` validando la relación `1:1` entre
    `LegalEntity` y `Tenant` y el aislamiento Cross-Holding.
    """

    def __init__(self) -> None:
        self._assignments: list[TenantHierarchyAssignment] = []

    def provision_tenant_schema(
        self,
        *,
        holding_id: str,
        legal_entity_id: str,
        tenant_id: str,
        schema_name: str,
    ) -> ProvisionedTenantSchema:
        """
        Valida `schema_name` y la cardinalidad `Holding -> LegalEntity (1:1) -> Tenant`
        antes de registrar el esquema y generar el plan DDL.
        """
        valid_schema = validate_tenant_schema_name(schema_name)
        candidate = TenantHierarchyAssignment(
            holding_id=holding_id,
            legal_entity_id=legal_entity_id,
            tenant_id=tenant_id,
            schema_name=valid_schema,
        )
        valid_card, reason_code = validate_holding_legal_entity_tenant_cardinality(
            [*self._assignments, candidate]
        )
        if not valid_card:
            if reason_code == "CROSS_HOLDING_TENANT_VIOLATION":
                raise CrossTenantAccessError(
                    f"Tenant '{tenant_id}' cannot be bound across different Holdings.",
                    i18n_key="tenancy:errors.cross_holding_forbidden",
                )
            raise OppyTecError(
                f"Tenant provisioning failed ({reason_code}) for schema '{valid_schema}'.",
                i18n_key="tenancy:errors.invalid_tenant_cardinality",
                status_code=409,
                error_code=reason_code,
            )

        self._assignments.append(candidate)
        ddl = (
            f'CREATE SCHEMA IF NOT EXISTS "{valid_schema}";',
            f'SET LOCAL search_path TO "{valid_schema}", public;',
        )
        return ProvisionedTenantSchema(
            holding_id=holding_id,
            legal_entity_id=legal_entity_id,
            tenant_id=tenant_id,
            schema_name=valid_schema,
            ddl_statements=ddl,
            seeded_roles=TENANT_BASE_ROLES,
        )

    def assert_same_holding_access(
        self,
        *,
        user_holding_id: str,
        target_tenant_id: str,
    ) -> TenantHierarchyAssignment:
        """Verifica que el `target_tenant_id` pertenezca exactamente al `user_holding_id`."""
        for item in self._assignments:
            if item.tenant_id == target_tenant_id:
                if item.holding_id != user_holding_id:
                    raise CrossTenantAccessError(
                        f"User from holding '{user_holding_id}' cannot access tenant '{target_tenant_id}' "
                        f"owned by holding '{item.holding_id}'.",
                        i18n_key="tenancy:errors.cross_tenant_forbidden",
                    )
                return item
        raise CrossTenantAccessError(
            f"Tenant '{target_tenant_id}' is not registered.",
            i18n_key="tenancy:errors.tenant_not_found",
            status_code=404,
        )
