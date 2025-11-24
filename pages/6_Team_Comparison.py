"""Team vs. Team comparison page with aggregate statistics."""

from __future__ import annotations

from typing import Any, Dict

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from components.sidebar import render_sidebar_filters
from config.colors import CHART_COLORS
from data_loader import load_data





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
    filters = render_sidebar_filters(df_teams)
    return _apply_filters(df_teams, filters)


def _get_team_name_column(df: pd.DataFrame) -> str | None:
    """Find the team name column name."""
    for col in df.columns:
        if "teamname" in col.lower() or ("team" in col.lower() and "name" in col.lower()):
            return col
    return None


def _get_team_metrics(team_data: pd.DataFrame) -> Dict[str, float]:
    """Extract and calculate average metrics for a team."""
    metrics = {}
    
    # Check for team-level KDA calculation
    kills_col = None
    deaths_col = None
    assists_col = None
    
    for col in team_data.columns:
        col_lower = col.lower()
        if "teamkill" in col_lower or (col_lower == "kills" and "team" in str(team_data.columns[0]).lower()):
            kills_col = col
        elif "teamdeath" in col_lower or (col_lower == "deaths" and "team" in str(team_data.columns[0]).lower()):
            deaths_col = col
        elif "teamassist" in col_lower or (col_lower == "assists" and "team" in str(team_data.columns[0]).lower()):
            assists_col = col
    
    # Calculate team KDA if possible
    if kills_col and deaths_col:
        kills = pd.to_numeric(team_data[kills_col], errors="coerce")
        deaths = pd.to_numeric(team_data[deaths_col], errors="coerce").replace(0, 1)
        assists = pd.to_numeric(team_data[assists_col], errors="coerce") if assists_col else pd.Series([0] * len(team_data))
        
        if assists_col:
            kda = ((kills + assists) / deaths).mean()
        else:
            kda = (kills / deaths).mean()
        metrics["KDA"] = kda if not pd.isna(kda) else 0.0
    elif "KDA" in team_data.columns:
        metrics["KDA"] = pd.to_numeric(team_data["KDA"], errors="coerce").mean()
    
    # DPM - Damage Per Minute (team level)
    dpm_col = None
    for col in team_data.columns:
        if col.lower() == "dpm" or ("team" in col.lower() and "dpm" in col.lower()):
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


def _create_overlaid_radar_chart(
    stats_a: Dict[str, float],
    stats_b: Dict[str, float],
    team_a_name: str,
    team_b_name: str,
    title: str = "팀 성능 비교"
) -> go.Figure:
    """Create an overlaid radar chart comparing two teams."""
    # Get all unique categories from both stats
    categories = list(set(list(stats_a.keys()) + list(stats_b.keys())))
    
    # Prepare values for both teams
    values_a = [stats_a.get(cat, 0.0) for cat in categories]
    values_b = [stats_b.get(cat, 0.0) for cat in categories]
    
    # Calculate max value for proper scaling
    all_values = values_a + values_b
    max_val = max(all_values) if all_values else 1
    
    fig = go.Figure()
    
    # Add trace for Team A
    fig.add_trace(
        go.Scatterpolar(
            r=values_a,
            theta=categories,
            fill="toself",
            name=team_a_name,
            line=dict(color=CHART_COLORS["team_a"], width=2),
            marker=dict(color=CHART_COLORS["team_a"]),
            hovertemplate=f"%{{theta}}: %{{r:.2f}} ({team_a_name})<extra></extra>",
        )
    )
    
    # Add trace for Team B
    fig.add_trace(
        go.Scatterpolar(
            r=values_b,
            theta=categories,
            fill="toself",
            name=team_b_name,
            line=dict(color=CHART_COLORS["team_b"], width=2),
            marker=dict(color=CHART_COLORS["team_b"]),
            hovertemplate=f"%{{theta}}: %{{r:.2f}} ({team_b_name})<extra></extra>",
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
                gridcolor=CHART_COLORS["grid"],
            ),
            angularaxis=dict(tickfont=dict(size=11)),
        ),
        margin=dict(l=20, r=20, t=60, b=40),
    )
    
    return fig


def _create_diverging_bar_chart(
    stats_a: Dict[str, float],
    stats_b: Dict[str, float],
    team_a_name: str,
    team_b_name: str,
    title: str = "통계 차이 비교"
) -> go.Figure:
    """Create a diverging bar chart showing the difference between two teams."""
    # Get all unique categories
    categories = list(set(list(stats_a.keys()) + list(stats_b.keys())))
    
    # Calculate differences (Team A - Team B)
    differences = {cat: stats_a.get(cat, 0.0) - stats_b.get(cat, 0.0) for cat in categories}
    
    # Sort by absolute difference for better visualization
    sorted_cats = sorted(categories, key=lambda x: abs(differences[x]), reverse=True)
    diffs = [differences[cat] for cat in sorted_cats]
    
    # Determine colors based on sign
    colors = [
        CHART_COLORS["positive"] if diff > 0 
        else CHART_COLORS["negative"] if diff < 0 
        else CHART_COLORS["neutral"] 
        for diff in diffs
    ]
    
    fig = go.Figure()
    
    fig.add_trace(
        go.Bar(
            x=diffs,
            y=sorted_cats,
            orientation="h",
            marker=dict(color=colors),
            hovertemplate="%{y}: %{x:+.2f}<br>" + 
                         f"{team_a_name}: %{{customdata[0]:.2f}}<br>" +
                         f"{team_b_name}: %{{customdata[1]:.2f}}<extra></extra>",
            customdata=[[stats_a.get(cat, 0.0), stats_b.get(cat, 0.0)] for cat in sorted_cats],
        )
    )
    
    fig.update_layout(
        title=title,
        xaxis_title=f"차이 ({team_a_name} - {team_b_name})",
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
                line=dict(color=CHART_COLORS["divider"], width=2, dash="dash"),
            )
        ],
        annotations=[
            dict(
                x=0,
                y=1.02,
                xref="x",
                yref="paper",
                text=f"{team_a_name} 유리",
                showarrow=False,
                font=dict(color=CHART_COLORS["positive"], size=10),
                xanchor="right",
            ),
            dict(
                x=0,
                y=1.02,
                xref="x",
                yref="paper",
                text=f"{team_b_name} 유리",
                showarrow=False,
                font=dict(color=CHART_COLORS["negative"], size=10),
                xanchor="left",
            ),
        ],
        hovermode="closest",
    )
    
    return fig


