"""Player vs. Player comparison page with position-based filtering."""

from __future__ import annotations

from typing import Any, Dict

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from components.charts import create_radar_chart
from data_loader import load_data


def _get_active_filters() -> Dict[str, Any]:
    filters = st.session_state.get("filters")
    if not filters:
        st.warning("Global filters are not initialized yet. Showing unfiltered data.")
        return {}
    return filters


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
    filters = _get_active_filters()
    return _apply_filters(df_players, filters)


def _get_player_id_column(df: pd.DataFrame) -> str | None:
    """Find the player ID column name."""
    for col in df.columns:
        if col.lower() in ["playerid", "playername", "participantid"]:
            return col
    return None


def _get_player_metrics(player_data: pd.DataFrame) -> Dict[str, float]:
    """Extract and calculate average metrics for a player."""
    metrics = {}
    
    # KDA is already computed in data_loader
    if "KDA" in player_data.columns:
        metrics["KDA"] = pd.to_numeric(player_data["KDA"], errors="coerce").mean()
    
    # DPM - Damage Per Minute
    dpm_col = None
    for col in player_data.columns:
        if col.lower() == "dpm":
            dpm_col = col
            break
    if dpm_col:
        metrics["DPM"] = pd.to_numeric(player_data[dpm_col], errors="coerce").mean()
    
    # GPM - Gold Per Minute
    gpm_col = None
    for col in player_data.columns:
        if "gpm" in col.lower():
            gpm_col = col
            break
    if gpm_col:
        metrics["GPM"] = pd.to_numeric(player_data[gpm_col], errors="coerce").mean()
    
    # VSPM - Vision Score Per Minute
    vspm_col = None
    for col in player_data.columns:
        if col.lower() == "vspm":
            vspm_col = col
            break
    if vspm_col:
        metrics["VSPM"] = pd.to_numeric(player_data[vspm_col], errors="coerce").mean()
    
    # Fill missing values with 0
    for key in ["KDA", "DPM", "GPM", "VSPM"]:
        if key not in metrics or pd.isna(metrics[key]):
            metrics[key] = 0.0
    
    return metrics


def _create_overlaid_radar_chart(
    stats_a: Dict[str, float],
    stats_b: Dict[str, float],
    player_a_name: str,
    player_b_name: str,
    title: str = "플레이어 성능 비교"
) -> go.Figure:
    """Create an overlaid radar chart comparing two players."""
    # Get all unique categories from both stats
    categories = list(set(list(stats_a.keys()) + list(stats_b.keys())))
    
    # Prepare values for both players
    values_a = [stats_a.get(cat, 0.0) for cat in categories]
    values_b = [stats_b.get(cat, 0.0) for cat in categories]
    
    # Calculate max value for proper scaling
    all_values = values_a + values_b
    max_val = max(all_values) if all_values else 1
    
    fig = go.Figure()
    
    # Add trace for Player A
    fig.add_trace(
        go.Scatterpolar(
            r=values_a,
            theta=categories,
            fill="toself",
            name=player_a_name,
            line=dict(color="#1f77b4", width=2),
            marker=dict(color="#1f77b4"),
            hovertemplate=f"%{{theta}}: %{{r:.2f}} ({player_a_name})<extra></extra>",
        )
    )
    
    # Add trace for Player B
    fig.add_trace(
        go.Scatterpolar(
            r=values_b,
            theta=categories,
            fill="toself",
            name=player_b_name,
            line=dict(color="#ff7f0e", width=2),
            marker=dict(color="#ff7f0e"),
            hovertemplate=f"%{{theta}}: %{{r:.2f}} ({player_b_name})<extra></extra>",
        )
    )
    
    fig.update_layout(
        title=title,
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.1, xanchor="center", x=0.5),
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, max_val * 1.1 if max_val > 0 else 1],
                tickfont=dict(size=11),
                gridcolor="#dfe6e9",
            ),
            angularaxis=dict(tickfont=dict(size=11)),
        ),
        margin=dict(l=20, r=20, t=60, b=40),
    )
    
    return fig


