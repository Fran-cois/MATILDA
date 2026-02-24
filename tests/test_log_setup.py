"""
Tests for utils/log_setup.py — setup_loggers.
"""

import logging

from utils.log_setup import setup_loggers


class TestSetupLoggers:
    def test_creates_logs_directory(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        setup_loggers()
        assert (tmp_path / "logs").is_dir()

    def test_idempotent_when_logs_dir_exists(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "logs").mkdir()
        setup_loggers()  # Must not raise even though logs/ already exists
        assert (tmp_path / "logs").is_dir()

    def test_query_time_logger_configured(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        setup_loggers()
        logger = logging.getLogger("query_time")
        assert logger.level == logging.ERROR
        handler_types = [type(h).__name__ for h in logger.handlers]
        assert "RotatingFileHandler" in handler_types

    def test_query_results_logger_configured(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        setup_loggers()
        logger = logging.getLogger("query_results")
        assert logger.level == logging.ERROR
        handler_types = [type(h).__name__ for h in logger.handlers]
        assert "RotatingFileHandler" in handler_types

    def test_log_files_created(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        setup_loggers()
        # RotatingFileHandler creates the file on first use; existence is not
        # guaranteed until a record is emitted, but the handler is attached.
        logger = logging.getLogger("query_time")
        logger.error("test entry")
        assert (tmp_path / "logs" / "query_time.log").exists()
