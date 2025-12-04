"""Player vs. Player comparison page with position-based filtering."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
import os

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
from factor_analyzer import FactorAnalyzer
from scipy.stats import percentileofscore

from components.charts import create_radar_chart
from components.sidebar import render_sidebar_filters
from config.colors import CHART_COLORS
from components.data_loader import load_data
from components.utils import apply_filters

st.set_page_config(layout="wide")


def _load_filtered_players() -> pd.DataFrame:
    df_players, _ = load_data()
    filters = render_sidebar_filters(df_players)
    return apply_filters(df_players, filters)


def _get_player_id_column(df: pd.DataFrame) -> str | None:
    """Find the player ID column name."""
    for col in df.columns:
        if col.lower() in ["playerid", "playername", "participantid"]:
            return col
    return None


def _load_cluster_info() -> pd.DataFrame:
    """Load cluster definitions from csv."""
    file_path = os.path.join("data", "val.csv")
    if not os.path.exists(file_path):
        st.error(f"Cluster data not found at {file_path}")
        return pd.DataFrame()
    
    try:
        df = pd.read_csv(file_path)
        if len(df.columns) >= 2:
            df.columns = ['variable', 'cluster_label'] + list(df.columns[2:])
            df['cluster'] = df['cluster_label'].astype(str).str.extract(r'(\d+)').astype(float)
            return df
    except Exception as e:
        st.error(f"Error loading cluster data: {e}")
        return pd.DataFrame()
    
    return df


def _calculate_factor_scores(player_name: str, position: str, full_data: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
    """Calculate Factor scores for the player based on clusters."""
    cluster_df = _load_cluster_info()
    if cluster_df.empty:
        return {}

    # Filter data for the same position
    position_data = full_data[full_data['position'] == position].reset_index(drop=True).copy()

    # Get player's position
    player_row = position_data[position_data['playername'] == player_name]
    if player_row.empty:
        return {}
    
    if len(position_data) < 3:
        return {}

    # Short Cluster Names
    cluster_names = {
        1: '성장',
        2: '후반',
        3: '팀파이트',
        4: '라인전',
        5: '사망',
        6: '방어',
        7: '공격',
        8: '전투우위'
    }
    
    results = {}
    
    for cluster_id in range(1, 9):
        vars_in_cluster = cluster_df[cluster_df['cluster'] == cluster_id]['variable'].tolist()
        valid_vars = [v for v in vars_in_cluster if v in position_data.columns]
        
        if not valid_vars:
            results[cluster_id] = {'name': cluster_names.get(cluster_id, str(cluster_id)), 'score': 0.0}
            continue
            
        X = position_data[valid_vars].fillna(0)
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        
        scores = None
        if X.shape[1] == 1:
            scores = X_scaled
        else:
            try:
                fa = FactorAnalyzer(n_factors=1, rotation=None)
                fa.fit(X_scaled)
                scores = fa.transform(X_scaled)
            except:
                try:
                    pca = PCA(n_components=1)
                    scores = pca.fit_transform(X_scaled)
                except:
                    scores = X_scaled.mean(axis=1).reshape(-1, 1)

        if pd.Series(scores.flatten()).corr(X.sum(axis=1).reset_index(drop=True)) < 0:
            scores = -scores
            
        player_score = scores[player_row.index].mean()
        percentile = 50 + (player_score - scores.mean()) / scores.std() * 10
        
        # Invert for negative indicators (5: Deaths, 8: Enemy Combat Advantage)
        # So that Higher Score = Better Performance (Low Deaths, Low Enemy Advantage)
        if cluster_id in [5, 8]:
            percentile = 100 - percentile
        
        results[cluster_id] = {
            'name': cluster_names.get(cluster_id, str(cluster_id)),
            'score': percentile
        }
        
    return results


def _create_style_radar_chart(scores_a: Dict, scores_b: Dict, name_a: str, name_b: str) -> go.Figure:
    """Create overlaid radar chart for style analysis."""
    categories = []
    vals_a = []
    vals_b = []
    
    # Ensure order 1-8
    for i in range(1, 9):
        if i in scores_a:
            categories.append(scores_a[i]['name'])
            vals_a.append(scores_a[i]['score'])
            vals_b.append(scores_b.get(i, {'score': 0})['score'])
            
    fig = go.Figure()
    
    fig.add_trace(go.Scatterpolar(
        r=vals_a, theta=categories, fill='toself', name=name_a,
        line=dict(color=CHART_COLORS['player_a']),
        marker=dict(color=CHART_COLORS['player_a'])
    ))
    
    fig.add_trace(go.Scatterpolar(
        r=vals_b, theta=categories, fill='toself', name=name_b,
        line=dict(color=CHART_COLORS['player_b']),
        marker=dict(color=CHART_COLORS['player_b'])
    ))
    
    # Calculate dynamic range to highlight differences
    all_vals = vals_a + vals_b
    if all_vals:
        min_val = min(all_vals)
        max_val = max(all_vals)
        # Zoom in: range from (min - 10) to (max + 10), clamped to 0-100
        range_min = max(0, min_val - 10)
        range_max = min(100, max_val + 10)
    else:
        range_min, range_max = 0, 100

    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[range_min, range_max])),
        showlegend=True,
        title="플레이어 스타일 비교 (8 Factors)"
    )
    return fig


def _create_diff_chart(scores_a: Dict, scores_b: Dict, name_a: str, name_b: str) -> go.Figure:
    """Create bar chart showing score differences."""
    categories = []
    diffs = []
    
    for i in range(1, 9):
        if i in scores_a:
            cat = scores_a[i]['name']
            diff = scores_a[i]['score'] - scores_b.get(i, {'score': 0})['score']
            categories.append(cat)
            diffs.append(diff)
            
    # Sort by diff
    sorted_indices = sorted(range(len(diffs)), key=lambda k: diffs[k])
    categories = [categories[i] for i in sorted_indices]
    diffs = [diffs[i] for i in sorted_indices]
    
    colors = [CHART_COLORS['player_a'] if d > 0 else CHART_COLORS['player_b'] for d in diffs]
    
    fig = go.Figure(go.Bar(
        y=categories, x=diffs, orientation='h',
        marker=dict(color=colors),
        text=[f"{abs(d):.1f}" for d in diffs],
        textposition='auto'
    ))
    
    fig.update_layout(
        title=f"스타일 차이 ({name_a} - {name_b})",
        xaxis_title="Score Difference",
        yaxis_title=None
    )
    return fig


def _get_most_champs(df: pd.DataFrame) -> pd.DataFrame:
    """Get top 5 champions stats."""
    if df.empty:
        return pd.DataFrame()
        
    stats = df.groupby("champion").agg(
        gameplay=("champion", "count"),
        win_rate=("result", lambda x: pd.to_numeric(x, errors="coerce").mean() * 100),
        kda=("KDA", "mean"),
        gd10=("golddiffat10", "mean"),
        gd15=("golddiffat15", "mean"),
        gd20=("golddiffat20", "mean"),
        gd25=("golddiffat25", "mean"),
        cpm=("cspm", "mean"),
        dpm=("dpm", "mean"),
        vs=("visionscore", "mean"),
    ).reset_index()
    
    return stats.sort_values("gameplay", ascending=False).head(5)


def _get_head_to_head_stats(df_all: pd.DataFrame, player_a: str, player_b: str) -> pd.DataFrame:
    """Find games where players faced each other."""
    # Get all games for both players
    games_a = df_all[df_all['playername'] == player_a]
    games_b = df_all[df_all['playername'] == player_b]
    
    # Merge on gameid
    merged = pd.merge(games_a, games_b, on='gameid', suffixes=('_a', '_b'))
    
    # Filter for opposing teams
    opponents = merged[merged['teamname_a'] != merged['teamname_b']].copy()
    
    return opponents


def render_page():
    st.header("Player vs. Player Comparison")
    
    filtered_df = _load_filtered_players()
    if filtered_df.empty:
        st.warning("데이터가 없습니다.")
        return

    player_id_col = 'playername'
    unique_players = sorted(filtered_df[player_id_col].dropna().unique().tolist(), key=str)
    
    # Layout: Player Selection
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Player A")
        st.caption("&nbsp;") # Empty caption for alignment
        player_a = st.selectbox("Select Player A", unique_players, key="p_a")
        
    with col2:
        st.subheader("Player B")
        if player_a:
            # Get Position of A
            pos_a = filtered_df[filtered_df[player_id_col] == player_a]['position'].iloc[0]
            st.caption(f"Player A Position: **{pos_a}**")
            
            # Filter B candidates (same position)
            candidates = filtered_df[
                (filtered_df['position'] == pos_a) & 
                (filtered_df[player_id_col] != player_a)
            ][player_id_col].unique().tolist()
            
            player_b = st.selectbox("Select Player B", sorted(candidates, key=str), key="p_b")
        else:
            player_b = None

    if player_a and player_b:
        st.divider()
        
        # Data
        df_a = filtered_df[filtered_df[player_id_col] == player_a]
        df_b = filtered_df[filtered_df[player_id_col] == player_b]
        
        # 1. Player Style Analysis
        st.subheader("Player Style Analysis")
        scores_a = _calculate_factor_scores(player_a, pos_a, filtered_df)
        scores_b = _calculate_factor_scores(player_b, pos_a, filtered_df)
        
        if scores_a and scores_b:
            sc1, sc2 = st.columns(2)
            with sc1:
                radar = _create_style_radar_chart(scores_a, scores_b, player_a, player_b)
                st.plotly_chart(radar, use_container_width=True)
            with sc2:
                diff_chart = _create_diff_chart(scores_a, scores_b, player_a, player_b)
                st.plotly_chart(diff_chart, use_container_width=True)
        else:
            st.info("스타일 분석을 위한 데이터가 부족합니다.")
            
        st.divider()
        
        # 3. Most 5 Champions
        st.subheader("Most 5 Champions")
        
        mc1, mc2 = st.columns(2)
        
        most_a = _get_most_champs(df_a)
        most_b = _get_most_champs(df_b)
        
        col_config = {
            "win_rate": st.column_config.NumberColumn("Win%", format="%.1f%%"),
            "kda": st.column_config.NumberColumn("KDA", format="%.2f"),
            "gd10": st.column_config.NumberColumn("GD@10", format="%.0f"),
            "gd15": st.column_config.NumberColumn("GD@15", format="%.0f"),
            "dpm": st.column_config.NumberColumn("DPM", format="%.0f"),
        }
        
        with mc1:
            st.caption(f"**{player_a}**")
            st.dataframe(most_a, hide_index=True, column_config=col_config, width="stretch")
            
        with mc2:
            st.caption(f"**{player_b}**")
            st.dataframe(most_b, hide_index=True, column_config=col_config, width="stretch")
            
        st.divider()
        
        # 4. Head-to-Head
        st.subheader("상대 전적 (Head-to-Head)")
        
        h2h_games = _get_head_to_head_stats(filtered_df, player_a, player_b)
        
        if not h2h_games.empty:
            # Stats Diff in H2H
            st.caption(f"총 {len(h2h_games)}경기 맞대결")
            
            # Calculate A's Win Rate vs B
            wins_vs = h2h_games['result_a'].sum()
            wr_vs = (wins_vs / len(h2h_games)) * 100
            st.metric(f"{player_a} 승률 vs {player_b}", f"{wr_vs:.1f}% ({wins_vs}승 {len(h2h_games)-wins_vs}패)")
            
            # Game Log
            st.write("맞대결 기록")
            display_cols = ['date_a', 'result_a', 'champion_a', 'champion_b', 'KDA_a', 'KDA_b']
            
            # Rename for display
            log_df = h2h_games[display_cols].rename(columns={
                'date_a': 'Date',
                'result_a': 'Result (A)',
                'champion_a': f'{player_a} Champ',
                'champion_b': f'{player_b} Champ',
                'KDA_a': f'{player_a} KDA',
                'KDA_b': f'{player_b} KDA'
            })
            
            st.dataframe(log_df, hide_index=True, width="stretch")
            
        else:
            st.info("맞대결 기록이 없습니다.")

render_page()

