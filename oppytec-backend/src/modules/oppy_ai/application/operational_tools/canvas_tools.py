"""
Herramientas de Renderizado para el Canvas Analítico de OppyFy (Split-View Canvas).
Genera artefactos estructurados para tablas dinámicas y gráficos interactivos (Recharts).
"""
from __future__ import annotations

from typing import Any

from src.core.observability import trace_span
from src.modules.oppy_ai.domain.oppyfy_rbac import hardcoded_data_stripping


@hardcoded_data_stripping
def render_canvas_table(
    title: str,
    columns: list[str],
    rows: list[list[Any]],
    *,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Genera la carga estructurada para renderizar una tabla analítica en el Canvas lateral.
    """
    with trace_span(
        "oppyfy.tool.render_canvas_table",
        attributes={"tool": "render_canvas_table", "title": title},
        tracer_name="oppytec.oppyfy",
    ):
        return {
            "artifact_type": "canvas_table",
            "title": title,
            "columns": columns,
            "rows": rows,
            "total_rows": len(rows),
            "metadata": metadata or {},
        }


@hardcoded_data_stripping
def render_canvas_chart(
    chart_type: str,
    title: str,
    series: list[dict[str, Any]],
    *,
    categories: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Genera la carga estructurada para renderizar un gráfico Recharts (bar, line, pie)
    en el Canvas lateral de OppyFy.
    """
    with trace_span(
        "oppyfy.tool.render_canvas_chart",
        attributes={"tool": "render_canvas_chart", "chart_type": chart_type, "title": title},
        tracer_name="oppytec.oppyfy",
    ):
        return {
            "artifact_type": "canvas_chart",
            "chart_type": chart_type,
            "title": title,
            "categories": categories or [],
            "series": series,
            "metadata": metadata or {},
        }
