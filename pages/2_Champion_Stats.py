"""Champion-level insights for pick/win/ban trends."""

from __future__ import annotations

from typing import Any, Dict

import pandas as pd
import plotly.express as px
import streamlit as st

from components.sidebar import render_sidebar_filters
from components.data_loader import load_data
from components.utils import apply_filters

st.set_page_config(layout="wide")








def _load_filtered_players() -> pd.DataFrame:
    df_players, _ = load_data()
    filters = render_sidebar_filters(df_players)
    return apply_filters(df_players, filters)


def _calculate_champion_stats(filtered_df: pd.DataFrame) -> pd.DataFrame:
    """Calculate champion-specific statistics including win rate, pick rate, and ban rate."""
    if filtered_df.empty:
        return pd.DataFrame()

    # Calculate win rate and pick count by champion
    # We use 'gameplay' as the count of games played (picks)
    # Merge positions into a string
    champ_stats = filtered_df.groupby("champion").agg(
        win_rate=("result", lambda x: pd.to_numeric(x, errors="coerce").mean() * 100),
        gameplay=("champion", "count"),
        position=("position", lambda x: "/".join(sorted(x.unique())))
    ).reset_index()

    # Calculate total games (unique game IDs)
    if "gameid" in filtered_df.columns:
        total_games = filtered_df["gameid"].nunique()
        unique_games_df = filtered_df.drop_duplicates(subset=["gameid"])
    else:
        # Fallback if no gameid (unlikely in this dataset)
        total_games = len(filtered_df) / 10
        unique_games_df = filtered_df

    # Calculate pick rate (picks per game)
    champ_stats["pick_rate"] = champ_stats["gameplay"] / total_games * 100 if total_games > 0 else 0

    # Calculate ban counts from ban columns (ban1-ban5)
    # Bans are global per champion, so we count them from unique games
    ban_columns = [col for col in filtered_df.columns if col.startswith("ban") and col[3:].isdigit()]
    ban_counts = {}
    
    for _, row in unique_games_df.iterrows():
        for ban_col in ban_columns:
            ban_champ = row[ban_col]
            if pd.notna(ban_champ) and ban_champ != "":
                ban_counts[ban_champ] = ban_counts.get(ban_champ, 0) + 1

    # Create Ban Dataframe
    ban_df = pd.DataFrame(list(ban_counts.items()), columns=["champion", "ban_count"])
    ban_df["ban_rate"] = ban_df["ban_count"] / total_games * 100 if total_games > 0 else 0

    # Merge Ban Rate into Stats
    # We merge on 'champion'.
    champ_stats = champ_stats.merge(ban_df[["champion", "ban_rate"]], on="champion", how="left")
    champ_stats["ban_rate"] = champ_stats["ban_rate"].fillna(0)

    # Calculate P+B%
    champ_stats["p_b_rate"] = champ_stats["pick_rate"] + champ_stats["ban_rate"]

    # Fill missing values
    champ_stats["win_rate"] = champ_stats["win_rate"].fillna(0)
    
    # Sort by Gameplay desc
    champ_stats = champ_stats.sort_values("gameplay", ascending=False)

    return champ_stats


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

    # Display Table
    st.subheader("Champion Statistics Table")
    
    # Format for display
    display_cols = ["champion", "position", "gameplay", "pick_rate", "ban_rate", "p_b_rate", "win_rate"]
    display_df = champ_stats[display_cols].copy()
    
    # Rename columns for display
    display_df.columns = ["Champion", "Position", "Gameplay", "Pick%", "Ban%", "P+B%", "Win%"]
    
    st.dataframe(
        display_df,
        column_config={
            "Pick%": st.column_config.NumberColumn(format="%.1f%%"),
            "Ban%": st.column_config.NumberColumn(format="%.1f%%"),
            "P+B%": st.column_config.NumberColumn(format="%.1f%%"),
            "Win%": st.column_config.NumberColumn(format="%.1f%%"),
        },
        width="stretch",
        hide_index=True
    )
    
    # Debug section in expander
    with st.expander("🔧 디버그 정보", expanded=False):
        if st.checkbox("필터링된 데이터 미리보기", value=False):
            st.write("Shape:", filtered_df.shape)
            st.dataframe(filtered_df.head(), width="stretch")

    return filtered_df


filtered_players_df = render_page()
