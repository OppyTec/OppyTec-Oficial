"""
oppytec-backend/src/modules/recipes/domain/allergens.py
Catálogo oficial normado de los 14 Alérgenos Alimentarios (Reglamento UE 1169/2011, RSA Chile y FDA).
Value Objects inmutables con soporte bilingüe (es/en) y códigos canónicos normalizados.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Sequence


class StandardAllergenCode(str, Enum):
    """Códigos estandarizados para los 14 alérgenos de declaración obligatoria."""

    GLUTEN = "GLUTEN"
    CRUSTACEANS = "CRUSTACEANS"
    EGGS = "EGGS"
    FISH = "FISH"
    PEANUTS = "PEANUTS"
    SOYBEANS = "SOYBEANS"
    MILK = "MILK"
    NUTS = "NUTS"
    CELERY = "CELERY"
    MUSTARD = "MUSTARD"
    SESAME = "SESAME"
    SULPHITES = "SULPHITES"
    LUPIN = "LUPIN"
    MOLLUSCS = "MOLLUSCS"


@dataclass(frozen=True)
class AllergenDefinition:
    """Definición inmutable de un alérgeno alimentario normado."""

    code: str
    nombre: str
    nombre_en: str
    icono: str
    descripcion: str
    descripcion_en: str

    @property
    def name(self) -> str:
        """Alias en inglés/español para interoperabilidad."""
        return self.nombre

    @property
    def name_en(self) -> str:
        """Alias en inglés."""
        return self.nombre_en

    @property
    def icon(self) -> str:
        """Ícono Lucide asignado."""
        return self.icono


STANDARD_ALLERGENS: dict[str, AllergenDefinition] = {
    StandardAllergenCode.GLUTEN.value: AllergenDefinition(
        code=StandardAllergenCode.GLUTEN.value,
        nombre="Gluten",
        nombre_en="Gluten",
        icono="Wheat",
        descripcion="Cereales que contienen gluten: trigo, centeno, cebada, avena, espelta, kamut y productos derivados.",
        descripcion_en="Cereals containing gluten: wheat, rye, barley, oats, spelt, kamut and products thereof.",
    ),
    StandardAllergenCode.CRUSTACEANS.value: AllergenDefinition(
        code=StandardAllergenCode.CRUSTACEANS.value,
        nombre="Crustáceos",
        nombre_en="Crustaceans",
        icono="Crab",
        descripcion="Crustáceos y productos a base de crustáceos (camarones, langostinos, cangrejos, etc.).",
        descripcion_en="Crustaceans and products thereof (shrimp, prawns, crabs, lobster, etc.).",
    ),
    StandardAllergenCode.EGGS.value: AllergenDefinition(
        code=StandardAllergenCode.EGGS.value,
        nombre="Huevos",
        nombre_en="Eggs",
        icono="Egg",
        descripcion="Huevos y productos a base de huevo.",
        descripcion_en="Eggs and products thereof.",
    ),
    StandardAllergenCode.FISH.value: AllergenDefinition(
        code=StandardAllergenCode.FISH.value,
        nombre="Pescado",
        nombre_en="Fish",
        icono="Fish",
        descripcion="Pescado y productos a base de pescado.",
        descripcion_en="Fish and products thereof.",
    ),
    StandardAllergenCode.PEANUTS.value: AllergenDefinition(
        code=StandardAllergenCode.PEANUTS.value,
        nombre="Maní",
        nombre_en="Peanuts",
        icono="Nut",
        descripcion="Maní / cacahuates y productos a base de maní.",
        descripcion_en="Peanuts and products thereof.",
    ),
    StandardAllergenCode.SOYBEANS.value: AllergenDefinition(
        code=StandardAllergenCode.SOYBEANS.value,
        nombre="Soya",
        nombre_en="Soybeans",
        icono="Bean",
        descripcion="Soya / soja y productos a base de soya.",
        descripcion_en="Soybeans and products thereof.",
    ),
    StandardAllergenCode.MILK.value: AllergenDefinition(
        code=StandardAllergenCode.MILK.value,
        nombre="Lácteos",
        nombre_en="Milk",
        icono="Milk",
        descripcion="Leche y sus derivados (incluida la lactosa).",
        descripcion_en="Milk and dairy products thereof (including lactose).",
    ),
    StandardAllergenCode.NUTS.value: AllergenDefinition(
        code=StandardAllergenCode.NUTS.value,
        nombre="Frutos Secos",
        nombre_en="Tree Nuts",
        icono="Nut",
        descripcion="Frutos de cáscara: almendras, avellanas, nueces, anacardos, pacanas, pistachos, etc.",
        descripcion_en="Tree nuts: almonds, hazelnuts, walnuts, cashews, pecans, pistachios, etc.",
    ),
    StandardAllergenCode.CELERY.value: AllergenDefinition(
        code=StandardAllergenCode.CELERY.value,
        nombre="Apio",
        nombre_en="Celery",
        icono="Carrot",
        descripcion="Apio y productos derivados.",
        descripcion_en="Celery and products thereof.",
    ),
    StandardAllergenCode.MUSTARD.value: AllergenDefinition(
        code=StandardAllergenCode.MUSTARD.value,
        nombre="Mostaza",
        nombre_en="Mustard",
        icono="Soup",
        descripcion="Mostaza y productos derivados.",
        descripcion_en="Mustard and products thereof.",
    ),
    StandardAllergenCode.SESAME.value: AllergenDefinition(
        code=StandardAllergenCode.SESAME.value,
        nombre="Sésamo",
        nombre_en="Sesame",
        icono="Sparkles",
        descripcion="Granos de sésamo / ajonjolí y productos a base de granos de sésamo.",
        descripcion_en="Sesame seeds and products thereof.",
    ),
    StandardAllergenCode.SULPHITES.value: AllergenDefinition(
        code=StandardAllergenCode.SULPHITES.value,
        nombre="Sulfitos",
        nombre_en="Sulphites",
        icono="Wine",
        descripcion="Dióxido de azufre y sulfitos en concentraciones superiores a 10 mg/kg o 10 mg/litro.",
        descripcion_en="Sulphur dioxide and sulphites at concentrations > 10 mg/kg or 10 mg/litre.",
    ),
    StandardAllergenCode.LUPIN.value: AllergenDefinition(
        code=StandardAllergenCode.LUPIN.value,
        nombre="Altramuces",
        nombre_en="Lupin",
        icono="Sprout",
        descripcion="Altramuces / lupino y productos a base de altramuces.",
        descripcion_en="Lupin and products thereof.",
    ),
    StandardAllergenCode.MOLLUSCS.value: AllergenDefinition(
        code=StandardAllergenCode.MOLLUSCS.value,
        nombre="Moluscos",
        nombre_en="Molluscs",
        icono="Shell",
        descripcion="Moluscos y productos a base de moluscos (mejillones, almejas, pulpo, calamares).",
        descripcion_en="Molluscs and products thereof (mussels, clams, squid, octopus).",
    ),
}

# Diccionario de alias / sinónimos para normalización flexible
ALLERGEN_ALIASES: dict[str, str] = {
    # Gluten
    "gluten": "GLUTEN",
    "trigo": "GLUTEN",
    "wheat": "GLUTEN",
    "cebada": "GLUTEN",
    "centeno": "GLUTEN",
    "avena": "GLUTEN",
    # Crustáceos
    "crustaceos": "CRUSTACEANS",
    "crustáceos": "CRUSTACEANS",
    "crustaceans": "CRUSTACEANS",
    "camaron": "CRUSTACEANS",
    "camarón": "CRUSTACEANS",
    "shrimp": "CRUSTACEANS",
    "mariscos_crustaceos": "CRUSTACEANS",
    # Huevos
    "huevos": "EGGS",
    "huevo": "EGGS",
    "eggs": "EGGS",
    "egg": "EGGS",
    # Pescado
    "pescado": "FISH",
    "fish": "FISH",
    # Maní
    "mani": "PEANUTS",
    "maní": "PEANUTS",
    "peanuts": "PEANUTS",
    "peanut": "PEANUTS",
    "cacahuete": "PEANUTS",
    "cacahuate": "PEANUTS",
    # Soya
    "soya": "SOYBEANS",
    "soja": "SOYBEANS",
    "soy": "SOYBEANS",
    "soybeans": "SOYBEANS",
    # Lácteos
    "lacteos": "MILK",
    "lácteos": "MILK",
    "leche": "MILK",
    "milk": "MILK",
    "dairy": "MILK",
    "queso": "MILK",
    # Frutos secos
    "frutos secos": "NUTS",
    "frutos_secos": "NUTS",
    "nuts": "NUTS",
    "tree_nuts": "NUTS",
    "nueces": "NUTS",
    "nuez": "NUTS",
    "almendras": "NUTS",
    # Apio
    "apio": "CELERY",
    "celery": "CELERY",
    # Mostaza
    "mostaza": "MUSTARD",
    "mustard": "MUSTARD",
    # Sésamo
    "sesamo": "SESAME",
    "sésamo": "SESAME",
    "sesame": "SESAME",
    "ajonjoli": "SESAME",
    "ajonjolí": "SESAME",
    # Sulfitos
    "sulfitos": "SULPHITES",
    "sulphites": "SULPHITES",
    "sulfites": "SULPHITES",
    "dioxido_de_azufre": "SULPHITES",
    # Altramuces
    "altramuces": "LUPIN",
    "lupin": "LUPIN",
    "lupino": "LUPIN",
    # Moluscos
    "moluscos": "MOLLUSCS",
    "molluscs": "MOLLUSCS",
    "mollusks": "MOLLUSCS",
}


def normalize_allergen_code(raw: str) -> str | None:
    """Normaliza un código o nombre de alérgeno al código normado canónico en mayúsculas."""
    if not raw or not isinstance(raw, str):
        return None
    cleaned = raw.strip().upper()
    if cleaned in STANDARD_ALLERGENS:
        return cleaned
    lower = raw.strip().lower()
    canonical = ALLERGEN_ALIASES.get(lower)
    if canonical and canonical in STANDARD_ALLERGENS:
        return canonical
    return None


def get_allergen_definition(code: str) -> AllergenDefinition | None:
    """Obtiene la definición normada de un alérgeno a partir de su código o alias."""
    norm = normalize_allergen_code(code)
    if norm:
        return STANDARD_ALLERGENS.get(norm)
    return None


def list_standard_allergens() -> list[AllergenDefinition]:
    """Retorna la lista de los 14 alérgenos normados en orden canónico."""
    return list(STANDARD_ALLERGENS.values())


def resolve_allergen_definitions(codes: Sequence[str]) -> list[AllergenDefinition]:
    """
    Resuelve una secuencia de códigos o alias a una lista ordenada y desduplicada
    de objetos AllergenDefinition. Ignora códigos inválidos o no reconocidos.
    """
    seen: set[str] = set()
    result: list[AllergenDefinition] = []
    for c in codes:
        norm = normalize_allergen_code(c)
        if norm and norm not in seen and norm in STANDARD_ALLERGENS:
            seen.add(norm)
            result.append(STANDARD_ALLERGENS[norm])
    # Ordenamos según el orden estándar normado
    order = list(STANDARD_ALLERGENS.keys())
    result.sort(key=lambda a: order.index(a.code) if a.code in order else 99)
    return result
