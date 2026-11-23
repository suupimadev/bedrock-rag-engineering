"""記事(docs/articles/article-02.md)用のグラフ画像を、実測結果のCSV/JSONから生成するスクリプト。

アプリ本体の実行には使わない、記事執筆用の一回限りのツール。
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt

from evaluation.runner import aggregate_rubric_scores, load_records_from_csv

# 日本語ラベルが文字化けしないよう、macOS標準の日本語対応フォントを指定する
plt.rcParams["font.family"] = ["Hiragino Sans", "sans-serif"]

OBJECTIVE_SUMMARY_PATH = Path("results/eval_20261103-101202_rescored_summary.json")
RUBRIC_SUMMARY_PATH = Path("results/eval_20261114-143554_summary.json")
RUBRIC_RECORDS_PATH = Path("results/eval_20261114-143554_records.csv")
OUTPUT_DIR = Path("docs/articles/images")

DISPLAY_NAMES = {
    "amazon.nova-lite-v1:0": "Nova Lite",
    "apac.amazon.nova-micro-v1:0": "Nova Micro",
    "apac.amazon.nova-pro-v1:0": "Nova Pro",
}
COLORS = ["#4C72B0", "#DD8452", "#55A868"]


def _ordered_models(summary: dict) -> list[str]:
    preferred = list(DISPLAY_NAMES.keys())
    return [m for m in preferred if m in summary]


def make_objective_chart(summary: dict, output_path: Path) -> None:
    models = _ordered_models(summary)
    labels = [DISPLAY_NAMES[m] for m in models]

    fig, axes = plt.subplots(1, 3, figsize=(12, 4))

    avg_ms = [summary[m]["avg_duration_ms"] for m in models]
    axes[0].bar(labels, avg_ms, color=COLORS)
    axes[0].set_title("平均応答時間(ms)")
    axes[0].set_ylabel("ms")

    accuracy = [summary[m]["accuracy"] * 100 for m in models]
    axes[1].bar(labels, accuracy, color=COLORS)
    axes[1].set_title("正答率(%)")
    axes[1].set_ylim(0, 100)

    cost = [summary[m]["total_estimated_cost_usd"] for m in models]
    axes[2].bar(labels, cost, color=COLORS)
    axes[2].set_title("合計推定コスト(USD)")

    fig.suptitle("客観問題12問の比較")
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def make_rubric_speed_cost_chart(summary: dict, output_path: Path) -> None:
    models = _ordered_models(summary)
    labels = [DISPLAY_NAMES[m] for m in models]

    fig, axes = plt.subplots(1, 2, figsize=(9, 4))

    avg_ms = [summary[m]["avg_duration_ms"] for m in models]
    axes[0].bar(labels, avg_ms, color=COLORS)
    axes[0].set_title("平均応答時間(ms)")
    axes[0].set_ylabel("ms")

    cost = [summary[m]["total_estimated_cost_usd"] for m in models]
    axes[1].bar(labels, cost, color=COLORS)
    axes[1].set_title("合計推定コスト(USD)")

    fig.suptitle("ルーブリック問題8問の速度・コスト比較")
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def make_rubric_quality_chart(rubric_summary: dict, output_path: Path) -> None:
    models = [m for m in DISPLAY_NAMES if m in rubric_summary]
    labels = [DISPLAY_NAMES[m] for m in models]
    axes_keys = [("avg_accuracy", "正確性"), ("avg_completeness", "網羅性"), ("avg_clarity", "わかりやすさ")]

    x = range(len(models))
    width = 0.25
    fig, ax = plt.subplots(figsize=(7, 4.5))
    for i, (key, label) in enumerate(axes_keys):
        values = [rubric_summary[m][key] for m in models]
        offsets = [xi + (i - 1) * width for xi in x]
        ax.bar(offsets, values, width=width, label=label)

    ax.set_xticks(list(x))
    ax.set_xticklabels(labels)
    ax.set_ylim(0, 5)
    ax.set_ylabel("点(5点満点)")
    ax.set_title("ルーブリック問題8問の品質スコア(AI下書き+人間レビュー採点)")
    legend = ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.08), ncol=3, frameon=False)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_extra_artists=(legend,), bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    objective_summary = json.loads(OBJECTIVE_SUMMARY_PATH.read_text(encoding="utf-8"))
    make_objective_chart(objective_summary, OUTPUT_DIR / "objective_comparison.png")

    rubric_summary = json.loads(RUBRIC_SUMMARY_PATH.read_text(encoding="utf-8"))
    make_rubric_speed_cost_chart(rubric_summary, OUTPUT_DIR / "rubric_speed_cost.png")

    rubric_records = load_records_from_csv(RUBRIC_RECORDS_PATH)
    rubric_quality = aggregate_rubric_scores(rubric_records)
    make_rubric_quality_chart(rubric_quality, OUTPUT_DIR / "rubric_quality.png")

    print(f"生成しました: {OUTPUT_DIR}/objective_comparison.png")
    print(f"生成しました: {OUTPUT_DIR}/rubric_speed_cost.png")
    print(f"生成しました: {OUTPUT_DIR}/rubric_quality.png")


if __name__ == "__main__":
    main()
