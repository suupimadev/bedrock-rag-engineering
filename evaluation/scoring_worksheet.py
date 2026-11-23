from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from app.models import AVAILABLE_MODELS

MODEL_DISPLAY_NAMES = {model.id: model.display_name for model in AVAILABLE_MODELS}


def generate_worksheet(records_csv: Path, dataset_path: Path, output_path: Path) -> None:
    """評価結果CSVから、ルーブリック問題だけを質問ごとにまとめた採点シート(Markdown)を作る。"""
    questions = {q["id"]: q["question"] for q in json.loads(dataset_path.read_text(encoding="utf-8"))}

    with records_csv.open(encoding="utf-8") as f:
        rubric_rows = [row for row in csv.DictReader(f) if row["category"] == "rubric"]

    by_question: dict[str, list[dict]] = {}
    for row in rubric_rows:
        by_question.setdefault(row["question_id"], []).append(row)

    lines = [
        "# ルーブリック採点シート",
        "",
        "採点基準は `datasets/rubric.md` を参照(正確性・網羅性・わかりやすさ、各1〜5点)。",
        f"元データ: `{records_csv}`",
        "",
    ]
    for question_id in sorted(by_question):
        question_text = questions.get(question_id, "(質問文が見つかりません)")
        lines.append(f"## {question_id}: {question_text}")
        lines.append("")
        for row in by_question[question_id]:
            display_name = MODEL_DISPLAY_NAMES.get(row["model_id"], row["model_id"])
            lines.append(f"### {display_name}({row['model_id']})")
            lines.append("")
            lines.append(row["reply"])
            lines.append("")
            lines.append("- 正確性: ___ / 5")
            lines.append("- 網羅性: ___ / 5")
            lines.append("- わかりやすさ: ___ / 5")
            lines.append("")
        lines.append("---")
        lines.append("")

    output_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="ルーブリック採点用のワークシート(Markdown)を生成する")
    parser.add_argument("records_csv", type=Path, help="evaluation.runnerが出力したrecords CSVのパス")
    parser.add_argument("--dataset", type=Path, default=Path("datasets/questions.json"))
    parser.add_argument("--output", type=Path, default=None, help="省略時は<records_csv>_scoring_worksheet.md")
    args = parser.parse_args()

    output_path = args.output or args.records_csv.with_name(args.records_csv.stem + "_scoring_worksheet.md")
    generate_worksheet(args.records_csv, args.dataset, output_path)
    print(f"採点シートを作成しました: {output_path}")


if __name__ == "__main__":
    main()
