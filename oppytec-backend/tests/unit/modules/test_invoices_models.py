"""
oppytec-backend/tests/unit/modules/test_invoices_models.py
Pruebas Unitarias para los Modelos ORM SQLAlchemy 2.0 Async del Módulo de Facturas
y verificación de la migración correlativa Alembic 0016.
"""
from __future__ import annotations

import ast
import uuid
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import inspect

from src.modules.invoices.infrastructure.models import (
    Base,
    InvoiceAuditFlagModel,
    InvoiceLineItemModel,
    InvoiceModel,
    SupplierProductAliasModel,
)

pytestmark = pytest.mark.unit


def test_invoice_model_attributes_and_defaults() -> None:
    """Verifica que InvoiceModel posea todos los campos especificados con tipos y defaults."""
    tenant_id = uuid.uuid4()
    invoice = InvoiceModel(
        tenant_id=tenant_id,
        file_name="factura_proveedor_123.pdf",
        file_type="pdf",
        vendor_name="Distribuidora Gastronómica SpA",
        vendor_tax_id="76192083-9",
        invoice_number="F-9988",
    )

    assert invoice.tenant_id == tenant_id
    assert invoice.file_name == "factura_proveedor_123.pdf"
    assert invoice.file_type == "pdf"
    assert invoice.vendor_name == "Distribuidora Gastronómica SpA"
    assert invoice.currency == "CLP"
    assert invoice.dte_type == 33
    assert invoice.status == "PENDING"
    assert invoice.exchange_rate == Decimal("1.0000")
    assert invoice.net_amount == Decimal("0.0000")
    assert invoice.tax_amount == Decimal("0.0000")
    assert invoice.total_amount == Decimal("0.0000")
    assert invoice.gemini_tokens_used == 0
    assert invoice.gemini_cost_usd == Decimal("0.000000")
    assert invoice.is_stock_ingested is False
    assert InvoiceModel.__tablename__ == "invoices"


def test_invoice_line_item_model_attributes_and_defaults() -> None:
    """Verifica InvoiceLineItemModel y su vinculación con la factura."""
    invoice_id = uuid.uuid4()
    catalog_id = uuid.uuid4()
    bodega_id = 1

    line = InvoiceLineItemModel(
        invoice_id=invoice_id,
        line_number=1,
        raw_description="Caja Pechuga de Pollo 18kg",
        quantity=Decimal("2.0000"),
        unit="caja",
        unit_price=Decimal("45000.0000"),
        line_total=Decimal("90000.0000"),
        vat_rate=Decimal("19.00"),
        matched_catalog_item_id=catalog_id,
        packaging_factor=Decimal("18.0000"),
        calculated_stock_qty=Decimal("36.0000"),
        inventory_unit="kg",
        inventory_unit_cost=Decimal("2500.0000"),
        target_bodega_id=bodega_id,
    )

    assert line.invoice_id == invoice_id
    assert line.raw_description == "Caja Pechuga de Pollo 18kg"
    assert line.quantity == Decimal("2.0000")
    assert line.packaging_factor == Decimal("18.0000")
    assert line.calculated_stock_qty == Decimal("36.0000")
    assert line.inventory_unit == "kg"
    assert line.inventory_unit_cost == Decimal("2500.0000")
    assert line.target_bodega_id == 1
    assert line.match_status == "UNMATCHED"
    assert InvoiceLineItemModel.__tablename__ == "invoice_lines"


def test_supplier_product_alias_model_attributes() -> None:
    """Verifica SupplierProductAliasModel para el mapeo semántico de productos."""
    tenant_id = uuid.uuid4()
    supplier_id = uuid.uuid4()
    catalog_id = uuid.uuid4()

    alias = SupplierProductAliasModel(
        tenant_id=tenant_id,
        supplier_id=supplier_id,
        raw_vendor_product_name="PECH DESH CONGELADA 18KG",
        catalog_item_id=catalog_id,
        default_packaging_factor=Decimal("18.0000"),
        default_inventory_unit="kg",
        is_verified=True,
        times_used=3,
    )

    assert alias.tenant_id == tenant_id
    assert alias.supplier_id == supplier_id
    assert alias.raw_vendor_product_name == "PECH DESH CONGELADA 18KG"
    assert alias.catalog_item_id == catalog_id
    assert alias.default_packaging_factor == Decimal("18.0000")
    assert alias.default_inventory_unit == "kg"
    assert alias.is_verified is True
    assert alias.times_used == 3
    assert SupplierProductAliasModel.__tablename__ == "supplier_product_aliases"


def test_invoice_audit_flag_model_attributes() -> None:
    """Verifica InvoiceAuditFlagModel y su registro de discrepancias."""
    invoice_id = uuid.uuid4()
    flag = InvoiceAuditFlagModel(
        invoice_id=invoice_id,
        severity="CRITICAL",
        rule_code="TOTAL_NET_MISMATCH",
        message="Discrepancia contable: Total != Neto + IVA",
    )

    assert flag.invoice_id == invoice_id
    assert flag.severity == "CRITICAL"
    assert flag.rule_code == "TOTAL_NET_MISMATCH"
    assert "Discrepancia" in flag.message
    assert InvoiceAuditFlagModel.__tablename__ == "invoice_audit_flags"


def test_relationships_cascade_wiring() -> None:
    """Verifica las relaciones bidireccionales entre InvoiceModel y sus líneas/flags."""
    invoice = InvoiceModel(
        tenant_id=uuid.uuid4(),
        file_name="factura.pdf",
        file_type="pdf",
    )
    line = InvoiceLineItemModel(
        line_number=1,
        raw_description="Item 1",
        quantity=Decimal("1.0000"),
        unit_price=Decimal("1000.0000"),
        line_total=Decimal("1000.0000"),
    )
    flag = InvoiceAuditFlagModel(
        severity="INFO",
        rule_code="INFO_RULE",
        message="Información de validación",
    )

    invoice.lines.append(line)
    invoice.audit_flags.append(flag)

    assert len(invoice.lines) == 1
    assert invoice.lines[0].raw_description == "Item 1"
    assert len(invoice.audit_flags) == 1
    assert invoice.audit_flags[0].rule_code == "INFO_RULE"


def test_alembic_0016_structure_and_scope() -> None:
    """Verifica que la migración 0016 cumpla con la linealidad y las reglas de Alembic."""
    migration_file = (
        Path(__file__).parents[3]
        / "alembic"
        / "versions"
        / "0016_tenant_invoices_dte_and_supplier_aliases.py"
    )
    assert migration_file.exists(), f"Migración {migration_file} no encontrada"

    content = migration_file.read_text(encoding="utf-8")
    tree = ast.parse(content, filename=str(migration_file))

    assignments = {}
    functions = set()
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and isinstance(node.value, ast.Constant):
                    assignments[target.id] = node.value.value
        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name) and isinstance(node.value, ast.Constant):
                assignments[node.target.id] = node.value.value
        elif isinstance(node, ast.FunctionDef):
            functions.add(node.name)

    assert assignments.get("revision") == "0016_tenant_invoices_dte_and_supplier_aliases"
    assert assignments.get("down_revision") == "0015_tenant_actividades_triada_enriquecida"
    assert assignments.get("migration_scope") == "tenant"
    assert "upgrade" in functions
    assert "downgrade" in functions
    assert "_apply_tenant_upgrade_to_schema" in functions
    assert "_apply_tenant_downgrade_to_schema" in functions
