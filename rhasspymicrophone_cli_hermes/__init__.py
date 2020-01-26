"""Hermes MQTT server for Rhasspy TTS using external program"""
import io
import json
import logging
import re
import subprocess
import threading
import time
import typing
import wave

import attr
from rhasspyhermes.audioserver import (
    AudioDevice,
    AudioDeviceMode,
    AudioDevices,
    AudioFrame,
    AudioGetDevices,
)
from rhasspyhermes.base import Message

_LOGGER = logging.getLogger(__name__)


class MicrophoneHermesMqtt:
    """Hermes MQTT server for Rhasspy microphone input using external program."""

    def __init__(
        self,
        client,
        record_command: typing.List[str],
        sample_rate: int,
        sample_width: int,
        channels: int,
        chunk_size: int = 2048,
        list_command: typing.Optional[typing.List[str]] = None,
        siteId: str = "default",
    ):
        self.client = client
        self.record_command = record_command
        self.sample_rate = sample_rate
        self.sample_width = sample_width
        self.channels = channels
        self.chunk_size = chunk_size
        self.list_command = list_command
        self.siteId = siteId

        self.audioframe_topic: str = AudioFrame.topic(siteId=self.siteId)
        self.test_audio_buffer: typing.Optional[bytes] = None

    # -------------------------------------------------------------------------

    def record(self):
        """Record audio from external program's stdout."""
        try:
            _LOGGER.debug(self.record_command)

            record_proc = subprocess.Popen(self.record_command, stdout=subprocess.PIPE)
            _LOGGER.debug("Recording audio")

            while True:
                chunk = record_proc.stdout.read(self.chunk_size)
                if chunk:
                    if self.test_audio_buffer:
                        # Add to buffer for microphone test
                        self.test_audio_buffer += chunk

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

    def handle_get_devices(self, get_devices: AudioGetDevices) -> AudioDevices:
        """Get available microphones and optionally test them."""
        devices: typing.List[AudioDevice] = []

        if self.list_command:
            try:
                # Run list command
                _LOGGER.debug(self.list_command)

                output = subprocess.check_output(
                    self.list_command, universal_newlines=True
                ).splitlines()

                # Parse output (assume like arecord -L)
                name, description = None, None
                first_mic = True
                for line in output:
                    line = line.rstrip()
                    if re.match(r"^\s", line):
                        description = line.strip()
                        if first_mic:
                            description = description + "*"
                            first_mic = False
                    else:
                        if name is not None:
                            devices.append(
                                AudioDevice(
                                    mode=AudioDeviceMode.INPUT,
                                    id=name,
                                    name=name,
                                    description=description,
                                )
                            )

                        name = line.strip()
            except Exception:
                _LOGGER.exception("handle_get_devices")
        else:
            _LOGGER.warning("No device list command. Cannot list microphones.")

        return AudioDevices(
            devices=devices, id=get_devices.id, siteId=get_devices.siteId
        )

    # -------------------------------------------------------------------------

    def on_message(self, client, userdata, msg):
        """Received message from MQTT broker."""
        try:
            _LOGGER.debug("Received %s byte(s) on %s", len(msg.payload), msg.topic)

            if msg.topic == AudioGetDevices.topic():
                json_payload = json.loads(msg.payload)
                if self._check_siteId(json_payload):
                    result = self.handle_get_devices(
                        AudioGetDevices.from_dict(json_payload)
                    )
                    self.publish(result)
        except Exception:
            _LOGGER.exception("on_message")

    def on_connect(self, client, userdata, flags, rc):
        """Connected to MQTT broker."""
        try:
            threading.Thread(target=self.record, daemon=True).start()
        except Exception:
            _LOGGER.exception("on_connect")

    def publish(self, message: Message, **topic_args):
        """Publish a Hermes message to MQTT."""
        try:
            assert self.client
            topic = message.topic(**topic_args)

            _LOGGER.debug("-> %s", message)
            payload: typing.Union[str, bytes] = json.dumps(attr.asdict(message))

            _LOGGER.debug("Publishing %s char(s) to %s", len(payload), topic)
            self.client.publish(topic, payload)
        except Exception:
            _LOGGER.exception("on_message")

    def _check_siteId(self, json_payload: typing.Dict[str, typing.Any]) -> bool:
        return json_payload.get("siteId", "default") == self.siteId

    # -------------------------------------------------------------------------
