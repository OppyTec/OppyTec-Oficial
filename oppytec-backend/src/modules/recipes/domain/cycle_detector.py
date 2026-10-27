"""
oppytec-backend/src/modules/recipes/domain/cycle_detector.py
Algoritmo de Detección Anti-Recursión Cíclica en Grafos Acíclicos Dirigidos (DAG)
para Escandallos Gastronómicos y Sub-recetas anidadas.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence

from src.core.observability import get_tenant_telemetry_context, trace_span
from src.modules.recipes.domain.exceptions import RecipeCycleError


def check_recipe_cycles(
    recipe_id: int | str,
    subrecipe_ids_tree: Mapping[int | str, Sequence[int | str]] | Callable[[int | str], Sequence[int | str]],
    *,
    tenant_id: str | None = None,
) -> None:
    """
    Verifica que la receta no contenga dependencias cíclicas directas o indirectas hacia sí misma
    ni en subárboles alcanzables.

    :param recipe_id: Identificador de la receta raíz a validar.
    :param subrecipe_ids_tree: Diccionario o función que mapea un recipe_id a sus sub-recetas inmediatas.
    :param tenant_id: Identificador opcional del tenant para trazabilidad OpenTelemetry.
    :raises RecipeCycleError: Si se detecta un ciclo, indicando la ruta exacta (ej. 'A -> B -> A').
    """
    resolved_tenant = tenant_id or get_tenant_telemetry_context().tenant_id or "default"
    get_children: Callable[[int | str], Sequence[int | str]]
    if callable(subrecipe_ids_tree):
        get_children = subrecipe_ids_tree
    else:
        tree_map = subrecipe_ids_tree
        get_children = lambda rid: tree_map.get(rid, ())

    path: list[int | str] = [recipe_id]
    path_set: set[int | str] = {recipe_id}
    visited_safe: set[int | str] = set()

    with trace_span(
        "recipe.cycle_detection.run",
        attributes={
            "tenant_id": resolved_tenant,
            "recipe_id": recipe_id,
            "cycle_detected": False,
        },
        tracer_name="oppytec.recipes",
    ) as span_attrs:
        def dfs(current: int | str) -> None:
            children = get_children(current) or ()
            for child in children:
                if child in path_set:
                    idx = path.index(child)
                    cycle_slice = path[idx:] + [child]
                    cycle_str = " -> ".join(map(str, cycle_slice))
                    span_attrs["cycle_detected"] = True
                    span_attrs["cycle_path"] = cycle_str
                    raise RecipeCycleError(f"Recipe sub-recipe cycle detected: {cycle_str}")
                if child not in visited_safe:
                    path.append(child)
                    path_set.add(child)
                    dfs(child)
                    path.pop()
                    path_set.remove(child)
            visited_safe.add(current)

        dfs(recipe_id)
        span_attrs["visited_nodes_count"] = len(visited_safe)


def would_create_cycle(
    parent_recipe_id: int | str,
    child_subrecipe_id: int | str,
    current_tree: Mapping[int | str, Sequence[int | str]],
) -> bool:
    """
    Evalúa preventivamente si asociar `child_subrecipe_id` dentro de `parent_recipe_id`
    introduciría un ciclo en el grafo existente.

    :return: True si causaría un ciclo, False si la relación es segura (DAG válido).
    """
    if parent_recipe_id == child_subrecipe_id:
        return True

    # Creamos un árbol provisional incorporando la relación propuesta
    simulated_tree: dict[int | str, list[int | str]] = {
        k: list(v) for k, v in current_tree.items()
    }
    existing_children = simulated_tree.setdefault(parent_recipe_id, [])
    if child_subrecipe_id not in existing_children:
        existing_children.append(child_subrecipe_id)

    try:
        check_recipe_cycles(parent_recipe_id, simulated_tree)
        return False
    except RecipeCycleError:
        return True


def find_all_cycles(
    graph: Mapping[int | str, Sequence[int | str]],
) -> list[list[int | str]]:
    """
    Analiza un grafo completo de recetas y sub-recetas y retorna todos los ciclos elementales detectados.
    """
    cycles: list[list[int | str]] = []
    visited_globally: set[int | str] = set()

    for start_node in graph:
        if start_node in visited_globally:
            continue
        try:
            check_recipe_cycles(start_node, graph)
        except RecipeCycleError as err:
            # Extraer ruta del mensaje si es posible
            err_msg = str(err)
            if ": " in err_msg:
                cycle_nodes = [node.strip() for node in err_msg.split(": ")[-1].split("->")]
                cycles.append(cycle_nodes)
        visited_globally.add(start_node)

    return cycles


__all__ = [
    "check_recipe_cycles",
    "find_all_cycles",
    "would_create_cycle",
]
