"""Reusable sidebar component for global filters."""

from __future__ import annotations

from typing import Any, Dict, List, Sequence, Tuple

import streamlit as st

ALL_OPTION = "All"
FILTER_CONFIG: Sequence[Tuple[str, str]] = (
    ("year", "Year"),
    ("split", "Split"),
    ("playoffs", "Playoff"),
    ("patch", "Patch"),
)


def _sorted_unique(series: Any) -> List[Any]:
    values = series.dropna().unique().tolist()
    if not values:
        return []
    try:
        return sorted(values)
    except TypeError:
        return sorted(values, key=lambda value: str(value))


def render_sidebar_filters(df_players) -> Dict[str, Any]:
    """Render the global sidebar filters and return the selected values."""
    st.sidebar.title("LCK Global Filters")
    filters: Dict[str, Any] = {}

    for column, label in FILTER_CONFIG:
        if column not in df_players.columns:
            st.sidebar.warning(f"Missing '{column}' column in dataset.")
            filters[column] = None
            continue

        options = [ALL_OPTION] + _sorted_unique(df_players[column])
        if len(options) == 1:
            st.sidebar.warning(f"No data available for {label} filter.")
            filters[column] = None
            continue

        # Use session state to initialize if available
        key = f"filter-{column}"
        default_index = 0
        
        # If the key exists in session state, Streamlit handles it, 
        # but we can also explicitly check previous filters if needed.
        # For now, we rely on Streamlit's widget key persistence.

        selection = st.sidebar.selectbox(
            label,
            options=options,
            index=default_index,
            key=key,
        )
        filters[column] = None if selection == ALL_OPTION else selection

    st.sidebar.caption("필터는 세션 전체에서 공유됩니다.")
    with st.sidebar.expander("선택된 필터", expanded=False):
        st.json(filters)

    st.session_state["filters"] = filters
    return filters
