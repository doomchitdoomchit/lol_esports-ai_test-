"""Utilities for loading and caching LCK data used across the app."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import pandas as pd
import streamlit as st

DEFAULT_DATA_PATH = Path("data") / "lck.csv"
DEFAULT_NA_VALUES: tuple[str, ...] = ("", "NA", "N/A")


def _resolve_column(columns: Iterable[str], *candidates: str) -> str:
    for candidate in candidates:
        if candidate in columns:
            return candidate
    raise KeyError(f"None of the candidate columns {candidates} exist in the dataset.")


def _drop_unnamed_columns(df: pd.DataFrame) -> pd.DataFrame:
    unnamed_cols = [col for col in df.columns if col.strip().lower().startswith("unnamed")]
    if unnamed_cols:
        df = df.drop(columns=unnamed_cols)
    return df


def _safe_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").fillna(0)


@st.cache_data
def load_data(file_path: str | Path = DEFAULT_DATA_PATH) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load, clean, and split the LCK dataset for players and teams.

    Args:
        file_path: Path to the CSV file. Defaults to ``data/lck.csv``.

    Returns:
        Tuple of two DataFrames: (players, teams). The players DataFrame includes
        a computed ``KDA`` column, while the teams DataFrame contains rows where
        ``position == 'team'``.

    Raises:
        FileNotFoundError: If the CSV cannot be located.
        ValueError: If required columns are missing or if either result DataFrame
            would be empty.
    """

    csv_path = Path(file_path)
    if not csv_path.exists():
        raise FileNotFoundError(f"Could not locate data file at {csv_path}")

    df = pd.read_csv(csv_path, keep_default_na=True, na_values=DEFAULT_NA_VALUES)
    df = _drop_unnamed_columns(df)
    df = df.rename(columns=lambda col: col.strip())

    position_col = _resolve_column(df.columns, "position", "Position")
    player_identifier_col = _resolve_column(df.columns, "playerid", "playername", "participantid")
    kills_col = _resolve_column(df.columns, "Kills", "kills")
    assists_col = _resolve_column(df.columns, "Assists", "assists")
    deaths_col = _resolve_column(df.columns, "Deaths", "deaths")

    df = df.dropna(subset=[position_col]).copy()
    positions = df[position_col].astype(str).str.strip()
    positions_lower = positions.str.lower()

    non_team_mask = positions_lower != "team"
    valid_players_mask = df[player_identifier_col].notna()
    df = df[~non_team_mask | (non_team_mask & valid_players_mask)].copy()

    df_players = df[non_team_mask & valid_players_mask].copy()
    df_teams = df[~non_team_mask].copy()

    if df_players.empty:
        raise ValueError("No player-level rows were found in the dataset.")
    if df_teams.empty:
        raise ValueError("No team-level rows were found in the dataset.")

    kills = _safe_numeric(df_players[kills_col])
    assists = _safe_numeric(df_players[assists_col])
    deaths = _safe_numeric(df_players[deaths_col]).replace(0, 1)
    df_players["KDA"] = (kills + assists) / deaths

    df_players = df_players.reset_index(drop=True)
    df_teams = df_teams.reset_index(drop=True)

    return df_players, df_teams

