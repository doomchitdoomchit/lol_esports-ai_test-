"""Player-level profile page with performance indicators and trends."""

from __future__ import annotations

from typing import Any, Dict

import pandas as pd
import plotly.express as px
import streamlit as st


from components.sidebar import render_sidebar_filters
from config.colors import CHART_COLORS
from components.data_loader import load_data
from components.utils import apply_filters
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
from scipy.stats import percentileofscore
import os

st.set_page_config(layout="wide")








def _load_filtered_players() -> pd.DataFrame:
    df_players, _ = load_data()
    filters = render_sidebar_filters(df_players)
    return apply_filters(df_players, filters)


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


def _load_cluster_info() -> pd.DataFrame:
    """Load cluster definitions from csv."""
    # Using data/val.csv as requested
    file_path = os.path.join("data", "val.csv")
    if not os.path.exists(file_path):
        st.error(f"Cluster data not found at {file_path}")
        return pd.DataFrame()
    
    # The new format has a header like ",0" and rows like "variable,Factor X"
    # We'll read it without header first to inspect or just skip first row if we know format
    # Based on user description: "Factor 1, ..."
    # Actually, the file content snippet showed:
    # ,0
    # kills,Factor 2
    # ...
    
    try:
        df = pd.read_csv(file_path)
        # Rename columns to standard names
        # Expecting the first column to be variable and second to be the factor string
        if len(df.columns) >= 2:
            df.columns = ['variable', 'cluster_label'] + list(df.columns[2:])
            
            # Extract cluster ID from "Factor X"
            # We use regex to extract the number
            df['cluster'] = df['cluster_label'].astype(str).str.extract(r'(\d+)').astype(float)
            
            return df
    except Exception as e:
        st.error(f"Error loading cluster data: {e}")
        return pd.DataFrame()
    
    return df


from factor_analyzer import FactorAnalyzer

