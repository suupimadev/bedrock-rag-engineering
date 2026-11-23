from app.pricing import PRICING_TABLE, estimate_cost_usd


def test_estimate_cost_usd_for_known_model() -> None:
    cost = estimate_cost_usd("amazon.nova-lite-v1:0", input_tokens=1000, output_tokens=1000)
    pricing = PRICING_TABLE["amazon.nova-lite-v1:0"]
    assert cost == round(pricing.input_price_per_1k_tokens + pricing.output_price_per_1k_tokens, 8)


def test_estimate_cost_usd_scales_with_token_count() -> None:
    cost_1k = estimate_cost_usd("apac.amazon.nova-pro-v1:0", input_tokens=1000, output_tokens=0)
    cost_2k = estimate_cost_usd("apac.amazon.nova-pro-v1:0", input_tokens=2000, output_tokens=0)
    assert cost_2k == round(cost_1k * 2, 8)


def test_estimate_cost_usd_zero_tokens_is_zero() -> None:
    cost = estimate_cost_usd("amazon.nova-lite-v1:0", input_tokens=0, output_tokens=0)
    assert cost == 0.0


def test_estimate_cost_usd_unknown_model_returns_none() -> None:
    cost = estimate_cost_usd("some-unpriced-model", input_tokens=100, output_tokens=100)
    assert cost is None
