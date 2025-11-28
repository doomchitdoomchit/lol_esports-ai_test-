
import pandas as pd
import numpy as np

def calculate_most_5_champions(player_data: pd.DataFrame) -> pd.DataFrame:
    """
    Proposed logic for calculating Most 5 Champions.
    """
    if player_data.empty:
        return pd.DataFrame()

    # Group by champion
    stats = player_data.groupby("champion").agg(
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

    # Sort by gameplay descending
    stats = stats.sort_values("gameplay", ascending=False)
    
    # Take top 5
    return stats.head(5)

def test_player_profile_logic():
    # Mock Data
    data = {
        "champion": ["Aatrox", "Aatrox", "Lee Sin", "Lee Sin", "Ahri", "Ezreal", "Karma"],
        "result": [1, 0, 1, 1, 0, 1, 0], # Aatrox: 50%, Lee Sin: 100%
        "KDA": [3.0, 1.0, 5.0, 4.0, 2.0, 6.0, 1.0],
        "golddiffat10": [100, -50, 200, 150, -100, 300, -200],
        "golddiffat15": [200, -100, 400, 300, -200, 600, -400],
        "golddiffat20": [300, -150, 600, 450, -300, 900, -600],
        "golddiffat25": [400, -200, 800, 600, -400, 1200, -800],
        "cspm": [8.0, 7.0, 6.0, 6.5, 8.5, 9.0, 1.0],
        "dpm": [500, 400, 300, 350, 600, 800, 200],
        "visionscore": [20, 15, 40, 35, 25, 10, 60],
    }
    df = pd.DataFrame(data)
    
    print("Input Data (Head):")
    print(df.head())
    
    most_5 = calculate_most_5_champions(df)
    
    print("\nMost 5 Champions:")
    print(most_5)
    
    # Assertions
    # Aatrox: 2 games, 50% WR.
    aatrox = most_5[most_5["champion"] == "Aatrox"].iloc[0]
    assert aatrox["gameplay"] == 2
    assert aatrox["win_rate"] == 50.0
    assert aatrox["kda"] == 2.0
    assert aatrox["gd10"] == 25.0 # (100 - 50) / 2
    
    # Lee Sin: 2 games, 100% WR.
    lee = most_5[most_5["champion"] == "Lee Sin"].iloc[0]
    assert lee["gameplay"] == 2
    assert lee["win_rate"] == 100.0
    
    # Check sorting (Aatrox and Lee Sin have 2 games, others 1. They should be top 2)
    top_2_champs = most_5["champion"].iloc[:2].tolist()
    assert "Aatrox" in top_2_champs
    assert "Lee Sin" in top_2_champs
    
    print("\nTest Finished Successfully")

if __name__ == "__main__":
    test_player_profile_logic()
