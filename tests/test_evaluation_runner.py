import json

import pytest

from app.bedrock_client import BedrockInvocationError, ChatResult
from app.models import AVAILABLE_MODELS
from evaluation.runner import (
    MAX_OUTPUT_TOKENS_CEILING,
    MAX_QUESTIONS,
    MAX_REPEATS,
    EvalRecord,
    aggregate_by_model,
    aggregate_rubric_scores,
    load_questions,
    load_records_from_csv,
    percentile,
    rescore_objective,
    run_evaluation,
    save_records_csv,
    save_summary_json,
)

OBJECTIVE_QUESTION = {"id": "obj-01", "category": "objective", "question": "1+1は？", "expected_keywords": ["2"]}
RUBRIC_QUESTION = {"id": "sub-01", "category": "rubric", "question": "AWSの良いところを教えて"}


def fake_correct_call(message: str, model_id: str, temperature: float, max_tokens: int) -> ChatResult:
    return ChatResult(
        reply="答えは2です",
        model_id=model_id,
        input_tokens=5,
        output_tokens=5,
        bedrock_duration_ms=100.0,
        estimated_cost_usd=0.0001,
    )


def fake_failing_call(message: str, model_id: str, temperature: float, max_tokens: int) -> ChatResult:
    raise BedrockInvocationError("throttled", status_code=429)


def test_run_evaluation_scores_objective_question_correctly() -> None:
    records = run_evaluation([OBJECTIVE_QUESTION], repeats=1, temperature=0.2, call_fn=fake_correct_call)
    assert len(records) == len(AVAILABLE_MODELS)
    assert all(r.is_correct is True for r in records)


def test_run_evaluation_leaves_rubric_question_unscored() -> None:
    records = run_evaluation([RUBRIC_QUESTION], repeats=1, temperature=0.2, call_fn=fake_correct_call)
    assert all(r.is_correct is None for r in records)


def test_run_evaluation_records_errors_without_raising() -> None:
    records = run_evaluation([OBJECTIVE_QUESTION], repeats=1, temperature=0.2, call_fn=fake_failing_call)
    assert all(r.error is not None for r in records)
    assert all(r.is_correct is None for r in records)


def test_run_evaluation_rejects_too_many_repeats() -> None:
    with pytest.raises(ValueError):
        run_evaluation([OBJECTIVE_QUESTION], repeats=MAX_REPEATS + 1, temperature=0.2, call_fn=fake_correct_call)


def test_run_evaluation_rejects_too_many_questions() -> None:
    too_many_questions = [OBJECTIVE_QUESTION] * (MAX_QUESTIONS + 1)
    with pytest.raises(ValueError):
        run_evaluation(too_many_questions, repeats=1, temperature=0.2, call_fn=fake_correct_call)


def test_run_evaluation_rejects_max_tokens_over_ceiling() -> None:
    with pytest.raises(ValueError):
        run_evaluation(
            [OBJECTIVE_QUESTION],
            repeats=1,
            temperature=0.2,
            call_fn=fake_correct_call,
            max_tokens=MAX_OUTPUT_TOKENS_CEILING + 1,
        )


def test_run_evaluation_passes_max_tokens_through_to_call_fn() -> None:
    received_max_tokens = {}

    def fake_call_capturing_max_tokens(message, model_id, temperature, max_tokens):
        received_max_tokens["value"] = max_tokens
        return fake_correct_call(message, model_id, temperature, max_tokens)

    run_evaluation(
        [OBJECTIVE_QUESTION],
        repeats=1,
        temperature=0.2,
        call_fn=fake_call_capturing_max_tokens,
        max_tokens=512,
    )
    assert received_max_tokens["value"] == 512


def test_load_questions_rejects_dataset_over_limit(tmp_path) -> None:
    oversized = [OBJECTIVE_QUESTION] * (MAX_QUESTIONS + 1)
    dataset_path = tmp_path / "too_many.json"
    dataset_path.write_text(json.dumps(oversized), encoding="utf-8")
    with pytest.raises(ValueError):
        load_questions(dataset_path)


def test_percentile_picks_nearest_rank() -> None:
    values = [10.0, 20.0, 30.0, 40.0, 50.0]
    assert percentile(values, 0.95) == 50.0
    assert percentile([], 0.95) is None


