"""
oppytec-backend/src/modules/recipes/domain/__init__.py
Capa de Dominio Puro para el Módulo de Gestión de Recetas, Escandallos y Combos.
DDD, Clean Architecture, inmutabilidad y precisión Decimal estricta (0 floats).
"""
from __future__ import annotations

from src.modules.recipes.domain.allergens import (
    ALLERGEN_ALIASES,
    STANDARD_ALLERGENS,
    AllergenDefinition,
    StandardAllergenCode,
    get_allergen_definition,
    list_standard_allergens,
    normalize_allergen_code,
    resolve_allergen_definitions,
)
from src.modules.recipes.domain.cycle_detector import (
    check_recipe_cycles,
    find_all_cycles,
    would_create_cycle,
)
from src.modules.recipes.domain.entities import (
    Combo,
    ComboGrupoOpcion,
    ComboItem,
    GrupoOpciones,
    GrupoOpcionesItem,
    Receta,
    RecetaGrupoOpcion,
    RecetaIngrediente,
)
from src.modules.recipes.domain.exceptions import (
    InvalidOptionSelectionError,
    InvalidQuantityError,
    InvalidYieldError,
    PolymorphicReferenceError,
    RecipeCycleError,
    RecipeDomainError,
)
from src.modules.recipes.domain.value_objects import (
    PRECISION_COST,
    PRECISION_MONEY,
    PRECISION_PERCENTAGE,
    PRECISION_QUANTITY,
    DynamicCostSummary,
    IngredientQuantity,
    OptionSelectionRule,
    ServingYield,
)

__all__ = [
    # Allergens
    "ALLERGEN_ALIASES",
    "STANDARD_ALLERGENS",
    "AllergenDefinition",
    "StandardAllergenCode",
    "get_allergen_definition",
    "list_standard_allergens",
    "normalize_allergen_code",
    "resolve_allergen_definitions",
    # Exceptions
    "InvalidOptionSelectionError",
    "InvalidQuantityError",
    "InvalidYieldError",
    "PolymorphicReferenceError",
    "RecipeCycleError",
    "RecipeDomainError",
    # Value Objects
    "DynamicCostSummary",
    "IngredientQuantity",
    "OptionSelectionRule",
    "PRECISION_COST",
    "PRECISION_MONEY",
    "PRECISION_PERCENTAGE",
    "PRECISION_QUANTITY",
    "ServingYield",
    # Cycle Detector
    "check_recipe_cycles",
    "find_all_cycles",
    "would_create_cycle",
    # Entities
    "Combo",
    "ComboGrupoOpcion",
    "ComboItem",
    "GrupoOpciones",
    "GrupoOpcionesItem",
    "Receta",
    "RecetaGrupoOpcion",
    "RecetaIngrediente",
]
