"""Tests for mwe_register module."""

from unittest.mock import Mock, patch

from pjsua_bot import mwe_register


class TestMweRegister:
    """Test cases for mwe_register module."""

    def test_pump_handles_exception(self) -> None:
        """Test that pump function handles exceptions gracefully."""
        mock_ep = Mock()
        mock_ep.libHandleEvents = Mock(side_effect=Exception("Event error"))

        # Should not raise, just print error
        mwe_register.pump(mock_ep)
        mock_ep.libHandleEvents.assert_called_once_with(50)

    def test_pump_success(self) -> None:
        """Test that pump function calls libHandleEvents."""
        mock_ep = Mock()
        mwe_register.pump(mock_ep)
        mock_ep.libHandleEvents.assert_called_once_with(50)

    @patch("pjsua_bot.mwe_register.pj")
    def test_main_creates_endpoint(self, mock_pj) -> None:
        """Test that main function creates endpoint."""
        mock_ep = Mock()
        mock_pj.Endpoint.return_value = mock_ep
        mock_ep_cfg = Mock()
        mock_pj.EpConfig.return_value = mock_ep_cfg
        mock_tp = Mock()
        mock_pj.TransportConfig.return_value = mock_tp
        mock_acfg = Mock()
        mock_pj.AccountConfig.return_value = mock_acfg
        mock_auth_cred = Mock()
        mock_pj.AuthCredInfo.return_value = mock_auth_cred

        # Mock account
        mock_acc = Mock()
        mock_acc.getInfo.return_value.regIsActive = True
        mock_acc.getInfo.return_value.regStatus = 200

        with patch("pjsua_bot.mwe_register.argparse.ArgumentParser") as mock_parser:
            mock_args = Mock()
            mock_args.user = "test_user"
            mock_args.password = "test_pass"
            mock_args.domain = "test.com"
            mock_args.auth_user = None
            mock_args.transport = "udp"
            mock_args.local_port = 5070
            mock_args.wait = 1  # Short wait for testing
            mock_parser.return_value.parse_args.return_value = mock_args

            with patch("pjsua_bot.mwe_register.Acc", return_value=mock_acc):
                with patch("pjsua_bot.mwe_register.time.time", side_effect=[0, 2, 3]):
                    # Should complete without error
                    try:
                        mwe_register.main()
                    except SystemExit:
                        pass  # May exit after completion

        mock_ep.libCreate.assert_called_once()
        mock_ep.libInit.assert_called_once()
        mock_ep.transportCreate.assert_called_once()
        mock_ep.libStart.assert_called_once()
