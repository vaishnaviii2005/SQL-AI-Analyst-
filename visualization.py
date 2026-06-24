"""Plotly chart builder for query results."""

from __future__ import annotations

from typing import Any

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

DARK_LAYOUT = dict(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter, sans-serif", color="#e2e8f0"),
    margin=dict(l=40, r=20, t=50, b=40),
    height=380,
)


def _resolve_columns(df: pd.DataFrame, x_col: str | None, y_col: str | None) -> tuple[str, str]:
    if x_col in df.columns and y_col in df.columns:
        return x_col, y_col
    if len(df.columns) >= 2:
        return str(df.columns[0]), str(df.columns[1])
    raise ValueError("Not enough columns to chart")


def build_plotly_figure(rows: list[dict], chart_config: dict[str, Any]) -> go.Figure:
    """Build an interactive Plotly figure from query rows and LLM chart config."""
    df = pd.DataFrame(rows)
    if df.empty:
        fig = go.Figure()
        fig.update_layout(**DARK_LAYOUT, title="No data to display")
        return fig

    chart_type = chart_config.get("type", "table")
    title = chart_config.get("title", "Query Results")
    color = chart_config.get("color", "#6366f1")

    if chart_type == "table" or len(df.columns) < 2:
        fig = go.Figure(
            data=[go.Table(
                header=dict(values=list(df.columns), fill_color="#1c2030", font=dict(color="#94a3b8")),
                cells=dict(values=[df[c].astype(str) for c in df.columns], fill_color="#151821"),
            )]
        )
        fig.update_layout(**DARK_LAYOUT, title=title, height=420)
        return fig

    x_col, y_col = _resolve_columns(df, chart_config.get("x_col"), chart_config.get("y_col"))

    if chart_type == "line":
        fig = px.line(df, x=x_col, y=y_col, title=title, markers=True)
        fig.update_traces(line_color="#10b981", marker_color="#10b981")
    elif chart_type == "pie":
        fig = px.pie(df, names=x_col, values=y_col, title=title, hole=0.45)
        fig.update_traces(marker=dict(line=dict(color="#1c2030", width=2)))
    elif chart_type == "scatter":
        fig = px.scatter(df, x=x_col, y=y_col, title=title, color_discrete_sequence=[color])
    else:
        fig = px.bar(df, x=x_col, y=y_col, title=title, color_discrete_sequence=[color])
        fig.update_traces(marker_line_width=0)

    fig.update_layout(**DARK_LAYOUT)
    fig.update_xaxes(gridcolor="rgba(42,47,69,0.6)")
    fig.update_yaxes(gridcolor="rgba(42,47,69,0.6)")
    return fig


def figure_to_json(fig: go.Figure) -> str:
    return fig.to_json()
