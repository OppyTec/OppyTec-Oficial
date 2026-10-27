"""
oppytec-backend/tests/modules/recipes/test_recipe_cycle_detection.py
Suite de pruebas exhaustivas para detección de ciclos en grafos acíclicos dirigidos (DAG):
- Grafos DAG complejos, diamantes válidos, diamantes anidados y bosques disjuntos.
- Rechazo estricto de auto-referencias directas (A -> A) e indirectas profundas (A -> B -> C -> D -> A).
- Ciclos en sub-ramas no adyacentes a la raíz (A -> B -> C -> D -> C).
- Invariantes de would_create_cycle y find_all_cycles.
- Integración transaccional con RecipeService garantizando atomicidad y ausencia de mutaciones ante ciclos.
"""
from __future__ import annotations

from decimal import Decimal

import pytest

from src.modules.recipes.application.option_group_service import OptionGroupService
from src.modules.recipes.application.recipe_service import (
    RecipeIngredientDTO,
    RecipeService,
)
from src.modules.recipes.domain.cycle_detector import (
    check_recipe_cycles,
    find_all_cycles,
    would_create_cycle,
)
from src.modules.recipes.domain.exceptions import RecipeCycleError

pytestmark = pytest.mark.unit


# ==============================================================================
# 1. PRUEBAS DE GRAFOS DAG VÁLIDOS (ACÍCLICOS COMPLEJOS)
# ==============================================================================

class TestValidComplexDAGs:
    """Verificación de que grafos complejos sin ciclos son aceptados sin falsos positivos."""

    def test_single_linear_chain(self) -> None:
        """Cadena lineal simple: 1 -> 2 -> 3 -> 4 -> 5."""
        tree = {
            1: [2],
            2: [3],
            3: [4],
            4: [5],
            5: [],
        }
        check_recipe_cycles(1, tree)

    def test_classic_diamond_dag(self) -> None:
        """
        Diamante clásico (ambos caminos convergen en un nodo común sin ciclo):
            1
           / \\
          2   3
           \\ /
            4
        """
        tree = {
            1: [2, 3],
            2: [4],
            3: [4],
            4: [],
        }
        check_recipe_cycles(1, tree)

    def test_nested_dual_diamond_dag(self) -> None:
        """
        Doble diamante anidado (múltiples caminos hacia un nodo terminal común):
             1
            / \\
           2   3
          / \\ / \\
         4   5   6
          \\ |  /
             7
        """
        tree = {
            1: [2, 3],
            2: [4, 5],
            3: [5, 6],
            4: [7],
            5: [7],
            6: [7],
            7: [],
        }
        check_recipe_cycles(1, tree)

    def test_wide_star_dag(self) -> None:
        """Grafo tipo abanico/estrella: una receta maestra utiliza 50 sub-recetas base."""
        children = list(range(2, 52))
        tree = {1: children}
        for c in children:
            tree[c] = []
        check_recipe_cycles(1, tree)

    def test_deep_binary_tree_dag(self) -> None:
        """Árbol binario balanceado de 5 niveles (31 nodos) sin ciclos."""
        tree: dict[int, list[int]] = {}
        for i in range(1, 16):
            tree[i] = [2 * i, 2 * i + 1]
        for i in range(16, 32):
            tree[i] = []
        check_recipe_cycles(1, tree)

    def test_multiple_shared_subrecipes_in_same_dish(self) -> None:
        """
        Caso realista gourmet: Una salsa base (nodo 10) es usada por:
        - El relleno (nodo 2)
        - El marinado (nodo 3)
        - La cobertura (nodo 4)
        Y el plato final (nodo 1) usa 2, 3, 4 y directamente 10.
        """
        tree = {
            1: [2, 3, 4, 10],
            2: [10],
            3: [10],
            4: [10],
            10: [],
        }
        check_recipe_cycles(1, tree)


# ==============================================================================
# 2. RECHAZO DE CICLOS SIMPLES Y PROFUNDOS
# ==============================================================================

