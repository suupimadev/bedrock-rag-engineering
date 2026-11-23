from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ModelPricing:
    input_price_per_1k_tokens: float  # USD
    output_price_per_1k_tokens: float  # USD


# 2026年10月時点、サードパーティ集計サイトからの参考値(USD)。
# AWS公式の請求額とは異なる場合がある「推定値」であり、実際の請求額ではない。
PRICING_TABLE: dict[str, ModelPricing] = {
    "amazon.nova-lite-v1:0": ModelPricing(input_price_per_1k_tokens=0.00006, output_price_per_1k_tokens=0.00024),
    "apac.amazon.nova-micro-v1:0": ModelPricing(
        input_price_per_1k_tokens=0.000035, output_price_per_1k_tokens=0.00014
    ),
    "apac.amazon.nova-pro-v1:0": ModelPricing(input_price_per_1k_tokens=0.0008, output_price_per_1k_tokens=0.0032),
}


def estimate_cost_usd(model_id: str, input_tokens: int, output_tokens: int) -> Optional[float]:
    """モデル・トークン数から概算コスト(USD)を計算する。

    料金表にないモデルの場合はNoneを返す(計算不能であることを明示するため、0は返さない)。
    """
    pricing = PRICING_TABLE.get(model_id)
    if pricing is None:
        return None

    input_cost = (input_tokens / 1000) * pricing.input_price_per_1k_tokens
    output_cost = (output_tokens / 1000) * pricing.output_price_per_1k_tokens
    return round(input_cost + output_cost, 8)
