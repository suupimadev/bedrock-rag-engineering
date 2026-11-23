from evaluation.scoring import normalize_text, score_objective


def test_normalize_text_strips_whitespace_and_lowercases() -> None:
    assert normalize_text("  Tokyo  ") == "tokyo"
    assert normalize_text("東京 です") == "東京です"


def test_score_objective_matches_exact_keyword() -> None:
    assert score_objective("東京です", ["東京"]) is True


def test_score_objective_matches_case_insensitively() -> None:
    assert score_objective("The answer is Thank You!", ["thank you"]) is True


def test_score_objective_no_match_returns_false() -> None:
    assert score_objective("大阪です", ["東京"]) is False


def test_score_objective_matches_any_of_multiple_keywords() -> None:
    assert score_objective("It's 100 cents.", ["100", "一万"]) is True


# 以下2件は実際にNova Microが返した回答。正規化前は不正解と誤判定されていた
def test_score_objective_ignores_latex_markup() -> None:
    assert score_objective("水の化学式は \\( \\text{H}_2\\text{O} \\) です。", ["H2O", "H₂O"]) is True


def test_score_objective_ignores_thousands_separator() -> None:
    assert score_objective("1キロバイトは1,000バイトです。", ["1024", "1000"]) is True


def test_score_objective_ignores_markdown_bold() -> None:
    assert score_objective("数字のみで答えると、**100**です。", ["100"]) is True


def test_score_objective_still_rejects_wrong_number_after_normalization() -> None:
    assert score_objective("1キロバイトは1,200バイトです。", ["1024", "1000"]) is False