class TestRecipeCycleRejection:
    """Verificación de que todo tipo de ciclos son interceptados con la ruta exacta."""

    def test_direct_self_cycle_a_to_a(self) -> None:
        """Auto-referencia directa: 1 -> 1."""
        tree = {1: [1]}
        with pytest.raises(RecipeCycleError) as exc_info:
            check_recipe_cycles(1, tree)
        assert "1 -> 1" in str(exc_info.value)

    def test_cycle_2_nodes_a_to_b_to_a(self) -> None:
        """Ciclo corto de 2 nodos: 1 -> 2 -> 1."""
        tree = {1: [2], 2: [1]}
        with pytest.raises(RecipeCycleError) as exc_info:
            check_recipe_cycles(1, tree)
        assert "1 -> 2 -> 1" in str(exc_info.value)

    def test_cycle_3_nodes_a_to_b_to_c_to_a(self) -> None:
        """Ciclo triangular de 3 nodos: 1 -> 2 -> 3 -> 1."""
        tree = {
            1: [2],
            2: [3],
            3: [1],
        }
        with pytest.raises(RecipeCycleError) as exc_info:
            check_recipe_cycles(1, tree)
        assert "1 -> 2 -> 3 -> 1" in str(exc_info.value)

    def test_deep_cycle_4_nodes_a_to_b_to_c_to_d_to_a(self) -> None:
        """Ciclo profundo de 4 nodos: A -> B -> C -> D -> A."""
        tree = {
            "A": ["B"],
            "B": ["C"],
            "C": ["D"],
            "D": ["A"],
        }
        with pytest.raises(RecipeCycleError) as exc_info:
            check_recipe_cycles("A", tree)
        assert "A -> B -> C -> D -> A" in str(exc_info.value)

    def test_deep_cycle_8_nodes(self) -> None:
        """Ciclo largo de 8 nodos: 1 -> 2 -> 3 -> 4 -> 5 -> 6 -> 7 -> 8 -> 1."""
        tree = {
            1: [2],
            2: [3],
            3: [4],
            4: [5],
            5: [6],
            6: [7],
            7: [8],
            8: [1],
        }
        with pytest.raises(RecipeCycleError) as exc_info:
            check_recipe_cycles(1, tree)
        assert "1 -> 2 -> 3 -> 4 -> 5 -> 6 -> 7 -> 8 -> 1" in str(exc_info.value)

    def test_cycle_in_deep_subbranch_not_involving_root(self) -> None:
        """
        Ciclo en sub-rama:
        La raíz es 100, que llama a 200.
        200 llama a 300.
        300 forma un ciclo con 400 y 500: 300 -> 400 -> 500 -> 300.
        El error debe reportar el ciclo interno y no incluir a 100 ni 200 en el bucle cerrado.
        """
        tree = {
            100: [200],
            200: [300],
            300: [400],
            400: [500],
            500: [300],
        }
        with pytest.raises(RecipeCycleError) as exc_info:
            check_recipe_cycles(100, tree)
        assert "300 -> 400 -> 500 -> 300" in str(exc_info.value)

    def test_cycle_on_diamond_reconnection(self) -> None:
        """
        Diamante con una conexión inversa que causa un ciclo:
        1 -> [2, 3], 2 -> 4, 3 -> 4, pero 4 -> 2.
        """
        tree = {
            1: [2, 3],
            2: [4],
            3: [4],
            4: [2],  # Ciclo 2 -> 4 -> 2
        }
        with pytest.raises(RecipeCycleError) as exc_info:
            check_recipe_cycles(1, tree)
        assert "2 -> 4 -> 2" in str(exc_info.value)


# ==============================================================================
# 3. PRUEBAS DE would_create_cycle Y find_all_cycles
# ==============================================================================