def _create_diverging_bar_chart(
    stats_a: Dict[str, float],
    stats_b: Dict[str, float],
    player_a_name: str,
    player_b_name: str,
    title: str = "통계 차이 비교"
) -> go.Figure:
    """Create a diverging bar chart showing the difference between two players."""
    # Get all unique categories
    categories = list(set(list(stats_a.keys()) + list(stats_b.keys())))
    
    # Calculate differences (Player A - Player B)
    differences = {cat: stats_a.get(cat, 0.0) - stats_b.get(cat, 0.0) for cat in categories}
    
    # Sort by absolute difference for better visualization
    sorted_cats = sorted(categories, key=lambda x: abs(differences[x]), reverse=True)
    diffs = [differences[cat] for cat in sorted_cats]
    
    # Determine colors based on sign
    colors = ["#2ecc71" if diff > 0 else "#e74c3c" if diff < 0 else "#95a5a6" for diff in diffs]
    
    fig = go.Figure()
    
    fig.add_trace(
        go.Bar(
            x=diffs,
            y=sorted_cats,
            orientation="h",
            marker=dict(color=colors),
            hovertemplate="%{y}: %{x:+.2f}<br>" + 
                         f"{player_a_name}: %{{customdata[0]:.2f}}<br>" +
                         f"{player_b_name}: %{{customdata[1]:.2f}}<extra></extra>",
            customdata=[[stats_a.get(cat, 0.0), stats_b.get(cat, 0.0)] for cat in sorted_cats],
        )
    )
    
    fig.update_layout(
        title=title,
        xaxis_title=f"차이 ({player_a_name} - {player_b_name})",
        yaxis_title="메트릭",
        yaxis={"categoryorder": "total ascending"},
        shapes=[
            dict(
                type="line",
                xref="x",
                yref="paper",
                x0=0,
                y0=0,
                x1=0,
                y1=1,
                line=dict(color="#34495e", width=2, dash="dash"),
            )
        ],
        annotations=[
            dict(
                x=0,
                y=1.02,
                xref="x",
                yref="paper",
                text=f"{player_a_name} 유리",
                showarrow=False,
                font=dict(color="#2ecc71", size=10),
                xanchor="right",
            ),
            dict(
                x=0,
                y=1.02,
                xref="x",
                yref="paper",
                text=f"{player_b_name} 유리",
                showarrow=False,
                font=dict(color="#e74c3c", size=10),
                xanchor="left",
            ),
        ],
        hovermode="closest",
    )
    
    return fig


