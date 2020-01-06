"""Hermes MQTT server for Rhasspy TTS using external program"""
import io
import logging
import shlex
import subprocess
import threading
import time
import wave

from rhasspyhermes.audioserver import AudioFrame

_LOGGER = logging.getLogger(__name__)


class MicrophoneHermesMqtt:
    """Hermes MQTT server for Rhasspy microphone input using external program."""

    def __init__(
        self,
        client,
        record_command: str,
        sample_rate: int,
        sample_width: int,
        channels: int,
        chunk_size: int = 2048,
        siteId: str = "default",
    ):
        self.client = client
        self.record_command = record_command
        self.sample_rate = sample_rate
        self.sample_width = sample_width
        self.channels = channels
        self.chunk_size = chunk_size
        self.siteId = siteId

        self.audioframe_topic: str = AudioFrame.topic(siteId=self.siteId)

    # -------------------------------------------------------------------------

    def record(self):
        """Record audio from external program's stdout."""
        try:
            record_command = shlex.split(self.record_command)
            _LOGGER.debug(record_command)

            record_proc = subprocess.Popen(record_command, stdout=subprocess.PIPE)
            _LOGGER.debug("Recording audio")

            while True:
                chunk = record_proc.stdout.read(self.chunk_size)
                if chunk:
                    with io.BytesIO() as wav_buffer:
                        wav_file: wave.Wave_write = wave.open(wav_buffer, "wb")
                        with wav_file:
                            wav_file.setframerate(self.sample_rate)
                            wav_file.setsampwidth(self.sample_width)
                            wav_file.setnchannels(self.channels)
                            wav_file.writeframes(chunk)

                        # Publish to audioFrame topic
                        self.client.publish(
                            self.audioframe_topic, wav_buffer.getvalue()
                        )
                else:
                    # Avoid 100% CPU usage
                    time.sleep(0.01)
        except Exception:
            _LOGGER.exception("record")

    # -------------------------------------------------------------------------

    def on_connect(self, client, userdata, flags, rc):
        """Connected to MQTT broker."""
        try:
            threading.Thread(target=self.record, daemon=True).start()
        except Exception:
            _LOGGER.exception("on_connect")
