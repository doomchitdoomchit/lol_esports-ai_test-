"""Exploratory Data Analysis page for the LCK dashboard."""

from __future__ import annotations

from typing import Any, Dict

import pandas as pd
import plotly.express as px
import streamlit as st

from data_loader import load_data


def _get_active_filters() -> Dict[str, Any]:
    filters = st.session_state.get("filters")
    if not filters:
        st.warning(
            "Global filters are not initialized yet. Showing unfiltered results."
        )
        return {}
    return filters


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


def _summaries(filtered_df):
    col1, col2, col3 = st.columns(3)

    total_games = len(filtered_df)
    col1.metric("Total Games", f"{total_games:,}")

    if "playerid" in filtered_df.columns:
        unique_players = filtered_df["playerid"].nunique()
    else:
        unique_players = 0
        st.warning("'playerid' column missing; unable to compute unique players.")
    col2.metric("Unique Players", f"{unique_players:,}")

    win_rate_display = "0%"
    if total_games > 0 and "result" in filtered_df.columns:
        wins = pd.to_numeric(filtered_df["result"], errors="coerce")
        valid = wins.dropna()
        if not valid.empty:
            win_rate = valid.mean()
            win_rate_display = f"{win_rate:.1%}"
    elif "result" not in filtered_df.columns:
        st.warning("'result' column missing; unable to compute win rate.")
    col3.metric("Overall Win Rate", win_rate_display)


def _win_loss_chart(filtered_df):
    st.subheader("Win/Loss Distribution")
    if filtered_df.empty:
        st.info("선택된 필터에 해당하는 경기가 없습니다.")
        return
    if "result" not in filtered_df.columns:
        st.warning("'result' column missing; unable to render distribution.")
        return

    results = pd.to_numeric(filtered_df["result"], errors="coerce").dropna()
    if results.empty:
        st.info("결과 데이터를 해석할 수 없어 차트를 표시할 수 없습니다.")
        return

    label_map = {1: "Win", 0: "Loss"}
    counts = results.value_counts().rename(index=label_map)
    chart_df = counts.reset_index()
    chart_df.columns = ["Result", "Count"]

    fig = px.pie(
        chart_df,
        names="Result",
        values="Count",
        hole=0.35,
        color="Result",
        color_discrete_map={"Win": "#2ecc71", "Loss": "#e74c3c"},
    )
    fig.update_layout(legend_title_text="", margin=dict(t=40, b=10))
    st.plotly_chart(fig, use_container_width=True)


def _data_preview(filtered_df):
    st.subheader("Data Preview")
    if filtered_df.empty:
        st.info("표시할 행이 없습니다. 필터를 조정해 보세요.")
        return
    st.dataframe(filtered_df.head(20), use_container_width=True)
    st.caption(f"Showing up to 20 of {len(filtered_df):,} rows.")
    # TODO: add download button for filtered dataset if needed


def render_page():
    st.header("Exploratory Data Analysis")

    df_players, _ = load_data()
    filters = _get_active_filters()
    filtered_df = _apply_filters(df_players, filters)

    st.caption("글로벌 필터에 맞춰 플레이어 데이터를 슬라이싱했습니다.")
    _summaries(filtered_df)
    _win_loss_chart(filtered_df)
    _data_preview(filtered_df)

    if st.checkbox("디버그: 필터 상태 보기", value=False):
        st.json(filters)
        st.write("Filtered shape:", filtered_df.shape)

    return filtered_df


filtered_players_df = render_page()

