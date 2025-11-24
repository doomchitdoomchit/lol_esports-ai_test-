
import pandas as pd
import numpy as np

def calculate_champion_stats_logic(filtered_df: pd.DataFrame) -> pd.DataFrame:
    """
    Proposed logic for calculating champion stats.
    """
    if filtered_df.empty:
        return pd.DataFrame()

    # 1. Calculate Basic Stats (Win Rate, Pick Count) grouped by Champion
    # We use 'gameplay' as the count of games played (picks)
    # We merge positions into a string
    stats = filtered_df.groupby("champion").agg(
        win_rate=("result", "mean"),
        gameplay=("champion", "count"),  # This is pick_count
        position=("position", lambda x: "/".join(sorted(x.unique())))
    ).reset_index()

    # 2. Calculate Total Unique Games (for rates)
    if "gameid" in filtered_df.columns:
        total_games = filtered_df["gameid"].nunique()
    else:
        total_games = len(filtered_df) / 10 
        
    # 3. Calculate Pick Rate
    stats["pick_rate"] = stats["gameplay"] / total_games if total_games > 0 else 0

    # 4. Calculate Ban Rate (Global per Champion)
    if "gameid" in filtered_df.columns:
        unique_games_df = filtered_df.drop_duplicates(subset=["gameid"])
    else:
        unique_games_df = filtered_df

    ban_columns = [col for col in filtered_df.columns if col.startswith("ban") and col[3:].isdigit()]
    ban_counts = {}
    
    for _, row in unique_games_df.iterrows():
        for ban_col in ban_columns:
            ban_champ = row[ban_col]
            if pd.notna(ban_champ) and ban_champ != "":
                ban_counts[ban_champ] = ban_counts.get(ban_champ, 0) + 1
    
    # Create Ban Dataframe
    ban_df = pd.DataFrame(list(ban_counts.items()), columns=["champion", "ban_count"])
    ban_df["ban_rate"] = ban_df["ban_count"] / total_games if total_games > 0 else 0
    
    # 5. Merge Ban Rate into Stats
    stats = stats.merge(ban_df[["champion", "ban_rate"]], on="champion", how="left")
    stats["ban_rate"] = stats["ban_rate"].fillna(0)

    # 6. Calculate P+B%
    stats["p_b_rate"] = stats["pick_rate"] + stats["ban_rate"]

    return stats

def test_champion_stats():
    # Mock Data
    # 2 Games.
    # Game 1: Team A (Win) vs Team B (Loss). 
    #   Bans: A banned [C1, C2, C3], B banned [C4, C5, C6]
    #   Picks: A [P1-Top, P2-Jng...], B [P6-Top...]
    
    data = {
        "gameid": ["G1"]*10 + ["G2"]*10,
        "result": [1]*5 + [0]*5 + [0]*5 + [1]*5, # G1: T1 Win, T2 Loss. G2: T1 Loss, T2 Win.
        "position": ["top", "jng", "mid", "bot", "sup"] * 4,
        "champion": [
            "Aatrox", "Lee Sin", "Ahri", "Ezreal", "Karma", # G1 T1
            "Renekton", "Viego", "Orianna", "Kaisa", "Lulu", # G1 T2
            "Renekton", "Lee Sin", "Ahri", "Ezreal", "Karma", # G2 T1 (Renekton Top now)
            "Aatrox", "Viego", "Orianna", "Kaisa", "Lulu", # G2 T2 (Aatrox Top now)
        ],
        "ban1": ["Zed"]*10 + ["Zed"]*10, # Zed banned in both games
        "ban2": ["Yasuo"]*10 + [""]*10, # Yasuo banned in G1 only
    }
    # Add dummy cols for other bans
    for i in range(3, 6):
        data[f"ban{i}"] = [""] * 20
        
    df = pd.DataFrame(data)
    
    print("Input Data (Head):")
    print(df.head())
    
    stats = calculate_champion_stats_logic(df)
    
    print("\nCalculated Stats:")
    print(stats)
    
    # Assertions
    
    # Aatrox: Picked in G1 (Top), G2 (Top). Position should be "top".
    aatrox = stats[stats["champion"] == "Aatrox"].iloc[0]
    print("\nAatrox Stats:", aatrox.to_dict())
    assert aatrox["gameplay"] == 2
    assert aatrox["win_rate"] == 1.0
    assert aatrox["pick_rate"] == 1.0
    assert aatrox["position"] == "top"
    
    # Renekton: Picked in G1 (Top), G2 (Top). Position "top".
    renekton = stats[stats["champion"] == "Renekton"].iloc[0]
    print("\nRenekton Stats:", renekton.to_dict())
    assert renekton["position"] == "top"
    
    # Let's modify data to test merged positions
    # Change Aatrox in G2 to Mid
    df.loc[15, "position"] = "mid" # Index 15 is Aatrox in G2 (T2 Top originally, now Mid)
    # Note: Index 15 corresponds to G2 T2 Top.
    
    print("\nRetesting with multi-position Aatrox...")
    stats_multi = calculate_champion_stats_logic(df)
    aatrox_multi = stats_multi[stats_multi["champion"] == "Aatrox"].iloc[0]
    print("Aatrox Multi Stats:", aatrox_multi.to_dict())
    
    # Position should be "mid/top" or "top/mid" (sorted)
    assert aatrox_multi["position"] == "mid/top"
    
    print("\nTest Finished Successfully")

if __name__ == "__main__":
    test_champion_stats()
