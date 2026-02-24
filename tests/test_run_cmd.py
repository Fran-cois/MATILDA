"""
Tests for utils/run_cmd.py — run_cmd and start_memory_monitor.
Uses unittest.mock to avoid launching real subprocesses.
"""

import subprocess
import threading
from unittest.mock import MagicMock, patch

from utils.run_cmd import run_cmd, start_memory_monitor

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_process(returncode=0, output=b"", errors=b""):
    """Return a mock Popen-compatible object."""
    proc = MagicMock()
    proc.returncode = returncode
    proc.communicate.return_value = (output, errors)
    proc.pid = 12345
    # Support context-manager protocol used by `with Popen(...) as p`
    proc.__enter__ = lambda s: s
    proc.__exit__ = MagicMock(return_value=False)
    return proc


# ---------------------------------------------------------------------------
# run_cmd — standard (no pipe, no redirect)
# ---------------------------------------------------------------------------


class TestRunCmdStandard:
    def test_success_returns_true(self):
        proc = _make_process(returncode=0)
        with patch("utils.run_cmd.subprocess.Popen", return_value=proc):
            assert run_cmd("echo hello", memory_limit_gb=0) is True

    def test_failure_returns_false(self):
        proc = _make_process(returncode=1, errors=b"oops")
        with patch("utils.run_cmd.subprocess.Popen", return_value=proc):
            assert run_cmd("false", memory_limit_gb=0) is False

    def test_timeout_returns_false(self):
        proc = _make_process()
        proc.communicate.side_effect = subprocess.TimeoutExpired("cmd", 1)
        with patch("utils.run_cmd.subprocess.Popen", return_value=proc):
            assert run_cmd("sleep 100", timeout=1, memory_limit_gb=0) is False
        proc.terminate.assert_called_once()

    def test_exception_returns_false(self):
        with patch("utils.run_cmd.subprocess.Popen", side_effect=OSError("not found")):
            assert run_cmd("nonexistent_command_xyz") is False

    def test_no_memory_limit_skips_monitor(self):
        proc = _make_process(returncode=0)
        with patch("utils.run_cmd.subprocess.Popen", return_value=proc):
            with patch("utils.run_cmd.start_memory_monitor") as mock_mon:
                run_cmd("echo hi", memory_limit_gb=0)
                mock_mon.assert_not_called()

    def test_with_memory_limit_starts_monitor(self):
        proc = _make_process(returncode=0)
        with patch("utils.run_cmd.subprocess.Popen", return_value=proc):
            with patch("utils.run_cmd.start_memory_monitor") as mock_mon:
                run_cmd("echo hi", memory_limit_gb=1.0)
                mock_mon.assert_called_once_with(proc.pid, 1.0)


# ---------------------------------------------------------------------------
# run_cmd — pipe path
# ---------------------------------------------------------------------------


class TestRunCmdPipe:
    def _patch_popen_pipe(self, proc1, proc2):
        """Context manager that returns proc1 for the first Popen call and proc2 for the second."""
        side_effects = [proc1, proc2]
        return patch("utils.run_cmd.subprocess.Popen", side_effect=side_effects)

    def test_pipe_success(self):
        proc1 = _make_process(returncode=0)
        proc1.stdout = MagicMock()
        proc2 = _make_process(returncode=0)
        with self._patch_popen_pipe(proc1, proc2):
            assert run_cmd("echo hello | cat") is True

    def test_pipe_failure(self):
        proc1 = _make_process(returncode=0)
        proc1.stdout = MagicMock()
        proc2 = _make_process(returncode=1, errors=b"fail")
        with self._patch_popen_pipe(proc1, proc2):
            assert run_cmd("echo hello | cat") is False

    def test_pipe_timeout(self):
        proc1 = _make_process(returncode=0)
        proc1.stdout = MagicMock()
        proc2 = _make_process()
        proc2.communicate.side_effect = subprocess.TimeoutExpired("cmd", 1)
        with self._patch_popen_pipe(proc1, proc2):
            assert run_cmd("echo hello | cat", timeout=1) is False
        proc2.terminate.assert_called_once()


# ---------------------------------------------------------------------------
# run_cmd — output redirection path
# ---------------------------------------------------------------------------


class TestRunCmdRedirect:
    def test_redirect_success(self, tmp_path):
        out_file = tmp_path / "out.txt"
        proc = _make_process(returncode=0)
        with patch("utils.run_cmd.subprocess.Popen", return_value=proc):
            assert run_cmd(f"echo hello > {out_file}") is True

    def test_redirect_failure(self, tmp_path):
        out_file = tmp_path / "out.txt"
        proc = _make_process(returncode=1, errors=b"err")
        with patch("utils.run_cmd.subprocess.Popen", return_value=proc):
            assert run_cmd(f"false > {out_file}") is False

    def test_redirect_timeout(self, tmp_path):
        out_file = tmp_path / "out.txt"
        proc = _make_process()
        proc.communicate.side_effect = subprocess.TimeoutExpired("cmd", 1)
        with patch("utils.run_cmd.subprocess.Popen", return_value=proc):
            assert run_cmd(f"sleep 100 > {out_file}", timeout=1) is False
        proc.terminate.assert_called_once()


# ---------------------------------------------------------------------------
# start_memory_monitor
# ---------------------------------------------------------------------------


class TestStartMemoryMonitor:
    def test_returns_daemon_thread(self):
        mock_process = MagicMock()
        mock_process.is_running.return_value = False  # loop exits immediately
        with patch("utils.run_cmd.psutil.Process", return_value=mock_process):
            thread = start_memory_monitor(pid=999, memory_limit_gb=1.0)
        assert isinstance(thread, threading.Thread)
        assert thread.daemon is True

    def test_terminates_on_memory_exceeded(self):
        mock_process = MagicMock()
        # First call: over limit; second: process no longer running
        mock_process.is_running.side_effect = [True, False]
        mock_process.memory_info.return_value.rss = int(2 * 1024**3)  # 2 GB

        with patch("utils.run_cmd.psutil.Process", return_value=mock_process):
            thread = start_memory_monitor(pid=999, memory_limit_gb=1.0)
            thread.join(timeout=2)

        mock_process.terminate.assert_called_once()

    def test_no_terminate_when_under_limit(self):
        mock_process = MagicMock()
        mock_process.is_running.side_effect = [True, False]
        mock_process.memory_info.return_value.rss = int(0.5 * 1024**3)  # 0.5 GB

        with patch("utils.run_cmd.psutil.Process", return_value=mock_process):
            with patch("utils.run_cmd.time.sleep"):  # skip the sleep
                thread = start_memory_monitor(pid=999, memory_limit_gb=1.0)
                thread.join(timeout=2)

        mock_process.terminate.assert_not_called()
