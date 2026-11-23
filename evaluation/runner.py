from __future__ import annotations

import argparse
import csv
import json
import statistics
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable, Optional

from app.bedrock_client import BedrockInvocationError, ChatResult, converse_with_bedrock
from app.models import AVAILABLE_MODELS, ModelInfo, is_model_allowed
from evaluation.scoring import score_objective

# 事故防止のためのハードリミット(ユーザー承認済みの値)
MAX_QUESTIONS = 30
MAX_REPEATS = 3
MAX_OUTPUT_TOKENS = 256
MAX_OUTPUT_TOKENS_CEILING = 1024  # --max-tokensで指定できる上限(コスト事故防止)
DEFAULT_TEMPERATURE = 0.2

DATASET_PATH = Path("datasets/questions.json")
RESULTS_DIR = Path("results")

CallFn = Callable[[str, str, float, int], ChatResult]


@dataclass
class EvalRecord:
    model_id: str
    question_id: str
    category: str
    repeat_index: int
    temperature: float
    reply: str
    input_tokens: int
    output_tokens: int
    bedrock_duration_ms: float
    estimated_cost_usd: Optional[float]
    is_correct: Optional[bool]
    error: Optional[str]
    # ルーブリック問題用。自動採点はせず、datasets/rubric.mdの基準で人間が後から記入する欄
    rubric_accuracy: Optional[int] = None
    rubric_completeness: Optional[int] = None
    rubric_clarity: Optional[int] = None


def load_questions(path: Path) -> list[dict]:
    questions = json.loads(path.read_text(encoding="utf-8"))
    if len(questions) > MAX_QUESTIONS:
        raise ValueError(f"質問数が上限({MAX_QUESTIONS})を超えています: {len(questions)}問")
    return questions


def mock_bedrock_call(message: str, model_id: str, temperature: float, max_tokens: int) -> ChatResult:
    """コストゼロでハーネスの動作確認をするためのダミー応答。"""
    return ChatResult(
        reply=f"[MOCK] {model_id} からのダミー応答です。実際のBedrock呼び出しは行っていません。",
        model_id=model_id,
        input_tokens=len(message),
        output_tokens=20,
        bedrock_duration_ms=100.0,
        estimated_cost_usd=0.0,
    )


def live_bedrock_call(message: str, model_id: str, temperature: float, max_tokens: int) -> ChatResult:
    return converse_with_bedrock(message, model_id=model_id, temperature=temperature, max_tokens=max_tokens)


def run_evaluation(
    questions: list[dict],
    repeats: int,
    temperature: float,
    call_fn: CallFn,
    models: Optional[list[ModelInfo]] = None,
    max_tokens: int = MAX_OUTPUT_TOKENS,
) -> list[EvalRecord]:
    if repeats > MAX_REPEATS:
        raise ValueError(f"繰り返し回数が上限({MAX_REPEATS})を超えています: {repeats}回")
    if len(questions) > MAX_QUESTIONS:
        raise ValueError(f"質問数が上限({MAX_QUESTIONS})を超えています: {len(questions)}問")
    if max_tokens > MAX_OUTPUT_TOKENS_CEILING:
        raise ValueError(f"max_tokensが上限({MAX_OUTPUT_TOKENS_CEILING})を超えています: {max_tokens}")

    models = models if models is not None else AVAILABLE_MODELS
    records: list[EvalRecord] = []

    # 同時実行数は常に1(意図的に並列化しない。コスト・スロットリング事故防止のため)
    for model in models:
        for question in questions:
            for repeat_index in range(repeats):
                try:
                    result = call_fn(question["question"], model.id, temperature, max_tokens)
                except BedrockInvocationError as exc:
                    records.append(
                        EvalRecord(
                            model_id=model.id,
                            question_id=question["id"],
                            category=question["category"],
                            repeat_index=repeat_index,
                            temperature=temperature,
                            reply="",
                            input_tokens=0,
                            output_tokens=0,
                            bedrock_duration_ms=0.0,
                            estimated_cost_usd=None,
                            is_correct=None,
                            error=str(exc),
                        )
                    )
                    continue

                is_correct: Optional[bool] = None
                if question["category"] == "objective":
                    is_correct = score_objective(result.reply, question["expected_keywords"])

                records.append(
                    EvalRecord(
                        model_id=model.id,
                        question_id=question["id"],
                        category=question["category"],
                        repeat_index=repeat_index,
                        temperature=temperature,
                        reply=result.reply,
                        input_tokens=result.input_tokens,
                        output_tokens=result.output_tokens,
                        bedrock_duration_ms=result.bedrock_duration_ms,
                        estimated_cost_usd=result.estimated_cost_usd,
                        is_correct=is_correct,
                        error=None,
                    )
                )

    return records


