"""Team-level profile page with performance indicators and trends."""

from __future__ import annotations

from typing import Any, Dict

import pandas as pd
import plotly.express as px
import streamlit as st

from components.charts import create_radar_chart
from components.sidebar import render_sidebar_filters
from config.colors import CHART_COLORS
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


def _load_filtered_teams() -> pd.DataFrame:
    _, df_teams = load_data()
    filters = render_sidebar_filters(df_teams)
    return _apply_filters(df_teams, filters)


def _get_team_metrics(team_data: pd.DataFrame) -> Dict[str, float]:
    """Extract and calculate average metrics for a team."""
    metrics = {}
    
    # Basic averages
    metrics["Games"] = len(team_data)
    
    if "result" in team_data.columns:
        metrics["Win Rate"] = team_data["result"].mean() * 100
    
    # KDA - Calculate as (Sum Kills + Sum Assists) / Sum Deaths
    # We use case-insensitive lookup for safety
    kills_col = next((c for c in team_data.columns if c.lower() == "kills"), None)
    deaths_col = next((c for c in team_data.columns if c.lower() == "deaths"), None)
    assists_col = next((c for c in team_data.columns if c.lower() == "assists"), None)

    if kills_col and deaths_col and assists_col:
        t_kills = pd.to_numeric(team_data[kills_col], errors="coerce").sum()
        t_deaths = pd.to_numeric(team_data[deaths_col], errors="coerce").sum()
        t_assists = pd.to_numeric(team_data[assists_col], errors="coerce").sum()
        
        metrics["KDA"] = (t_kills + t_assists) / t_deaths if t_deaths > 0 else 0.0
    elif "KDA" in team_data.columns:
        # Fallback to average if raw columns missing
        metrics["KDA"] = pd.to_numeric(team_data["KDA"], errors="coerce").mean()
    else:
        metrics["KDA"] = 0.0
    
    # DPM
    dpm_col = None
    for col in team_data.columns:
        if col.lower() == "dpm" or "team" in col.lower() and "dpm" in col.lower():
            dpm_col = col
            break
    if dpm_col:
        metrics["DPM"] = pd.to_numeric(team_data[dpm_col], errors="coerce").mean()
    
    # Earned GPM
    gpm_col = None
    for col in team_data.columns:
        if "earned gpm" in col.lower():
            gpm_col = col
            break
    if gpm_col:
        metrics["Earned GPM"] = pd.to_numeric(team_data[gpm_col], errors="coerce").mean()
    
    # VSPM
    vspm_col = None
    for col in team_data.columns:
        if col.lower() == "vspm":
            vspm_col = col
            break
    if vspm_col:
        metrics["VSPM"] = pd.to_numeric(team_data[vspm_col], errors="coerce").mean()

    # Objectives (Mean)
    for col, name in [
        ("inhibitors", "Inhibitors"),
        ("towers", "Towers"),
        ("dragons", "Dragons"),
        ("barons", "Barons"),
        ("void_grubs", "Void Grubs"),
    ]:
        if col in team_data.columns:
            metrics[name] = pd.to_numeric(team_data[col], errors="coerce").mean()

    # First Objectives (%)
    for col, name in [
        ("firstblood", "First Blood"),
        ("firsttower", "First Tower"),
        ("firstdragon", "First Dragon"),
        ("firstbaron", "First Baron"),
        ("atakhans", "Atakhans"), # Assuming atakhans is a binary/count column where mean represents rate
    ]:
        if col in team_data.columns:
             metrics[name] = pd.to_numeric(team_data[col], errors="coerce").mean() * 100

    return metrics


def _get_league_metrics(df_teams: pd.DataFrame) -> Dict[str, float]:
    """Calculate league-wide average metrics."""
    return _get_team_metrics(df_teams)


