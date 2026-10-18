# Regla 02: Estándares Backend (Python 3.12, FastAPI, SQLAlchemy 2 Async, Zero-Any)
- Tipado estricto: `mypy --strict` y `ruff check` deben devolver Exit Code 0. Prohibido usar `Any` no justificado.
- Uso exclusivo de `decimal.Decimal` y `NUMERIC` para dinero, costos, stock, conversiones de unidades y tasas FX (prohibido `float`).
- Todos los esquemas Pydantic v2 de entrada deben declarar `model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)`.
