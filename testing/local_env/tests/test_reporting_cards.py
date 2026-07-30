import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))  # testing/local_env
from reporting import cards  # noqa: E402  (import-only smoke check; real tests in Task 2)


def test_cards_module_imports():
    assert hasattr(cards, "__name__")