def test_aggregate_by_model_computes_accuracy_and_timing() -> None:
    records = run_evaluation([OBJECTIVE_QUESTION], repeats=2, temperature=0.2, call_fn=fake_correct_call)
    summary = aggregate_by_model(records)
    first_model_id = AVAILABLE_MODELS[0].id
    model_summary = summary[first_model_id]
    assert model_summary["total_calls"] == 2
    assert model_summary["error_count"] == 0
    assert model_summary["accuracy"] == 1.0
    assert model_summary["avg_duration_ms"] == 100.0


def test_save_records_and_summary_round_trip(tmp_path) -> None:
    records = run_evaluation([OBJECTIVE_QUESTION], repeats=1, temperature=0.2, call_fn=fake_correct_call)
    summary = aggregate_by_model(records)

    records_path = tmp_path / "records.csv"
    summary_path = tmp_path / "summary.json"
    save_records_csv(records, records_path)
    save_summary_json(summary, summary_path)

    assert records_path.exists()
    saved_summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert set(saved_summary.keys()) == {model.id for model in AVAILABLE_MODELS}


def test_run_evaluation_respects_models_filter() -> None:
    single_model = [AVAILABLE_MODELS[0]]
    records = run_evaluation(
        [OBJECTIVE_QUESTION], repeats=1, temperature=0.2, call_fn=fake_correct_call, models=single_model
    )
    assert {r.model_id for r in records} == {AVAILABLE_MODELS[0].id}


def test_save_and_load_records_csv_round_trip_preserves_rubric_fields(tmp_path) -> None:
    original = [
        EvalRecord(
            model_id="amazon.nova-lite-v1:0",
            question_id="sub-01",
            category="rubric",
            repeat_index=0,
            temperature=0.2,
            reply="クラウドのメリットは...",
            input_tokens=10,
            output_tokens=50,
            bedrock_duration_ms=321.0,
            estimated_cost_usd=0.00001,
            is_correct=None,
            error=None,
            rubric_accuracy=4,
            rubric_completeness=5,
            rubric_clarity=3,
        )
    ]
    csv_path = tmp_path / "records.csv"
    save_records_csv(original, csv_path)

    loaded = load_records_from_csv(csv_path)
    assert loaded[0].rubric_accuracy == 4
    assert loaded[0].rubric_completeness == 5
    assert loaded[0].rubric_clarity == 3


def test_aggregate_rubric_scores_computes_averages_and_excludes_unscored() -> None:
    scored = EvalRecord(
        model_id="amazon.nova-lite-v1:0",
        question_id="sub-01",
        category="rubric",
        repeat_index=0,
        temperature=0.2,
        reply="...",
        input_tokens=1,
        output_tokens=1,
        bedrock_duration_ms=1.0,
        estimated_cost_usd=0.0,
        is_correct=None,
        error=None,
        rubric_accuracy=4,
        rubric_completeness=4,
        rubric_clarity=2,
    )
    unscored = EvalRecord(
        model_id="amazon.nova-lite-v1:0",
        question_id="sub-02",
        category="rubric",
        repeat_index=0,
        temperature=0.2,
        reply="...",
        input_tokens=1,
        output_tokens=1,
        bedrock_duration_ms=1.0,
        estimated_cost_usd=0.0,
        is_correct=None,
        error=None,
    )

    summary = aggregate_rubric_scores([scored, unscored])

    model_summary = summary["amazon.nova-lite-v1:0"]
    assert model_summary["scored_count"] == 1
    assert model_summary["avg_accuracy"] == 4
    assert model_summary["avg_completeness"] == 4
    assert model_summary["avg_clarity"] == 2


def test_rescore_objective_updates_is_correct_without_calling_bedrock() -> None:
    record = EvalRecord(
        model_id="apac.amazon.nova-micro-v1:0",
        question_id="obj-12",
        category="objective",
        repeat_index=0,
        temperature=0.2,
        reply="1キロバイトは1,000バイトです。",
        input_tokens=1,
        output_tokens=1,
        bedrock_duration_ms=1.0,
        estimated_cost_usd=0.0,
        is_correct=False,
        error=None,
    )
    questions = [{"id": "obj-12", "category": "objective", "question": "...", "expected_keywords": ["1024", "1000"]}]

    rescored = rescore_objective([record], questions)

    assert rescored[0].is_correct is True