def _create_normalized_radar_chart(team_data: pd.DataFrame, league_data: pd.DataFrame, team_name: str):
    """Create a normalized radar chart comparing team to league."""
    
    metrics_to_plot = {
        "DPM": "dpm",
        "Earned GPM": "earned gpm", 
        "KDA": "KDA",
        "VSPM": "vspm"
    }
    
    team_vals = {}
    league_vals = {}
    max_vals = {}
    min_vals = {}
    
    # Calculate averages and find min/max for normalization
    # First, aggregate league data by team to get team-level averages for min/max
    # This ensures we compare "Team Avg" vs "Best/Worst Team Avg", not "Best/Worst Game"
    team_name_col = next((col for col in league_data.columns if "teamname" in col.lower() or "team" in col.lower() and "name" in col.lower()), None)
    
    league_team_means = pd.DataFrame()
    if team_name_col:
        # We only care about the numeric columns we are plotting
        cols_to_agg = []
        for col_key in metrics_to_plot.values():
             for col in league_data.columns:
                if col_key.lower() == col.lower() or (col_key.lower() in col.lower() and len(col) < len(col_key) + 5):
                     cols_to_agg.append(col)
                     break
        
        if cols_to_agg:
             # Group by team and calculate mean for relevant columns
             league_team_means = league_data.groupby(team_name_col)[cols_to_agg].mean()

    for label, col_key in metrics_to_plot.items():
        # Special handling for KDA to ensure (kills + assists) / deaths
        if label == "KDA":
            # Calculate Team KDA
            t_kills = pd.to_numeric(team_data.get("kills", 0), errors="coerce").sum()
            t_deaths = pd.to_numeric(team_data.get("deaths", 0), errors="coerce").replace(0, 1).sum()
            t_assists = pd.to_numeric(team_data.get("assists", 0), errors="coerce").sum()
            team_mean = (t_kills + t_assists) / t_deaths if t_deaths > 0 else 0
            
            # Calculate League KDA (Macro average of all games)
            l_kills = pd.to_numeric(league_data.get("kills", 0), errors="coerce").sum()
            l_deaths = pd.to_numeric(league_data.get("deaths", 0), errors="coerce").replace(0, 1).sum()
            l_assists = pd.to_numeric(league_data.get("assists", 0), errors="coerce").sum()
            league_mean = (l_kills + l_assists) / l_deaths if l_deaths > 0 else 0
            
            # For min/max, we calculate KDA for EACH TEAM and take min/max of those averages
            if team_name_col:
                # Calculate KDA per team
                team_kdas = []
                for team in league_data[team_name_col].unique():
                    td = league_data[league_data[team_name_col] == team]
                    tk = pd.to_numeric(td.get("kills", 0), errors="coerce").sum()
                    t_d = pd.to_numeric(td.get("deaths", 0), errors="coerce").replace(0, 1).sum()
                    ta = pd.to_numeric(td.get("assists", 0), errors="coerce").sum()
                    team_kdas.append((tk + ta) / t_d)
                
                league_max = max(team_kdas) if team_kdas else league_mean * 2
                league_min = min(team_kdas) if team_kdas else 0
            else:
                league_max = league_mean * 2
                league_min = 0
                
        else:
            # Find actual column name for other metrics
            col_name = None
            for col in team_data.columns:
                if col_key.lower() == col.lower() or (col_key.lower() in col.lower() and len(col) < len(col_key) + 5):
                     col_name = col
                     break
            
            if not col_name:
                continue
                
            team_mean = pd.to_numeric(team_data[col_name], errors="coerce").mean()
            league_mean = pd.to_numeric(league_data[col_name], errors="coerce").mean()
            
            # Use pre-calculated team means for min/max if available
            if not league_team_means.empty and col_name in league_team_means.columns:
                league_max = league_team_means[col_name].max()
                league_min = league_team_means[col_name].min()
            else:
                # Fallback to game-level min/max (less ideal)
                league_max = pd.to_numeric(league_data[col_name], errors="coerce").max()
                league_min = pd.to_numeric(league_data[col_name], errors="coerce").min()
        
        team_vals[label] = team_mean
        league_vals[label] = league_mean
        max_vals[label] = league_max
        min_vals[label] = league_min

    if not team_vals:
        st.warning("레이더 차트를 위한 데이터가 부족합니다.")
        return None

    # Normalize
    categories = list(team_vals.keys())
    team_norm = []
    league_norm = []
    
    for cat in categories:
        mn = min_vals[cat]
        mx = max_vals[cat]
        if mx == mn:
            team_norm.append(0.5)
            league_norm.append(0.5)
        else:
            team_norm.append((team_vals[cat] - mn) / (mx - mn))
            league_norm.append((league_vals[cat] - mn) / (mx - mn))
            
    import plotly.graph_objects as go
    
    fig = go.Figure()
    
    # League Average
    fig.add_trace(go.Scatterpolar(
        r=league_norm,
        theta=categories,
        fill='toself',
        name='League Avg',
        hoverinfo='text',
        text=[f"{v:.2f}" for v in league_vals.values()],
        line=dict(color='gray', dash='dash')
    ))
    
    # Team
    fig.add_trace(go.Scatterpolar(
        r=team_norm,
        theta=categories,
        fill='toself',
        name=team_name,
        hoverinfo='text',
        text=[f"{v:.2f}" for v in team_vals.values()],
        line=dict(color=CHART_COLORS["team_profile"])
    ))
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=False,
                range=[0, 1]
            )
        ),
        showlegend=True,
        title=f"{team_name} vs League Performance (Normalized)"
    )
    
    return fig

