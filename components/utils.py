"""Utility functions for the LCK dashboard."""

from typing import Any, Dict

import pandas as pd
import streamlit as st


def apply_filters(df: pd.DataFrame, filters: Dict[str, Any]) -> pd.DataFrame:
    """Apply a dictionary of filters to a DataFrame.
    
    Args:
        df: The DataFrame to filter.
        filters: A dictionary where keys are column names and values are filter values.
                 Values of None, "", or "All" are ignored.
                 
    Returns:
        The filtered DataFrame.
    """
    filtered_df = df.copy()
    for column, value in filters.items():
        if value in (None, "", "All"):
            continue
        if column not in filtered_df.columns:
            st.sidebar.warning(f"'{column}' 컬럼이 없어 필터를 건너뜀")
            continue
        filtered_df = filtered_df[filtered_df[column] == value]
    return filtered_df
