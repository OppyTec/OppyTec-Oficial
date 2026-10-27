"""
oppytec-backend/src/modules/recipes/application/option_group_service.py
Servicio de Aplicación para Gestión de Biblioteca y Creación In-situ de Grupos de Opciones Polimórficos.
Cumple Clean Architecture, Regla Inmutable 02 (Decimal estricto, 0 floats) y RBAC de 3 niveles.
"""
from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from src.modules.recipes.domain.entities import (
    GrupoOpciones as DomainGrupoOpciones,
    GrupoOpcionesItem as DomainGrupoOpcionesItem,
)
from src.modules.recipes.domain.exceptions import (
    InvalidOptionSelectionError,
    InvalidQuantityError,
    OptionGroupInUseError,
    OptionGroupNotFoundError,
    PolymorphicReferenceError,
)
from src.modules.recipes.domain.value_objects import OptionSelectionRule


@dataclass
class OptionItemDTO:
    """DTO para creación o actualización de un ítem dentro de un grupo de opciones."""

    id: int | None = None
    producto_id: int | None = None
    receta_id: int | None = None
    nombre: str | None = None
    cantidad: Decimal = Decimal("1.0000")
    es_opcion_default: bool = False
    recargo_precio: Decimal = Decimal("0.00")
    orden: int = 0
    costo_referencial: Decimal = Decimal("0.00")

    def to_domain(self) -> DomainGrupoOpcionesItem:
        return DomainGrupoOpcionesItem(
            id=self.id,
            producto_id=self.producto_id,
            receta_id=self.receta_id,
            nombre=self.nombre,
            cantidad=self.cantidad,
            es_opcion_default=self.es_opcion_default,
            recargo_precio=self.recargo_precio,
            orden=self.orden,
        )


OptionGroupItemDTO = OptionItemDTO


@dataclass
class OptionGroupDTO:
    """DTO para creación o actualización de un grupo de opciones."""

    id: int | None = None
    nombre: str = ""
    descripcion: str | None = None
    seleccion_minima: int = 1
    seleccion_maxima: int = 1
    permite_repetir: bool = False
    items: list[OptionItemDTO] = field(default_factory=list)
    tenant_id: str | None = None
    is_deleted: bool = False

    @property
    def min_selecciones(self) -> int:
        return self.seleccion_minima

    @property
    def max_selecciones(self) -> int:
        return self.seleccion_maxima


