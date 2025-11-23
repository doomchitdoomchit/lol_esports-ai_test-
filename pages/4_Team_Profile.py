"""Team-level profile page with performance indicators and trends."""

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


def _load_filtered_teams() -> pd.DataFrame:
    _, df_teams = load_data()
    filters = _get_active_filters()
    return _apply_filters(df_teams, filters)


def _get_team_metrics(team_data: pd.DataFrame) -> Dict[str, float]:
    """Extract and calculate average metrics for a team."""
    metrics = {}
    
    # Check for team-level KDA calculation
    # Teams might have teamkills, teamdeaths columns
    kills_col = None
    deaths_col = None
    assists_col = None
    
    for col in team_data.columns:
        col_lower = col.lower()
        if "teamkill" in col_lower or (col_lower == "kills" and "team" in team_data.columns[0].lower()):
            kills_col = col
        elif "teamdeath" in col_lower or (col_lower == "deaths" and "team" in team_data.columns[0].lower()):
            deaths_col = col
        elif "teamassist" in col_lower or (col_lower == "assists" and "team" in team_data.columns[0].lower()):
            assists_col = col
    
    # Calculate team KDA if possible
    if kills_col and deaths_col:
        kills = pd.to_numeric(team_data[kills_col], errors="coerce")
        deaths = pd.to_numeric(team_data[deaths_col], errors="coerce").replace(0, 1)
        assists = pd.to_numeric(team_data[assists_col], errors="coerce") if assists_col else 0
        
        if not assists_col:
            kda = (kills / deaths).mean()
        else:
            kda = ((kills + assists) / deaths).mean()
        metrics["KDA"] = kda if not pd.isna(kda) else 0.0
    elif "KDA" in team_data.columns:
        metrics["KDA"] = pd.to_numeric(team_data["KDA"], errors="coerce").mean()
    
    # DPM - Damage Per Minute (team level)
    dpm_col = None
    for col in team_data.columns:
        if col.lower() == "dpm" or "team" in col.lower() and "dpm" in col.lower():
            dpm_col = col
            break
    if dpm_col:
        metrics["DPM"] = pd.to_numeric(team_data[dpm_col], errors="coerce").mean()
    
    # GPM - Gold Per Minute (team level)
    gpm_col = None
    for col in team_data.columns:
        if "gpm" in col.lower():
            gpm_col = col
            break
    if gpm_col:
        metrics["GPM"] = pd.to_numeric(team_data[gpm_col], errors="coerce").mean()
    
    # VSPM - Vision Score Per Minute (team level)
    vspm_col = None
    for col in team_data.columns:
        if col.lower() == "vspm" or ("team" in col.lower() and "vspm" in col.lower()):
            vspm_col = col
            break
    if vspm_col:
        metrics["VSPM"] = pd.to_numeric(team_data[vspm_col], errors="coerce").mean()
    
    # Fill missing values with 0
    for key in ["KDA", "DPM", "GPM", "VSPM"]:
        if key not in metrics or pd.isna(metrics[key]):
            metrics[key] = 0.0
    
    return metrics


def _create_radar_chart_for_team(team_data: pd.DataFrame, team_name: str):
    """Create a radar chart for team performance metrics."""
    if team_data.empty:
        st.info("팀 데이터가 없어 레이더 차트를 생성할 수 없습니다.")
        return None
    
    metrics = _get_team_metrics(team_data)
    
    if not metrics or all(v == 0.0 for v in metrics.values()):
        st.warning("표시할 성능 지표가 없습니다.")
        return None
    
    radar_fig = create_radar_chart(
        metrics,
        title=f"{team_name} 성능 지표",
        trace_color="#2ecc71"
    )
    return radar_fig