def percentile(values: list[float], pct: float) -> Optional[float]:
    """pct(0.0〜1.0)に対応する値を最近傍法で求める(例: pct=0.95でP95)。"""
    if not values:
        return None
    sorted_values = sorted(values)
    index = min(int(len(sorted_values) * pct), len(sorted_values) - 1)
    return sorted_values[index]


def aggregate_by_model(records: list[EvalRecord]) -> dict[str, dict]:
    summary: dict[str, dict] = {}
    model_ids = list(dict.fromkeys(r.model_id for r in records))  # 登場順・重複なし
    for model_id in model_ids:
        model_records = [r for r in records if r.model_id == model_id]
        success_records = [r for r in model_records if r.error is None]
        durations = [r.bedrock_duration_ms for r in success_records]
        objective_records = [r for r in success_records if r.category == "objective"]
        correct_count = sum(1 for r in objective_records if r.is_correct)
        costs = [r.estimated_cost_usd for r in success_records if r.estimated_cost_usd is not None]
        error_count = len(model_records) - len(success_records)

        summary[model_id] = {
            "total_calls": len(model_records),
            "error_count": error_count,
            "success_rate": (len(success_records) / len(model_records)) if model_records else None,
            "avg_duration_ms": statistics.mean(durations) if durations else None,
            "p95_duration_ms": percentile(durations, 0.95),
            "objective_question_count": len(objective_records),
            "accuracy": (correct_count / len(objective_records)) if objective_records else None,
            "total_estimated_cost_usd": sum(costs) if costs else None,
        }
    return summary


