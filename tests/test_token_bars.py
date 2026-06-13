from tktop.metrics.types import TokenUsage
from tktop.tui.widgets.token_bars import TokenBars, _fmt


def test_token_bars_shows_model():
    bars = TokenBars()
    bars.update_usage(TokenUsage(input_tokens=100, output_tokens=50), "claude-opus-4-6")
    text = bars.render()
    assert "claude-opus-4-6" in text.plain


def test_token_bars_no_model_by_default():
    bars = TokenBars()
    bars.update_usage(TokenUsage(input_tokens=100, output_tokens=50))
    text = bars.render()
    assert "Model" not in text.plain


def test_token_bars_model_persists_across_updates():
    bars = TokenBars()
    bars.update_usage(TokenUsage(input_tokens=100, output_tokens=50), "claude-opus-4-6")
    bars.update_usage(TokenUsage(input_tokens=200, output_tokens=100))
    text = bars.render()
    assert "claude-opus-4-6" in text.plain


def test_fmt_millions():
    assert _fmt(1_500_000) == "1.5M"


def test_fmt_thousands():
    assert _fmt(2_500) == "2.5k"


def test_fmt_small():
    assert _fmt(42) == "42"