def _create_laning_phase_charts(team_data: pd.DataFrame, league_data: pd.DataFrame):
    """Create charts for laning phase indicators (Gold/CS Diff)."""
    
    time_points = [10, 15, 20, 25]
    
    # Gold Diff
    gold_diff_cols = [f"golddiffat{t}" for t in time_points]
    cs_diff_cols = [f"csdiffat{t}" for t in time_points]
    
    team_gold_diff = []
    league_abs_gold_diff = []
    
    team_cs_diff = []
    league_abs_cs_diff = []
    
    valid_times = []
    
    for i, t in enumerate(time_points):
        g_col = gold_diff_cols[i]
        c_col = cs_diff_cols[i]
        
        if g_col in team_data.columns and c_col in team_data.columns:
            valid_times.append(t)
            
            # Team Average (Signed)
            team_gold_diff.append(pd.to_numeric(team_data[g_col], errors="coerce").mean())
            team_cs_diff.append(pd.to_numeric(team_data[c_col], errors="coerce").mean())
            
            # League Absolute Average (Adjusted: sum(abs) / (2 * len))
            l_gold_vals = pd.to_numeric(league_data[g_col], errors="coerce")
            l_cs_vals = pd.to_numeric(league_data[c_col], errors="coerce")
            
            league_abs_gold_diff.append(l_gold_vals.abs().sum() / (2 * len(l_gold_vals)))
            league_abs_cs_diff.append(l_cs_vals.abs().sum() / (2 * len(l_cs_vals)))
            
    if not valid_times:
        st.info("라인전 지표 데이터가 없습니다.")
        return

    # Create DataFrames for Plotly
    df_gold = pd.DataFrame({
        "Time": valid_times,
        "Team Gold Diff": team_gold_diff,
        "League Avg Diff (Adj)": league_abs_gold_diff
    })
    
    df_cs = pd.DataFrame({
        "Time": valid_times,
        "Team CS Diff": team_cs_diff,
        "League Avg Diff (Adj)": league_abs_cs_diff
    })
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("평균 골드 격차")
        fig_gold = px.line(df_gold, x="Time", y=["Team Gold Diff", "League Avg Diff (Adj)"], markers=True)
        fig_gold.update_layout(
            yaxis_title="Gold Diff",
            legend=dict(
                yanchor="top",
                y=0.99,
                xanchor="left",
                x=0.01,
                bgcolor="rgba(0,0,0,0)"
            )
        )
        st.plotly_chart(fig_gold, use_container_width=True)
        
    with col2:
        st.subheader("평균 CS 격차")
        fig_cs = px.line(df_cs, x="Time", y=["Team CS Diff", "League Avg Diff (Adj)"], markers=True)
        fig_cs.update_layout(
            yaxis_title="CS Diff",
            legend=dict(
                yanchor="top",
                y=0.99,
                xanchor="left",
                x=0.01,
                bgcolor="rgba(0,0,0,0)"
            )
        )
        st.plotly_chart(fig_cs, use_container_width=True)