def _create_trend_line(team_data: pd.DataFrame, team_name: str, metric: str = "KDA"):
    """Create a trend line chart showing metric over time (Patch)."""
    if team_data.empty:
        st.info("팀 데이터가 없어 트렌드 차트를 생성할 수 없습니다.")
        return None
    
    # Determine metric column
    metric_col = None
    if metric == "KDA":
        # Try to find or calculate KDA
        if "KDA" in team_data.columns:
            metric_col = "KDA"
        else:
            # Try to calculate from team kills/deaths
            kills_col = None
            deaths_col = None
            assists_col = None
            
            for col in team_data.columns:
                col_lower = col.lower()
                if "teamkill" in col_lower:
                    kills_col = col
                elif "teamdeath" in col_lower:
                    deaths_col = col
                elif "teamassist" in col_lower:
                    assists_col = col
            
            if kills_col and deaths_col:
                kills = pd.to_numeric(team_data[kills_col], errors="coerce")
                deaths = pd.to_numeric(team_data[deaths_col], errors="coerce").replace(0, 1)
                assists = pd.to_numeric(team_data[assists_col], errors="coerce") if assists_col else 0
                
                if assists_col:
                    team_data = team_data.copy()
                    team_data["KDA"] = (kills + assists) / deaths
                else:
                    team_data = team_data.copy()
                    team_data["KDA"] = kills / deaths
                metric_col = "KDA"
    elif metric == "DPM":
        for col in team_data.columns:
            if col.lower() == "dpm":
                metric_col = col
                break
    elif metric == "GPM":
        for col in team_data.columns:
            if "gpm" in col.lower():
                metric_col = col
                break
    elif metric == "VSPM":
        for col in team_data.columns:
            if col.lower() == "vspm":
                metric_col = col
                break
    
    if metric_col is None or metric_col not in team_data.columns:
        st.warning(f"{metric} 메트릭을 찾을 수 없습니다.")
        return None
    
    # Get Patch column for x-axis
    patch_col = None
    for col in team_data.columns:
        if col.lower() == "patch":
            patch_col = col
            break
    
    if patch_col is None:
        st.warning("Patch 컬럼을 찾을 수 없습니다.")
        return None
    
    # Prepare data for trend line
    trend_df = team_data[[patch_col, metric_col]].copy()
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
        title=f"{team_name} {metric} 트렌드",
        markers=True
    )
    fig.update_layout(
        xaxis_title="Patch",
        yaxis_title=metric,
        hovermode="x unified"
    )
    
    return fig


def render_page() -> pd.DataFrame:
    st.header("Team Profile")
    
    filtered_df = _load_filtered_teams()
    st.caption("현재 글로벌 필터를 반영한 팀 데이터입니다.")
    
    if filtered_df.empty:
        st.warning("필터링된 데이터가 없습니다. 필터를 조정해 주세요.")
        return filtered_df
    
    # Get unique team names
    team_name_col = None
    for col in filtered_df.columns:
        if "teamname" in col.lower() or ("team" in col.lower() and "name" in col.lower()):
            team_name_col = col
            break
    
    if team_name_col is None:
        st.error("팀 이름 컬럼을 찾을 수 없습니다.")
        return filtered_df
    
    unique_teams = filtered_df[team_name_col].dropna().unique().tolist()
    
    if not unique_teams:
        st.warning("선택할 팀이 없습니다.")
        return filtered_df
    
    # Sort teams for better UX
    unique_teams = sorted(unique_teams, key=str)
    
    # Team selector
    selected_team = st.selectbox(
        "팀 선택",
        options=unique_teams,
        key="team_profile_selector"
    )
    
    if not selected_team:
        st.info("팀을 선택해 주세요.")
        return filtered_df
    
    # Filter data for selected team
    team_data = filtered_df[filtered_df[team_name_col] == selected_team].copy()
    
    if team_data.empty:
        st.warning(f"{selected_team} 팀의 데이터가 없습니다.")
        return filtered_df
    
    # Display basic info
    col1, col2, col3 = st.columns(3)
    
    total_games = len(team_data)
    col1.metric("총 경기 수", f"{total_games}")
    
    if "result" in team_data.columns:
        wins = pd.to_numeric(team_data["result"], errors="coerce")
        win_count = wins.sum() if not wins.isna().all() else 0
        win_rate = (win_count / total_games * 100) if total_games > 0 else 0
        col2.metric("승률", f"{win_rate:.1f}%")
    
    # Calculate average team KDA for display
    team_metrics = _get_team_metrics(team_data)
    avg_kda = team_metrics.get("KDA", 0.0)
    col3.metric("평균 KDA", f"{avg_kda:.2f}")
    
    st.divider()
    
    # Create two-column layout for charts
    col1, col2 = st.columns(2)
    
    # Radar chart
    with col1:
        st.subheader("성능 지표 레이더 차트")
        radar_fig = _create_radar_chart_for_team(team_data, selected_team)
        if radar_fig:
            st.plotly_chart(radar_fig, use_container_width=True)
    
    # Trend line chart
    with col2:
        st.subheader("KDA 트렌드")
        trend_fig = _create_trend_line(team_data, selected_team, metric="KDA")
        if trend_fig:
            st.plotly_chart(trend_fig, use_container_width=True)
    
    # Debug option
    if st.checkbox("디버그: 팀 데이터 미리보기", value=False):
        st.write("Shape:", team_data.shape)
        st.dataframe(team_data.head())
        st.write("Available columns:", list(team_data.columns))
    
    return filtered_df


filtered_teams_df = render_page()