class TestCycleHelperFunctions:
    """Verificación de helpers predictivos y utilitarios globales de grafos."""

    def test_would_create_cycle_self_reference(self) -> None:
        """Cualquier auto-referencia x -> x siempre retorna True."""
        tree: dict[int, list[int]] = {1: [2], 2: []}
        assert would_create_cycle(1, 1, tree) is True
        assert would_create_cycle(2, 2, tree) is True
        assert would_create_cycle(99, 99, tree) is True

    def test_would_create_cycle_direct_reverse(self) -> None:
        """Si existe 1 -> 2, intentar agregar 2 -> 1 retorna True."""
        tree = {1: [2], 2: []}
        assert would_create_cycle(2, 1, tree) is True
        # Agregar 1 -> 3 es seguro
        assert would_create_cycle(1, 3, tree) is False

    def test_would_create_cycle_deep_indirect(self) -> None:
        """En cadena 1 -> 2 -> 3 -> 4, añadir 4 -> 1 retorna True."""
        tree = {
            1: [2],
            2: [3],
            3: [4],
            4: [],
        }
        assert would_create_cycle(4, 1, tree) is True
        assert would_create_cycle(4, 2, tree) is True
        assert would_create_cycle(4, 3, tree) is True
        # En cambio, agregar atajo hacia adelante 1 -> 4 retorna False
        assert would_create_cycle(1, 4, tree) is False
        # O agregar una nueva hoja 4 -> 5 retorna False
        assert would_create_cycle(4, 5, tree) is False

    def test_would_create_cycle_does_not_mutate_tree(self) -> None:
        """would_create_cycle no debe mutar el grafo original."""
        tree = {1: [2], 2: []}
        tree_copy = {1: [2], 2: []}
        res = would_create_cycle(2, 1, tree)
        assert res is True
        assert tree == tree_copy

    def test_find_all_cycles_acyclic_graph_returns_empty(self) -> None:
        """Un grafo DAG acíclico retorna lista vacía de ciclos."""
        tree = {
            1: [2, 3],
            2: [4],
            3: [4],
            4: [],
        }
        cycles = find_all_cycles(tree)
        assert cycles == []

    def test_find_all_cycles_multiple_independent_cycles(self) -> None:
        """Encuentra múltiples ciclos independientes en distintos componentes."""
        graph = {
            # Componente 1: ciclo 1 <-> 2
            1: [2],
            2: [1],
            # Componente 2: acíclica
            10: [11],
            11: [],
            # Componente 3: ciclo 20 -> 21 -> 22 -> 20
            20: [21],
            21: [22],
            22: [20],
        }
        cycles = find_all_cycles(graph)
        assert len(cycles) >= 2


# ==============================================================================
# 4. INTEGRACIÓN DE CICLOS CON RECIPESERVICE (CAPA DE APLICACIÓN)
# ==============================================================================

