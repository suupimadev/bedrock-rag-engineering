import json
from pathlib import Path

from evaluation.scoring_worksheet import generate_worksheet

CSV_HEADER = "model_id,question_id,category,repeat_index,temperature,reply,input_tokens,output_tokens,bedrock_duration_ms,estimated_cost_usd,is_correct,error,rubric_accuracy,rubric_completeness,rubric_clarity"


def test_generate_worksheet_groups_by_question_and_includes_score_blanks(tmp_path: Path) -> None:
    dataset_path = tmp_path / "questions.json"
    dataset_path.write_text(
        json.dumps([{"id": "sub-01", "category": "rubric", "question": "クラウドの利点は？"}]),
        encoding="utf-8",
    )

    records_csv = tmp_path / "records.csv"
    records_csv.write_text(
        CSV_HEADER
        + "\n"
        + 'amazon.nova-lite-v1:0,sub-01,rubric,0,0.2,"これが回答です",10,20,100.0,0.00001,,,,,'
        + "\n",
        encoding="utf-8",
    )

    output_path = tmp_path / "worksheet.md"
    generate_worksheet(records_csv, dataset_path, output_path)

    content = output_path.read_text(encoding="utf-8")
    assert "sub-01: クラウドの利点は？" in content
    assert "Nova Lite(amazon.nova-lite-v1:0)" in content
    assert "これが回答です" in content
    assert "正確性: ___ / 5" in content
