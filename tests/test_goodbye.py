"""Tests for GoodbyePlaybackMixin."""

import os
import sys
import tempfile
import time
import wave
from unittest.mock import Mock, patch

import pytest

from pjsua_bot.calls.goodbye import GoodbyePlaybackMixin


class MockCall(GoodbyePlaybackMixin):
    """Mock call class that uses GoodbyePlaybackMixin."""

    def __init__(self) -> None:
        self._acc_ref = Mock()
        self._acc_ref.goodbye_file = None
        self._acc_ref.waiting_file = None
        self._call_media = None
        self._vad = None
        self._mixed_recorder = None
        self._collected_events = []
        self.init_goodbye_state()


class TestGoodbyePlaybackMixin:
    """Test cases for GoodbyePlaybackMixin."""

    def test_init_goodbye_state(self) -> None:
        """Test initialization of goodbye state."""
        call = MockCall()
        assert call._goodbye_player is None
        assert call._goodbye_playback_started is False
        assert call._goodbye_playback_finished is False
        assert call._goodbye_stop_time is None
        assert call._goodbye_requested is False
        assert call._waiting_player is None
        assert call._waiting_playback_started is False
        assert call._waiting_playback_finished is False
        assert call._waiting_stop_time is None
        assert call._waiting_requested is False
        assert call._asr_complete is False
        assert call._hangup_time is None

    def test_play_goodbye_message_no_file(self) -> None:
        """Test playing goodbye message when no file is configured."""
        call = MockCall()
        call._play_goodbye_message()
        # Should return early without doing anything
        assert call._goodbye_playback_started is False

    def test_play_goodbye_message_file_not_found(self) -> None:
        """Test playing goodbye message when file doesn't exist."""
        call = MockCall()
        call._acc_ref.goodbye_file = "/nonexistent/file.wav"
        with patch("builtins.print"):  # Suppress print output
            call._play_goodbye_message()
            assert call._goodbye_playback_finished is True

    def test_play_goodbye_message_no_call_media(self) -> None:
        """Test playing goodbye message when call media is not available."""
        call = MockCall()
        call._acc_ref.goodbye_file = "/path/to/file.wav"
        call._call_media = None
        with patch("os.path.exists", return_value=True):
            with patch("builtins.print"):  # Suppress print output
                call._play_goodbye_message()
                assert call._goodbye_playback_finished is True

    def test_play_goodbye_message_success(self) -> None:
        """Test successful goodbye message playback."""
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            with wave.open(tmp.name, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(16000)
                wf.writeframes(b"\x00" * 16000)  # 1 second

            try:
                call = MockCall()
                call._acc_ref.goodbye_file = tmp.name
                call._call_media = Mock()

                mock_player = Mock()
                mock_pj_module = Mock()
                mock_pj_module.AudioMediaPlayer.return_value = mock_player
                mock_endpoint = Mock()
                mock_adm = Mock()
                mock_playback = Mock()
                mock_pj_module.Endpoint.instance.return_value = mock_endpoint
                mock_endpoint.audDevManager.return_value = mock_adm
                mock_adm.getPlaybackDevMedia.return_value = mock_playback

                # Patch pjsua2 in sys.modules before the import happens
                sys.modules["pjsua2"] = mock_pj_module
                try:
                    # Patch get_wav_duration at the utils module level (where it's imported from)
                    with patch("pjsua_bot.utils.get_wav_duration", return_value=1.0):
                        with patch("builtins.print"):  # Suppress print output
                            call._play_goodbye_message()

                            assert call._goodbye_playback_started is True
                            assert call._goodbye_requested is True
                            assert call._goodbye_stop_time is not None
                            mock_player.createPlayer.assert_called_once()
                            mock_player.startTransmit.assert_called()
                finally:
                    # Clean up
                    if "pjsua2" in sys.modules and isinstance(sys.modules["pjsua2"], Mock):
                        del sys.modules["pjsua2"]
            finally:
                if os.path.exists(tmp.name):
                    os.unlink(tmp.name)

    def test_check_goodbye_status_not_started(self) -> None:
        """Test checking goodbye status when playback hasn't started."""
        call = MockCall()
        call.check_goodbye_status()
        # Should return early without doing anything
        assert call._goodbye_playback_finished is False

    def test_check_goodbye_status_time_not_reached(self) -> None:
        """Test checking goodbye status before stop time."""
        call = MockCall()
        call._goodbye_playback_started = True
        call._goodbye_stop_time = time.time() + 10.0  # 10 seconds in future
        call._goodbye_player = Mock()
        call._call_media = Mock()

        call.check_goodbye_status()
        # Should not finish yet
        assert call._goodbye_playback_finished is False

    def test_check_goodbye_status_time_reached(self) -> None:
        """Test checking goodbye status when stop time is reached."""
        call = MockCall()
        call._goodbye_playback_started = True
        call._goodbye_stop_time = time.time() - 1.0  # 1 second in past
        call._goodbye_player = Mock()
        call._call_media = Mock()

        with patch("builtins.print"):  # Suppress print output
            call.check_goodbye_status()

            assert call._goodbye_playback_finished is True

    def test_check_goodbye_status_already_finished(self) -> None:
        """Test checking goodbye status when already finished."""
        call = MockCall()
        call._goodbye_playback_started = True
        call._goodbye_playback_finished = True
        call._goodbye_stop_time = time.time() - 1.0

        call.check_goodbye_status()
        # Should remain finished
        assert call._goodbye_playback_finished is True

    def test_play_waiting_message_no_file(self) -> None:
        """Test playing waiting message when no file is configured."""
        call = MockCall()
        call._play_waiting_message()
        # Should return early without doing anything
        assert call._waiting_playback_started is False

    def test_play_waiting_message_already_playing(self) -> None:
        """Test playing waiting message when already playing."""
        call = MockCall()
        call._acc_ref.waiting_file = "/path/to/file.wav"
        call._waiting_playback_started = True
        call._waiting_requested = True  # Already requested
        # Should return early without doing anything
        call._play_waiting_message()
        # Should remain True (already was)
        assert call._waiting_requested is True

    def test_play_waiting_message_success(self) -> None:
        """Test successful waiting message playback."""
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            with wave.open(tmp.name, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(16000)
                wf.writeframes(b"\x00" * 16000)

            try:
                call = MockCall()
                call._acc_ref.waiting_file = tmp.name
                call._call_media = Mock()

                mock_player = Mock()
                mock_pj_module = Mock()
                mock_pj_module.AudioMediaPlayer.return_value = mock_player
                mock_endpoint = Mock()
                mock_adm = Mock()
                mock_playback = Mock()
                mock_pj_module.Endpoint.instance.return_value = mock_endpoint
                mock_endpoint.audDevManager.return_value = mock_adm
                mock_adm.getPlaybackDevMedia.return_value = mock_playback

                # Patch pjsua2 in sys.modules before the import happens
                sys.modules["pjsua2"] = mock_pj_module
                try:
                    # Patch get_wav_duration at the utils module level (where it's imported from)
                    with patch("pjsua_bot.utils.get_wav_duration", return_value=1.0):
                        with patch("builtins.print"):  # Suppress print output
                            call._play_waiting_message()

                            assert call._waiting_playback_started is True
                            assert call._waiting_requested is True
                            mock_player.createPlayer.assert_called_once()
                finally:
                    # Clean up
                    if "pjsua2" in sys.modules and isinstance(sys.modules["pjsua2"], Mock):
                        del sys.modules["pjsua2"]
            finally:
                if os.path.exists(tmp.name):
                    os.unlink(tmp.name)

    def test_check_waiting_status_not_started(self) -> None:
        """Test checking waiting status when playback hasn't started."""
        call = MockCall()
        call.check_waiting_status()
        # Should return early
        assert call._waiting_playback_finished is False

    def test_check_waiting_status_time_reached(self) -> None:
        """Test checking waiting status when stop time is reached."""
        call = MockCall()
        call._waiting_playback_started = True
        call._waiting_stop_time = time.time() - 1.0
        call._waiting_player = Mock()
        call._call_media = Mock()

        with patch("builtins.print"):  # Suppress print output
            call.check_waiting_status()

            assert call._waiting_playback_finished is True

    def test_check_waiting_status_already_finished(self) -> None:
        """Test checking waiting status when already finished."""
        call = MockCall()
        call._waiting_playback_started = True
        call._waiting_playback_finished = True
        call._waiting_stop_time = time.time() - 1.0

        call.check_waiting_status()
        # Should remain finished
        assert call._waiting_playback_finished is True

    def test_check_waiting_status_time_not_reached(self) -> None:
        """Test checking waiting status before stop time."""
        call = MockCall()
        call._waiting_playback_started = True
        call._waiting_stop_time = time.time() + 10.0  # 10 seconds in future
        call._waiting_player = Mock()
        call._call_media = Mock()

        call.check_waiting_status()
        # Should not finish yet
        assert call._waiting_playback_finished is False

