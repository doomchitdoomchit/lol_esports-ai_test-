"""Exploratory Data Analysis page for the LCK dashboard."""

from __future__ import annotations

from typing import Any, Dict

import pandas as pd
import plotly.express as px
import streamlit as st

from components.sidebar import render_sidebar_filters
from config.colors import CHART_COLORS, COLOR_DISCRETE_MAP
from data_loader import load_data


def _get_active_filters(df_players) -> Dict[str, Any]:
    # Render sidebar and get filters directly
    return render_sidebar_filters(df_players)


def _apply_filters(df, filters: Dict[str, Any]):
    filtered_df = df.copy()
    for column, value in filters.items():
        if value in (None, "", "All"):
            continue
        if column not in filtered_df.columns:
            st.sidebar.warning(f"'{column}' 컬럼이 없어 필터를 건너뜀")
            continue
        filtered_df = filtered_df[filtered_df[column] == value]
    return filtered_df


def _process_champion_stats(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate champion picks, bans, wins, and losses."""
    if df.empty:
        return pd.DataFrame()

    # Process Picks
    pick_cols = [f"pick{i}" for i in range(1, 6)]
    # Subset to avoid conflict with existing 'champion' column
    picks = df[["result"] + pick_cols].melt(id_vars=["result"], value_vars=pick_cols, value_name="champion").dropna(subset=["champion"])
    
    # Calculate Pick Stats
    pick_stats = picks.groupby("champion").agg(
        picks=("champion", "count"),
        wins=("result", "sum")
    ).reset_index()
    pick_stats["losses"] = pick_stats["picks"] - pick_stats["wins"]

    # Process Bans
    ban_cols = [f"ban{i}" for i in range(1, 6)]
    # Subset to avoid conflict
    bans = df[ban_cols].melt(value_vars=ban_cols, value_name="champion").dropna(subset=["champion"])
    ban_stats = bans["champion"].value_counts().reset_index()
    ban_stats.columns = ["champion", "bans"]

    # Merge Stats
    stats = pd.merge(pick_stats, ban_stats, on="champion", how="outer").fillna(0)
    stats["picks"] = stats["picks"].astype(int)
    stats["wins"] = stats["wins"].astype(int)
    stats["losses"] = stats["losses"].astype(int)
    stats["bans"] = stats["bans"].astype(int)
    stats["total_games"] = stats["picks"] + stats["bans"]
    
    # Calculate Rates
    stats["win_rate"] = (stats["wins"] / stats["picks"] * 100).fillna(0)
    stats["loss_rate"] = (stats["losses"] / stats["picks"] * 100).fillna(0)
    
    return stats


def _render_champion_analysis(team_df: pd.DataFrame):
    st.subheader("Champion Analysis (Team Data)")
    
    if team_df.empty:
        st.warning("No team data found.")
        return

    stats = _process_champion_stats(team_df)
    if stats.empty:
        st.warning("No champion statistics could be calculated.")
        return

    # Top Lists
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Most Picked")
        top_picks = stats.nlargest(10, "picks")[["champion", "picks", "wins", "losses"]]
        st.dataframe(top_picks, use_container_width=True, hide_index=True)

    with col2:
        st.markdown("### Most Banned")
        top_bans = stats.nlargest(10, "bans")[["champion", "bans"]]
        st.dataframe(top_bans, use_container_width=True, hide_index=True)

    # Filter for min games for rate stats
    min_games = 18
    rate_stats = stats[stats["picks"] >= min_games]

    col3, col4 = st.columns(2)

    with col3:
        st.markdown(f"### Highest Win Rate (Min {min_games} Games)")
        if not rate_stats.empty:
            top_wins = rate_stats.nlargest(10, "win_rate")[["champion", "win_rate", "picks", "wins", "losses"]]
            # Format rate
            top_wins["win_rate"] = top_wins["win_rate"].map("{:.1f}%".format)
            st.dataframe(top_wins, use_container_width=True, hide_index=True)
        else:
            st.info(f"No champions with >= {min_games} games.")

    with col4:
        st.markdown(f"### Highest Loss Rate (Min {min_games} Games)")
        if not rate_stats.empty:
            top_losses = rate_stats.nlargest(10, "loss_rate")[["champion", "loss_rate", "picks", "wins", "losses"]]
            # Format rate
            top_losses["loss_rate"] = top_losses["loss_rate"].map("{:.1f}%".format)
            st.dataframe(top_losses, use_container_width=True, hide_index=True)
        else:
            st.info(f"No champions with >= {min_games} games.")


def _render_game_analysis(team_df: pd.DataFrame):
    st.subheader("Game Analysis (Team Data)")
    
    if team_df.empty:
        return

    # Side Win Rate
    if "side" in team_df.columns and "result" in team_df.columns:
        st.markdown("### Side Win Rate")
        side_wins = team_df.groupby("side")["result"].mean().reset_index()
        side_wins["result"] = side_wins["result"] * 100
        
        fig_side = px.pie(
            side_wins, 
            names="side", 
            values="result", 
            color="side",
            title="Win Rate by Side (%)",
            color_discrete_map={"Blue": CHART_COLORS.get("blue_side", "blue"), "Red": CHART_COLORS.get("red_side", "red")},
            hole=0.4
        )
        fig_side.update_traces(textposition='inside', textinfo='percent+label', texttemplate='%{label}<br>%{percent:.2%}')
        st.plotly_chart(fig_side, use_container_width=True)

    col1, col2 = st.columns(2)

    # Game Duration
    with col1:
        if "gamelength" in team_df.columns:
            st.markdown("### Game Duration Distribution")
            # Convert seconds to minutes for better readability
            durations = team_df["gamelength"] / 60
            fig_duration = px.histogram(
                durations, 
                nbins=20, 
                title="Game Duration (Minutes)",
                labels={"value": "Minutes"},
                color_discrete_sequence=[CHART_COLORS.get("primary", "blue")]
            )
            fig_duration.update_layout(showlegend=False)
            st.plotly_chart(fig_duration, use_container_width=True)

    # First Objectives Win Rate
    with col2:
        st.markdown("### First Objective Win Rates")
        objectives = ["firstblood", "firstdragon", "firstbaron", "firsttower", "firstherald"]
        obj_data = []
        
        for obj in objectives:
            if obj in team_df.columns and "result" in team_df.columns:
                # Calculate win rate when securing the objective (value == 1)
                subset = team_df[team_df[obj] == 1]
                if not subset.empty:
                    win_rate = subset["result"].mean() * 100
                    obj_data.append({"Objective": obj, "Win Rate": win_rate})
        
        if obj_data:
            obj_df = pd.DataFrame(obj_data)
            fig_obj = px.bar(
                obj_df,
                x="Objective",
                y="Win Rate",
                title="Win Rate when Securing First Objective (%)",
                color="Win Rate",
                color_continuous_scale="Viridis"
            )
            st.plotly_chart(fig_obj, use_container_width=True)


def render_page():
    st.header("Exploratory Data Analysis")

    df_players, df_teams = load_data()
    
    # Apply filters to both datasets
    filters = _get_active_filters(df_players)
    filtered_teams = _apply_filters(df_teams, filters)

    st.caption("Global filters applied. Analysis based on Team Data.")
    
    if filtered_teams.empty:
        st.warning("No data available with current filters.")
        return

    _render_champion_analysis(filtered_teams)
    st.divider()
    _render_game_analysis(filtered_teams)

    # Debug section in expander
    with st.expander("🔧 Debug Info", expanded=False):
        if st.checkbox("Show Filter State", value=False):
            st.json(filters)
            st.write("Filtered Teams shape:", filtered_teams.shape)

    return filtered_teams


filtered_players_df = render_page()
