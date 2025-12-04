"""Streamlit entry point for the LOL Esports analytics dashboard."""

from __future__ import annotations

from typing import Any, Dict, List, Sequence, Tuple

import streamlit as st

from components.data_loader import load_data

st.set_page_config(page_title="LCK Analytics", layout="wide")

# Apply custom CSS for improved visual hierarchy
st.markdown("""
<style>
    /* Improve header and subheader styling */
    h1 {
        margin-bottom: 0.5rem;
        font-weight: 600;
    }
    
    h2 {
        margin-top: 1rem;
        margin-bottom: 0.5rem;
        font-weight: 500;
        font-size: 1.5rem;
    }
    
    h3 {
        margin-top: 0.75rem;
        margin-bottom: 0.5rem;
        font-weight: 500;
        font-size: 1.2rem;
    }
    
    /* Improve spacing for captions */
    .stCaption {
        margin-bottom: 1rem;
    }
    
    /* Improve metric card spacing */
    [data-testid="stMetricValue"] {
        font-size: 2rem;
    }
    
    /* Improve container spacing */
    .stContainer {
        padding: 0.5rem 0;
    }
    
    /* Improve expander styling */
    .streamlit-expanderHeader {
        font-weight: 500;
    }
    
    /* Reduce excessive padding in plotly charts */
    .js-plotly-plot {
        margin: 0;
    }
    
    /* Improve divider visibility */
    hr {
        margin: 1rem 0;
        border: none;
        border-top: 1px solid #e0e0e0;
    }
</style>
""", unsafe_allow_html=True)

from components.sidebar import render_sidebar_filters


def main() -> Dict[str, Any]:
    """Render the base layout with preloaded datasets and sidebar filters."""

    df_players, df_teams = load_data()
    filters = render_sidebar_filters(df_players)

    st.title("LOL Esports (LCK) Insights")
    st.caption("Explore player and team level trends across seasons.")

    st.header("주요 기능 (Major Features)")
    
    st.markdown("이 프로젝트는 다음과 같은 분석 페이지를 제공합니다:")

    st.subheader("1. EDA")
    st.page_link("pages/1_EDA.py", label="Go to EDA", icon="📊")
    st.markdown("""
    *   **Champion Analysis**: 팀 데이터를 기반으로 챔피언 픽/밴/승률/패배율을 분석합니다.
    *   **Game Analysis**: 진영별 승률(Blue vs Red), 게임 시간 분포, 첫 오브젝트 획득 시 승률 등을 시각화합니다.
    """)

    st.subheader("2. Champion Stats")
    st.page_link("pages/2_Champion_Stats.py", label="Go to Champion Stats", icon="🏆")
    st.markdown("""
    *   챔피언별 상세 통계(Pick%, Ban%, Win%, P+B%)를 테이블 형태로 제공합니다.
    *   포지션별 필터링 및 정렬 기능을 지원합니다.
    """)

    st.subheader("3. Player Profile")
    st.page_link("pages/3_Player_Profile.py", label="Go to Player Profile", icon="👤")
    st.markdown("""
    *   선수 개인의 상세 프로필 및 성과 지표(KDA, DPM, GPM 등)를 조회합니다.
    *   **Player Style Analysis**: 8가지 요인(Factor) 기반의 레이더 차트를 통해 선수의 플레이 스타일을 분석합니다.
    *   **Most 5 Champions**: 선수가 주로 사용하는 상위 5개 챔피언의 상세 성적을 보여줍니다.
    """)

    st.subheader("4. Team Profile")
    st.page_link("pages/4_Team_Profile.py", label="Go to Team Profile", icon="🛡️")
    st.markdown("""
    *   팀 단위의 성과 지표 및 리그 평균과의 비교 분석을 제공합니다.
    *   **Performance Radar**: 리그 평균 대비 팀의 주요 지표(KDA, DPM, GPM, VSPM)를 레이더 차트로 비교합니다.
    *   **Laning Phase**: 시간대별(10~25분) 골드 및 CS 격차를 시각화합니다.
    *   **Object Control**: 오브젝트(드래곤, 바론, 전령 등) 획득에 따른 승률을 분석합니다.
    """)

    st.subheader("5. Player Comparison")
    st.page_link("pages/5_Player_Comparison.py", label="Go to Player Comparison", icon="🆚")
    st.markdown("""
    *   두 선수를 선택하여 1:1로 비교 분석합니다.
    *   **Style Comparison**: 두 선수의 플레이 스타일을 겹쳐진 레이더 차트와 차이 그래프로 비교합니다.
    *   **Head-to-Head**: 두 선수의 맞대결 전적 및 상세 기록을 조회합니다.
    """)

    st.divider()

    if st.sidebar.checkbox("Show sample data", value=False):
        st.subheader("Sample player rows")
        st.dataframe(df_players.head())
        st.subheader("Sample team rows")
        st.dataframe(df_teams.head())

    return {
        "players": df_players,
        "teams": df_teams,
        "filters": filters,
    }


if __name__ == "__main__":
    main()

