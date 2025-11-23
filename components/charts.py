"""Chart utilities shared across Streamlit pages."""

from __future__ import annotations

from collections import OrderedDict
from typing import Iterable, Mapping, MutableMapping, Sequence

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from config.colors import CHART_COLORS, QUALITATIVE_COLORS

DEFAULT_TRACE_COLOR = CHART_COLORS["primary"]
QUAL_COLORS = QUALITATIVE_COLORS


def _normalize_stats(stats_data: Mapping | MutableMapping | pd.Series | pd.DataFrame) -> OrderedDict[str, float]:
    """Convert supported inputs into an ordered mapping of numeric stats."""

    if isinstance(stats_data, pd.Series):
        iterable = stats_data.items()
    elif isinstance(stats_data, pd.DataFrame):
        if stats_data.shape[0] != 1:
            raise ValueError("DataFrame input must contain exactly one row for radar charts.")
        iterable = stats_data.iloc[0].items()
    elif isinstance(stats_data, Mapping):
        iterable = stats_data.items()
    else:
        raise TypeError("stats_data must be a mapping, pandas Series, or single-row DataFrame.")

    ordered: OrderedDict[str, float] = OrderedDict()
    for key, value in iterable:
        if value is None or (isinstance(value, float) and np.isnan(value)):
            continue
        try:
            ordered[str(key)] = float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Stat '{key}' must be numeric.") from exc

    if not ordered:
        raise ValueError("At least one numeric stat is required for the radar chart.")

    return ordered


def _ensure_series(stats_data: Iterable | Mapping | pd.Series | pd.DataFrame) -> list[OrderedDict[str, float]]:
    """Normalize single or multiple stat collections into ordered dictionaries."""

    if isinstance(stats_data, (Mapping, pd.Series, pd.DataFrame)):
        series_list = [stats_data]
    else:
        series_list = list(stats_data)  # type: ignore[arg-type]
        if not series_list:
            raise ValueError("At least one series is required to build a radar chart.")

    return [_normalize_stats(entry) for entry in series_list]


def create_radar_chart(
    stats_data: Mapping | MutableMapping | pd.Series | pd.DataFrame | Sequence,
    title: str,
    labels: Sequence[str] | None = None,
    radar_range: tuple[float, float] | None = None,
    trace_color: str | None = None,
) -> go.Figure:
    """Build a radar chart from one or multiple stat collections.

    Args:
        stats_data: Single mapping/Series/DataFrame row or a sequence of them.
        title: Title rendered above the chart.
        labels: Optional labels for each trace; defaults to the title for single trace.
        radar_range: Optional manual override for radial axis range ``(min, max)``.
        trace_color: Backwards-compatible color override for single-trace charts.
    """

    series = _ensure_series(stats_data)
    if labels is None:
        labels = [title] if len(series) == 1 else [f"Series {idx + 1}" for idx in range(len(series))]
    if len(labels) != len(series):
        raise ValueError("labels length must match the number of series provided.")

    categories: list[str] = []
    for stats in series:
        for key in stats.keys():
            if key not in categories:
                categories.append(key)

    color_cycle = QUAL_COLORS or [DEFAULT_TRACE_COLOR]
    fig = go.Figure()
    all_values: list[float] = []

    for idx, (stats, label) in enumerate(zip(series, labels)):
        values = [stats.get(cat, 0.0) for cat in categories]
        all_values.extend(values)
        color = trace_color if len(series) == 1 and trace_color else color_cycle[idx % len(color_cycle)]
        fig.add_trace(
            go.Scatterpolar(
                r=values,
                theta=categories,
                fill="toself",
                name=label,
                line=dict(color=color, width=2),
                marker=dict(color=color),
                hovertemplate="%{theta}: %{r:.2f}<extra></extra>",
            )
        )

    computed_max = max(all_values) if all_values else 1
    radial_min, radial_max = radar_range if radar_range else (0, computed_max * 1.1 or 1)

    fig.update_layout(
        title=title,
        showlegend=len(series) > 1,
        legend=dict(orientation="h", yanchor="bottom", y=-0.1, xanchor="center", x=0.5),
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[radial_min, radial_max],
                tickfont=dict(size=11),
                gridcolor="#dfe6e9",
            ),
            angularaxis=dict(tickfont=dict(size=11)),
        ),
        margin=dict(l=20, r=20, t=60, b=40),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )

    return fig

