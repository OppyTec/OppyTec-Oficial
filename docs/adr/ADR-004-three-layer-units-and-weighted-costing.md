# ADR-004: Motor Matemático de Conversión de 3 Capas y Costo Promedio Ponderado con `Decimal`

- **Estado:** Aprobado e Inmutable
- **Fecha:** 2026-10-19
- **Estrategia de Referencia:** `specs/02-TRD.md` / `.agent/rules/03-clean-architecture-and-ddd.md`

---

## 1. Contexto

En la operación gastronómica y hotelera de `OppyTec-Legacy`, un mismo insumo se compra en un formato logístico (Capa 1: ej. `Caja` de 12 botellas), se almacena y controla en bodega en una unidad de inventario (Capa 2: ej. `Botella` de 750 ml) y se dosifica en recetas o porciones de venta en una unidad de consumo (Capa 3: ej. `ml` o `gramos`). El uso de punto flotante binario (`float` IEEE 754) introduce errores de redondeo acumulativos en el Kardex y en el cálculo del Costo Promedio Ponderado (CPP).

## 2. Decisión

Preservar con **paridad matemática 100% respecto a `OppyTec-Legacy`** el modelo de conversión de 3 capas de unidades e implementar todos los cálculos de stock, recetas y finanzas exclusivamente con **`decimal.Decimal` (`NUMERIC(18, 6)` en PostgreSQL)**:

1. **Fórmula de Conversión de 3 Capas (`Capa 1 -> Capa 2 -> Capa 3`):**
   - `factor_compra_a_bodega` ($F_{1\to 2}$) y `factor_bodega_a_consumo` ($F_{2\to 3}$).
   - Toda entrada por factura en Capa 1 se normaliza a Capa 2 y Capa 3 sin pérdida de precisión empleando `ROUND_HALF_UP`.
2. **Costo Promedio Ponderado (CPP / WAC):**
   $$\text{CPP}_{\text{nuevo}} = \frac{(\text{Stock}_{\text{actual}} \times \text{CPP}_{\text{actual}}) + (\text{Cantidad}_{\text{entrada}} \times \text{Costo}_{\text{entrada}})}{\text{Stock}_{\text{actual}} + \text{Cantidad}_{\text{entrada}}}$$
3. **Prohibición Absoluta de `float`:** Ninguna entidad de dominio, esquema Pydantic ni columna SQL de precios, cantidades o factores de conversión puede usar `float`.

## 3. Consecuencias

- **Positivas:**
  - Exactitud contable bancaria sin deriva de decimales tras millones de movimientos de Kardex y explosiones recursivas de sub-recetas.
  - Paridad 1:1 auditable frente al motor histórico de `OppyTec-Legacy`.
- **Negativas / Trade-offs:**
  - Ligero overhead de serialización respecto a `float`, mitigado mediante el uso de `Pydantic v2` (núcleo Rust) y `orjson`.

## 4. Verificación Determinista en Tests

- **Suite de Caja Blanca y Paridad:** `oppytec-backend/tests/architecture/test_fx_currency_precision_and_governance.py`, `test_module_test_parity.py` y pruebas `Hypothesis` sobre el motor de conversión de 3 capas.
- **Invariante Verificada:** Escaneo AST que bloquea cualquier anotación `: float` en módulos financieros o de inventario, y pruebas de propiedad con `Hypothesis` que validan la reversibilidad y exactitud contra las fórmulas de `OppyTec-Legacy`.
