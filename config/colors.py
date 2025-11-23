"""Centralized color theme configuration for all charts and visualizations."""

# Main color palette
CHART_COLORS = {
    # Win/Loss colors
    "win": "#2ecc71",  # Green
    "loss": "#e74c3c",  # Red
    
    # Player colors (for comparisons)
    "player_a": "#1f77b4",  # Blue
    "player_b": "#ff7f0e",  # Orange
    
    # Team colors (for comparisons)
    "team_a": "#3498db",  # Light Blue
    "team_b": "#e67e22",  # Orange
    
    # Profile colors
    "player_profile": "#1f77b4",  # Blue
    "team_profile": "#2ecc71",  # Green
    
    # Comparison colors
    "positive": "#2ecc71",  # Green (better)
    "negative": "#e74c3c",  # Red (worse)
    "neutral": "#95a5a6",  # Gray (equal)
    
    # Chart elements
    "grid": "#dfe6e9",  # Light gray for gridlines
    "divider": "#34495e",  # Dark gray for dividers/zero lines
    
    # Default colors
    "primary": "#1f77b4",  # Primary blue
    "secondary": "#2ecc71",  # Secondary green
    "accent": "#ff7f0e",  # Accent orange
}

# Color mapping for discrete color scales
COLOR_DISCRETE_MAP = {
    "win_loss": {
        "Win": CHART_COLORS["win"],
        "Loss": CHART_COLORS["loss"],
    },
}

# List of colors for multi-series charts (qualitative palette)
QUALITATIVE_COLORS = [
    CHART_COLORS["player_a"],
    CHART_COLORS["player_b"],
    CHART_COLORS["team_a"],
    CHART_COLORS["team_b"],
    CHART_COLORS["accent"],
    "#9467bd",  # Purple
    "#8c564b",  # Brown
    "#e377c2",  # Pink
]

