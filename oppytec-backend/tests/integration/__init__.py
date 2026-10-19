"""
Suite de Pruebas de Integración de OppyTec SaaS v2.0 (`tests/integration/`).
Verifica aislamiento físico Multi-Tenant (`SET LOCAL search_path`), Soft-Delete con
liberación inmediata de cupos + Kill-Switch de sesión, acceso transversal por Holding
y paridad matemática 100% con `OppyTec-Legacy` en los 10 módulos de negocio.
"""
from __future__ import annotations