def _calculate_object_win_rates(team_data: pd.DataFrame):
    """Calculate win rates for first objectives and objective counts."""
    
    if "result" not in team_data.columns:
        st.warning("승패 데이터(result)가 없어 승률을 계산할 수 없습니다.")
        return

    # 1. First Objectives Win Rate
    first_objs = {
        "First Blood": "firstblood",
        "First Tower": "firsttower",
        "First Dragon": "firstdragon",
        "First Baron": "firstbaron"
    }
    
    first_wr_data = {}
    
    for label, col in first_objs.items():
        if col in team_data.columns:
            # Filter games where team got the first objective (value == 1)
            got_obj = team_data[team_data[col] == 1]
            if not got_obj.empty:
                wr = got_obj["result"].mean() * 100
                first_wr_data[label] = wr
            else:
                first_wr_data[label] = 0.0
    
    # 2. Win Rate by Count (Voidgrubs, Dragon, Baron)
    count_objs = {
        "Void Grubs": "void_grubs",
        "Dragons": "dragons",
        "Barons": "barons"
    }
    
    st.subheader("오브젝트 컨트롤 시 승률")
    
    # Display First Objectives WR
    if first_wr_data:
        cols = st.columns(len(first_wr_data))
        for i, (label, wr) in enumerate(first_wr_data.items()):
            cols[i].metric(f"{label} 획득 시 승률", f"{wr:.1f}%")
            
    st.divider()
    
    # Display Count-based WR
    col1, col2, col3 = st.columns(3)
    cols_map = [col1, col2, col3]
    
    for i, (label, col) in enumerate(count_objs.items()):
        if col in team_data.columns:
            # Ensure column is integer
            team_data[col] = pd.to_numeric(team_data[col], errors='coerce').fillna(0).astype(int)
            
            # Group by count and calculate win rate
            wr_by_count = team_data.groupby(col)["result"].agg(['mean', 'count']).reset_index()
            wr_by_count.columns = [label, "Win Rate", "Games"]
            wr_by_count["Win Rate"] = wr_by_count["Win Rate"] * 100
            
            with cols_map[i]:
                st.write(f"**{label} 획득 수별 승률**")
                st.dataframe(
                    wr_by_count.style.format({"Win Rate": "{:.1f}%"}),
                    hide_index=True,
                    width="stretch"
                )








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
    
    # Display basic info in a container
    with st.container():
        team_metrics = _get_team_metrics(team_data)
        
        # Row 1: Basic Stats
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("총 경기 수", f"{int(team_metrics.get('Games', 0))}")
        c2.metric("승률", f"{team_metrics.get('Win Rate', 0):.1f}%")
        c3.metric("평균 KDA", f"{team_metrics.get('KDA', 0):.2f}")
        c4.metric("평균 DPM", f"{team_metrics.get('DPM', 0):.0f}")
        c5.metric("평균 Earned GPM", f"{team_metrics.get('Earned GPM', 0):.0f}")
        
        # Row 2: Objectives Mean
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Mean Inhibitors", f"{team_metrics.get('Inhibitors', 0):.1f}")
        c2.metric("Mean Towers", f"{team_metrics.get('Towers', 0):.1f}")
        c3.metric("Mean Dragons", f"{team_metrics.get('Dragons', 0):.1f}")
        c4.metric("Mean Barons", f"{team_metrics.get('Barons', 0):.1f}")
        c5.metric("Mean Void Grubs", f"{team_metrics.get('Void Grubs', 0):.1f}")

        # Row 3: First Objectives & Atakhans
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("First Blood %", f"{team_metrics.get('First Blood', 0):.1f}%")
        c2.metric("First Tower %", f"{team_metrics.get('First Tower', 0):.1f}%")
        c3.metric("First Dragon %", f"{team_metrics.get('First Dragon', 0):.1f}%")
        c4.metric("First Baron %", f"{team_metrics.get('First Baron', 0):.1f}%")
        c5.metric("Atakhans %", f"{team_metrics.get('Atakhans', 0):.1f}%")
    
    st.divider()
    
    # Create two columns for Radar and Laning
    col_radar, col_laning = st.columns([1, 2])
    
    with col_radar:
        st.subheader("성능 지표 레이더")
        st.caption("vs League (Normalized)")
        radar_fig = _create_normalized_radar_chart(team_data, filtered_df, selected_team)
        if radar_fig:
            st.plotly_chart(radar_fig, use_container_width=True)
            
    with col_laning:
        st.subheader("라인전 지표")
        st.caption("vs League Avg Diff Adj (abs(sum)/2*len)")
        _create_laning_phase_charts(team_data, filtered_df)
    
    st.divider()
    
    # Object Control Win Rates
    _calculate_object_win_rates(team_data)
    
    # Debug section in expander
    with st.expander("🔧 디버그 정보", expanded=False):
        if st.checkbox("팀 데이터 미리보기", value=False):
            st.write("Shape:", team_data.shape)
            st.dataframe(team_data.head(), width="stretch")
            st.write("Available columns:", list(team_data.columns))
    
    return filtered_df


filtered_teams_df = render_page()