def render_page() -> pd.DataFrame:
    st.header("Team vs. Team Comparison")
    st.caption("두 팀의 집계 통계를 비교할 수 있습니다.")
    
    filtered_df = _load_filtered_teams()
    
    if filtered_df.empty:
        st.warning("필터링된 데이터가 없습니다. 필터를 조정해 주세요.")
        return filtered_df
    
    # Get team name column
    team_name_col = _get_team_name_column(filtered_df)
    if team_name_col is None:
        st.error("팀 이름 컬럼을 찾을 수 없습니다.")
        return filtered_df
    
    # Get unique teams
    unique_teams = filtered_df[team_name_col].dropna().unique().tolist()
    if not unique_teams:
        st.warning("선택할 팀이 없습니다.")
        return filtered_df
    
    # Sort teams for better UX
    unique_teams = sorted(unique_teams, key=str)
    
    # Create two-column layout
    col1, col2 = st.columns(2)
    
    # Team A selector
    with col1:
        st.subheader("Team A")
        team_a = st.selectbox(
            "팀 A 선택",
            options=unique_teams,
            key="team_comparison_a"
        )
    
    # Team B selector
    with col2:
        st.subheader("Team B")
        team_b = st.selectbox(
            "팀 B 선택",
            options=unique_teams,
            key="team_comparison_b"
        )
    
    # Display comparison if both teams are selected
    if team_a and team_b:
        if team_a == team_b:
            st.warning("같은 팀은 비교할 수 없습니다. 다른 팀을 선택해 주세요.")
            return filtered_df
        
        st.divider()
        
        # Get data for both teams
        team_a_data = filtered_df[filtered_df[team_name_col] == team_a].copy()
        team_b_data = filtered_df[filtered_df[team_name_col] == team_b].copy()
        
        if team_a_data.empty or team_b_data.empty:
            st.warning("팀 데이터를 불러올 수 없습니다.")
            return filtered_df
        
        # Calculate metrics for both teams
        stats_a = _get_team_metrics(team_a_data)
        stats_b = _get_team_metrics(team_b_data)
        
        # Display basic info in a container
        with st.container():
            info_col1, info_col2 = st.columns(2)
            
            with info_col1:
                st.metric("Team A 경기 수", len(team_a_data))
                if "result" in team_a_data.columns:
                    wins_a = pd.to_numeric(team_a_data["result"], errors="coerce").sum()
                    win_rate_a = (wins_a / len(team_a_data) * 100) if len(team_a_data) > 0 else 0
                    st.metric("Team A 승률", f"{win_rate_a:.1f}%")
            
            with info_col2:
                st.metric("Team B 경기 수", len(team_b_data))
                if "result" in team_b_data.columns:
                    wins_b = pd.to_numeric(team_b_data["result"], errors="coerce").sum()
                    win_rate_b = (wins_b / len(team_b_data) * 100) if len(team_b_data) > 0 else 0
                    st.metric("Team B 승률", f"{win_rate_b:.1f}%")
        
        st.divider()
        
        # Create comparison charts in a container
        with st.container():
            chart_col1, chart_col2 = st.columns(2)
            
            with chart_col1:
                st.subheader("레이더 차트 비교")
                radar_fig = _create_overlaid_radar_chart(
                    stats_a,
                    stats_b,
                    team_a,
                    team_b,
                    title=f"{team_a} vs {team_b}"
                )
                st.plotly_chart(radar_fig, use_container_width=True)
            
            with chart_col2:
                st.subheader("통계 차이 비교")
                diverging_fig = _create_diverging_bar_chart(
                    stats_a,
                    stats_b,
                    team_a,
                    team_b,
                    title=f"{team_a} vs {team_b}"
                )
                st.plotly_chart(diverging_fig, use_container_width=True)
        
        # Debug section in expander
        with st.expander("🔧 디버그 정보", expanded=False):
            if st.checkbox("팀 통계 표시", value=False):
                debug_col1, debug_col2 = st.columns(2)
                with debug_col1:
                    st.write(f"**{team_a} 통계:**")
                    st.json(stats_a)
                    st.write("**샘플 데이터:**")
                    st.dataframe(team_a_data.head(3))
                with debug_col2:
                    st.write(f"**{team_b} 통계:**")
                    st.json(stats_b)
                    st.write("**샘플 데이터:**")
                    st.dataframe(team_b_data.head(3))
    
    return filtered_df


filtered_teams_df = render_page()

