"""Player-level profile page with performance indicators and trends."""

from __future__ import annotations

from typing import Any, Dict

import pandas as pd
import plotly.express as px
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
    
    # GPM - Gold Per Minute (check for 'gpm' or 'earned gpm')
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


def _create_radar_chart_for_player(player_data: pd.DataFrame, player_id: str):
    """Create a radar chart for player performance metrics."""
    if player_data.empty:
        st.info("플레이어 데이터가 없어 레이더 차트를 생성할 수 없습니다.")
        return None
    
    metrics = _get_player_metrics(player_data)
    
    if not metrics or all(v == 0.0 for v in metrics.values()):
        st.warning("표시할 성능 지표가 없습니다.")
        return None
    
    radar_fig = create_radar_chart(
        metrics,
        title=f"{player_id} 성능 지표",
        trace_color="#1f77b4"
    )
    return radar_fig


def _create_trend_line(player_data: pd.DataFrame, player_id: str, metric: str = "KDA"):
    """Create a trend line chart showing metric over time (Patch)."""
    if player_data.empty:
        st.info("플레이어 데이터가 없어 트렌드 차트를 생성할 수 없습니다.")
        return None
    
    # Determine metric column
    metric_col = None
    if metric == "KDA":
        metric_col = "KDA"
    elif metric == "DPM":
        for col in player_data.columns:
            if col.lower() == "dpm":
                metric_col = col
                break
    elif metric == "GPM":
        for col in player_data.columns:
            if "gpm" in col.lower():
                metric_col = col
                break
    elif metric == "VSPM":
        for col in player_data.columns:
            if col.lower() == "vspm":
                metric_col = col
                break
    
    if metric_col is None or metric_col not in player_data.columns:
        st.warning(f"{metric} 메트릭을 찾을 수 없습니다.")
        return None
    
    # Get Patch column for x-axis
    patch_col = None
    for col in player_data.columns:
        if col.lower() == "patch":
            patch_col = col
            break
    
    if patch_col is None:
        st.warning("Patch 컬럼을 찾을 수 없습니다.")
        return None
    
    # Prepare data for trend line
    trend_df = player_data[[patch_col, metric_col]].copy()
    trend_df[metric_col] = pd.to_numeric(trend_df[metric_col], errors="coerce")
    trend_df = trend_df.dropna(subset=[patch_col, metric_col])
    
    if trend_df.empty:
        st.info("트렌드 차트를 그릴 데이터가 없습니다.")
        return None
    
    # Sort by patch for proper trend visualization
    try:
        trend_df = trend_df.sort_values(by=patch_col)
    except Exception:
        # If sorting fails, just use the data as-is
        pass
    
    # Group by patch and calculate mean for cleaner trend
    trend_agg = trend_df.groupby(patch_col)[metric_col].mean().reset_index()
    
    fig = px.line(
        trend_agg,
        x=patch_col,
        y=metric_col,
        title=f"{player_id} {metric} 트렌드",
        markers=True
    )
    fig.update_layout(
        xaxis_title="Patch",
        yaxis_title=metric,
        hovermode="x unified"
    )
    
    return fig


def render_page() -> pd.DataFrame:
    st.header("Player Profile")
    
    filtered_df = _load_filtered_players()
    st.caption("현재 글로벌 필터를 반영한 플레이어 데이터입니다.")
    
    if filtered_df.empty:
        st.warning("필터링된 데이터가 없습니다. 필터를 조정해 주세요.")
        return filtered_df
    
    # Get unique player IDs
    player_id_col = None
    for col in filtered_df.columns:
        if col.lower() in ["playerid", "playername", "participantid"]:
            player_id_col = col
            break
    
    if player_id_col is None:
        st.error("플레이어 ID 컬럼을 찾을 수 없습니다.")
        return filtered_df
    
    unique_players = filtered_df[player_id_col].dropna().unique().tolist()
    
    if not unique_players:
        st.warning("선택할 플레이어가 없습니다.")
        return filtered_df
    
    # Sort players for better UX
    unique_players = sorted(unique_players, key=str)
    
    # Player selector
    selected_player = st.selectbox(
        "플레이어 선택",
        options=unique_players,
        key="player_profile_selector"
    )
    
    if not selected_player:
        st.info("플레이어를 선택해 주세요.")
        return filtered_df
    
    # Filter data for selected player
    player_data = filtered_df[filtered_df[player_id_col] == selected_player].copy()
    
    if player_data.empty:
        st.warning(f"{selected_player} 플레이어의 데이터가 없습니다.")
        return filtered_df
    
    # Display basic info
    col1, col2, col3 = st.columns(3)
    
    total_games = len(player_data)
    col1.metric("총 경기 수", f"{total_games}")
    
    if "result" in player_data.columns:
        wins = pd.to_numeric(player_data["result"], errors="coerce")
        win_count = wins.sum() if not wins.isna().all() else 0
        win_rate = (win_count / total_games * 100) if total_games > 0 else 0
        col2.metric("승률", f"{win_rate:.1f}%")
    
    if "position" in player_data.columns:
        position = player_data["position"].iloc[0] if not player_data["position"].empty else "N/A"
        col3.metric("포지션", position)
    
    st.divider()
    
    # Create two-column layout for charts
    col1, col2 = st.columns(2)
    
    # Radar chart
    with col1:
        st.subheader("성능 지표 레이더 차트")
        radar_fig = _create_radar_chart_for_player(player_data, selected_player)
        if radar_fig:
            st.plotly_chart(radar_fig, use_container_width=True)
    
    # Trend line chart
    with col2:
        st.subheader("KDA 트렌드")
        trend_fig = _create_trend_line(player_data, selected_player, metric="KDA")
        if trend_fig:
            st.plotly_chart(trend_fig, use_container_width=True)
    
    # Debug option
    if st.checkbox("디버그: 플레이어 데이터 미리보기", value=False):
        st.write("Shape:", player_data.shape)
        st.dataframe(player_data.head())
    
    return filtered_df


filtered_players_df = render_page()

