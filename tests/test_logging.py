import logging
from src.logging_config import setup_logging


def test_setup_logging():
    setup_logging(level="DEBUG")
    root = logging.getLogger()
    assert root.level == logging.DEBUG
    assert len(root.handlers) == 1

    setup_logging(level="INFO")
    assert root.level == logging.INFO