def save_records_csv(records: list[EvalRecord], path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        if not records:
            return
        writer = csv.DictWriter(f, fieldnames=list(asdict(records[0]).keys()))
        writer.writeheader()
        for record in records:
            writer.writerow(asdict(record))


def save_summary_json(summary: dict[str, dict], path: Path) -> None:
    path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")


def _optional_int(value: str) -> Optional[int]:
    return int(value) if value not in ("", None) else None


def _optional_float(value: str) -> Optional[float]:
    return float(value) if value not in ("", None) else None


def _optional_bool(value: str) -> Optional[bool]:
    if value == "True":
        return True
    if value == "False":
        return False
    return None


def load_records_from_csv(path: Path) -> list[EvalRecord]:
    """datasets/rubric.mdの基準で人手採点を書き込んだCSVを読み込む。"""
    records: list[EvalRecord] = []
    with path.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            records.append(
                EvalRecord(
                    model_id=row["model_id"],
                    question_id=row["question_id"],
                    category=row["category"],
                    repeat_index=int(row["repeat_index"]),
                    temperature=float(row["temperature"]),
                    reply=row["reply"],
                    input_tokens=int(row["input_tokens"]),
                    output_tokens=int(row["output_tokens"]),
                    bedrock_duration_ms=float(row["bedrock_duration_ms"]),
                    estimated_cost_usd=_optional_float(row["estimated_cost_usd"]),
                    is_correct=_optional_bool(row["is_correct"]),
                    error=row["error"] or None,
                    rubric_accuracy=_optional_int(row.get("rubric_accuracy", "")),
                    rubric_completeness=_optional_int(row.get("rubric_completeness", "")),
                    rubric_clarity=_optional_int(row.get("rubric_clarity", "")),
                )
            )
    return records


def rescore_objective(records: list[EvalRecord], questions: list[dict]) -> list[EvalRecord]:
    """保存済みの回答を、現在の採点ロジックで採点し直す(Bedrockは呼ばない)。"""
    expected = {q["id"]: q["expected_keywords"] for q in questions if q["category"] == "objective"}
    for record in records:
        if record.error is None and record.question_id in expected:
            record.is_correct = score_objective(record.reply, expected[record.question_id])
    return records


def aggregate_rubric_scores(records: list[EvalRecord]) -> dict[str, dict]:
    """人手で記入したルーブリックスコアをモデルごとに集計する。

    3軸すべてが未記入(None)の行は集計対象から除外する。
    """
    summary: dict[str, dict] = {}
    model_ids = list(dict.fromkeys(r.model_id for r in records if r.category == "rubric"))
    for model_id in model_ids:
        scored = [
            r
            for r in records
            if r.model_id == model_id
            and r.category == "rubric"
            and r.rubric_accuracy is not None
            and r.rubric_completeness is not None
            and r.rubric_clarity is not None
        ]
        summary[model_id] = {
            "scored_count": len(scored),
            "avg_accuracy": statistics.mean(r.rubric_accuracy for r in scored) if scored else None,
            "avg_completeness": statistics.mean(r.rubric_completeness for r in scored) if scored else None,
            "avg_clarity": statistics.mean(r.rubric_clarity for r in scored) if scored else None,
        }
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="複数Bedrockモデルの性能・品質比較評価ハーネス")
    parser.add_argument("--repeats", type=int, default=3, help=f"同一質問の繰り返し回数(最大{MAX_REPEATS})")
    parser.add_argument("--temperature", type=float, default=DEFAULT_TEMPERATURE)
    parser.add_argument("--dataset", type=Path, default=DATASET_PATH)
    parser.add_argument(
        "--model-id",
        type=str,
        default=None,
        help="このモデルIDのみ実行する(省略時は許可された全モデル)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="対象質問の先頭からこの件数のみ使う(小規模トライアル用。省略時は全件)",
    )
    parser.add_argument(
        "--category",
        type=str,
        choices=["objective", "rubric"],
        default=None,
        help="このカテゴリの質問のみ実行する(省略時は全カテゴリ)",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=MAX_OUTPUT_TOKENS,
        help=f"1回の応答で生成する最大トークン数(上限{MAX_OUTPUT_TOKENS_CEILING}。省略時は{MAX_OUTPUT_TOKENS})",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="実際にBedrockへ課金リクエストを送る(指定しない場合はモックで無料実行)",
    )
    parser.add_argument(
        "--aggregate-rubric",
        type=Path,
        default=None,
        help="評価は実行せず、datasets/rubric.mdの基準で人手採点済みのCSVを集計して表示する",
    )
    parser.add_argument(
        "--rescore",
        type=Path,
        default=None,
        help="評価は実行せず、保存済みrecords CSVの客観問題を現在の採点ロジックで再採点する(課金なし)",
    )
    args = parser.parse_args()

    if args.rescore is not None:
        records = rescore_objective(load_records_from_csv(args.rescore), load_questions(args.dataset))
        stem = args.rescore.stem.removesuffix("_records")
        records_path = args.rescore.with_name(f"{stem}_rescored_records.csv")
        summary_path = args.rescore.with_name(f"{stem}_rescored_summary.json")
        save_records_csv(records, records_path)
        save_summary_json(aggregate_by_model(records), summary_path)
        print(f"再採点しました: {records_path} / {summary_path}")
        return

    if args.aggregate_rubric is not None:
        records = load_records_from_csv(args.aggregate_rubric)
        rubric_summary = aggregate_rubric_scores(records)
        print(json.dumps(rubric_summary, ensure_ascii=False, indent=2))
        return

    questions = load_questions(args.dataset)
    if args.category is not None:
        questions = [q for q in questions if q["category"] == args.category]
    if args.limit is not None:
        questions = questions[: args.limit]

    models = AVAILABLE_MODELS
    if args.model_id is not None:
        if not is_model_allowed(args.model_id):
            print(f"エラー: model_id '{args.model_id}' は許可されたモデル一覧にありません。")
            return
        models = [m for m in AVAILABLE_MODELS if m.id == args.model_id]

    if args.live:
        estimated_calls = len(models) * len(questions) * args.repeats
        print(
            f"[警告] --live が指定されました。Bedrockへ最大 {estimated_calls} 回の"
            "実際のAPI呼び出しを行い、課金が発生します。"
        )
        confirmation = input("本当に実行しますか？ 'yes' と入力してください: ")
        if confirmation.strip().lower() != "yes":
            print("中止しました。")
            return

    call_fn: CallFn = live_bedrock_call if args.live else mock_bedrock_call
    records = run_evaluation(
        questions, args.repeats, args.temperature, call_fn, models=models, max_tokens=args.max_tokens
    )
    summary = aggregate_by_model(records)

    RESULTS_DIR.mkdir(exist_ok=True)
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    records_path = RESULTS_DIR / f"eval_{timestamp}_records.csv"
    summary_path = RESULTS_DIR / f"eval_{timestamp}_summary.json"
    save_records_csv(records, records_path)
    save_summary_json(summary, summary_path)

    print(f"完了: {records_path} / {summary_path} に保存しました。")


if __name__ == "__main__":
    main()