class TestRecipeServiceCyclePrevention:
    """Verificación de que RecipeService bloquea transaccionalmente cualquier creación o actualización con ciclos."""

    def test_application_service_blocks_deep_cycle_a_b_c_d_a(self) -> None:
        """
        Crea 4 recetas en secuencia A -> B -> C -> D:
        - R1 (A)
        - R2 (B, usa R1)
        - R3 (C, usa R2)
        - R4 (D, usa R3)
        Al intentar actualizar R1 para usar R4, RecipeService lanza RecipeCycleError.
        """
        svc = RecipeService(option_group_service=OptionGroupService())
        tenant = "tenant_dag_test"

        # R1 base
        r1 = svc.create_recipe(
            codigo="R1",
            nombre="Base de Caldo",
            es_subreceta=True,
            precio_venta_neto=Decimal("1000.00"),
            tenant_id=tenant,
        )

        # R2 usa R1
        r2 = svc.create_recipe(
            codigo="R2",
            nombre="Salsa Reducida",
            es_subreceta=True,
            precio_venta_neto=Decimal("2000.00"),
            ingredientes=[
                RecipeIngredientDTO(subreceta_id=r1.id, cantidad_receta=Decimal("1.0000")),
            ],
            tenant_id=tenant,
        )

        # R3 usa R2
        r3 = svc.create_recipe(
            codigo="R3",
            nombre="Guiso Concentrado",
            es_subreceta=True,
            precio_venta_neto=Decimal("3000.00"),
            ingredientes=[
                RecipeIngredientDTO(subreceta_id=r2.id, cantidad_receta=Decimal("1.0000")),
            ],
            tenant_id=tenant,
        )

        # R4 usa R3
        r4 = svc.create_recipe(
            codigo="R4",
            nombre="Plato Final",
            es_subreceta=False,
            precio_venta_neto=Decimal("4000.00"),
            ingredientes=[
                RecipeIngredientDTO(subreceta_id=r3.id, cantidad_receta=Decimal("1.0000")),
            ],
            tenant_id=tenant,
        )

        # Intentar cerrar el ciclo vinculando R1 -> R4
        with pytest.raises(RecipeCycleError) as exc_info:
            svc.update_recipe(
                recipe_id=r1.id,
                ingredientes=[
                    RecipeIngredientDTO(subreceta_id=r4.id, cantidad_receta=Decimal("1.0000")),
                ],
                tenant_id=tenant,
            )

        err_msg = str(exc_info.value)
        # La ruta del ciclo debe contener la secuencia cerrada
        assert f"{r1.id} -> {r4.id} -> {r3.id} -> {r2.id} -> {r1.id}" in err_msg

        # Verificar atomicidad: R1 no fue modificado
        persisted_r1 = svc.get_recipe(r1.id, tenant_id=tenant)
        assert len(persisted_r1.ingredientes_fijos) == 0

    def test_application_service_permits_valid_diamond_subrecipes(self) -> None:
        """
        RecipeService permite diamantes válidos sin lanzar ciclo falso:
        R_Plato (1) -> usa R_Salsa (2) y R_Pasta (3)
        R_Salsa (2) -> usa R_Fondo (4)
        R_Pasta (3) -> usa R_Fondo (4)
        """
        svc = RecipeService(option_group_service=OptionGroupService())
        tenant = "tenant_diamond_test"

        svc.set_ingredient_cost(999, Decimal("100.0000"))

        # R4: Fondo
        r4 = svc.create_recipe(
            codigo="R4-FONDO",
            nombre="Fondo de Verduras",
            es_subreceta=True,
            porciones_rendimiento=Decimal("1.0000"),
            precio_venta_neto=Decimal("500.00"),
            ingredientes=[
                RecipeIngredientDTO(producto_id=999, cantidad_receta=Decimal("2.0000")),
            ],
            tenant_id=tenant,
        )

        # R2: Salsa (usa R4)
        r2 = svc.create_recipe(
            codigo="R2-SALSA",
            nombre="Salsa Pomodoro",
            es_subreceta=True,
            porciones_rendimiento=Decimal("1.0000"),
            precio_venta_neto=Decimal("1500.00"),
            ingredientes=[
                RecipeIngredientDTO(subreceta_id=r4.id, cantidad_receta=Decimal("1.0000")),
            ],
            tenant_id=tenant,
        )

        # R3: Pasta (usa R4)
        r3 = svc.create_recipe(
            codigo="R3-PASTA",
            nombre="Masa al Huevo",
            es_subreceta=True,
            porciones_rendimiento=Decimal("1.0000"),
            precio_venta_neto=Decimal("1200.00"),
            ingredientes=[
                RecipeIngredientDTO(subreceta_id=r4.id, cantidad_receta=Decimal("1.0000")),
            ],
            tenant_id=tenant,
        )

        # R1: Plato Completo (usa R2 y R3)
        r1 = svc.create_recipe(
            codigo="R1-PLATO",
            nombre="Fettuccine Pomodoro",
            es_subreceta=False,
            porciones_rendimiento=Decimal("1.0000"),
            precio_venta_neto=Decimal("5000.00"),
            ingredientes=[
                RecipeIngredientDTO(subreceta_id=r2.id, cantidad_receta=Decimal("1.0000")),
                RecipeIngredientDTO(subreceta_id=r3.id, cantidad_receta=Decimal("1.0000")),
            ],
            tenant_id=tenant,
        )

        assert r1.id is not None
        # R4 cost = 2 * 100 = 200
        # R2 cost = 200
        # R3 cost = 200
        # R1 cost = 200 + 200 = 400
        assert r1.costo_porcion == Decimal("400.0000")
