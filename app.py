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

from components.sidebar import render_sidebar_filters


def main() -> Dict[str, Any]:
    """Render the base layout with preloaded datasets and sidebar filters."""

    df_players, df_teams = load_data()
    filters = render_sidebar_filters(df_players)

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

