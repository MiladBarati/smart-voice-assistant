"""Tests for OutCall class."""

from unittest.mock import Mock, patch

import pytest

from pjsua_bot.calls.out_call import OutCall


class TestOutCall:
    """Test cases for OutCall class."""

    def test_init(self) -> None:
        """Test OutCall initialization."""
        mock_account = Mock()
        with patch("pjsua_bot.calls.out_call.pj.Call.__init__"):
            call = OutCall(mock_account)
            assert call.connected is False
            assert call._acc_ref == mock_account
            assert call._player is None
            assert call._collected_events == []

    def test_collect_event(self) -> None:
        """Test event collection."""
        mock_account = Mock()
        with patch("pjsua_bot.calls.out_call.pj.Call.__init__"):
            call = OutCall(mock_account)
            # Mock getId to avoid C++ call
            call.getId = Mock(return_value=123)
            call._collect_event("test_event", key1="value1")

            assert len(call._collected_events) == 1
            event = call._collected_events[0]
            assert event["event_type"] == "test_event"
            assert event["key1"] == "value1"
            assert "@timestamp" in event

    def test_on_call_state_confirmed(self) -> None:
        """Test call state change to confirmed."""
        mock_account = Mock()
        with patch("pjsua_bot.calls.out_call.pj.Call.__init__"):
            call = OutCall(mock_account)
            call.getId = Mock(return_value=123)  # Mock getId

            mock_info = Mock()
            mock_info.state = 4  # PJSIP_INV_STATE_CONFIRMED
            mock_info.stateText = "CONFIRMED"
            mock_info.lastStatusCode = 200

            with patch.object(call, "getInfo", return_value=mock_info):
                with patch("pjsua_bot.calls.out_call.pj") as mock_pj:
                    mock_pj.PJSIP_INV_STATE_CONFIRMED = 4
                    mock_pj.PJSIP_INV_STATE_DISCONNECTED = 5

                    with patch("builtins.print"):  # Suppress print output
                        call.onCallState(Mock())

                        assert call.connected is True
                        assert len(call._collected_events) == 1
                        event = call._collected_events[0]
                        assert event["event_type"] == "call_state_change"

    def test_on_call_state_disconnected(self) -> None:
        """Test call state change to disconnected."""
        mock_account = Mock()
        with patch("pjsua_bot.calls.out_call.pj.Call.__init__"):
            call = OutCall(mock_account)
            call.getId = Mock(return_value=123)  # Mock getId
            call._player = Mock()  # Set a player

            mock_info = Mock()
            mock_info.state = 5  # PJSIP_INV_STATE_DISCONNECTED
            mock_info.stateText = "DISCONNECTED"
            mock_info.lastStatusCode = 200

            with patch.object(call, "getInfo", return_value=mock_info):
                with patch("pjsua_bot.calls.out_call.pj") as mock_pj:
                    mock_pj.PJSIP_INV_STATE_CONFIRMED = 4
                    mock_pj.PJSIP_INV_STATE_DISCONNECTED = 5

                    with patch("builtins.print"):  # Suppress print output
                        call.onCallState(Mock())

                        assert call.connected is False
                        assert call._player is None

    def test_on_call_media_state_with_play_file(self) -> None:
        """Test call media state with play file configured."""
        mock_account = Mock()
        mock_account.play_file = "/path/to/audio.wav"
        with patch("pjsua_bot.calls.out_call.pj.Call.__init__"):
            call = OutCall(mock_account)
            call.getId = Mock(return_value=123)  # Mock getId

            mock_info = Mock()
            mock_media = Mock()
            mock_media.type = 0  # PJMEDIA_TYPE_AUDIO
            mock_media.status = 1  # PJSUA_CALL_MEDIA_ACTIVE
            mock_media.index = 0
            mock_info.media = [mock_media]

            mock_audio_media = Mock()
            mock_endpoint = Mock()
            mock_adm = Mock()
            mock_playback = Mock()

            with patch.object(call, "getInfo", return_value=mock_info):
                with patch.object(call, "getAudioMedia", return_value=mock_audio_media):
                    with patch("pjsua_bot.calls.out_call.pj") as mock_pj:
                        mock_pj.PJMEDIA_TYPE_AUDIO = 0
                        mock_pj.PJSUA_CALL_MEDIA_ACTIVE = 1
                        mock_pj.Endpoint.instance.return_value = mock_endpoint
                        mock_endpoint.audDevManager.return_value = mock_adm
                        mock_adm.getPlaybackDevMedia.return_value = mock_playback

                        mock_player = Mock()
                        with patch(
                            "pjsua_bot.calls.out_call.pj.AudioMediaPlayer",
                            return_value=mock_player,
                        ):
                            with patch("builtins.print"):  # Suppress print output
                                call.onCallMediaState(Mock())

                                mock_player.createPlayer.assert_called_once()
                                mock_player.startTransmit.assert_called()
                                assert call._player == mock_player

                                # Check events
                                assert len(call._collected_events) >= 1
                                event_types = [
                                    e["event_type"] for e in call._collected_events
                                ]
                                assert "media_active" in event_types
                                assert "playback_started" in event_types

    def test_on_call_media_state_without_play_file(self) -> None:
        """Test call media state without play file (bridge audio)."""
        mock_account = Mock()
        mock_account.play_file = None
        with patch("pjsua_bot.calls.out_call.pj.Call.__init__"):
            call = OutCall(mock_account)
            call.getId = Mock(return_value=123)  # Mock getId

            mock_info = Mock()
            mock_media = Mock()
            mock_media.type = 0  # PJMEDIA_TYPE_AUDIO
            mock_media.status = 1  # PJSUA_CALL_MEDIA_ACTIVE
            mock_media.index = 0
            mock_info.media = [mock_media]

            mock_audio_media = Mock()
            mock_endpoint = Mock()
            mock_adm = Mock()
            mock_playback = Mock()
            mock_capture = Mock()

            with patch.object(call, "getInfo", return_value=mock_info):
                with patch.object(call, "getAudioMedia", return_value=mock_audio_media):
                    with patch("pjsua_bot.calls.out_call.pj") as mock_pj:
                        mock_pj.PJMEDIA_TYPE_AUDIO = 0
                        mock_pj.PJSUA_CALL_MEDIA_ACTIVE = 1
                        mock_pj.Endpoint.instance.return_value = mock_endpoint
                        mock_endpoint.audDevManager.return_value = mock_adm
                        mock_adm.getPlaybackDevMedia.return_value = mock_playback
                        mock_adm.getCaptureDevMedia.return_value = mock_capture

                        with patch("builtins.print"):  # Suppress print output
                            call.onCallMediaState(Mock())

                            mock_audio_media.startTransmit.assert_called()
                            mock_capture.startTransmit.assert_called()

                            # Check events
                            assert len(call._collected_events) >= 1
                            event_types = [
                                e["event_type"] for e in call._collected_events
                            ]
                            assert "media_active" in event_types
                            assert "audio_bridged" in event_types

    def test_on_call_media_state_player_error(self) -> None:
        """Test call media state when player creation fails."""
        mock_account = Mock()
        mock_account.play_file = "/path/to/audio.wav"
        with patch("pjsua_bot.calls.out_call.pj.Call.__init__"):
            call = OutCall(mock_account)
            call.getId = Mock(return_value=123)  # Mock getId

            mock_info = Mock()
            mock_media = Mock()
            mock_media.type = 0  # PJMEDIA_TYPE_AUDIO
            mock_media.status = 1  # PJSUA_CALL_MEDIA_ACTIVE
            mock_media.index = 0
            mock_info.media = [mock_media]

            mock_audio_media = Mock()
            mock_endpoint = Mock()
            mock_adm = Mock()
            mock_playback = Mock()

            with patch.object(call, "getInfo", return_value=mock_info):
                with patch.object(call, "getAudioMedia", return_value=mock_audio_media):
                    with patch("pjsua_bot.calls.out_call.pj") as mock_pj:
                        mock_pj.PJMEDIA_TYPE_AUDIO = 0
                        mock_pj.PJSUA_CALL_MEDIA_ACTIVE = 1
                        mock_pj.Endpoint.instance.return_value = mock_endpoint
                        mock_endpoint.audDevManager.return_value = mock_adm
                        mock_adm.getPlaybackDevMedia.return_value = mock_playback

                        with patch(
                            "pjsua_bot.calls.out_call.pj.AudioMediaPlayer"
                        ) as mock_player_class:
                            mock_player_class.side_effect = Exception("Player error")
                            with patch("builtins.print"):  # Suppress print output
                                call.onCallMediaState(Mock())

                                # Should collect error event
                                assert len(call._collected_events) >= 1
                                event_types = [
                                    e["event_type"] for e in call._collected_events
                                ]
                                assert "media_error" in event_types

    def test_on_call_media_state_media_error(self) -> None:
        """Test call media state when media handling fails."""
        mock_account = Mock()
        with patch("pjsua_bot.calls.out_call.pj.Call.__init__"):
            call = OutCall(mock_account)
            call.getId = Mock(return_value=123)  # Mock getId

            mock_info = Mock()
            mock_media = Mock()
            mock_media.type = 0  # PJMEDIA_TYPE_AUDIO
            mock_media.status = 1  # PJSUA_CALL_MEDIA_ACTIVE
            mock_media.index = 0
            mock_info.media = [mock_media]

            with patch.object(call, "getInfo", return_value=mock_info):
                with patch.object(call, "getAudioMedia", side_effect=Exception("Error")):
                    with patch("pjsua_bot.calls.out_call.pj") as mock_pj:
                        mock_pj.PJMEDIA_TYPE_AUDIO = 0
                        mock_pj.PJSUA_CALL_MEDIA_ACTIVE = 1

                        with patch("builtins.print"):  # Suppress print output
                            call.onCallMediaState(Mock())

                            # Should collect error event
                            assert len(call._collected_events) >= 1
                            event_types = [
                                e["event_type"] for e in call._collected_events
                            ]
                            assert "media_error" in event_types

