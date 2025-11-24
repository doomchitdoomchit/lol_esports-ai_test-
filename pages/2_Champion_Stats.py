"""Champion-level insights for pick/win/ban trends."""

from __future__ import annotations

from typing import Any, Dict

import pandas as pd
import plotly.express as px
import streamlit as st

from components.sidebar import render_sidebar_filters
from data_loader import load_data

st.set_page_config(layout="wide")





def _apply_filters(df: pd.DataFrame, filters: Dict[str, Any]) -> pd.DataFrame:
    filtered = df.copy()
    for column, value in filters.items():
        if value in (None, "", "All"):
            continue
        if column not in filtered.columns:
            st.sidebar.warning(f"'{column}' 컬럼이 없어 필터를 건너뜀")
            continue
        filtered = filtered[filtered[column] == value]
    return filtered


def _load_filtered_players() -> pd.DataFrame:
    df_players, _ = load_data()
    filters = render_sidebar_filters(df_players)
    return _apply_filters(df_players, filters)


def _calculate_champion_stats(filtered_df: pd.DataFrame) -> pd.DataFrame:
    """Calculate champion-specific statistics including win rate, pick rate, and ban rate."""
    if filtered_df.empty:
        return pd.DataFrame()

    # Calculate win rate and pick count by champion
    champ_stats = filtered_df.groupby("champion").agg(
        win_rate=("result", lambda x: pd.to_numeric(x, errors="coerce").mean()),
        pick_count=("champion", "count"),
    )

    # Calculate total games (unique game IDs)
    total_games = filtered_df["gameid"].nunique() if "gameid" in filtered_df.columns else len(filtered_df)

    # Calculate pick rate (picks per game)
    # Each game has 10 picks (5 per team), so we need to normalize
    champ_stats["pick_rate"] = champ_stats["pick_count"] / total_games if total_games > 0 else 0

    # Calculate ban counts from ban columns (ban1-ban5)
    ban_columns = [col for col in filtered_df.columns if col.startswith("ban") and col[3:].isdigit()]
    ban_counts = {}
    
    for _, row in filtered_df.iterrows():
        for ban_col in ban_columns:
            ban_champ = row[ban_col]
            if pd.notna(ban_champ) and ban_champ != "":
                ban_counts[ban_champ] = ban_counts.get(ban_champ, 0) + 1

    # Convert ban counts to Series and calculate ban rate
    ban_series = pd.Series(ban_counts, name="ban_count")
    champ_stats = champ_stats.join(ban_series, how="outer")
    champ_stats["ban_count"] = champ_stats["ban_count"].fillna(0)
    champ_stats["ban_rate"] = champ_stats["ban_count"] / total_games if total_games > 0 else 0

    # Fill missing values
    champ_stats["win_rate"] = champ_stats["win_rate"].fillna(0)
    champ_stats["pick_count"] = champ_stats["pick_count"].fillna(0)
    champ_stats["pick_rate"] = champ_stats["pick_rate"].fillna(0)

    return champ_stats


def _create_pick_win_scatter(champ_stats: pd.DataFrame):
    """Create a scatter plot visualizing pick rate vs win rate."""
    if champ_stats.empty:
        st.info("표시할 챔피언 데이터가 없습니다.")
        return

    fig = px.scatter(
        champ_stats,
        x="pick_rate",
        y="win_rate",
        hover_name=champ_stats.index,
        labels={
            "pick_rate": "Pick Rate (picks per game)",
            "win_rate": "Win Rate",
        },
        title="Pick Rate vs Win Rate",
    )
    fig.update_traces(marker=dict(size=8, opacity=0.6))
    fig.update_layout(
        xaxis_title="Pick Rate",
        yaxis_title="Win Rate",
        hovermode="closest",
    )
    return fig


def _create_top_banned_chart(champ_stats: pd.DataFrame):
    """Create a horizontal bar chart for top 10 most banned champions."""
    if champ_stats.empty:
        st.info("표시할 밴 데이터가 없습니다.")
        return None

    # Sort by ban rate and get top 10
    top_banned = champ_stats.nlargest(10, "ban_rate")

    if top_banned.empty:
        st.info("밴 데이터가 없습니다.")
        return None

    fig = px.bar(
        top_banned,
        x="ban_rate",
        y=top_banned.index,
        orientation="h",
        labels={
            "ban_rate": "Ban Rate (bans per game)",
            "y": "Champion",
        },
        title="Top 10 Most Banned Champions",
    )
    fig.update_layout(
        yaxis={"categoryorder": "total ascending"},
        xaxis_title="Ban Rate",
        yaxis_title="",
    )
    return fig


def render_page() -> pd.DataFrame:
    st.header("Champion Stats")
    filtered_df = _load_filtered_players()
    st.caption("현재 글로벌 필터를 반영한 챔피언별 데이터입니다.")

    if filtered_df.empty:
        st.warning("필터링된 데이터가 없습니다. 필터를 조정해 주세요.")
        return filtered_df

    # Calculate champion statistics
    champ_stats = _calculate_champion_stats(filtered_df)

    if champ_stats.empty:
        st.info("챔피언 통계를 계산할 수 없습니다.")
        return filtered_df

    # Create two columns for side-by-side layout in a container
    with st.container():
        col1, col2 = st.columns(2)

        # Scatter plot: Pick Rate vs Win Rate
        with col1:
            scatter_fig = _create_pick_win_scatter(champ_stats)
            if scatter_fig:
                st.plotly_chart(scatter_fig, use_container_width=True)

        # Bar chart: Top 10 Banned Champions
        with col2:
            ban_fig = _create_top_banned_chart(champ_stats)
            if ban_fig:
                st.plotly_chart(ban_fig, use_container_width=True)
    
    # Debug section in expander
    with st.expander("🔧 디버그 정보", expanded=False):
        if st.checkbox("필터링된 데이터 미리보기", value=False):
            st.write("Shape:", filtered_df.shape)
            st.dataframe(filtered_df.head(), width="stretch")

    return filtered_df


filtered_players_df = render_page()
