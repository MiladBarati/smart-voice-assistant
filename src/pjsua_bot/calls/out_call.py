"""Outbound call handler with media playback support."""

from datetime import datetime
from typing import TYPE_CHECKING, Any

try:
    import pjsua2 as pj  # pragma: no cover - depends on runtime env
except ModuleNotFoundError:  # pragma: no cover - depends on runtime env
    pj = None

if TYPE_CHECKING:

    class BaseCall(pj.Call): ...

elif pj is not None:
    BaseCall = pj.Call
else:

    class BaseCall(object):
        pass


class OutCall(BaseCall):
    """Outbound call handler with media playback support."""

    def __init__(self, acc: Any):
        if pj is None:
            raise RuntimeError(
                "pjsua2 is required to use OutCall. "
                "Install/build pjsua2 bindings or run without SIP features."
            )
        super().__init__(acc)
        self.connected = False
        self._acc_ref = acc
        self._player = None
        # Batch logging - collect events during call
        self._collected_events: list[dict[str, Any]] = []

    def _collect_event(self, event_type: str, **kwargs: Any) -> None:
        """Collect an event for batch logging at the end of the call."""
        event = {
            "event_type": event_type,
            "@timestamp": datetime.utcnow().isoformat() + "Z",
            "call_id": str(self.getId()) if hasattr(self, "getId") else "unknown",
            **kwargs,
        }
        self._collected_events.append(event)

    def onCallState(self, prm: Any) -> None:  # noqa: N802 - PJSUA2 callback name
        """Handle call state changes."""
        ci = self.getInfo()
        print(f"***CallState: state={ci.stateText} code={ci.lastStatusCode}")

        # Collect call state change event
        self._collect_event(
            event_type="call_state_change",
            call_state=ci.stateText,
            call_code=ci.lastStatusCode,
            state=ci.state,
            state_text=ci.stateText,
            last_status_code=ci.lastStatusCode,
        )

        if ci.state == pj.PJSIP_INV_STATE_CONFIRMED:
            self.connected = True
        if ci.state == pj.PJSIP_INV_STATE_DISCONNECTED:
            self.connected = False

            # drop player reference so it can be cleaned up
            self._player = None

    def onCallMediaState(self, prm: Any) -> None:  # noqa: N802 - PJSUA2 callback name
        """Handle call media state changes."""
        ci = self.getInfo()
        for mi in ci.media:
            if (
                mi.type == pj.PJMEDIA_TYPE_AUDIO
                and mi.status == pj.PJSUA_CALL_MEDIA_ACTIVE
            ):
                try:
                    # Collect media active event
                    self._collect_event(
                        event_type="media_active",
                        media_type="audio",
                        media_status="active",
                    )

                    call_media = self.getAudioMedia(mi.index)
                    adm = pj.Endpoint.instance().audDevManager()
                    playback = adm.getPlaybackDevMedia()
                    # If a play file is configured, play it to the remote side
                    if getattr(self._acc_ref, "play_file", None):
                        try:
                            player = pj.AudioMediaPlayer()
                            # Create player with PJMEDIA_FILE_NO_LOOP to play only once
                            player.createPlayer(
                                self._acc_ref.play_file, pj.PJMEDIA_FILE_NO_LOOP
                            )
                            player.startTransmit(call_media)  # file -> remote
                            call_media.startTransmit(
                                playback
                            )  # remote -> local speakers (monitor)
                            print(
                                (
                                    "***Media: playing file to remote: "
                                    f"{self._acc_ref.play_file}"
                                )
                            )
                            self._player = player

                            # Collect playback started event
                            self._collect_event(
                                event_type="playback_started",
                                media_type="audio",
                                file_played=self._acc_ref.play_file,
                            )
                        except Exception as e:
                            print(f"***Media player error: {e}")
                            # Collect media error event
                            self._collect_event(
                                event_type="media_error",
                                media_type="audio",
                                error=str(e),
                            )
                    else:
                        capture = adm.getCaptureDevMedia()
                        # Bridge call <-> sound device
                        call_media.startTransmit(playback)  # remote -> speakers
                        capture.startTransmit(call_media)  # mic -> remote
                        print("***Media: audio bridged to sound device")

                        # Collect audio bridge event
                        self._collect_event(
                            event_type="audio_bridged",
                            media_type="audio",
                            media_status="bridged",
                        )
                except Exception as e:
                    print(f"***Media error: {e}")
                    # Collect media error event
                    self._collect_event(
                        event_type="media_error", media_type="audio", error=str(e)
                    )
