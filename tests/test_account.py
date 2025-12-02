"""Tests for Account class."""

from unittest.mock import Mock, patch

from pjsua_bot.account import Account


class TestAccount:
    """Test cases for Account class."""

    def test_init_default_values(self) -> None:
        """Test Account initialization with default values."""
        with patch("pjsua_bot.account.pj.Account.__init__"):
            account = Account()
            assert account.auto_answer is False
            assert account.calls == {}
            assert account.play_file is None
            assert account.goodbye_file is None
            assert account.waiting_file is None
            assert account._collected_events == []
            assert account._asr_service is None
            assert account._asr_available is False
            assert account.enable_intent is False
            assert account._intent_classifier is None

    def test_collect_event(self) -> None:
        """Test event collection."""
        with patch("pjsua_bot.account.pj.Account.__init__"):
            account = Account()
            account._collect_event("test_event", key1="value1", key2="value2")

            assert len(account._collected_events) == 1
            event = account._collected_events[0]
            assert event["event_type"] == "test_event"
            assert event["key1"] == "value1"
            assert event["key2"] == "value2"
            assert "call_id" in event
            assert "@timestamp" in event

    def test_on_reg_state_success(self) -> None:
        """Test registration state change on success."""
        with patch("pjsua_bot.account.pj.Account.__init__"):
            account = Account()
            account.username = "test_user"
            account.domain = "test_domain"

            mock_info = Mock()
            mock_info.regIsActive = True
            mock_info.regStatus = 200

            mock_prm = Mock()
            mock_prm.reason = "OK"

            with patch.object(account, "getInfo", return_value=mock_info):
                with patch("builtins.print"):  # Suppress print output
                    account.onRegState(mock_prm)

                    assert len(account._collected_events) == 1
                    event = account._collected_events[0]
                    assert event["event_type"] == "registration_success"
                    assert event["code"] == 200
                    assert event["active"] is True

    def test_on_reg_state_failure(self) -> None:
        """Test registration state change on failure."""
        with patch("pjsua_bot.account.pj.Account.__init__"):
            account = Account()
            account.username = "test_user"
            account.domain = "test_domain"

            mock_info = Mock()
            mock_info.regIsActive = False
            mock_info.regStatus = 401

            mock_prm = Mock()
            mock_prm.reason = "Unauthorized"

            with patch.object(account, "getInfo", return_value=mock_info):
                with patch("builtins.print"):  # Suppress print output
                    account.onRegState(mock_prm)

                    assert len(account._collected_events) == 1
                    event = account._collected_events[0]
                    assert event["event_type"] == "registration_failed"
                    assert event["code"] == 401
                    assert event["active"] is False

    def test_on_incoming_call_auto_answer(self) -> None:
        """Test incoming call with auto-answer enabled."""
        with patch("pjsua_bot.account.pj.Account.__init__"):
            account = Account()
            account.auto_answer = True

            mock_call = Mock()
            mock_call_info = Mock()
            mock_call_info.remoteUri = "sip:1001@host"
            mock_call.getInfo.return_value = mock_call_info
            mock_call._caller_number = None

            mock_prm = Mock()
            mock_prm.callId = 123

            with patch("pjsua_bot.calls.AnyCall", return_value=mock_call):
                with patch("pjsua_bot.account.pj.CallOpParam"):
                    with patch("builtins.print"):  # Suppress print output
                        account.onIncomingCall(mock_prm)

                        assert 123 in account.calls
                        assert account.calls[123] == mock_call
                        mock_call.answer.assert_called_once()

                        # Check events
                        assert len(account._collected_events) >= 1
                        event_types = [
                            e["event_type"] for e in account._collected_events
                        ]
                        assert "incoming_call" in event_types
                        assert "call_answered" in event_types

    def test_on_incoming_call_no_auto_answer(self) -> None:
        """Test incoming call without auto-answer."""
        with patch("pjsua_bot.account.pj.Account.__init__"):
            account = Account()
            account.auto_answer = False

            mock_call = Mock()
            mock_call_info = Mock()
            mock_call_info.remoteUri = "sip:1001@host"
            mock_call.getInfo.return_value = mock_call_info
            mock_call._caller_number = None

            mock_prm = Mock()
            mock_prm.callId = 456

            with patch("pjsua_bot.calls.AnyCall", return_value=mock_call):
                with patch("pjsua_bot.account.pj.CallOpParam"):
                    with patch("builtins.print"):  # Suppress print output
                        account.onIncomingCall(mock_prm)

                        assert 456 in account.calls
                        mock_call.answer.assert_called_once()

                        # Check events
                        assert len(account._collected_events) >= 1
                        event_types = [
                            e["event_type"] for e in account._collected_events
                        ]
                        assert "incoming_call" in event_types
                        assert "call_ringing" in event_types

    def test_on_incoming_call_parse_error(self) -> None:
        """Test incoming call when caller info parsing fails."""
        with patch("pjsua_bot.account.pj.Account.__init__"):
            account = Account()
            account.auto_answer = False

            mock_call = Mock()
            mock_call.getInfo.side_effect = Exception("Parse error")
            mock_call._caller_number = None

            mock_prm = Mock()
            mock_prm.callId = 789

            with patch("pjsua_bot.calls.AnyCall", return_value=mock_call):
                with patch("pjsua_bot.account.pj.CallOpParam"):
                    with patch("builtins.print"):  # Suppress print output
                        account.onIncomingCall(mock_prm)

                        assert 789 in account.calls
                        assert mock_call._caller_number == "unknown"

    def test_on_incoming_call_exception(self) -> None:
        """Test incoming call when exception occurs."""
        with patch("pjsua_bot.account.pj.Account.__init__"):
            account = Account()

            mock_prm = Mock()
            mock_prm.callId = 999

            with patch("pjsua_bot.calls.AnyCall", side_effect=Exception("Call error")):
                with patch("builtins.print"):  # Suppress print output
                    account.onIncomingCall(mock_prm)

                    # Should collect error event
                    assert len(account._collected_events) >= 1
                    event_types = [e["event_type"] for e in account._collected_events]
                    assert "call_error" in event_types
