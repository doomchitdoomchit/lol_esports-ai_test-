import pytest

from components.charts import create_radar_chart


def test_create_radar_chart_single_series():
    stats = {"KDA": 4.5, "DPM": 600}
    fig = create_radar_chart(stats, title="Sample Player")
    assert fig.data and len(fig.data) == 1
    trace = fig.data[0]
    assert list(trace.theta) == ["KDA", "DPM"]
    assert list(trace.r) == [4.5, 600]


def test_create_radar_chart_multi_series():
    stats = [
        {"KDA": 4.5, "DPM": 600},
        {"KDA": 3.2, "DPM": 520},
    ]
    fig = create_radar_chart(stats, title="Comparison", labels=["Player A", "Player B"])
    assert len(fig.data) == 2
    assert fig.layout.showlegend is True
    assert fig.data[0].name == "Player A"
    assert fig.data[1].name == "Player B"


def test_create_radar_chart_invalid_labels():
    stats = [{"KDA": 4.5}, {"KDA": 5.0}]
    with pytest.raises(ValueError):
        create_radar_chart(stats, title="Mismatch", labels=["Only one"])


def test_create_radar_chart_non_numeric_value():
    stats = {"KDA": "not-a-number"}
    with pytest.raises(ValueError):
        create_radar_chart(stats, title="Invalid")

