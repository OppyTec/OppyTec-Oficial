#!/usr/bin/env python3
"""
tests/panel-admin-oppytec/run_e2e.py
Script CLI ejecutor de la Suite E2E Playwright de OppyTec v2.0.

Uso:
    python run_e2e.py --headless               # Ejecución rápida en segundo plano (CI/CD)
    python run_e2e.py --visual                 # Ejecución visual en Chromium con slow_mo=500ms
    python run_e2e.py --flow 1                 # Ejecuta solo test_001_superadmin_auth_flow.py
    python run_e2e.py --flow 2 --visual        # Ejecuta flujo 2 en modo visual
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parents[1] if len(CURRENT_DIR.parents) >= 2 else CURRENT_DIR


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Ejecutor de Pruebas E2E Playwright para Panel Administrativo OppyTec v2.0"
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--visual",
        action="store_true",
        help="Abre el navegador Chromium en modo visual con slow_mo de 500ms.",
    )
    group.add_argument(
        "--headless",
        action="store_true",
        default=True,
        help="Ejecuta en modo sin cabeza (headless) de alto rendimiento (default).",
    )
    parser.add_argument(
        "--flow",
        type=int,
        choices=[1, 2, 3, 4, 5, 6],
        help="Número correlativo de flujo específico a ejecutar (1..6).",
    )
    parser.add_argument(
        "--keep-snapshot",
        action="store_true",
        help="No borra el snapshot de base de datos generado al inicio.",
    )

    args = parser.parse_args()

    # Configurar variables de entorno según CLI
    env = os.environ.copy()
    if args.visual:
        env["PLAYWRIGHT_HEADLESS"] = "false"
        env["PLAYWRIGHT_SLOW_MO"] = "500"
        print("[RUNNER] Modo VISUAL activado (Chromium con slow_mo=500ms).")
    else:
        env["PLAYWRIGHT_HEADLESS"] = "true"
        env["PLAYWRIGHT_SLOW_MO"] = "0"
        print("[RUNNER] Modo HEADLESS activado.")

    # Determinar archivos a ejecutar
    flow_map = {
        1: "test_001_superadmin_auth_flow.py",
        2: "test_002_admin_operators_flow.py",
        3: "test_003_holdings_management_flow.py",
        4: "test_004_legal_entities_flow.py",
        5: "test_005_commercial_plans_flow.py",
        6: "test_006_tenants_onboarding_flow.py",
    }

    if args.flow:
        target_file = CURRENT_DIR / flow_map[args.flow]
        test_targets = [str(target_file)]
        print(f"[RUNNER] Ejecutando exclusivamente Flujo #{args.flow}: {target_file.name}")
    else:
        test_targets = [str(CURRENT_DIR)]
        print("[RUNNER] Ejecutando suite completa correlativa (Flujos 1 a 3).")

    # Comando pytest aislado
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "-c",
        str(CURRENT_DIR / "pytest.ini"),
        *test_targets,
    ]

    print(f"[RUNNER] Comando: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=str(CURRENT_DIR), env=env)
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
