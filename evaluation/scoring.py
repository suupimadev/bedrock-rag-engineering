from __future__ import annotations

import re

# LaTeXの \text{H} のような装飾を中身だけに戻す
_LATEX_TEXT_PATTERN = re.compile(r"\\text\{([^}]*)\}")
# 数式の囲み記号・添字記号・桁区切りなど、意味を変えずに表記だけ揺れる文字
_NOISE_CHARS = ("\\(", "\\)", "$", "_", "{", "}", ",", "，", "*", "`")


def normalize_text(text: str) -> str:
    """比較用にテキストを正規化する。

    空白・大文字小文字に加えて、LLMが付けがちなLaTeX記法(\\( \\text{H}_2\\text{O} \\))、
    Markdownの強調(**100**)、桁区切りのカンマ(1,000)の表記ゆれを取り除く。
    """
    text = _LATEX_TEXT_PATTERN.sub(r"\1", text)
    for noise in _NOISE_CHARS:
        text = text.replace(noise, "")
    return text.strip().lower().replace(" ", "").replace("　", "")


def score_objective(reply: str, expected_keywords: list[str]) -> bool:
    """客観問題を自動採点する。

    expected_keywordsのいずれか1つでもreplyに含まれていれば正解とみなす
    (完全一致ではなく部分一致。LLMは前後に説明文を付け足すことが多いため)。
    """
    normalized_reply = normalize_text(reply)
    return any(normalize_text(keyword) in normalized_reply for keyword in expected_keywords)
