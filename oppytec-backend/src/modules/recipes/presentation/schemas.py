"""
oppytec-backend/src/modules/recipes/presentation/schemas.py
Esquemas Pydantic v2 (`extra="forbid"`, `Decimal` exclusivo) para:
- Biblioteca de Grupos de Opciones Polimórficos e Ítems
- Fichas Técnicas de Recetas y Escandallos Dinámicos
- Promociones y Combos Comerciales
- Simulación en Vivo de Costos y Márgenes
- Compatibilidad Retroactiva con Escandallos Básicos
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from src.core.guards.xss_sanitizer import sanitize_text_input


# ============================================================================
# COMPATIBILIDAD RETROACTIVA (ESCANDALLOS BÁSICOS & SIMULACIÓN)
# ============================================================================


class RecipeLinePayload(BaseModel):
    """Línea de un escandallo: insumo (`ingredient_id`) o sub-receta (`sub_recipe_id`)."""

    model_config = ConfigDict(extra="forbid")

    quantity: Decimal = Field(..., gt=Decimal("0"))
    ingredient_id: int | None = Field(default=None, gt=0)
    sub_recipe_id: int | None = Field(default=None, gt=0)
    waste_pct: Decimal = Field(default=Decimal("0"), ge=Decimal("0"), lt=Decimal("100"))
    unit_cost: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))


class EscandalloCreateRequest(BaseModel):
    """Creación o actualización de una receta/escandallo con cálculo recursivo en `Decimal`."""

    model_config = ConfigDict(extra="forbid")

    recipe_id: int = Field(..., gt=0)
    name: str = Field(..., min_length=2, max_length=160)
    yield_portions: Decimal = Field(default=Decimal("1"), gt=Decimal("0"))
    net_price: Decimal = Field(..., gt=Decimal("0"))
    lines: list[RecipeLinePayload] = Field(..., min_length=1)

    @field_validator("name")
    @classmethod
    def _sanitize_recipe_name(cls, value: str) -> str:
        return sanitize_text_input(value, field_name="name")


class EscandalloCostResponse(BaseModel):
    """Reporte de costeo recursivo de una receta: costo por porción, Food Cost % y margen."""

    model_config = ConfigDict(extra="forbid")

    recipe_id: int
    name: str
    portion_cost: Decimal
    net_price: Decimal
    food_cost_pct: Decimal
    margin_amount: Decimal
    margin_pct: Decimal


class MarginSimulationRequest(BaseModel):
    """Simulación de margen y Food Cost % ante cambios de precio o costo de receta."""

    model_config = ConfigDict(extra="forbid")

    portion_cost: Decimal = Field(..., ge=Decimal("0"))
    proposed_net_price: Decimal = Field(..., gt=Decimal("0"))


class MarginSimulationResponse(BaseModel):
    """Resultado de la simulación de margen en `Decimal`."""

    model_config = ConfigDict(extra="forbid")

    portion_cost: Decimal
    proposed_net_price: Decimal
    food_cost_pct: Decimal
    margin_amount: Decimal
    margin_pct: Decimal


# ============================================================================
# 1. GRUPOS DE OPCIONES POLIMÓRFICOS
# ============================================================================


class OptionGroupItemCreate(BaseModel):
    """Ítem seleccionable dentro de un grupo de opciones (XOR producto/receta)."""

    model_config = ConfigDict(extra="forbid")

    producto_id: int | None = Field(default=None, gt=0)
    receta_id: int | None = Field(default=None, gt=0)
    nombre: str | None = Field(default=None, max_length=180)
    cantidad: Decimal = Field(default=Decimal("1.0000"), gt=Decimal("0"))
    es_opcion_default: bool = False
    recargo_precio: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0"))
    orden: int = Field(default=0, ge=0)

    @field_validator("nombre")
    @classmethod
    def _sanitize_item_name(cls, value: str | None) -> str | None:
        if value:
            return sanitize_text_input(value, field_name="nombre")
        return value

    @model_validator(mode="after")
    def _validate_xor_reference(self) -> OptionGroupItemCreate:
        has_prod = self.producto_id is not None
        has_rec = self.receta_id is not None
        if has_prod == has_rec:
            raise ValueError(
                "OptionGroupItem must specify exactly one target: either 'producto_id' or 'receta_id' (exclusive XOR)."
            )
        return self


class OptionGroupItemResponse(BaseModel):
    """Respuesta serializada de un ítem de opción."""

    model_config = ConfigDict(extra="forbid")

    id: int
    producto_id: int | None = None
    receta_id: int | None = None
    nombre: str | None = None
    target_type: str = "producto"
    cantidad: Decimal
    es_opcion_default: bool
    recargo_precio: Decimal
    orden: int
    costo_referencial: Decimal = Decimal("0.00")


class OptionGroupCreateRequest(BaseModel):
    """Creación de un grupo de opciones en biblioteca o in-situ."""

    model_config = ConfigDict(extra="forbid")

    nombre: str = Field(..., min_length=2, max_length=120)
    descripcion: str | None = Field(default=None, max_length=500)
    seleccion_minima: int = Field(default=1, ge=0)
    seleccion_maxima: int = Field(default=1, ge=1)
    permite_repetir: bool = False
    items: list[OptionGroupItemCreate] = Field(default_factory=list)

    @field_validator("nombre")
    @classmethod
    def _sanitize_name(cls, value: str) -> str:
        return sanitize_text_input(value, field_name="nombre")

    @field_validator("descripcion")
    @classmethod
    def _sanitize_desc(cls, value: str | None) -> str | None:
        if value:
            return sanitize_text_input(value, field_name="descripcion")
        return value

    @model_validator(mode="after")
    def _validate_cardinality(self) -> OptionGroupCreateRequest:
        if self.seleccion_minima > self.seleccion_maxima:
            raise ValueError("seleccion_minima cannot be greater than seleccion_maxima.")
        return self


class OptionGroupUpdateRequest(BaseModel):
    """Actualización de un grupo de opciones existente."""

    model_config = ConfigDict(extra="forbid")

    nombre: str | None = Field(default=None, min_length=2, max_length=120)
    descripcion: str | None = Field(default=None, max_length=500)
    seleccion_minima: int | None = Field(default=None, ge=0)
    seleccion_maxima: int | None = Field(default=None, ge=1)
    permite_repetir: bool | None = None
    items: list[OptionGroupItemCreate] | None = None

    @field_validator("nombre")
    @classmethod
    def _sanitize_name(cls, value: str | None) -> str | None:
        if value:
            return sanitize_text_input(value, field_name="nombre")
        return value

    @field_validator("descripcion")
    @classmethod
    def _sanitize_desc(cls, value: str | None) -> str | None:
        if value:
            return sanitize_text_input(value, field_name="descripcion")
        return value


class OptionGroupResponse(BaseModel):
    """Representación completa de un grupo de opciones con sus ítems."""

    model_config = ConfigDict(extra="forbid")

    id: int
    nombre: str
    descripcion: str | None = None
    seleccion_minima: int
    seleccion_maxima: int
    min_selecciones: int
    max_selecciones: int
    permite_repetir: bool
    items: list[OptionGroupItemResponse] = Field(default_factory=list)


# ============================================================================
# 2. CATEGORÍAS DE RECETAS Y COMBOS
# ============================================================================


class RecipeCategoryCreateRequest(BaseModel):
    """Creación de categoría de receta."""

    model_config = ConfigDict(extra="forbid")

    nombre: str = Field(..., min_length=2, max_length=180)
    color: str | None = Field(default="#f59e0b", max_length=32)
    icono: str | None = Field(default="ChefHat", max_length=64)
    orden: int = Field(default=0, ge=0)

    @field_validator("nombre")
    @classmethod
    def _sanitize_name(cls, value: str) -> str:
        return sanitize_text_input(value, field_name="nombre")


class RecipeCategoryUpdateRequest(BaseModel):
    """Actualización de categoría de receta."""

    model_config = ConfigDict(extra="forbid")

    nombre: str | None = Field(default=None, min_length=2, max_length=180)
    color: str | None = Field(default=None, max_length=32)
    icono: str | None = Field(default=None, max_length=64)
    orden: int | None = Field(default=None, ge=0)


class RecipeCategoryResponse(BaseModel):
    """Respuesta de categoría de receta."""

    model_config = ConfigDict(extra="forbid")

    id: int
    nombre: str
    color: str | None = None
    icono: str | None = None
    orden: int = 0


class ComboCategoryCreateRequest(BaseModel):
    """Creación de categoría de combo."""

    model_config = ConfigDict(extra="forbid")

    nombre: str = Field(..., min_length=2, max_length=180)
    color: str | None = Field(default="#ec4899", max_length=32)
    icono: str | None = Field(default="Boxes", max_length=64)
    orden: int = Field(default=0, ge=0)

    @field_validator("nombre")
    @classmethod
    def _sanitize_name(cls, value: str) -> str:
        return sanitize_text_input(value, field_name="nombre")


class ComboCategoryUpdateRequest(BaseModel):
    """Actualización de categoría de combo."""

    model_config = ConfigDict(extra="forbid")

    nombre: str | None = Field(default=None, min_length=2, max_length=180)
    color: str | None = Field(default=None, max_length=32)
    icono: str | None = Field(default=None, max_length=64)
    orden: int | None = Field(default=None, ge=0)


class ComboCategoryResponse(BaseModel):
    """Respuesta de categoría de combo."""

    model_config = ConfigDict(extra="forbid")

    id: int
    nombre: str
    color: str | None = None
    icono: str | None = None
    orden: int = 0


# ============================================================================
# 3. RECETAS GASTRONÓMICAS Y ESCANDALLOS
# ============================================================================


class RecipeIngredientCreate(BaseModel):
    """Ingrediente fijo del escandallo base (XOR producto/subreceta)."""

    model_config = ConfigDict(extra="forbid")

    producto_id: int | None = Field(default=None, gt=0)
    subreceta_id: int | None = Field(default=None, gt=0)
    cantidad_receta: Decimal = Field(..., gt=Decimal("0"))
    porcentaje_merma: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0"), lt=Decimal("100"))
    bodega_consumo_id: int | None = Field(default=None, gt=0)
    notas: str | None = Field(default=None, max_length=255)

    @model_validator(mode="after")
    def _validate_xor_ingredient(self) -> RecipeIngredientCreate:
        has_prod = self.producto_id is not None
        has_sub = self.subreceta_id is not None
        if has_prod == has_sub:
            raise ValueError(
                "RecipeIngredient must specify exactly one target: either 'producto_id' or 'subreceta_id' (exclusive XOR)."
            )
        return self


class RecipeIngredientResponse(BaseModel):
    """Respuesta de ingrediente fijo costeado."""

    model_config = ConfigDict(extra="forbid")

    id: int
    producto_id: int | None = None
    subreceta_id: int | None = None
    nombre: str | None = None
    target_type: str = "producto"
    unidad: str = "und"
    cantidad_receta: Decimal
    porcentaje_merma: Decimal
    costo_unitario: Decimal
    costo_total: Decimal
    bodega_consumo_id: int | None = None
    notas: str | None = None


class RecipeOptionGroupLinkRequest(BaseModel):
    """Vinculación de grupo de opciones a una receta."""

    model_config = ConfigDict(extra="forbid")

    grupo_id: int = Field(..., gt=0)
    orden: int = Field(default=0, ge=0)
    es_requerido: bool = True


class RecipeOptionGroupLinkResponse(BaseModel):
    """Respuesta de vinculación de grupo a una receta."""

    model_config = ConfigDict(extra="forbid")

    grupo_id: int
    orden: int
    es_requerido: bool
    grupo: OptionGroupResponse | None = None


class RecipeCreateRequest(BaseModel):
    """Creación de receta gastronómica estática o dinámica."""

    model_config = ConfigDict(extra="forbid")

    codigo: str = Field(..., min_length=2, max_length=64)
    nombre: str = Field(..., min_length=2, max_length=180)
    descripcion: str | None = Field(default=None, max_length=1000)
    categoria_receta_id: int | None = Field(default=None, gt=0)
    es_subreceta: bool = False
    es_dinamica: bool = False
    porciones_rendimiento: Decimal = Field(default=Decimal("1.0000"), gt=Decimal("0"))
    precio_venta_neto: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0"))
    precio_venta_bruto: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0"))
    iva_porcentaje: Decimal = Field(default=Decimal("19.00"), ge=Decimal("0"))
    iva_incluido: bool = True
    imagen_url: str | None = Field(default=None, max_length=512)
    preparacion: str | None = None
    video_url: str | None = Field(default=None, max_length=512)
    documento_url: str | None = Field(default=None, max_length=512)
    tiempo_preparacion_minutos: int | None = Field(default=None, ge=0)
    ingredientes: list[RecipeIngredientCreate] = Field(default_factory=list)
    grupos_opciones: list[RecipeOptionGroupLinkRequest] = Field(default_factory=list)

    @field_validator("codigo")
    @classmethod
    def _sanitize_codigo(cls, value: str) -> str:
        return sanitize_text_input(value, field_name="codigo").upper()

    @field_validator("nombre")
    @classmethod
    def _sanitize_name(cls, value: str) -> str:
        return sanitize_text_input(value, field_name="nombre")


class RecipeUpdateRequest(BaseModel):
    """Actualización de receta gastronómica."""

    model_config = ConfigDict(extra="forbid")

    nombre: str | None = Field(default=None, min_length=2, max_length=180)
    descripcion: str | None = Field(default=None, max_length=1000)
    categoria_receta_id: int | None = Field(default=None, gt=0)
    es_subreceta: bool | None = None
    es_dinamica: bool | None = None
    porciones_rendimiento: Decimal | None = Field(default=None, gt=Decimal("0"))
    precio_venta_neto: Decimal | None = Field(default=None, ge=Decimal("0"))
    precio_venta_bruto: Decimal | None = Field(default=None, ge=Decimal("0"))
    iva_porcentaje: Decimal | None = Field(default=None, ge=Decimal("0"))
    iva_incluido: bool | None = None
    imagen_url: str | None = Field(default=None, max_length=512)
    preparacion: str | None = None
    video_url: str | None = Field(default=None, max_length=512)
    documento_url: str | None = Field(default=None, max_length=512)
    tiempo_preparacion_minutos: int | None = Field(default=None, ge=0)
    ingredientes: list[RecipeIngredientCreate] | None = None
    grupos_opciones: list[RecipeOptionGroupLinkRequest] | None = None

    @field_validator("nombre")
    @classmethod
    def _sanitize_name(cls, value: str | None) -> str | None:
        if value:
            return sanitize_text_input(value, field_name="nombre")
        return value


class RecipeSummaryResponse(BaseModel):
    """Resumen de receta para listados tabulares rápidos."""

    model_config = ConfigDict(extra="forbid")

    id: int
    codigo: str
    nombre: str
    descripcion: str | None = None
    categoria_receta_id: int | None = None
    categoria_nombre: str | None = None
    es_subreceta: bool
    es_dinamica: bool
    porciones_rendimiento: Decimal
    costo_total_calculado: Decimal
    costo_porcion: Decimal
    costo_peor_caso: Decimal
    costo_mejor_caso: Decimal
    precio_venta_neto: Decimal
    precio_venta_bruto: Decimal
    margen_neto: Decimal
    margen_bruto: Decimal
    margen_pct: Decimal
    food_cost_pct: Decimal
    imagen_url: str | None = None


class RecipeDetailResponse(RecipeSummaryResponse):
    """Detalle completo de receta gastronómica con escandallo e ingredientes."""

    iva_porcentaje: Decimal
    iva_incluido: bool
    preparacion: str | None = None
    video_url: str | None = None
    documento_url: str | None = None
    tiempo_preparacion_minutos: int | None = None
    ingredientes_fijos: list[RecipeIngredientResponse] = Field(default_factory=list)
    grupos_opciones: list[RecipeOptionGroupLinkResponse] = Field(default_factory=list)
    subrecetas_tree: list[dict[str, Any]] = Field(default_factory=list)
    alergenos: list[AllergenInfo] = Field(default_factory=list)
    allergens: list[AllergenInfo] = Field(default_factory=list)


# ============================================================================
# ALÉRGENOS ALIMENTARIOS Y FICHA TÉCNICA DE COCINA
# ============================================================================


class AllergenInfo(BaseModel):
    """Información estandarizada de alérgeno alimentario normado."""

    model_config = ConfigDict(extra="forbid")

    code: str = Field(..., description="Código canónico del alérgeno (ej. GLUTEN, CRUSTACEANS, EGGS)")
    nombre: str = Field(..., description="Nombre normado en español")
    nombre_en: str | None = Field(default=None, description="Nombre normado en inglés")
    icono: str | None = Field(default=None, description="Identificador del ícono Lucide")
    descripcion: str | None = Field(default=None, description="Descripción técnica del alérgeno")


class KitchenSheetOptionItemResponse(BaseModel):
    """Opción disponible en un grupo para preparación en cocina."""

    model_config = ConfigDict(extra="forbid")

    item_id: int | None = None
    producto_id: int | None = None
    receta_id: int | None = None
    nombre: str
    target_type: str
    cantidad_base: Decimal
    cantidad_escalada: Decimal
    unidad: str
    es_opcion_default: bool
    recargo_precio: Decimal
    alergenos: list[AllergenInfo] = Field(default_factory=list)


class KitchenSheetOptionGroupResponse(BaseModel):
    """Grupo de modificadores u opciones dinámicas en la ficha técnica de cocina."""

    model_config = ConfigDict(extra="forbid")

    grupo_id: int
    grupo_nombre: str
    seleccion_minima: int
    seleccion_maxima: int
    es_requerido: bool
    opciones: list[KitchenSheetOptionItemResponse] = Field(default_factory=list)


class KitchenSheetItem(BaseModel):
    """Ítem de ingrediente o subreceta en la ficha técnica de cocina con escalamiento y merma."""

    model_config = ConfigDict(extra="forbid")

    ingrediente_id: int | None = None
    producto_id: int | None = None
    subreceta_id: int | None = None
    nombre: str
    target_type: str
    unidad: str
    cantidad_neta_base: Decimal
    cantidad_neta_escalada: Decimal
    porcentaje_merma: Decimal
    cantidad_bruta_escalada: Decimal
    notas: str | None = None
    alergenos: list[AllergenInfo] = Field(default_factory=list)
    subreceta_desglose: list[KitchenSheetItem] = Field(default_factory=list)


class KitchenSheetResponse(BaseModel):
    """Ficha técnica de cocina escalada con alérgenos, merma e instrucciones de preparación."""

    model_config = ConfigDict(extra="forbid")

    recipe_id: int
    codigo: str
    nombre: str
    descripcion: str | None = None
    categoria_nombre: str | None = None
    porciones_base: Decimal
    porciones_solicitadas: Decimal
    factor_escalamiento: Decimal
    tiempo_preparacion_minutos: int | None = None
    preparacion: str | None = None
    video_url: str | None = None
    documento_url: str | None = None
    ingredientes_fijos: list[KitchenSheetItem] = Field(default_factory=list)
    grupos_opciones: list[KitchenSheetOptionGroupResponse] = Field(default_factory=list)
    alergenos_consolidados: list[AllergenInfo] = Field(default_factory=list)
    allergens: list[AllergenInfo] = Field(default_factory=list)


# ============================================================================
# 4. COMBOS COMERCIALES
# ============================================================================


class ComboItemCreate(BaseModel):
    """Componente fijo de un combo (XOR producto/receta)."""

    model_config = ConfigDict(extra="forbid")

    producto_id: int | None = Field(default=None, gt=0)
    receta_id: int | None = Field(default=None, gt=0)
    cantidad: Decimal = Field(default=Decimal("1.0000"), gt=Decimal("0"))

    @model_validator(mode="after")
    def _validate_xor_item(self) -> ComboItemCreate:
        has_prod = self.producto_id is not None
        has_rec = self.receta_id is not None
        if has_prod == has_rec:
            raise ValueError(
                "ComboItem must specify exactly one target: either 'producto_id' or 'receta_id' (exclusive XOR)."
            )
        return self


class ComboItemResponse(BaseModel):
    """Respuesta serializada de componente de combo."""

    model_config = ConfigDict(extra="forbid")

    id: int
    producto_id: int | None = None
    receta_id: int | None = None
    nombre: str | None = None
    target_type: str = "producto"
    cantidad: Decimal
    costo_unitario: Decimal
    costo_total: Decimal


class ComboOptionGroupLinkRequest(BaseModel):
    """Vinculación de grupo de opciones a un combo."""

    model_config = ConfigDict(extra="forbid")

    grupo_id: int = Field(..., gt=0)
    orden: int = Field(default=0, ge=0)
    es_requerido: bool = True


class ComboOptionGroupLinkResponse(BaseModel):
    """Respuesta de grupo de opciones vinculado a un combo."""

    model_config = ConfigDict(extra="forbid")

    grupo_id: int
    orden: int
    es_requerido: bool
    grupo: OptionGroupResponse | None = None


class ComboCreateRequest(BaseModel):
    """Creación de combo promocional."""

    model_config = ConfigDict(extra="forbid")

    nombre: str = Field(..., min_length=2, max_length=180)
    codigo: str | None = Field(default=None, max_length=64)
    descripcion: str | None = Field(default=None, max_length=1000)
    categoria_combo_id: int | None = Field(default=None, gt=0)
    es_dinamico: bool = False
    precio_venta_neto: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0"))
    precio_venta_bruto: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0"))
    iva_porcentaje: Decimal = Field(default=Decimal("19.00"), ge=Decimal("0"))
    iva_incluido: bool = True
    imagen_url: str | None = Field(default=None, max_length=512)
    items: list[ComboItemCreate] = Field(default_factory=list)
    grupos_opciones: list[ComboOptionGroupLinkRequest] = Field(default_factory=list)

    @field_validator("codigo")
    @classmethod
    def _sanitize_codigo(cls, value: str | None) -> str | None:
        if value:
            return sanitize_text_input(value, field_name="codigo").upper()
        return value

    @field_validator("nombre")
    @classmethod
    def _sanitize_name(cls, value: str) -> str:
        return sanitize_text_input(value, field_name="nombre")


class ComboUpdateRequest(BaseModel):
    """Actualización de combo comercial."""

    model_config = ConfigDict(extra="forbid")

    nombre: str | None = Field(default=None, min_length=2, max_length=180)
    codigo: str | None = Field(default=None, max_length=64)
    descripcion: str | None = Field(default=None, max_length=1000)
    categoria_combo_id: int | None = Field(default=None, gt=0)
    es_dinamico: bool | None = None
    precio_venta_neto: Decimal | None = Field(default=None, ge=Decimal("0"))
    precio_venta_bruto: Decimal | None = Field(default=None, ge=Decimal("0"))
    iva_porcentaje: Decimal | None = Field(default=None, ge=Decimal("0"))
    iva_incluido: bool | None = None
    imagen_url: str | None = Field(default=None, max_length=512)
    items: list[ComboItemCreate] | None = None
    grupos_opciones: list[ComboOptionGroupLinkRequest] | None = None


class ComboSummaryResponse(BaseModel):
    """Resumen de combo para vista tabular."""

    model_config = ConfigDict(extra="forbid")

    id: int
    codigo: str | None = None
    nombre: str
    descripcion: str | None = None
    categoria_combo_id: int | None = None
    categoria_nombre: str | None = None
    es_dinamico: bool
    precio_venta_neto: Decimal
    precio_venta_bruto: Decimal
    costo_total_calculado: Decimal
    margen_amount: Decimal
    margen_pct: Decimal
    food_cost_pct: Decimal
    disponibilidad_stock_porciones: int | None = None
    esta_disponible: bool = True
    imagen_url: str | None = None


class ComboDetailResponse(ComboSummaryResponse):
    """Detalle completo de combo con componentes fijos y grupos de opciones."""

    iva_porcentaje: Decimal
    iva_incluido: bool
    items_fijos: list[ComboItemResponse] = Field(default_factory=list)
    grupos_opciones: list[ComboOptionGroupLinkResponse] = Field(default_factory=list)


# ============================================================================
# 5. SIMULADOR DE COSTOS DINÁMICOS ANTE OPCIONES PARTICULARES
# ============================================================================


class RecipeCostSimulationRequest(BaseModel):
    """Petición de simulación de costos ante selecciones dinámicas particulares."""

    model_config = ConfigDict(extra="forbid")

    selected_option_item_ids: list[int] = Field(default_factory=list)


class SimulatedOptionResponse(BaseModel):
    """Detalle de una opción seleccionada en el resultado de la simulación."""

    model_config = ConfigDict(extra="forbid")

    item_id: int
    grupo_id: int
    grupo_nombre: str
    nombre: str
    cantidad: Decimal
    costo_unitario: Decimal
    costo_total: Decimal
    recargo_precio: Decimal


class RecipeCostSimulationResponse(BaseModel):
    """Resultado financiero de la simulación de costo de receta."""

    model_config = ConfigDict(extra="forbid")

    recipe_id: int
    recipe_nombre: str
    base_fixed_cost: Decimal
    options_cost: Decimal
    total_cost: Decimal
    portion_cost: Decimal
    total_surcharge: Decimal
    effective_net_price: Decimal
    effective_gross_price: Decimal
    margin_amount: Decimal
    margin_pct: Decimal
    food_cost_pct: Decimal
    selected_options: list[SimulatedOptionResponse] = Field(default_factory=list)