def render_page() -> pd.DataFrame:
    st.header("Player vs. Player Comparison")
    st.caption("같은 포지션의 플레이어만 비교할 수 있습니다.")
    
    filtered_df = _load_filtered_players()
    
    if filtered_df.empty:
        st.warning("필터링된 데이터가 없습니다. 필터를 조정해 주세요.")
        return filtered_df
    
    # Get player ID column
    player_id_col = _get_player_id_column(filtered_df)
    if player_id_col is None:
        st.error("플레이어 ID 컬럼을 찾을 수 없습니다.")
        return filtered_df
    
    # Check for position column
    position_col = None
    for col in filtered_df.columns:
        if col.lower() == "position":
            position_col = col
            break
    
    if position_col is None:
        st.error("포지션 컬럼을 찾을 수 없습니다.")
        return filtered_df
    
    # Get unique players
    unique_players = filtered_df[player_id_col].dropna().unique().tolist()
    if not unique_players:
        st.warning("선택할 플레이어가 없습니다.")
        return filtered_df
    
    # Sort players for better UX
    unique_players = sorted(unique_players, key=str)
    
    # Create two-column layout
    col1, col2 = st.columns(2)
    
    # Player A selector
    with col1:
        st.subheader("Player A")
        player_a = st.selectbox(
            "플레이어 A 선택",
            options=unique_players,
            key="player_comparison_a"
        )
    
    # Player B selector (dependent on Player A's position)
    with col2:
        st.subheader("Player B")
        
        if not player_a:
            st.info("먼저 Player A를 선택해 주세요.")
            player_b = None
        else:
            # Get Player A's position
            player_a_data = filtered_df[filtered_df[player_id_col] == player_a]
            if player_a_data.empty:
                st.warning(f"{player_a} 플레이어의 데이터를 찾을 수 없습니다.")
                player_b = None
            else:
                pos_a = player_a_data[position_col].iloc[0] if not player_a_data[position_col].empty else None
                
                if pos_a is None or pd.isna(pos_a):
                    st.warning(f"{player_a} 플레이어의 포지션을 찾을 수 없습니다.")
                    player_b = None
                else:
                    # Display Player A's position
                    st.caption(f"Player A 포지션: **{pos_a}**")
                    
                    # Filter players with the same position (excluding Player A)
                    eligible_players = filtered_df[
                        (filtered_df[position_col] == pos_a) & 
                        (filtered_df[player_id_col] != player_a)
                    ][player_id_col].dropna().unique().tolist()
                    
                    if not eligible_players:
                        st.warning(f"{pos_a} 포지션의 다른 플레이어가 없습니다.")
                        player_b = None
                    else:
                        eligible_players = sorted(eligible_players, key=str)
                        player_b = st.selectbox(
                            "플레이어 B 선택 (같은 포지션만 표시됨)",
                            options=eligible_players,
                            key="player_comparison_b"
                        )
    
    # Display comparison if both players are selected
    if player_a and player_b:
        st.divider()
        
        # Get data for both players
        player_a_data = filtered_df[filtered_df[player_id_col] == player_a].copy()
        player_b_data = filtered_df[filtered_df[player_id_col] == player_b].copy()
        
        if player_a_data.empty or player_b_data.empty:
            st.warning("플레이어 데이터를 불러올 수 없습니다.")
            return filtered_df
        
        # Calculate metrics for both players
        stats_a = _get_player_metrics(player_a_data)
        stats_b = _get_player_metrics(player_b_data)
        
        # Display basic info
        info_col1, info_col2 = st.columns(2)
        
        with info_col1:
            st.metric("Player A 경기 수", len(player_a_data))
            if "result" in player_a_data.columns:
                wins_a = pd.to_numeric(player_a_data["result"], errors="coerce").sum()
                win_rate_a = (wins_a / len(player_a_data) * 100) if len(player_a_data) > 0 else 0
                st.metric("Player A 승률", f"{win_rate_a:.1f}%")
        
        with info_col2:
            st.metric("Player B 경기 수", len(player_b_data))
            if "result" in player_b_data.columns:
                wins_b = pd.to_numeric(player_b_data["result"], errors="coerce").sum()
                win_rate_b = (wins_b / len(player_b_data) * 100) if len(player_b_data) > 0 else 0
                st.metric("Player B 승률", f"{win_rate_b:.1f}%")
        
        st.divider()
        
        # Create comparison charts
        chart_col1, chart_col2 = st.columns(2)
        
        with chart_col1:
            st.subheader("레이더 차트 비교")
            radar_fig = _create_overlaid_radar_chart(
                stats_a,
                stats_b,
                player_a,
                player_b,
                title=f"{player_a} vs {player_b}"
            )
            st.plotly_chart(radar_fig, use_container_width=True)
        
        with chart_col2:
            st.subheader("통계 차이 비교")
            diverging_fig = _create_diverging_bar_chart(
                stats_a,
                stats_b,
                player_a,
                player_b,
                title=f"{player_a} vs {player_b}"
            )
            st.plotly_chart(diverging_fig, use_container_width=True)
        
        # Debug option
        if st.checkbox("디버그: 플레이어 통계 표시", value=False):
            debug_col1, debug_col2 = st.columns(2)
            with debug_col1:
                st.write(f"**{player_a} 통계:**")
                st.json(stats_a)
            with debug_col2:
                st.write(f"**{player_b} 통계:**")
                st.json(stats_b)
    
    return filtered_df


filtered_players_df = render_page()

