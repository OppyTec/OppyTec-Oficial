"""
oppytec-backend/src/modules/recipes/domain/exceptions.py
Jerarquía de excepciones de dominio puro para Recetas, Escandallos, Combos y Opciones Dinámicas.
Cumple RFC 7807, i18n estricto y desacoplamiento total de infraestructura.
"""
from __future__ import annotations

from src.core.exceptions import OppyTecError, ResourceNotFoundError


class RecipeDomainError(OppyTecError, ValueError):
    """Excepción base para violaciones de reglas de negocio en el dominio de recetas."""

    default_status_code = 400
    default_error_code = "RECIPE_DOMAIN_ERROR"
    default_i18n_key = "recipes:errors.domain_error"
    default_title = "Recipe Domain Rule Violation"


class RecipeNotFoundError(ResourceNotFoundError):
    """La receta especificada no fue encontrada."""

    default_status_code = 404
    default_error_code = "RECIPE_NOT_FOUND"
    default_i18n_key = "recipes:errors.not_found"
    default_title = "Recipe Not Found"


class ComboNotFoundError(ResourceNotFoundError):
    """El combo especificado no fue encontrado."""

    default_status_code = 404
    default_error_code = "COMBO_NOT_FOUND"
    default_i18n_key = "recipes:errors.combo_not_found"
    default_title = "Combo Not Found"


class OptionGroupNotFoundError(ResourceNotFoundError):
    """El grupo de opciones especificado no fue encontrado."""

    default_status_code = 404
    default_error_code = "OPTION_GROUP_NOT_FOUND"
    default_i18n_key = "recipes:errors.option_group_not_found"
    default_title = "Option Group Not Found"


class RecipeInUseError(RecipeDomainError):
    """La receta no se puede eliminar porque está en uso en combos o subrecetas activas."""

    default_status_code = 409
    default_error_code = "RECIPE_IN_USE"
    default_i18n_key = "recipes:errors.recipe_in_use"
    default_title = "Recipe In Use"


class OptionGroupInUseError(RecipeDomainError):
    """El grupo de opciones no se puede eliminar porque está vinculado a recetas o combos activos."""

    default_status_code = 409
    default_error_code = "OPTION_GROUP_IN_USE"
    default_i18n_key = "recipes:errors.option_group_in_use"
    default_title = "Option Group In Use"


class RecipeCycleError(RecipeDomainError):
    """Se detectó una dependencia cíclica entre recetas y sub-recetas (violación de DAG)."""

    default_status_code = 422
    default_error_code = "RECIPE_CYCLE_DETECTED"
    default_i18n_key = "recipes:errors.cycle_detected"
    default_title = "Recipe Sub-recipe Cycle Detected"


class InvalidYieldError(RecipeDomainError):
    """El rendimiento de porciones de la receta es inválido (debe ser estrictamente positivo)."""

    default_status_code = 422
    default_error_code = "RECIPE_INVALID_YIELD"
    default_i18n_key = "recipes:errors.invalid_yield"
    default_title = "Invalid Recipe Yield Portions"


class InvalidQuantityError(RecipeDomainError):
    """La cantidad o factor de merma del insumo es inválido."""

    default_status_code = 422
    default_error_code = "RECIPE_INVALID_QUANTITY"
    default_i18n_key = "recipes:errors.invalid_quantity"
    default_title = "Invalid Ingredient Quantity or Waste Percentage"


class InvalidOptionSelectionError(RecipeDomainError):
    """La regla de cardinalidad o la selección de opciones no cumple las restricciones."""

    default_status_code = 422
    default_error_code = "RECIPE_INVALID_OPTION_SELECTION"
    default_i18n_key = "recipes:errors.invalid_option_selection"
    default_title = "Invalid Option Selection Rule or Choice"


class PolymorphicReferenceError(RecipeDomainError):
    """Violación de integridad polimórfica XOR (debe apuntar exactamente a un target)."""

    default_status_code = 422
    default_error_code = "RECIPE_POLYMORPHIC_REFERENCE_ERROR"
    default_i18n_key = "recipes:errors.polymorphic_reference_error"
    default_title = "Invalid Polymorphic Reference"


__all__ = [
    "ComboNotFoundError",
    "InvalidOptionSelectionError",
    "InvalidQuantityError",
    "InvalidYieldError",
    "OptionGroupInUseError",
    "OptionGroupNotFoundError",
    "PolymorphicReferenceError",
    "RecipeCycleError",
    "RecipeDomainError",
    "RecipeInUseError",
    "RecipeNotFoundError",
]
