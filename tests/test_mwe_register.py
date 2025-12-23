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
    def test_main_creates_endpoint(self, mock_pj: Mock) -> None:
        """Test that main function creates endpoint."""
        mock_ep = Mock()
        mock_pj.Endpoint.return_value = mock_ep
        mock_ep_cfg = Mock()
        mock_pj.EpConfig.return_value = mock_ep_cfg
        mock_tp = Mock()
        mock_pj.TransportConfig.return_value = mock_tp
        mock_acfg = Mock()
        mock_pj.AccountConfig.return_value = mock_acfg
        mock_acfg.sipConfig.authCreds = []
        mock_auth_cred = Mock()
        mock_pj.AuthCredInfo.return_value = mock_auth_cred

        # Mock transport types
        mock_pj.PJSIP_TRANSPORT_UDP = 1

        # Mock account - Account class is used via pj.Account in main()
        # Create a plain object using SimpleNamespace to keep regStatus integer
        from types import SimpleNamespace

        mock_info = SimpleNamespace()
        mock_info.regIsActive = True
        mock_info.regStatus = 200  # Ensure this is an actual integer

        # Create account instance with getInfo method that returns our mock_info
        mock_acc_instance = Mock()
        # Use return_value to ensure getInfo() always returns the same mock_info object
        mock_acc_instance.getInfo = Mock(return_value=mock_info)
        mock_pj.Account = Mock(return_value=mock_acc_instance)

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

            # Mock time to simulate quick registration
            with patch(
                "pjsua_bot.mwe_register.time.time",
                side_effect=[0, 0.5, 1.5, 2, 3, 4, 5, 6, 7, 8],
            ):
                # Should complete without error
                try:
                    mwe_register.main()
                except SystemExit:
                    pass  # May exit after completion

        mock_ep.libCreate.assert_called_once()
        mock_ep.libInit.assert_called_once()
        mock_ep.transportCreate.assert_called_once()
        mock_ep.libStart.assert_called_once()