class OptionGroupService:
    """
    Servicio de Aplicación para gestionar grupos de opciones y modificadores.
    Soporta biblioteca compartida y creación in-situ con validación de reglas de cardinalidad y XOR polimórfico.
    """

    def __init__(self) -> None:
        # Almacenamiento indexado por (tenant_id, group_id)
        self._groups: dict[tuple[str, int], OptionGroupDTO] = {}
        self._next_id: int = 1
        self._item_seq: int = 1
        # Registro de relaciones: group_id -> set of recipe_ids / combo_ids
        self._group_recipes_usage: dict[int, set[int]] = {}
        self._group_combos_usage: dict[int, set[int]] = {}

    def reset(self) -> None:
        """Limpia el almacenamiento en memoria para aislamiento de pruebas unitarias."""
        self._groups.clear()
        self._next_id = 1
        self._item_seq = 1
        self._group_recipes_usage.clear()
        self._group_combos_usage.clear()

    def register_usage(
        self,
        group_id: int,
        *,
        recipe_id: int | None = None,
        combo_id: int | None = None,
    ) -> None:
        """Registra la vinculación de un grupo a una receta o combo para control de eliminación."""
        if recipe_id is not None:
            self._group_recipes_usage.setdefault(group_id, set()).add(recipe_id)
        if combo_id is not None:
            self._group_combos_usage.setdefault(group_id, set()).add(combo_id)

    def unregister_usage(
        self,
        group_id: int,
        *,
        recipe_id: int | None = None,
        combo_id: int | None = None,
    ) -> None:
        """Desvincula el uso de un grupo."""
        if recipe_id is not None and group_id in self._group_recipes_usage:
            self._group_recipes_usage[group_id].discard(recipe_id)
        if combo_id is not None and group_id in self._group_combos_usage:
            self._group_combos_usage[group_id].discard(combo_id)

    def is_in_use(self, group_id: int) -> bool:
        """Indica si el grupo está vinculado a alguna receta o combo activo."""
        rec_usage = self._group_recipes_usage.get(group_id, set())
        com_usage = self._group_combos_usage.get(group_id, set())
        return len(rec_usage) > 0 or len(com_usage) > 0

    def _validate_group_integrity(
        self,
        nombre: str,
        seleccion_minima: int,
        seleccion_maxima: int,
        items: Sequence[OptionItemDTO],
    ) -> None:
        """Valida las reglas de cardinalidad, defaults y unicidad polimórfica."""
        if not nombre or not nombre.strip():
            raise InvalidOptionSelectionError("Group 'nombre' cannot be empty.")

        # Validador de regla de selección
        try:
            OptionSelectionRule(
                min_selections=seleccion_minima,
                max_selections=seleccion_maxima,
            )
        except (InvalidOptionSelectionError, ValueError) as exc:
            raise InvalidOptionSelectionError(
                f"Invalid selection limits: {exc}",
                context={"min": seleccion_minima, "max": seleccion_maxima},
            ) from exc

        # Si el grupo es requerido (seleccion_minima >= 1) y tiene ítems, debe haber al menos un default
        if seleccion_minima >= 1 and len(items) > 0:
            has_default = any(it.es_opcion_default for it in items)
            if not has_default:
                raise InvalidOptionSelectionError(
                    "Required option groups (seleccion_minima >= 1) must have at least one default option (es_opcion_default=True).",
                    i18n_key="recipes:errors.required_group_missing_default",
                )

        # Validación polimórfica XOR de cada ítem
        for it in items:
            has_prod = it.producto_id is not None
            has_rec = it.receta_id is not None
            if has_prod == has_rec:
                raise PolymorphicReferenceError(
                    "Each OptionGroupItem must reference either 'producto_id' or 'receta_id' (exclusive XOR).",
                    i18n_key="recipes:errors.polymorphic_reference_error",
                )
            if it.cantidad <= Decimal("0"):
                raise InvalidQuantityError("Item quantity must be strictly greater than 0.")
            if it.recargo_precio < Decimal("0"):
                raise InvalidOptionSelectionError("Item price surcharge cannot be negative.")

    def create_option_group(
        self,
        *,
        nombre: str,
        descripcion: str | None = None,
        seleccion_minima: int = 1,
        seleccion_maxima: int = 1,
        permite_repetir: bool = False,
        items: list[OptionItemDTO] | None = None,
        tenant_id: str = "default",
    ) -> OptionGroupDTO:
        """Crea un grupo de opciones en la biblioteca general o in-situ para el tenant."""
        raw_items = items or []
        self._validate_group_integrity(nombre, seleccion_minima, seleccion_maxima, raw_items)

        gid = self._next_id
        self._next_id += 1

        assigned_items: list[OptionItemDTO] = []
        for idx, it in enumerate(raw_items):
            it_id = it.id or self._item_seq
            self._item_seq += 1
            assigned_items.append(
                OptionItemDTO(
                    id=it_id,
                    producto_id=it.producto_id,
                    receta_id=it.receta_id,
                    nombre=it.nombre,
                    cantidad=it.cantidad,
                    es_opcion_default=it.es_opcion_default,
                    recargo_precio=it.recargo_precio,
                    orden=it.orden if it.orden != 0 else idx,
                    costo_referencial=it.costo_referencial,
                )
            )

        dto = OptionGroupDTO(
            id=gid,
            nombre=nombre.strip(),
            descripcion=descripcion.strip() if descripcion else None,
            seleccion_minima=seleccion_minima,
            seleccion_maxima=seleccion_maxima,
            permite_repetir=permite_repetir,
            items=assigned_items,
            tenant_id=tenant_id,
        )
        self._groups[(tenant_id, gid)] = dto
        return dto

    def get_option_group(self, group_id: int, tenant_id: str = "default") -> OptionGroupDTO:
        """Obtiene un grupo de opciones activo del tenant."""
        dto = self._groups.get((tenant_id, group_id))
        if dto is None or dto.is_deleted:
            raise OptionGroupNotFoundError(
                f"OptionGroup with ID {group_id} not found in tenant '{tenant_id}'.",
                context={"group_id": group_id, "tenant_id": tenant_id},
            )
        return dto

    def list_option_groups(
        self,
        tenant_id: str = "default",
        *,
        search: str | None = None,
    ) -> list[OptionGroupDTO]:
        """Lista los grupos de opciones de la biblioteca del tenant con filtro opcional de búsqueda."""
        results: list[OptionGroupDTO] = []
        q = search.lower().strip() if search else None
        for (t_id, _), group in self._groups.items():
            if t_id == tenant_id and not group.is_deleted:
                if q is None or q in group.nombre.lower() or (group.descripcion and q in group.descripcion.lower()):
                    results.append(group)
        results.sort(key=lambda g: g.id or 0)
        return results

    def update_option_group(
        self,
        group_id: int,
        *,
        nombre: str | None = None,
        descripcion: str | None = None,
        seleccion_minima: int | None = None,
        seleccion_maxima: int | None = None,
        permite_repetir: bool | None = None,
        items: list[OptionItemDTO] | None = None,
        tenant_id: str = "default",
    ) -> OptionGroupDTO:
        """Actualiza la configuración e ítems de un grupo de opciones."""
        group = self.get_option_group(group_id, tenant_id)

        new_nombre = nombre if nombre is not None else group.nombre
        new_min = seleccion_minima if seleccion_minima is not None else group.seleccion_minima
        new_max = seleccion_maxima if seleccion_maxima is not None else group.seleccion_maxima
        new_items = items if items is not None else group.items

        self._validate_group_integrity(new_nombre, new_min, new_max, new_items)

        assigned_items: list[OptionItemDTO] = []
        for idx, it in enumerate(new_items):
            it_id = it.id or self._item_seq
            self._item_seq += 1
            assigned_items.append(
                OptionItemDTO(
                    id=it_id,
                    producto_id=it.producto_id,
                    receta_id=it.receta_id,
                    nombre=it.nombre,
                    cantidad=it.cantidad,
                    es_opcion_default=it.es_opcion_default,
                    recargo_precio=it.recargo_precio,
                    orden=it.orden if it.orden != 0 else idx,
                    costo_referencial=it.costo_referencial,
                )
            )

        updated = OptionGroupDTO(
            id=group.id,
            nombre=new_nombre.strip(),
            descripcion=descripcion.strip() if descripcion is not None else group.descripcion,
            seleccion_minima=new_min,
            seleccion_maxima=new_max,
            permite_repetir=permite_repetir if permite_repetir is not None else group.permite_repetir,
            items=assigned_items,
            tenant_id=tenant_id,
        )
        self._groups[(tenant_id, group_id)] = updated
        return updated

    def delete_option_group(self, group_id: int, tenant_id: str = "default") -> None:
        """Elimina un grupo de opciones validando que no esté en uso por recetas o combos activos."""
        group = self.get_option_group(group_id, tenant_id)

        if self.is_in_use(group_id):
            raise OptionGroupInUseError(
                f"Cannot delete OptionGroup ID {group_id}: it is currently linked to active recipes or combos.",
                context={"group_id": group_id},
            )

        group.is_deleted = True
