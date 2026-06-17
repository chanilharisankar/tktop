from tktop.metrics.types import TurnCost
from tktop.tui.widgets.cost_graph import CostGraph, _cost, _sample


def test_sample_passthrough_when_short():
    data = [1.0, 2.0, 3.0]
    assert _sample(data, 10) == data


def test_sample_downsamples_long_data():
    data = list(range(100))
    result = _sample(data, 10)
    assert len(result) == 10


def test_sample_preserves_first_element():
    data = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0]
    result = _sample(data, 3)
    assert result[0] == 0.5


def test_cost_graph_update_data():
    graph = CostGraph()
    graph.update_data([0.01, 0.05, 0.12], 0.12, 3)
    assert graph.data == [0.01, 0.05, 0.12]
    assert graph.total_cost == 0.12
    assert graph.turn_count == 3


def test_cost_graph_update_data_with_turn_costs():
    tc = [TurnCost(1, 0.01, 0.02, 0.0, 0.0)]
    graph = CostGraph()
    graph.update_data([0.03], 0.03, 1, tc)
    assert graph.turn_costs == tc


def test_cost_graph_render_waiting_message():
    graph = CostGraph()
    graph.update_data([], 0.0, 0)
    text = graph.render()
    assert "Waiting for data" in text.plain


def test_cost_graph_render_one_turn_shows_breakdown_table():
    turn_costs = [
        TurnCost(
            1,
            input_cost=0.003,
            output_cost=0.015,
            cache_write_cost=0.001,
            cache_read_cost=0.0002,
        ),
    ]
    graph = CostGraph()
    graph.update_data([0.0192], 0.0192, 1, turn_costs)
    plain = graph.render().plain
    assert "Trend starts after 2 assistant turns" in plain
    assert "Input" in plain
    assert "$0.0030" in plain


def test_cost_graph_render_unknown_pricing_message():
    turn_costs = [TurnCost(1), TurnCost(2)]
    graph = CostGraph()
    graph.update_data([0.0, 0.0], 0.0, 2, turn_costs)
    plain = graph.render().plain
    assert "No priced cost data for this model" in plain
    assert "Input" in plain


def test_cost_graph_render_with_data():
    graph = CostGraph()
    graph.update_data([0.01, 0.05, 0.12, 0.20], 0.20, 4)
    text = graph.render()
    plain = text.plain
    assert "Estimated API-equivalent cost" in plain
    assert "$0.2000" in plain
    assert "4" in plain
    assert "Waiting" not in plain


def test_cost_graph_render_shows_breakdown_table():
    turn_costs = [
        TurnCost(
            1, input_cost=0.003, output_cost=0.015,
            cache_write_cost=0.001, cache_read_cost=0.0002,
        ),
        TurnCost(
            2, input_cost=0.006, output_cost=0.030,
            cache_write_cost=0.0, cache_read_cost=0.001,
        ),
    ]
    graph = CostGraph()
    graph.update_data([0.02, 0.06], 0.06, 2, turn_costs)
    plain = graph.render().plain
    assert "Input" in plain
    assert "Output" in plain
    assert "CaWr" in plain
    assert "CaRd" in plain


def test_cost_graph_breakdown_truncates_to_last_10():
    turn_costs = [TurnCost(i, input_cost=0.01) for i in range(15)]
    cumulative = [0.01 * (i + 1) for i in range(15)]
    graph = CostGraph()
    graph.update_data(cumulative, 0.15, 15, turn_costs)
    plain = graph.render().plain
    assert "5 earlier turns hidden" in plain


def test_cost_formatter_zero():
    assert _cost(0) == "—"


def test_cost_formatter_tiny():
    assert _cost(0.00005) == "$0.00005"


def test_cost_formatter_normal():
    assert _cost(0.0123) == "$0.0123"
