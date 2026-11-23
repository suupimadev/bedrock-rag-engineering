from dataclasses import dataclass


@dataclass(frozen=True)
class ModelInfo:
    id: str
    display_name: str
    provider: str


AVAILABLE_MODELS: list[ModelInfo] = [
    ModelInfo(id="amazon.nova-lite-v1:0", display_name="Nova Lite", provider="Amazon"),
    ModelInfo(id="apac.amazon.nova-micro-v1:0", display_name="Nova Micro", provider="Amazon"),
    ModelInfo(id="apac.amazon.nova-pro-v1:0", display_name="Nova Pro", provider="Amazon"),
    # jp.anthropic.claude-haiku-5-5は2026-11-03時点でこのAWSアカウントに
    # モデルアクセス権がなく(AccessDeniedException)、比較対象から除外している。
]

ALLOWED_MODEL_IDS = frozenset(model.id for model in AVAILABLE_MODELS)


def is_model_allowed(model_id: str) -> bool:
    return model_id in ALLOWED_MODEL_IDS
