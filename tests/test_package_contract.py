from digit_probe import AnalysisResult, analyze_integer_symbols

import system_log_dynamics


def test_package_has_initial_version() -> None:
    assert system_log_dynamics.__version__ == "0.1.0"


def test_digit_probe_public_api_is_consumable() -> None:
    symbols = [0, 1, 2, 3] * 25

    result = analyze_integer_symbols(symbols, alphabet=4)

    assert isinstance(result, AnalysisResult)
    assert result.mode == "integers"
    assert result.sample_size == 100
    assert result.alphabet == 4
    assert result.counts == {0: 25, 1: 25, 2: 25, 3: 25}
