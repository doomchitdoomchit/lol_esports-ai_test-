"""Streamlit entry point for the LOL Esports analytics dashboard."""

from __future__ import annotations

from typing import Any, Dict, List, Sequence, Tuple

import streamlit as st

from data_loader import load_data

st.set_page_config(page_title="LCK Analytics", layout="wide")

# Apply custom CSS for improved visual hierarchy
st.markdown("""
<style>
    /* Improve header and subheader styling */
    h1 {
        margin-bottom: 0.5rem;
        font-weight: 600;
    }
    
    h2 {
        margin-top: 1rem;
        margin-bottom: 0.5rem;
        font-weight: 500;
        font-size: 1.5rem;
    }
    
    h3 {
        margin-top: 0.75rem;
        margin-bottom: 0.5rem;
        font-weight: 500;
        font-size: 1.2rem;
    }
    
    /* Improve spacing for captions */
    .stCaption {
        margin-bottom: 1rem;
    }
    
    /* Improve metric card spacing */
    [data-testid="stMetricValue"] {
        font-size: 2rem;
    }
    
    /* Improve container spacing */
    .stContainer {
        padding: 0.5rem 0;
    }
    
    /* Improve expander styling */
    .streamlit-expanderHeader {
        font-weight: 500;
    }
    
    /* Reduce excessive padding in plotly charts */
    .js-plotly-plot {
        margin: 0;
    }
    
    /* Improve divider visibility */
    hr {
        margin: 1rem 0;
        border: none;
        border-top: 1px solid #e0e0e0;
    }
</style>
""", unsafe_allow_html=True)

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


def _render_sidebar_filters(df_players) -> Dict[str, Any]:
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

        selection = st.sidebar.selectbox(
            label,
            options=options,
            index=0,
            key=f"filter-{column}",
        )
        filters[column] = None if selection == ALL_OPTION else selection

    st.sidebar.caption("필터는 세션 전체에서 공유됩니다.")
    with st.sidebar.expander("선택된 필터", expanded=False):
        st.json(filters)

    st.session_state["filters"] = filters
    return filters


def main() -> Dict[str, Any]:
    """Render the base layout with preloaded datasets and sidebar filters."""

    df_players, df_teams = load_data()
    filters = _render_sidebar_filters(df_players)

    st.title("LOL Esports (LCK) Insights")
    st.caption("Explore player and team level trends across seasons.")

    if st.sidebar.checkbox("Show sample data", value=False):
        st.subheader("Sample player rows")
        st.dataframe(df_players.head())
        st.subheader("Sample team rows")
        st.dataframe(df_teams.head())

    return {
        "players": df_players,
        "teams": df_teams,
        "filters": filters,
    }


if __name__ == "__main__":
    main()