def _calculate_factor_scores(player_name: str, position: str, full_data: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
    """
    Calculate Factor scores for the player based on clusters, relative to their position.
    Returns a dict: {cluster_id: {'name': str, 'score': float, 'vars': list}}
    """
    cluster_df = _load_cluster_info()
    if cluster_df.empty:
        return {}

    # Filter data for the same position
    position_data = full_data[full_data['position'] == position].reset_index(drop=True).copy()

    # Get player's position
    player_row = position_data[position_data['playername'] == player_name]
    if player_row.empty:
        return {}
    
    # If not enough data for analysis, return empty
    if len(position_data) < 3:
        return {}

    # Cluster mapping (Updated to 8 Factors)
    cluster_names = {
        1: '성장 기반 운영력 (Resource & Vision Baseline)',
        2: '후반 캐리 및 공성력 (Late-Game Carry & Siege)',
        3: '팀파이트 및 지원 능력 (Teamfight & Support)',
        4: '라인전 압도 지수 (Laning Phase Dominance)',
        5: '사망 기여 및 위험도 (Mortality & Risk)',
        6: '방어/전선 유지 및 중립 오브젝트 (Frontline & Objective)',
        7: '공격적 주도권 (Aggressive Initiative)',
        8: '상대팀 전투 우위 (Enemy Combat Advantage)'
    }
    
    results = {}
    
    # Loop through 8 factors
    for cluster_id in range(1, 9):
        # Get variables for this cluster
        vars_in_cluster = cluster_df[cluster_df['cluster'] == cluster_id]['variable'].tolist()
        
        # Filter variables that exist in the data
        valid_vars = [v for v in vars_in_cluster if v in position_data.columns]
        
        if not valid_vars:
            results[cluster_id] = {
                'name': cluster_names.get(cluster_id, str(cluster_id)),
                'score': 0.0,
                'vars': []
            }
            continue
            
        # Prepare data
        X = position_data[valid_vars].fillna(0)
        
        # Standardize
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        
        # Calculate scores
        scores = None
        
        # If only 1 variable, use it directly (standardized)
        if X.shape[1] == 1:
            scores = X_scaled
        else:
            try:
                # Use Factor Analysis
                # n_factors=1 to get a single composite score for the cluster
                fa = FactorAnalyzer(n_factors=1, rotation=None)
                fa.fit(X_scaled)
                scores = fa.transform(X_scaled)
            except Exception as e:
                # Fallback to PCA if FA fails (e.g. singular matrix, too few vars)
                # st.warning(f"FA failed for cluster {cluster_id}, falling back to PCA: {e}")
                try:
                    pca = PCA(n_components=1)
                    scores = pca.fit_transform(X_scaled)
                except:
                    # Fallback to mean if PCA also fails
                    scores = X_scaled.mean(axis=1).reshape(-1, 1)

        # Check direction: if correlation between component and sum of variables is negative, flip it
        # This ensures "more stats" = "higher score"
        if pd.Series(scores.flatten()).corr(X.sum(axis=1).reset_index(drop=True)) < 0:
            scores = -scores
            
        # Get score for the specific player
        # We need to find the index of the player in the position_data
        player_idx = position_data.index.get_loc(player_row.index[0])
        player_score = scores[player_row.index].mean()
        # Calculate percentile
        # percentile = percentileofscore(scores.flatten(), player_score)
        percentile = 50 + (player_score - scores.mean()) / scores.std() * 10
        percnet = (percentile-20) / 60 * 100
        
        results[cluster_id] = {
            'name': cluster_names.get(cluster_id, str(cluster_id)),
            'score': percentile,
            'vars': valid_vars,
            'percent': percnet,
        }
        
    return results


def render_page() -> pd.DataFrame:
    # st.header("Player Profile")
    
    filtered_df = _load_filtered_players()
    st.caption("현재 글로벌 필터를 반영한 플레이어 데이터입니다.")
    
    if filtered_df.empty:
        st.warning("필터링된 데이터가 없습니다. 필터를 조정해 주세요.")
        return filtered_df
    
    # Get unique player IDs
    # player_id_col = None
    # for col in filtered_df.columns:
    #     if col.lower() in ["playerid", "playername", "participantid"]:
    #         break
    player_id_col = 'playername'
    
    if player_id_col is None:
        st.error("플레이어 ID 컬럼을 찾을 수 없습니다.")
        return filtered_df
    
    unique_players = filtered_df[player_id_col].dropna().unique().tolist()
    
    if not unique_players:
        st.warning("선택할 플레이어가 없습니다.")
        return filtered_df
    
    # Sort players for better UX
    unique_players = sorted(unique_players, key=str)
    
    # Determine the index of the previously selected player if possible
    index = 0
    if "player_profile_selector" in st.session_state:
        previous_selection = st.session_state["player_profile_selector"]
        if previous_selection in unique_players:
            index = unique_players.index(previous_selection)
    
    # Player selector
    selected_player = st.selectbox(
        "플레이어 선택",
        options=unique_players,
        index=index,
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
    
    # Display basic info in a container
    # Display basic info in a container
    with st.container():
        col1, col2, col3, col4 = st.columns(4)
        
        # Team Name
        if "teamname" in player_data.columns:
            team_name = player_data["teamname"].iloc[0] if not player_data["teamname"].empty else "N/A"
            col1.metric("팀", team_name)
            
        # Position
        if "position" in player_data.columns:
            position = player_data["position"].iloc[0] if not player_data["position"].empty else "N/A"
            col2.metric("포지션", position)
            
        # Total Games
        total_games = len(player_data)
        col3.metric("총 경기 수", f"{total_games}")
        
        # Win Rate
        if "result" in player_data.columns:
            wins = pd.to_numeric(player_data["result"], errors="coerce")
            win_count = wins.sum() if not wins.isna().all() else 0
            win_rate = (win_count / total_games * 100) if total_games > 0 else 0
            col4.metric("승률", f"{win_rate:.1f}%")
    
    st.divider()

    # PCA Metrics Section
    st.subheader("Player Style Analysis (vs Position) N(50, 10)")
    
    # Calculate scores using the FULL dataset (filtered_df contains all players)
    # We need to pass the full dataset to calculate the distribution for the position
    pca_scores = _calculate_factor_scores(selected_player, position, filtered_df)
    st.caption("사망 기여 및 위험도 & 상대팀 전투 우위는 Negative지표입니다.")
    
    if pca_scores:
        # Display 8 clusters in 2 rows of 4
        # First row (Clusters 1-4)
        cols1 = st.columns(4)
        for i, cluster_id in enumerate(range(1, 5)):
            if cluster_id in pca_scores:
                data = pca_scores[cluster_id]
                with cols1[i]:
                    st.metric(
                        label=data['name'],
                        value=f"{data['score']:.0f}",
                        help=f"Variables: {', '.join(data['vars'])}"
                    )
        
        st.write("") # Spacer
        
        # Second row (Clusters 5-8)
        cols2 = st.columns(4)
        for i, cluster_id in enumerate(range(5, 9)):
            if cluster_id in pca_scores:
                data = pca_scores[cluster_id]
                with cols2[i]:
                    st.metric(
                        label=data['name'],
                        value=f"{data['score']:.0f}",
                        help=f"Variables: {', '.join(data['vars'])}"
                    )
    else:
        st.info("데이터 부족으로 스타일 분석을 수행할 수 없습니다.")
    
    # Most 5 Champions Table
    st.subheader("Most 5 Champions")
    
    if not player_data.empty:
        # Calculate stats per champion
        champ_stats = player_data.groupby("champion").agg(
            gameplay=("champion", "count"),
            win_rate=("result", lambda x: pd.to_numeric(x, errors="coerce").mean() * 100),
            kda=("KDA", "mean"),
            gd10=("golddiffat10", "mean"),
            gd15=("golddiffat15", "mean"),
            gd20=("golddiffat20", "mean"),
            gd25=("golddiffat25", "mean"),
            cpm=("cspm", "mean"),
            dpm=("dpm", "mean"),
            visionscore=("visionscore", "mean"),
        ).reset_index()
        
        # Sort by gameplay descending and take top 5
        most_5 = champ_stats.sort_values("gameplay", ascending=False).head(5)
        
        # Rename columns for display
        most_5 = most_5.rename(columns={
            "champion": "Champion",
            "gameplay": "Games",
            "win_rate": "Win Rate",
            "kda": "KDA",
            "gd10": "GD@10",
            "gd15": "GD@15",
            "gd20": "GD@20",
            "gd25": "GD@25",
            "cpm": "CPM",
            "dpm": "DPM",
            "visionscore": "VS",
        })
        
        # Display table
        st.dataframe(
            most_5,
            column_config={
                "Win Rate": st.column_config.NumberColumn(format="%.1f%%"),
                "KDA": st.column_config.NumberColumn(format="%.2f"),
                "GD@10": st.column_config.NumberColumn(format="%.0f"),
                "GD@15": st.column_config.NumberColumn(format="%.0f"),
                "GD@20": st.column_config.NumberColumn(format="%.0f"),
                "GD@25": st.column_config.NumberColumn(format="%.0f"),
                "CPM": st.column_config.NumberColumn(format="%.1f"),
                "DPM": st.column_config.NumberColumn(format="%.0f"),
                "VS": st.column_config.NumberColumn(format="%.1f"),
            },
            width="stretch",
            hide_index=True
        )
    else:
        st.info("챔피언 데이터가 없습니다.")

    st.divider()
    
    # Debug section in expander
    with st.expander("🔧 디버그 정보", expanded=False):
        if st.checkbox("플레이어 데이터 미리보기", value=False):
            st.write("Shape:", player_data.shape)
            st.dataframe(player_data.head(), width="stretch")
    
    return filtered_df


filtered_players_df = render_page()

